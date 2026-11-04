#!/usr/bin/env python3
"""scout_settings.py - resolve topic-scout settings from the request, the profile and defaults.

  scout_settings.py --request "TEXT" [--profile DIR] [--cwd DIR] [--today YYYY-MM-DD] [--json]

Prints a short settings card (or JSON). Each value says where it came from: the request,
the profile, or the default. The same request always yields the same settings.

Resolved values
  level      high | medium | low        how much the scout draws on the researcher's own material
  depth      quick | standard | full    quick: candidates only; standard: gate the top 1 in light
                                         mode; full: gate the top 3 in full mode
  finalists  number of candidates sent to novelty-gate (from depth unless given)
  corpus     paths to the researcher's material (never used at level low)
  direction  field or direction named in the request, if any
  cutoff     literature cutoff date
  out_dir    output directory
  profile    profile directory and whether it was found

Request phrases that are recognised (English and Korean), for example:
  level high   : "level: high", "based on my code", "my paper", "follow-up", "내 코드", "내 논문", "후속"
  level low    : "level: low", "exploratory", "broadly", "just the field", "탐색적", "넓게", "분야만"
  depth quick  : "depth: quick", "quick", "candidates only", "빠르게", "후보만", "간단히"
  depth full   : "depth: full", "thorough", "in depth", "꼼꼼", "자세히", "깊게"
  direction    : "field: medical imaging", "분야는 의료영상"
  cutoff       : "cutoff 2026-01-31", "기준일 2026-01-31"
  out_dir      : "out: ./my-scout"
  corpus paths : any existing path in the request, such as ./my-project or ~/papers
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

LEVELS = ("high", "medium", "low")
DEPTHS = ("quick", "standard", "full")
FINALISTS = {"quick": 0, "standard": 1, "full": 3}
GATE_MODE = {"quick": "none", "standard": "light", "full": "full"}
LEVEL_WORDS = {
    "high": ["based on my", "from my", "my code", "my paper", "my own", "my work", "my repo", "my project",
             "follow-up", "follow up", "내 코드", "내 논문", "내 자료", "내 연구", "내 프로젝트", "내 저장소",
             "기존 연구", "후속"],
    "low": ["exploratory", "explore broadly", "broadly", "just the field", "only the field", "loosely",
            "new area", "fresh area", "탐색적", "넓게", "분야만", "느낌만", "느낌 정도", "새로운 분야", "새 분야"],
}
DEPTH_WORDS = {
    "quick": ["quick", "fast", "candidates only", "just ideas", "no gate", "빠르게", "빨리", "후보만", "간단히", "가볍게"],
    "full": ["thorough", "deep dive", "in depth", "in-depth", "full review", "꼼꼼", "자세히", "깊게", "철저"],
}
LEVEL_ALIASES = {"high": "high", "medium": "medium", "mid": "medium", "low": "low",
                 "높": "high", "중": "medium", "중간": "medium", "낮": "low"}
RESEARCH_EXT = {".tex", ".py", ".ipynb", ".pdf", ".bib"}


def find_profile(explicit, cwd, env):
    for cand, src in ((explicit, "request"), (env.get("RESEARCH_PROFILE_DIR"), "RESEARCH_PROFILE_DIR"),
                      (os.path.join(cwd, "research-profile"), "./research-profile"),
                      (os.path.expanduser("~/research-profile"), "~/research-profile")):
        if cand and os.path.isfile(os.path.join(os.path.expanduser(cand), "profile.md")):
            return os.path.abspath(os.path.expanduser(cand)), src
    return None, None


def load_constants(profile_dir):
    with open(os.path.join(profile_dir, "profile.md"), encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r"```json\s+profile\s*\n(.*?)```", text, re.S)
    if not m:
        raise ValueError("profile.md has no ```json profile block")
    return json.loads(m.group(1))


def match_words(text, table):
    low = text.lower()
    return sorted({k for k, words in table.items() if any(w in low for w in words)})


def resolve_level(req, prof, notes):
    m = re.search(r"(?:level|레벨)\s*[:=]?\s*(high|medium|mid|low|중간|높|중|낮)", req, re.I)
    if m:
        return LEVEL_ALIASES[m.group(1).lower()], "request (explicit)"
    hits = match_words(req, LEVEL_WORDS)
    if len(hits) == 1:
        return hits[0], "request (phrase)"
    if len(hits) > 1:
        notes.append("request mentions both own-material and exploratory phrases; using the default level")
    v = prof.get("scout_level")
    if v in LEVELS:
        return v, "profile"
    if v is not None:
        notes.append(f"profile scout_level {v!r} is not one of {LEVELS}; ignored")
    return "medium", "default"


def resolve_depth(req, prof, notes):
    m = re.search(r"(?:depth|깊이)\s*[:=]?\s*(quick|standard|full)", req, re.I)
    if m:
        return m.group(1).lower(), "request (explicit)"
    hits = match_words(req, DEPTH_WORDS)
    if len(hits) == 1:
        return hits[0], "request (phrase)"
    if len(hits) > 1:
        notes.append("request mentions both quick and thorough; using the default depth")
    v = prof.get("scout_depth")
    if v in DEPTHS:
        return v, "profile"
    if v is not None:
        notes.append(f"profile scout_depth {v!r} is not one of {DEPTHS}; ignored")
    return "standard", "default"


def request_paths(req, cwd):
    found, missing = [], []
    for tok in re.findall(r"(?:^|[\s(\"'])((?:~|\.{1,2})?/[^\s,;)\"']+)", req):
        p = os.path.abspath(os.path.join(cwd, os.path.expanduser(tok)))
        (found if os.path.exists(p) else missing).append(p)
    return found, missing


def looks_like_research_dir(path):
    """One-level look at file names only; never used for the home directory or the filesystem root."""
    try:
        names = os.listdir(path)
    except OSError:
        return False
    hits = sum(1 for n in names if os.path.splitext(n)[1].lower() in RESEARCH_EXT)
    return ".git" in names or hits >= 2


OUT_RE = re.compile(r"(?:\bout(?:put)?|출력)\s*[:=]\s*(\S+)", re.I)


def resolve_corpus(level, req, prof, cwd, notes, out_dir):
    paths, missing = request_paths(OUT_RE.sub(" ", req), cwd)
    for p in missing:
        notes.append(f"path in the request not found: {p}")
    if level == "low":
        if paths or prof.get("corpus_paths"):
            notes.append("level low: the corpus is not read, even if paths are given")
        return [], "not used (level low)"
    if paths:
        return paths, "request"
    prof_paths = [os.path.abspath(os.path.expanduser(p)) for p in prof.get("corpus_paths") or []]
    if prof_paths:
        ok = [p for p in prof_paths if os.path.exists(p)]
        for p in set(prof_paths) - set(ok):
            notes.append(f"profile corpus path not found: {p}")
        if ok:
            return ok, "profile"
    home = os.path.abspath(os.path.expanduser("~"))
    here = os.path.abspath(cwd)
    if here not in (home, os.path.sep) and looks_like_research_dir(here):
        return [here], "working directory (auto)"
    notes.append("no corpus found; ask for a path or switch to level low")
    return [], "none"


def resolve(request, profile=None, cwd=None, today=None, env=None):
    cwd = cwd or os.getcwd()
    env = os.environ if env is None else env
    today = today or dt.date.today().isoformat()
    notes = []
    pdir, psrc = find_profile(profile, cwd, env)
    prof, pstatus = {}, "missing"
    if pdir:
        try:
            prof, pstatus = load_constants(pdir), "found"
        except (ValueError, json.JSONDecodeError) as e:
            pstatus = "invalid"
            notes.append(f"profile could not be read: {e}")
    else:
        notes.append("no profile found: run the onboarding (references/onboarding.md) before scouting")

    level, lsrc = resolve_level(request, prof, notes)
    depth, dsrc = resolve_depth(request, prof, notes)
    m = re.search(r"(?:finalists|gate)\s*[:=]\s*(\d+)", request, re.I)
    finalists, fsrc = (int(m.group(1)), "request") if m else (FINALISTS[depth], f"depth {depth}")
    m = re.search(r"(?:cutoff|기준일)\s*[:=]?\s*(\d{4}-\d{2}-\d{2})", request, re.I)
    cutoff, csrc = (m.group(1), "request") if m else (today, "default (today)")
    m = OUT_RE.search(request)
    home = os.path.abspath(os.path.expanduser("~"))
    if m:
        out_dir, osrc = os.path.abspath(os.path.join(cwd, os.path.expanduser(m.group(1).rstrip(".,;)")))), "request"
    elif os.path.abspath(cwd) in (home, os.path.sep) and pdir:
        out_dir, osrc = os.path.join(pdir, "runs", f"scout-{today}-{level}"), "default (profile runs/)"
    else:
        out_dir, osrc = os.path.abspath(os.path.join(cwd, f"scout-{today}-{level}")), "default"
    m = re.search(r"(?:\b(?:field|area|direction)\s*(?:is|:|=)\s*|분야\s*(?:는|은|:|=)\s*)([^,.;\n]+)", request, re.I)
    direction = m.group(1).strip() if m else None
    corpus, corsrc = resolve_corpus(level, request, prof, cwd, notes, out_dir)
    if level != "low" and not corpus and prof.get("interests"):
        notes.append("without a corpus, own-material candidates come from the profile prose and the ledger only")
    return {
        "profile": {"dir": pdir, "status": pstatus, "source": psrc},
        "level": {"value": level, "source": lsrc},
        "depth": {"value": depth, "source": dsrc},
        "finalists": {"value": finalists, "source": fsrc},
        "gate_mode": GATE_MODE[depth] if finalists else "none",
        "corpus": {"paths": corpus, "source": corsrc},
        "direction": direction,
        "cutoff": {"value": cutoff, "source": csrc},
        "out_dir": {"value": out_dir, "source": osrc},
        "notes": notes,
    }


def card(s):
    c = s["corpus"]
    lines = [
        f"level: {s['level']['value']} ({s['level']['source']}) · depth: {s['depth']['value']} ({s['depth']['source']})"
        + (f" · gate: top {s['finalists']['value']}, {s['gate_mode']} mode" if s["finalists"]["value"]
           else " · gate: none (the user picks what to gate)"),
        "corpus: " + (", ".join(c["paths"]) if c["paths"] else "-") + f" ({c['source']})",
        f"direction: {s['direction'] or '-'} · cutoff: {s['cutoff']['value']} · out: {s['out_dir']['value']}",
        f"profile: {s['profile']['dir'] or '-'} ({s['profile']['status']})",
    ]
    lines += [f"note: {n}" for n in s["notes"]]
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--request", required=True)
    p.add_argument("--profile")
    p.add_argument("--cwd")
    p.add_argument("--today")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    s = resolve(a.request, a.profile, a.cwd, a.today)
    print(json.dumps(s, ensure_ascii=False, indent=2) if a.json else card(s))
    return 0 if s["profile"]["status"] == "found" else 4


if __name__ == "__main__":
    sys.exit(main())
