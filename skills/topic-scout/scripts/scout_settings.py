#!/usr/bin/env python3
"""scout_settings.py - resolve topic-scout settings from explicit flags, the profile and defaults.

  scout_settings.py [--level high|medium|low] [--depth quick|standard|full] [--gate N]
                    [--corpus PATH ...] [--field TEXT] [--cutoff YYYY-MM-DD] [--out DIR]
                    [--extra-language CODE|none] [--scope global|track] [--track NAME [--focus TEXT]
                    [--track-tags a,b]] [--profile DIR] [--cwd DIR] [--today YYYY-MM-DD] [--json]

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
  scope      global (ideas from all topics) or track (one fixed topic; see tracks.py). The ledger
             duplicate check is global either way. --track implies scope track; a new track
             needs --focus and is created in <profile>/tracks/.
  profile    profile directory and whether it was found
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tracks  # noqa: E402  (same folder)

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


def too_broad(path):
    """The home directory, the filesystem root, or a folder that contains the home directory."""
    p = os.path.realpath(path)
    h = os.path.realpath(os.path.expanduser("~"))
    return p == os.path.sep or p == h or h.startswith(p.rstrip(os.sep) + os.sep)


def drop_broad(paths, notes):
    for p in [p for p in paths if too_broad(p)]:
        notes.append(f"corpus path not used: {p} is the home directory, the root, or contains the home directory")
    return [p for p in paths if not too_broad(p)]


def resolve_corpus(level, given, prof, cwd, notes):
    given = drop_broad([os.path.abspath(os.path.join(cwd, os.path.expanduser(p))) for p in given or []], notes)
    found = [p for p in given if os.path.exists(p)]
    for p in sorted(set(given) - set(found)):
        notes.append(f"corpus path not found: {p}")
    if level == "low":
        if given or prof.get("corpus_paths"):
            notes.append("level low: the corpus is not read, even if paths are given")
        return [], "not used (level low)"
    if found:
        return found, "request"
    prof_paths = drop_broad([os.path.abspath(os.path.expanduser(p)) for p in prof.get("corpus_paths") or []], notes)
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


def resolve_track(scope, name, focus, ttags, prof, pdir, notes):
    if name:
        scope, ssrc = "track", "request"
    elif scope:
        ssrc = "request"
    elif prof.get("scout_scope") in ("global", "track"):
        scope, ssrc = prof["scout_scope"], "profile"
    else:
        scope, ssrc = "global", "default"
    info = None
    if scope == "track":
        existing = sorted(f[:-5] for f in os.listdir(os.path.join(pdir, "tracks"))
                          if f.endswith(".json")) if pdir and os.path.isdir(os.path.join(pdir, "tracks")) else []
        if not pdir:
            notes.append("track scope needs a profile directory")
        elif not name:
            notes.append("scope is track but no track was named: ask the user which topic to fix "
                         + (f"(existing: {', '.join(existing)}) " if existing else "")
                         + "and rerun with --track NAME (plus --focus for a new one)")
        elif tracks.load(pdir, name):
            info = dict(tracks.summary(pdir, name), status="found")
            if focus and focus.strip() != info["focus"]:
                notes.append("--focus differs from the saved focus; the saved one is used "
                             "(change it with tracks.py edit if the user wants)")
        elif focus:
            try:
                tracks.create(pdir, name, focus, [t.strip() for t in (ttags or "").split(",") if t.strip()])
                info = dict(tracks.summary(pdir, name), status="created")
            except ValueError as e:
                notes.append(str(e))
        else:
            notes.append(f"track {name!r} does not exist yet: ask the user for a one-sentence focus "
                         "and rerun with --focus")
    return {"value": scope, "source": ssrc}, info


def resolve(level=None, depth=None, gate=None, corpus=None, field=None, cutoff=None, out=None,
            extra_language=None, profile=None, cwd=None, today=None, env=None,
            scope=None, track=None, focus=None, track_tags=None):
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
    scope_v, track_info = resolve_track(scope, track, focus, track_tags, prof, pdir, notes)
    if track_info and not field:
        field = track_info["focus"]
    if track_info and osrc.startswith("default"):
        out_dir = os.path.join(os.path.dirname(out_dir), f"scout-{today}-{track_info['name']}")
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
        "scope": scope_v,
        "track": track_info,
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
    t = s.get("track")
    if t:
        lines.insert(3, f"scope: track {t['name']} ({t['status']}) · next {t['next_candidate']} · "
                        f"{t['earlier']} earlier, {t['closed']} closed · duplicate check: all topics")
    else:
        lines.insert(3, f"scope: {s['scope']['value']} ({s['scope']['source']})"
                        + (" · ideas from all topics" if s["scope"]["value"] == "global" else ""))
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
    p.add_argument("--scope", choices=("global", "track"))
    p.add_argument("--track", help="track name (implies --scope track)")
    p.add_argument("--focus", help="one-sentence focus, needed to create a new track")
    p.add_argument("--track-tags", help="comma-separated tags for a new track")
    p.add_argument("--profile")
    p.add_argument("--cwd")
    p.add_argument("--today")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    s = resolve(a.level, a.depth, a.gate, a.corpus, a.field, a.cutoff, a.out, a.extra_language,
                a.profile, a.cwd, a.today, scope=a.scope, track=a.track, focus=a.focus, track_tags=a.track_tags)
    print(json.dumps(s, ensure_ascii=False, indent=2) if a.json else card(s))
    return 0 if s["profile"]["status"] == "found" else 4


if __name__ == "__main__":
    sys.exit(main())
