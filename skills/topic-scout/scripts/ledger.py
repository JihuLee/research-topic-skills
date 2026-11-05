#!/usr/bin/env python3
"""ledger.py - the research-topic ledger (JSON Lines), Python stdlib only.

One JSON object per line. Required keys: id, date (YYYY-MM-DD), title, claim, verdict.
verdict in: pass, near-miss, killed, dropped, closed, none, pending

Subcommands
  validate LEDGER
  list LEDGER [--verdict V] [--tag T]
  check LEDGER --claim TEXT [--top K] [--min SCORE]
      Near-duplicate search of a new idea against past topics (word Jaccard + character
      trigram cosine; works for any language). Shows verdicts and named killers.
  add LEDGER (--json OBJ | --file ENTRY.json | --from-summary OUT_DIR) [--dry-run]
      --from-summary reads OUT_DIR/gate_summary.json (or an older report with a gate-summary block).
  update LEDGER --id ID --set key=value [--set key=value ...]
      Values are parsed as JSON when possible (numbers, lists), otherwise kept as strings.
"""
import argparse
import datetime as dt
import json
import math
import os
import re
import sys
from collections import Counter

REQUIRED = ["id", "date", "title", "claim", "verdict"]
VERDICTS = {"pass", "near-miss", "killed", "dropped", "closed", "none", "pending"}
STAGES = {"idea", "gate", "b0", "pilot", "sealed", "brief", "done"}
STOP = set("""a an the of for and or to in on with by from via is are be as at that this these those using
use based towards toward we our new novel method methods approach model models learning""".split())


def load(path):
    entries = []
    try:
        with open(path, encoding="utf-8") as fh:
            for n, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append((n, json.loads(line)))
                except json.JSONDecodeError as e:
                    raise SystemExit(f"{path}:{n}: invalid JSON: {e}")
    except FileNotFoundError:
        pass
    return entries


def problems(entry):
    errs = []
    for k in REQUIRED:
        if not entry.get(k):
            errs.append(f"missing {k}")
    if entry.get("verdict") and entry["verdict"] not in VERDICTS:
        errs.append(f"verdict {entry['verdict']!r} not in {sorted(VERDICTS)}")
    if entry.get("stage") and entry["stage"] not in STAGES:
        errs.append(f"stage {entry['stage']!r} not in {sorted(STAGES)}")
    if entry.get("date") and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(entry["date"])):
        errs.append("date must be YYYY-MM-DD")
    for k in ("novelty", "feasibility"):
        v = entry.get(k)
        if v is not None and not (isinstance(v, int) and 1 <= v <= 5):
            errs.append(f"{k} must be an int 1-5")
    for kl in entry.get("killers") or []:
        if not isinstance(kl, dict) or not kl.get("title"):
            errs.append("each killer needs at least a title (and ideally url, why)")
    return errs


def words(text):
    toks = re.findall(r"[\w\-]+", (text or "").lower())
    return {t for t in toks if t not in STOP and len(t) > 1}


def trigrams(text):
    s = re.sub(r"\s+", " ", (text or "").lower())
    return Counter(s[i:i + 3] for i in range(max(0, len(s) - 2)))


def cosine(a, b):
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def similarity(a_text, b_text):
    wa, wb = words(a_text), words(b_text)
    jac = len(wa & wb) / len(wa | wb) if (wa | wb) else 0.0
    return 0.5 * jac + 0.5 * cosine(trigrams(a_text), trigrams(b_text))


def entry_text(e):
    return " ".join([e.get("title", ""), e.get("claim", ""), " ".join(e.get("tags") or [])])


def extract_summary(path):
    """Accept an output folder, gate_summary.json, or a markdown file with a json gate-summary block."""
    if os.path.isdir(path):
        path = os.path.join(path, "gate_summary.json")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if path.endswith(".json"):
        return json.loads(text)
    m = re.search(r"```json\s+gate-summary\s*\n(.*?)```", text, re.S)
    if not m:
        raise SystemExit("no gate_summary.json or ```json gate-summary block found")
    return json.loads(m.group(1))


def entries_from_summary(summary, report_path):
    today = dt.date.today().isoformat()
    out = []
    for c in summary.get("candidates", []):
        status = c.get("status", "pending")
        verdict = status if status in VERDICTS else "pending"
        killers = []
        if status in ("killed", "near-miss"):
            for pr in c.get("closest_prior", []):
                killers.append({"title": pr.get("title"), "url": pr.get("url"), "why": pr.get("overlap", "")})
        out.append({
            "id": f"{summary.get('date', today)}-{c.get('id')}",
            "date": summary.get("date", today),
            "title": c.get("title"),
            "claim": c.get("claim") or c.get("title"),
            "verdict": verdict,
            "stage": "gate",
            "novelty": c.get("novelty"),
            "feasibility": c.get("feasibility"),
            "killers": killers,
            "near_miss_b0": (c.get("b0") or {}).get("promote_if") if status == "near-miss" else None,
            "report": report_path,
        })
    return out


