#!/usr/bin/env python3
"""freeze.py - pre-register decision thresholds before seeing results (Python stdlib only).

  template                  print a skeleton thresholds JSON
  freeze FILE.json          hash the canonical JSON, write FILE.json.sha256 and a snapshot
                            FILE.json.frozen.json; refuses if a different hash is already recorded
  verify FILE.json          recompute and compare with FILE.json.sha256 (exit 1 on mismatch)
  amend FILE.json --reason TEXT [--after-results]
                            re-freeze an edited file and append {date, old, new, reason, changes}
                            to FILE.json.amendments.jsonl. With --after-results only tightening
                            changes are accepted (see TIGHTER); anything else exits 1 unchanged.

The hash covers the canonical form (sorted keys, no whitespace), so reformatting the file
does not change it but any change of a key or value does. Numbers must be JSON numbers:
freeze warns when a string looks like a number, because prose thresholds get misread.
After results are seen, thresholds may only be tightened through a logged amendment,
never relaxed. A changed prose condition (promote_if, kill_if, ...) cannot be checked
automatically, so after results it is refused: register a new file instead.
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import sys

TEMPLATE = {
    "schema": "thresholds/v1",
    "frozen_on": "YYYY-MM-DD",
    "question": "what this B0 decides",
    "primary_endpoint": {"name": "metric name", "direction": "higher_is_better", "unit": "per-image"},
    "resampling": {"unit": "image", "method": "paired_bootstrap", "n_boot": 10000, "ci": 0.95, "seed": 0},
    "min_effect": 0.0,
    "headroom_multiplier": 2.0,
    "promote_if": "oracle_headroom >= headroom_multiplier * min_effect and paired_ci_low > 0",
    "kill_if": "oracle_headroom < headroom_multiplier * min_effect",
    "inconclusive_if": "n_units < 200 or ci_width > 2 * min_effect",
    "blocked_if": "known_good fixture fails or required asset unavailable",
    "known_good": {"fixture": "describe the synthetic input where the effect exists", "expected": 0.0, "tolerance": 0.0},
    "null_fixture": {"fixture": "describe the input where the effect is absent", "expected": 0.0, "tolerance": 0.0},
    "baselines": ["native", "common_default", "simplest_key_info", "equal_compute"],
    "budget": {"gpu_hours": 0, "download_gb": 0, "wall_clock_hours": 0},
}
# Field -> which direction is stricter. Only these may change after results.
TIGHTER = {
    "$.min_effect": "up", "$.headroom_multiplier": "up", "$.resampling.ci": "up", "$.resampling.n_boot": "up",
    "$.known_good.tolerance": "down", "$.null_fixture.tolerance": "down",
    "$.budget.gpu_hours": "down", "$.budget.download_gb": "down", "$.budget.wall_clock_hours": "down",
    "$.baselines": "superset", "$.frozen_on": "any",
}
NUMERIC_STR = re.compile(r"^\s*[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?\s*$")


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(obj):
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def numeric_strings(obj, path="$"):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out += numeric_strings(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += numeric_strings(v, f"{path}[{i}]")
    elif isinstance(obj, str) and NUMERIC_STR.match(obj):
        out.append(path)
    return out


def changes(old, new, path="$"):
    """List (path, old, new) for every leaf that differs."""
    if isinstance(old, dict) and isinstance(new, dict):
        out = []
        for k in sorted(set(old) | set(new)):
            out += changes(old.get(k), new.get(k), f"{path}.{k}")
        return out
    return [] if old == new else [(path, old, new)]


def relaxing(diff):
    """Changes that are not provably tighter."""
    bad = []
    for path, o, n in diff:
        rule = TIGHTER.get(path)
        num = isinstance(o, (int, float)) and isinstance(n, (int, float))
        if rule == "any":
            continue
        if rule == "up" and num and n > o or rule == "down" and num and n < o:
            continue
        if rule == "superset" and isinstance(o, list) and isinstance(n, list) and set(o) <= set(n):
            continue
        bad.append(path)
    return bad


def write_frozen(file, obj, h):
    with open(file + ".sha256", "w", encoding="utf-8") as fh:
        fh.write(f"{h}  {file} (canonical-json)\n")
    with open(file + ".frozen.json", "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False, sort_keys=True)


def recorded_hash(file):
    try:
        with open(file + ".sha256", encoding="utf-8") as fh:
            return fh.read().split()[0]
    except FileNotFoundError:
        return None


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("template")
    sp = sub.add_parser("freeze"); sp.add_argument("file")
    sp = sub.add_parser("verify"); sp.add_argument("file")
    sp = sub.add_parser("amend"); sp.add_argument("file"); sp.add_argument("--reason", required=True)
    sp.add_argument("--after-results", action="store_true",
                    help="state that results were already seen (amendment must only tighten)")
    a = p.parse_args(argv)

    if a.cmd == "template":
        t = dict(TEMPLATE)
        t["frozen_on"] = dt.date.today().isoformat()
        print(json.dumps(t, indent=2, ensure_ascii=False))
        return 0

    with open(a.file, encoding="utf-8") as fh:
        obj = json.load(fh)
    h = digest(obj)
    if a.cmd == "freeze":
        for path in numeric_strings(obj):
            print(f"WARNING: {path} is a string that looks like a number; use a JSON number", file=sys.stderr)
        old_h = recorded_hash(a.file)
        if old_h and old_h != h:
            print(f"ERROR: {a.file} is already frozen with a different hash; use amend --reason", file=sys.stderr)
            return 1
        write_frozen(a.file, obj, h)
        print(h)
        return 0
    if a.cmd == "amend":
        old_h = recorded_hash(a.file)
        try:
            with open(a.file + ".frozen.json", encoding="utf-8") as fh:
                old_obj = json.load(fh)
        except FileNotFoundError:
            old_obj = None
        diff = changes(old_obj, obj) if isinstance(old_obj, dict) else []
        if a.after_results:
            if old_obj is None:
                print(f"ERROR: no {a.file}.frozen.json snapshot, so tightening cannot be checked", file=sys.stderr)
                return 1
            bad = relaxing(diff)
            if bad:
                print("ERROR: after results only tightening is allowed; not provably tighter: "
                      + ", ".join(bad) + ". Nothing was changed; register a new file instead.", file=sys.stderr)
                return 1
        entry = {"date": dt.date.today().isoformat(), "old": old_h, "new": h, "reason": a.reason,
                 "after_results": bool(a.after_results), "changes": [p for p, _, _ in diff]}
        with open(a.file + ".amendments.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        write_frozen(a.file, obj, h)
        print(h)
        return 0
    try:
        with open(a.file + ".sha256", encoding="utf-8") as fh:
            recorded = fh.read().split()[0]
    except FileNotFoundError:
        print(f"no {a.file}.sha256; run freeze first", file=sys.stderr)
        return 1
    if recorded == h:
        print(f"OK {h}")
        return 0
    print(f"MISMATCH recorded={recorded} current={h}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
