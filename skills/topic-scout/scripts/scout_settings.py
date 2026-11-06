#!/usr/bin/env python3
"""scout_settings.py - resolve topic-scout settings from explicit flags, the profile and defaults.

  scout_settings.py [--level high|medium|low] [--depth quick|standard|full] [--gate N]
                    [--corpus PATH ...] [--field TEXT] [--cutoff YYYY-MM-DD] [--out DIR]
                    [--extra-language CODE|none] [--profile DIR] [--cwd DIR] [--today YYYY-MM-DD] [--json]

The agent maps the user's words to flags (by meaning, so "depth estimation" sets nothing);
this script only fills the gaps from the profile and the defaults, and prints a short card
in which each value says where it came from. Exit code 4 means no profile was found.

Resolved values
  level      high | medium | low        how much the scout draws on the researcher's own material
  depth      quick | standard | full    quick: candidates only; standard: gate the top 1 in light
                                         mode; full: gate the top 3 in full mode
  finalists  number of candidates sent to novelty-gate (from depth unless --gate)
  corpus     paths to the researcher's material (never used at level low)
  direction  field or direction, if given
  cutoff     literature cutoff date
  out_dir    output directory
  extra_language  extra human-report language (ISO 639-1) besides English, if any
  profile    profile directory and whether it was found
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


def looks_like_research_dir(path):
    """One-level look at file names only; never used for the home directory or the filesystem root."""
    try:
        names = os.listdir(path)
    except OSError:
        return False
    hits = sum(1 for n in names if os.path.splitext(n)[1].lower() in RESEARCH_EXT)
    return ".git" in names or hits >= 2


def pick(value, allowed, key, prof, default, notes):
    if value:
        return value, "request"
    v = prof.get(key)
    if v in allowed:
        return v, "profile"
    if v is not None:
        notes.append(f"profile {key} {v!r} is not one of {allowed}; ignored")
    return default, "default"


def resolve_language(value, prof, notes):
    if value:
        code = value.lower()
        return (None if code in ("en", "none") else code), "request"
    v = prof.get("extra_report_language")
    if v:
        return (None if v == "en" else v), "profile"
    legacy = prof.get("output_language")
    if legacy and legacy != "en":
        notes.append("profile key output_language is read as extra_report_language")
        return legacy, "profile (output_language)"
    return None, "default (English only)"


def resolve_corpus(level, given, prof, cwd, notes):
    given = [os.path.abspath(os.path.join(cwd, os.path.expanduser(p))) for p in given or []]
    found = [p for p in given if os.path.exists(p)]
    for p in sorted(set(given) - set(found)):
        notes.append(f"corpus path not found: {p}")
    if level == "low":
        if given or prof.get("corpus_paths"):
            notes.append("level low: the corpus is not read, even if paths are given")
        return [], "not used (level low)"
    if found:
        return found, "request"
    prof_paths = [os.path.abspath(os.path.expanduser(p)) for p in prof.get("corpus_paths") or []]
    if prof_paths:
        ok = [p for p in prof_paths if os.path.exists(p)]
        for p in sorted(set(prof_paths) - set(ok)):
            notes.append(f"profile corpus path not found: {p}")
        if ok:
            return ok, "profile"
    home = os.path.abspath(os.path.expanduser("~"))
    here = os.path.abspath(cwd)
    if here not in (home, os.path.sep) and looks_like_research_dir(here):
        return [here], "working directory (auto)"
    notes.append("no corpus found; ask for a path or switch to level low")
    return [], "none"


def resolve(level=None, depth=None, gate=None, corpus=None, field=None, cutoff=None, out=None,
            extra_language=None, profile=None, cwd=None, today=None, env=None):
    cwd = cwd or os.getcwd()
    env = os.environ if env is None else env
    today = today or dt.date.today().isoformat()
    notes = []
    pdir, psrc = find_profile(profile, cwd, env)
    if profile and psrc != "request":
        notes.append(f"profile not found at {profile}; " + (f"using {pdir}" if pdir else "none found"))
    prof, pstatus = {}, "missing"
    if pdir:
        try:
            prof, pstatus = load_constants(pdir), "found"
        except (ValueError, json.JSONDecodeError) as e:
            pstatus = "invalid"
            notes.append(f"profile could not be read: {e}")
    else:
        notes.append("no profile found: run the onboarding (references/onboarding.md) before scouting")

    level, lsrc = pick(level, LEVELS, "scout_level", prof, "medium", notes)
    depth, dsrc = pick(depth, DEPTHS, "scout_depth", prof, "standard", notes)
    finalists, fsrc = (gate, "request") if gate is not None else (FINALISTS[depth], f"depth {depth}")
    cutoff, csrc = (cutoff, "request") if cutoff else (today, "default (today)")
    home = os.path.abspath(os.path.expanduser("~"))
    if out:
        out_dir, osrc = os.path.abspath(os.path.join(cwd, os.path.expanduser(out))), "request"
    elif os.path.abspath(cwd) in (home, os.path.sep) and pdir:
        out_dir, osrc = os.path.join(pdir, "runs", f"scout-{today}-{level}"), "default (profile runs/)"
    else:
        out_dir, osrc = os.path.abspath(os.path.join(cwd, f"scout-{today}-{level}")), "default"
    corpus, corsrc = resolve_corpus(level, corpus, prof, cwd, notes)
    lang, langsrc = resolve_language(extra_language, prof, notes)
    if level != "low" and not corpus and prof.get("interests"):
        notes.append("without a corpus, own-material candidates come from the profile prose and the ledger only")
    return {
        "profile": {"dir": pdir, "status": pstatus, "source": psrc},
        "level": {"value": level, "source": lsrc},
        "depth": {"value": depth, "source": dsrc},
        "finalists": {"value": finalists, "source": fsrc},
        "gate_mode": GATE_MODE[depth] if finalists else "none",
        "corpus": {"paths": corpus, "source": corsrc},
        "direction": field or None,
        "cutoff": {"value": cutoff, "source": csrc},
        "out_dir": {"value": out_dir, "source": osrc},
        "extra_language": {"value": lang, "source": langsrc},
        "notes": notes,
    }


def card(s):
    c = s["corpus"]
    lines = [
        f"level: {s['level']['value']} ({s['level']['source']}) · depth: {s['depth']['value']} ({s['depth']['source']})"
        + (f" · gate: top {s['finalists']['value']}, {s['gate_mode']} mode" if s["finalists"]["value"]
           else " · gate: none (the user picks what to gate)"),
        "corpus: " + (", ".join(c["paths"]) if c["paths"] else "-") + f" [{c['source']}]",
        f"direction: {s['direction'] or '-'} · cutoff: {s['cutoff']['value']} · out: {s['out_dir']['value']}",
        "reports: en" + (f" + {s['extra_language']['value']}" if s["extra_language"]["value"] else "")
        + f" ({s['extra_language']['source']})",
        f"profile: {s['profile']['dir'] or '-'} ({s['profile']['status']})",
    ]
    lines += [f"note: {n}" for n in s["notes"]]
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--level", choices=LEVELS)
    p.add_argument("--depth", choices=DEPTHS)
    p.add_argument("--gate", type=int, help="number of finalists to gate (overrides depth)")
    p.add_argument("--corpus", nargs="*", default=[])
    p.add_argument("--field")
    p.add_argument("--cutoff", type=lambda v: dt.date.fromisoformat(v).isoformat())
    p.add_argument("--out")
    p.add_argument("--extra-language", help="ISO 639-1 code, or none")
    p.add_argument("--profile")
    p.add_argument("--cwd")
    p.add_argument("--today")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    s = resolve(a.level, a.depth, a.gate, a.corpus, a.field, a.cutoff, a.out, a.extra_language,
                a.profile, a.cwd, a.today)
    print(json.dumps(s, ensure_ascii=False, indent=2) if a.json else card(s))
    return 0 if s["profile"]["status"] == "found" else 4


if __name__ == "__main__":
    sys.exit(main())
