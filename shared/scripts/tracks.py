#!/usr/bin/env python3
"""tracks.py - named topic tracks for topic-scout (Python stdlib only).

A track fixes one topic for a line of work ("scout, drop, scout again" on the same theme).
In a track, topic-scout draws ideas only from that topic and from this track's history; the
ledger duplicate check stays global. Tracks live in <profile>/tracks/<name>.json.

Subcommands (PROFILE is the profile directory)
  new PROFILE NAME --focus TEXT [--tags a,b]   create a track (name: lowercase letters, digits, hyphens)
  edit PROFILE NAME [--focus TEXT] [--tags a,b]
  list PROFILE                                 one line per track
  show PROFILE NAME [--max N]                  focus, tags, the next candidate number, and every earlier
                                               candidate: scout records in the track file plus ledger
                                               entries whose "track" is NAME (gated verdicts)
  record PROFILE NAME OUT_DIR                  add a scout run's candidates.jsonl to the track
                                               (new ids are added, known ids get their latest status)
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")


def track_path(profile, name):
    return os.path.join(profile, "tracks", f"{name}.json")


def load(profile, name):
    try:
        with open(track_path(profile, name), encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return None


def save(profile, t):
    os.makedirs(os.path.join(profile, "tracks"), exist_ok=True)
    t["updated"] = dt.date.today().isoformat()
    with open(track_path(profile, t["name"]), "w", encoding="utf-8") as fh:
        json.dump(t, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def create(profile, name, focus, tags=()):
    if not NAME.match(name or ""):
        raise ValueError(f"track name {name!r}: use lowercase letters, digits and hyphens")
    if not (focus or "").strip():
        raise ValueError("a new track needs a one-sentence focus")
    t = {"schema": "track/v1", "name": name, "focus": focus.strip(), "tags": list(tags),
         "created": dt.date.today().isoformat(), "runs": [], "candidates": []}
    save(profile, t)
    return t


def ledger_entries(profile, name):
    out = []
    try:
        with open(os.path.join(profile, "ledger.jsonl"), encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    e = json.loads(line)
                    if e.get("track") == name:
                        out.append(e)
    except FileNotFoundError:
        pass
    return out


def next_number(t, entries):
    nums = [0]
    for i in [c.get("id", "") for c in t.get("candidates", [])] + [e.get("id", "") for e in entries]:
        m = re.search(r"C(\d+)[A-Za-z-]*$", str(i))
        if m:
            nums.append(int(m.group(1)))
    return max(nums) + 1


def summary(profile, name):
    """Short dict for the settings card."""
    t = load(profile, name)
    if not t:
        return None
    entries = ledger_entries(profile, name)
    closed = sum(1 for c in t.get("candidates", []) if c.get("status") == "dropped")
    closed += sum(1 for e in entries if e.get("verdict") in ("killed", "closed", "dropped"))
    return {"name": name, "focus": t.get("focus"), "tags": t.get("tags", []),
            "next_candidate": f"C{next_number(t, entries)}",
            "earlier": len(t.get("candidates", [])) + len(entries), "closed": closed,
            "file": track_path(profile, name)}


def short(s, n):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("new"); sp.add_argument("profile"); sp.add_argument("name")
    sp.add_argument("--focus", required=True); sp.add_argument("--tags", default="")
    sp = sub.add_parser("edit"); sp.add_argument("profile"); sp.add_argument("name")
    sp.add_argument("--focus"); sp.add_argument("--tags")
    sp = sub.add_parser("list"); sp.add_argument("profile")
    sp = sub.add_parser("show"); sp.add_argument("profile"); sp.add_argument("name"); sp.add_argument("--max", type=int, default=80)
    sp = sub.add_parser("record"); sp.add_argument("profile"); sp.add_argument("name"); sp.add_argument("out")
    a = p.parse_args(argv)
    profile = os.path.abspath(os.path.expanduser(a.profile))
    tags = lambda s: [x.strip() for x in (s or "").split(",") if x.strip()]

    if a.cmd == "new":
        if load(profile, a.name):
            print(f"track {a.name!r} already exists; use edit", file=sys.stderr)
            return 1
        try:
            create(profile, a.name, a.focus, tags(a.tags))
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 1
        print(f"created track {a.name}")
        return 0

    if a.cmd == "list":
        d = os.path.join(profile, "tracks")
        names = sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json")) if os.path.isdir(d) else []
        if not names:
            print("no tracks")
        for n in names:
            s = summary(profile, n)
            print(f"{n:28} {s['earlier']:3} earlier ({s['closed']} closed) · next {s['next_candidate']} · {short(s['focus'], 90)}")
        return 0

    t = load(profile, a.name)
    if not t:
        print(f"no track {a.name!r} in {profile}/tracks", file=sys.stderr)
        return 1

    if a.cmd == "edit":
        if a.focus:
            t["focus"] = a.focus.strip()
        if a.tags is not None:
            t["tags"] = tags(a.tags)
        save(profile, t)
        print(f"updated track {a.name}")
        return 0

    if a.cmd == "show":
        entries = ledger_entries(profile, a.name)
        print(f"# Track {a.name}")
        print(f"focus: {t.get('focus')}")
        print(f"tags: {', '.join(t.get('tags', [])) or '-'}")
        print(f"next candidate: C{next_number(t, entries)}")
        print("Do not propose any of these again; build on them only as the track's own history.\n")
        rows = [(c.get("run", ""), c.get("id"), c.get("status", "?"), c.get("hypothesis", "")) for c in t.get("candidates", [])]
        rows += [(e.get("date", ""), e.get("id"), e.get("verdict"), e.get("title", "")) for e in entries]
        rows.sort(key=lambda r: str(r[0]), reverse=True)
        for date, cid, status, text in rows[: a.max]:
            print(f"- {date} {cid} [{status}] {short(text, 140)}")
        if len(rows) > a.max:
            print(f"... {len(rows) - a.max} older not shown (--max)")
        return 0

    if a.cmd == "record":
        path = os.path.join(a.out, "candidates.jsonl")
        try:
            with open(path, encoding="utf-8") as fh:
                rows = [json.loads(l) for l in fh if l.strip()]
        except FileNotFoundError:
            print(f"no candidates.jsonl in {a.out}", file=sys.stderr)
            return 1
        known = {c["id"]: c for c in t.get("candidates", [])}
        today = dt.date.today().isoformat()
        added = updated = 0
        for r in rows:
            cid = r.get("id")
            if not cid:
                continue
            hyp = short(r.get("hypothesis") or r.get("title"), 200)
            if cid in known:
                if known[cid].get("hypothesis") != hyp:
                    print(f"WARNING {cid}: already used in this track for another idea; renumber new candidates from "
                          f"C{next_number(t, ledger_entries(profile, a.name))}")
                    continue
                if known[cid].get("status") != r.get("status"):
                    known[cid]["status"] = r.get("status")
                    updated += 1
                continue
            c = {"id": cid, "hypothesis": hyp, "status": r.get("status"), "run": today}
            t.setdefault("candidates", []).append(c)
            known[cid] = c
            added += 1
        t.setdefault("runs", []).append({"date": today, "out": os.path.abspath(a.out), "candidates": len(rows)})
        save(profile, t)
        print(f"recorded {added} new and {updated} updated candidates in track {a.name}; "
              f"next C{next_number(t, ledger_entries(profile, a.name))}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