def parse_value(v):
    try:
        return json.loads(v)
    except json.JSONDecodeError:
        return v


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("validate"); sp.add_argument("ledger")
    sp = sub.add_parser("list"); sp.add_argument("ledger"); sp.add_argument("--verdict"); sp.add_argument("--tag")
    sp = sub.add_parser("check"); sp.add_argument("ledger"); sp.add_argument("--claim", required=True)
    sp.add_argument("--top", type=int, default=5); sp.add_argument("--min", type=float, default=0.2)
    sp = sub.add_parser("add"); sp.add_argument("ledger")
    g = sp.add_mutually_exclusive_group(required=True)
    g.add_argument("--json"); g.add_argument("--file"); g.add_argument("--from-summary")
    sp.add_argument("--dry-run", action="store_true")
    sp = sub.add_parser("update"); sp.add_argument("ledger"); sp.add_argument("--id", required=True)
    sp.add_argument("--set", action="append", required=True, metavar="KEY=VALUE")
    a = p.parse_args(argv)

    entries = load(a.ledger)

    if a.cmd == "validate":
        bad = 0
        ids = Counter(e.get("id") for _, e in entries)
        for n, e in entries:
            errs = problems(e)
            if ids.get(e.get("id"), 0) > 1:
                errs.append(f"duplicate id {e.get('id')!r}")
            for err in errs:
                bad += 1
                print(f"{a.ledger}:{n}: {err}")
        print(f"{len(entries)} entries, {bad} problems")
        return 1 if bad else 0

    if a.cmd == "list":
        for _, e in entries:
            if a.verdict and e.get("verdict") != a.verdict:
                continue
            if a.tag and a.tag not in (e.get("tags") or []):
                continue
            ks = "; ".join(k.get("title", "") for k in e.get("killers") or [])
            print(f"{e.get('date')} {e.get('id')} [{e.get('verdict')}] {e.get('title')}" + (f"  killers: {ks}" if ks else ""))
        return 0

    if a.cmd == "check":
        scored = sorted(((similarity(a.claim, entry_text(e)), e) for _, e in entries), key=lambda x: -x[0])
        hits = [(s, e) for s, e in scored[: a.top] if s >= a.min]
        if not hits:
            print("no similar ledger entries")
            return 0
        for s, e in hits:
            print(f"{s:.2f}  {e.get('id')} [{e.get('verdict')}] {e.get('title')}")
            print(f"      claim: {e.get('claim')}")
            for k in e.get("killers") or []:
                print(f"      killer: {k.get('title')} {k.get('url', '')} - {k.get('why', '')}")
        return 0

    if a.cmd == "add":
        if a.json:
            new = [json.loads(a.json)]
        elif a.file:
            with open(a.file, encoding="utf-8") as fh:
                new = [json.load(fh)]
        else:
            new = entries_from_summary(extract_summary(a.from_summary), a.from_summary)
        existing = {e.get("id") for _, e in entries}
        for e in new:
            e = {k: v for k, v in e.items() if v is not None}
            e.setdefault("date", dt.date.today().isoformat())
            errs = problems(e)
            if e.get("id") in existing:
                errs.append(f"id {e.get('id')!r} already exists (use update)")
            if errs:
                print(f"REJECTED {e.get('id')}: {'; '.join(errs)}")
                continue
            line = json.dumps(e, ensure_ascii=False)
            if a.dry_run:
                print("DRY-RUN " + line)
            else:
                with open(a.ledger, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
                print("ADDED " + e["id"])
        return 0

    if a.cmd == "update":
        found = False
        lines = []
        for _, e in entries:
            if e.get("id") == a.id:
                found = True
                for kv in a.set:
                    k, _, v = kv.partition("=")
                    e[k.strip()] = parse_value(v)
                errs = problems(e)
                if errs:
                    raise SystemExit(f"update rejected: {'; '.join(errs)}")
            lines.append(json.dumps(e, ensure_ascii=False))
        if not found:
            raise SystemExit(f"id {a.id!r} not found")
        with open(a.ledger, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        print("UPDATED " + a.id)
        return 0


if __name__ == "__main__":
    sys.exit(main())
