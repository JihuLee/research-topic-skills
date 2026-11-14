#!/usr/bin/env python3
"""ledger.py - the research-topic ledger (JSON Lines), Python stdlib only.

One JSON object per line. Required keys: id, date (YYYY-MM-DD), title, claim, verdict.
verdict in: pass, near-miss, killed, dropped, closed, none, pending

Optional keys include parent (the id of an earlier entry for the same topic: a revision or
re-check), history (earlier values, kept by `update`) and track (the topic track the entry
came from; see topic-scout's tracks.py). Entries are never deleted.

Subcommands
  validate LEDGER
  list LEDGER [--verdict V] [--tag T] [--track NAME]
  check LEDGER --claim TEXT [--also TEXT ...] [--tags a,b] [--track NAME] [--top K] [--min SCORE]
      Near-duplicate search of a new idea against past topics (word Jaccard + character
      trigram cosine; works for any language). It is word-based, so pass the same idea in
      other words with --also; each entry keeps its best score. Shared tags add a small boost.
      The check always covers the whole ledger; with --track, hits from other tracks are marked
      "other track" (a reason to drop, not material for new ideas).
  add LEDGER (--json OBJ | --file ENTRY.json | --from-summary OUT_DIR) [--dry-run]
      --from-summary reads OUT_DIR/gate_summary.json (or an older report with a gate-summary block).
  update LEDGER --id ID --set key=value [--set key=value ...]
      Values are parsed as JSON when possible (numbers, lists), otherwise kept as strings.
      The old values are appended to the entry's history.
  index LEDGER [--out FILE] [--track NAME]
      Write ledger_index.md next to the ledger: one line per topic family (latest entry,
      verdict, killer), grouped by first tag. Agents read this instead of the whole ledger.
      add and update refresh it automatically. With --track, print only that track's families
      (to stdout unless --out is given).
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
    if entry.get("parent") is not None and not isinstance(entry.get("parent"), str):
        errs.append("parent must be the id of an earlier entry")
    if entry.get("history") is not None and not isinstance(entry.get("history"), list):
        errs.append("history must be a list")
    if entry.get("track") is not None and not (isinstance(entry["track"], str) and re.match(r"^[a-z0-9][a-z0-9-]*$", entry["track"])):
        errs.append("track must be a track name (lowercase letters, digits, hyphens)")
    return errs


def families(entries):
    """Group entries by parent chains. Returns {root_id: [entries, oldest first]}."""
    by_id = {e.get("id"): e for e in entries}
    def root(e):
        seen = set()
        while e.get("parent") in by_id and e.get("id") not in seen:
            seen.add(e.get("id"))
            e = by_id[e["parent"]]
        return e.get("id")
    fam = {}
    for e in entries:
        fam.setdefault(root(e), []).append(e)
    for v in fam.values():
        v.sort(key=lambda e: (str(e.get("date", "")), str(e.get("id", ""))))
    return fam


def short(text, n):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def write_index(ledger_path, out=None, track=None):
    entries = [e for _, e in load(ledger_path)]
    if not track:
        out = out or os.path.join(os.path.dirname(os.path.abspath(ledger_path)), "ledger_index.md")
    fam = families(entries)
    if track:
        fam = {k: v for k, v in fam.items() if any(e.get("track") == track for e in v)}
    groups = {}
    for members in fam.values():
        head = members[-1]
        tag = (head.get("tags") or ["untagged"])[0]
        groups.setdefault(tag, []).append((head, members))
    lines = ["# Ledger index" + (f" — track {track}" if track else ""), "",
             f"Generated by ledger.py from {os.path.basename(ledger_path)}; do not edit. "
             f"{len(entries)} entries in {len(fam)} topic families. One line per family: latest date, id, verdict, title, first killer, tags.",
             "Read this instead of the whole ledger. For details: `ledger.py check` or `ledger.py list`.", ""]
    for tag in sorted(groups, key=lambda t: (-len(groups[t]), t)):
        lines.append(f"## {tag} ({len(groups[tag])})")
        for head, members in sorted(groups[tag], key=lambda x: str(x[0].get("date", "")), reverse=True):
            ks = head.get("killers") or []
            killer = f" — killer: {short(ks[0].get('title'), 60)}" if ks else ""
            more = f" (+{len(members) - 1} earlier: {', '.join(m.get('id') for m in members[:-1])})" if len(members) > 1 else ""
            tags = ", ".join(head.get("tags") or [])
            trk = f" (track: {head['track']})" if head.get("track") and not track else ""
            lines.append(f"- {head.get('date')} {head.get('id')} · {head.get('verdict')} · {short(head.get('title'), 80)}"
                         f"{killer}{more}" + (f" [{tags}]" if tags else "") + trk)
        lines.append("")
    if out in (None, "-"):
        print("\n".join(lines))
        return "stdout"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return out


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
            "track": summary.get("track"),
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
    sp.add_argument("--track")
    sp = sub.add_parser("check"); sp.add_argument("ledger"); sp.add_argument("--claim", required=True)
    sp.add_argument("--also", action="append", default=[], help="the same idea in other words (repeatable)")
    sp.add_argument("--tags", default="", help="comma-separated tags; shared tags add a small boost")
    sp.add_argument("--track", help="mark hits from other tracks")
    sp.add_argument("--top", type=int, default=5); sp.add_argument("--min", type=float, default=0.2)
    sp = sub.add_parser("add"); sp.add_argument("ledger")
    g = sp.add_mutually_exclusive_group(required=True)
    g.add_argument("--json"); g.add_argument("--file"); g.add_argument("--from-summary")
    sp.add_argument("--dry-run", action="store_true")
    sp = sub.add_parser("update"); sp.add_argument("ledger"); sp.add_argument("--id", required=True)
    sp.add_argument("--set", action="append", required=True, metavar="KEY=VALUE")
    for name in ("add", "update"):
        sub.choices[name].add_argument("--no-index", action="store_true", help="do not refresh ledger_index.md")
    sp = sub.add_parser("index"); sp.add_argument("ledger"); sp.add_argument("--out"); sp.add_argument("--track")
    a = p.parse_args(argv)

    entries = load(a.ledger)

    if a.cmd == "validate":
        bad = 0
        ids = Counter(e.get("id") for _, e in entries)
        for n, e in entries:
            errs = problems(e)
            if ids.get(e.get("id"), 0) > 1:
                errs.append(f"duplicate id {e.get('id')!r}")
            if e.get("parent") and e["parent"] not in ids:
                errs.append(f"parent {e['parent']!r} is not an id in this ledger")
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
            if a.track and e.get("track") != a.track:
                continue
            ks = "; ".join(k.get("title", "") for k in e.get("killers") or [])
            print(f"{e.get('date')} {e.get('id')} [{e.get('verdict')}] {e.get('title')}" + (f"  killers: {ks}" if ks else ""))
        return 0

    if a.cmd == "index":
        where = write_index(a.ledger, a.out, a.track)
        if where != "stdout":
            print("wrote " + where)
        return 0

    if a.cmd == "check":
        queries = [a.claim] + list(a.also)
        want = {t.strip().lower() for t in a.tags.split(",") if t.strip()}
        def score(e):
            base = max(similarity(q, entry_text(e)) for q in queries)
            shared = len(want & {t.lower() for t in e.get("tags") or []})
            return base + min(0.1, 0.05 * shared)
        scored = sorted(((score(e), e) for _, e in entries), key=lambda x: -x[0])
        hits = [(s, e) for s, e in scored[: a.top] if s >= a.min]
        if not hits:
            print("no similar ledger entries")
            return 0
        for s, e in hits:
            fam = f" (family of {e['parent']})" if e.get("parent") else ""
            other = (f"  <- other track: {e.get('track') or 'none'}; a reason to drop, not material"
                     if a.track and e.get("track") != a.track else "")
            print(f"{s:.2f}  {e.get('id')} [{e.get('verdict')}] {e.get('title')}{fam}{other}")
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
                if e.get("parent") and e["parent"] not in existing:
                    print(f"WARNING {e['id']}: parent {e['parent']!r} is not in the ledger")
                with open(a.ledger, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
                existing.add(e["id"])
                print("ADDED " + e["id"])
        if not a.dry_run and not a.no_index:
            write_index(a.ledger)
        return 0

    if a.cmd == "update":
        found = False
        lines = []
        for _, e in entries:
            if e.get("id") == a.id:
                found = True
                old = {}
                for kv in a.set:
                    k, _, v = kv.partition("=")
                    k = k.strip()
                    if k in ("id", "history"):
                        raise SystemExit(f"update rejected: {k} cannot be set")
                    old[k] = e.get(k)
                    e[k] = parse_value(v)
                e.setdefault("history", []).append({"date": dt.date.today().isoformat(), "previous": old})
                errs = problems(e)
                if errs:
                    raise SystemExit(f"update rejected: {'; '.join(errs)}")
            lines.append(json.dumps(e, ensure_ascii=False))
        if not found:
            raise SystemExit(f"id {a.id!r} not found")
        with open(a.ledger, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        print("UPDATED " + a.id)
        if not a.no_index:
            write_index(a.ledger)
        return 0


if __name__ == "__main__":
    sys.exit(main())
