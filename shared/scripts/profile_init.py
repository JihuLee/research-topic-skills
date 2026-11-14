#!/usr/bin/env python3
"""profile_init.py - create a researcher profile directory from a few answers (stdlib only).

  profile_init.py [--dir ~/research-profile] --interests "area one; area two"
                  [--exclusions "a; b"] [--gpu-hours 10] [--download-gb 10] [--wall-clock-hours 48]
                  [--hardware "2 GPUs, 24 GB each"] [--extra-language ko] [--venues "venue; venue"]
                  [--level medium] [--depth standard] [--corpus "path; path"] [--force]

Writes profile.md (prose placeholders + a json profile block), an empty ledger.jsonl,
a starter lessons.md and an assets.md table header. Refuses to overwrite an existing
profile.md unless --force. Lists are separated by semicolons.
"""
import argparse
import json
import os
import sys

LESSONS = """# Lessons

Your own checks, learned from past reviews. The novelty gate applies pinned and core lessons in every run, and a scoped lesson only when a candidate shares one of its tags. Do not repeat rules the skills already enforce (input-contract search, classical equivalents, theory-forced results, the four baselines, oracle first, data hygiene). Add what your own history taught you.

One top-level bullet per lesson, details as indented sub-bullets. Example (inside a comment, so it is not applied):
<!--
- [L1|core|evaluation|h0/x0/n0] Check: the official evaluation script and version were used, or the difference is stated.
- [L2|scoped|benchmark|h0/x0/n0] Check: leaderboard entries from the last three months were read, not only the paper tables.
-->

Tiers: pinned (always applied, never proposed for archiving), core (always applied, at most lessons_core_cap), scoped (only when tags match). h/x/n count catches, false alarms and applications; `lessons.py tally` updates them. Change lessons only with `lessons.py apply`: the gate proposes, you approve.

## Lessons
"""
ASSETS = """# Owned assets

| name | kind | path | size | license | provenance / training split | notes |
|---|---|---|---|---|---|---|
"""


def split(s):
    return [x.strip() for x in (s or "").split(";") if x.strip()]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dir", default="~/research-profile")
    p.add_argument("--interests", required=True)
    p.add_argument("--exclusions", default="")
    p.add_argument("--gpu-hours", type=float, default=10)
    p.add_argument("--download-gb", type=float, default=10)
    p.add_argument("--wall-clock-hours", type=float, default=48)
    p.add_argument("--hardware", default="unspecified")
    p.add_argument("--extra-language", default=None, help="ISO 639-1 code for an extra human report, e.g. ko")
    p.add_argument("--venues", default="")
    p.add_argument("--level", choices=["high", "medium", "low"], default="medium")
    p.add_argument("--depth", choices=["quick", "standard", "full"], default="standard")
    p.add_argument("--corpus", default="")
    p.add_argument("--force", action="store_true")
    a = p.parse_args(argv)

    d = os.path.abspath(os.path.expanduser(a.dir))
    prof = os.path.join(d, "profile.md")
    if os.path.exists(prof) and not a.force:
        print(f"{prof} already exists; edit it or pass --force", file=sys.stderr)
        return 1
    os.makedirs(d, exist_ok=True)
    num = lambda x: int(x) if float(x).is_integer() else x
    constants = {
        "extra_report_language": a.extra_language,
        "interests": split(a.interests),
        "preferred_contributions": ["method", "benchmark", "analysis"],
        "target_venues": split(a.venues),
        "exclusions": split(a.exclusions),
        "ground_truth_policy": "public data and verifiable ground truth only; simulators allowed; "
                               "no new human ratings or LLM judgments as the primary metric",
        "budgets": {"tiers": {"default": {"gpu_hours": num(a.gpu_hours), "download_gb": num(a.download_gb)}},
                    "wall_clock_hours": num(a.wall_clock_hours), "hardware": a.hardware},
        "novelty_entry_threshold": 4,
        "recency_window_months": 6,
        "approval_required_for": ["downloads", "experiments", "gpu"],
        "report_dir_pattern": "./gate-{slug}-{date}/",
        "scout_level": a.level,
        "scout_depth": a.depth,
        "scout_scope": "global",
        "lessons_core_cap": 20,
        "lessons_review_every_gates": 20,
        "lessons_max_active": 40,
        "corpus_paths": split(a.corpus),
        "handoff_template": None,
        "content_check_command": None,
    }
    text = ("# Research profile\n\nCreated by profile_init.py. Keep this file private.\n\n"
            "## Taste (prose)\n- What kinds of results excite you, and why:\n"
            "- What you are unusually good at (methods, domains, data or instrument access):\n"
            "- What you never want to work on again, and why:\n"
            "- How you like to be told \"no\":\n\n## Constants\n\n```json profile\n"
            + json.dumps(constants, ensure_ascii=False, indent=2) + "\n```\n")
    with open(prof, "w", encoding="utf-8") as fh:
        fh.write(text)
    for name, content in (("ledger.jsonl", ""), ("lessons.md", LESSONS), ("assets.md", ASSETS)):
        path = os.path.join(d, name)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
    print(f"created {d} (profile.md, ledger.jsonl, lessons.md, assets.md)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
