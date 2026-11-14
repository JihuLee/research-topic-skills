#!/usr/bin/env python3
"""lessons.py - keep a profile's lessons.md small and useful (Python stdlib only).

Lesson format (one top-level bullet; indented lines below it belong to it):

  - [L12|scoped|diffusion,metrics|h3/x0/n7] Check: <one checkable sentence>
    - optional detail lines

  tier     pinned (always applied, never proposed for archiving), core (always applied),
           scoped (applied only when a candidate shares a tag)
  h/x/n    times the check caught something / raised a false alarm / was applied

Plain bullets without the bracket header are "unmarked": they are applied as core until a
review gives them an id (op "adopt"). Headings and other text are kept as they are.

Files in the profile directory: lessons.md, lessons_archive.md (archived lessons are moved
there, never deleted) and lessons_state.json (tallied gate runs, gates since the last review).

Subcommands (PROFILE is the profile directory)
  list PROFILE [--tier T] [--tags a,b]       one line per lesson
  select PROFILE [--tags a,b]                full text of the lessons to apply in a gate run:
                                             pinned + core + unmarked + scoped lessons sharing a tag
  similar PROFILE --text TEXT [--top K]      closest existing lessons (also archived), for add/edit/no-op
  apply PROFILE PLAN.json [--dry-run]        apply delta operations (never rewrites other lessons):
      {"op": "add", "text": "Check: ...", "tier": "scoped", "tags": ["x"], "sub": ["detail"], "section": "Heading"}
      {"op": "edit", "id": "L3", "text": "...", "tier": "core", "tags": ["x"], "sub": [...]}   (any subset)
      {"op": "adopt", "ref": "U2", "tier": "scoped", "tags": ["x"]}      give an unmarked lesson an id
      {"op": "archive", "id": "L3", "reason": "..."}                     ("ref": "U4" archives an unmarked one)
      U-refs (U1, U2, ...) always refer to the numbering when the plan starts.
      {"op": "merge", "into": "L3", "ids": ["L7", "L9"], "text": "optional new text"}
  tally PROFILE OUT_DIR [OUT_DIR ...]        add each gate run's lesson results to the counters
                                             (gate_summary.json "lessons": [{"id", "result"}]);
                                             a run is counted once; prints whether a review is due
  review PROFILE [--json]                    tidy-up candidates: unmarked, near-duplicates, never caught,
                                             false alarms, promotions, core over its cap
  mark-reviewed PROFILE                      reset the review counter after a tidy-up

Thresholds come from profile.md (lessons_core_cap 20, lessons_review_every_gates 20,
lessons_max_active 40 by default). A review is due when gates since the last review reach
lessons_review_every_gates, active lessons exceed lessons_max_active, or pinned + core
lessons exceed lessons_core_cap.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ledger import similarity  # noqa: E402  (same folder; word + trigram similarity)

HEAD = re.compile(r"^- \[(L\d+)\|(pinned|core|scoped)\|([^|\]]*)\|h(\d+)/x(\d+)/n(\d+)\]\s?(.*)$")
PLAIN = re.compile(r"^- (?!\[L\d+\|)(.*\S.*)$")
TIERS = ("pinned", "core", "scoped")
RESULTS = {"caught", "clear", "n/a", "false_alarm"}
DEFAULTS = {"lessons_core_cap": 20, "lessons_review_every_gates": 20, "lessons_max_active": 40}
DUP_MIN = 0.45


class Lesson:
    def __init__(self, lid, tier, tags, h, x, n, text, sub, start, end, unmarked=False):
        self.id, self.tier, self.tags = lid, tier, tags
        self.h, self.x, self.n = h, x, n
        self.text, self.sub = text, sub
        self.start, self.end, self.unmarked = start, end, unmarked

    def header(self):
        return f"- [{self.id}|{self.tier}|{','.join(self.tags)}|h{self.h}/x{self.x}/n{self.n}] {self.text}"

    def block(self):
        return [self.header()] + self.sub

    def one_line(self):
        tags = ",".join(self.tags) or "-"
        return f"{self.id:5} {self.tier:7} {tags:24} h{self.h}/x{self.x}/n{self.n}  {self.text[:110]}"


def paths(profile):
    return (os.path.join(profile, "lessons.md"), os.path.join(profile, "lessons_archive.md"),
            os.path.join(profile, "lessons_state.json"))


def read_lines(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read().split("\n")
    except FileNotFoundError:
        return []


def parse(lines):
    """Return lessons in file order. Unmarked bullets get ids U1, U2, ... (not stored)."""
    out, i, u = [], 0, 0
    in_comment = False
    while i < len(lines):
        line = lines[i]
        if "<!--" in line and "-->" not in line:
            in_comment = True
        if in_comment:
            if "-->" in line:
                in_comment = False
            i += 1
            continue
        m, pm = HEAD.match(line), PLAIN.match(line)
        if not (m or pm):
            i += 1
            continue
        j = i + 1
        while j < len(lines) and lines[j].strip() and lines[j][:1] in (" ", "\t"):
            j += 1
        sub = lines[i + 1:j]
        if m:
            tags = [t.strip() for t in m.group(3).split(",") if t.strip()]
            text = re.sub(r"\s*<!--.*?-->\s*$", "", m.group(7)).strip()
            out.append(Lesson(m.group(1), m.group(2), tags, int(m.group(4)), int(m.group(5)), int(m.group(6)),
                              text, sub, i, j))
        else:
            u += 1
            out.append(Lesson(f"U{u}", "core", [], 0, 0, 0, pm.group(1).strip(), sub, i, j, unmarked=True))
        i = j
    return out


def thresholds(profile):
    t = dict(DEFAULTS)
    try:
        with open(os.path.join(profile, "profile.md"), encoding="utf-8") as fh:
            m = re.search(r"```json\s+profile\s*\n(.*?)```", fh.read(), re.S)
        if m:
            c = json.loads(m.group(1))
            for k in DEFAULTS:
                if isinstance(c.get(k), int) and c[k] > 0:
                    t[k] = c[k]
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return t


def load_state(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"tallied": [], "gates_since_review": 0, "last_review": None}


def save_state(path, state):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)
        fh.write("\n")


def split_tags(s):
    return {t.strip().lower() for t in (s or "").split(",") if t.strip()}


def due(profile, lessons, state):
    t = thresholds(profile)
    reasons = []
    if state.get("gates_since_review", 0) >= t["lessons_review_every_gates"]:
        reasons.append(f"{state['gates_since_review']} gate runs since the last review "
                       f"(every {t['lessons_review_every_gates']})")
    if len(lessons) > t["lessons_max_active"]:
        reasons.append(f"{len(lessons)} active lessons (more than {t['lessons_max_active']})")
    always = sum(1 for l in lessons if l.tier in ("pinned", "core"))
    if always > t["lessons_core_cap"]:
        reasons.append(f"{always} pinned + core lessons (cap {t['lessons_core_cap']})")
    return reasons


def next_id(lessons, archived):
    nums = [int(l.id[1:]) for l in lessons + archived if l.id.startswith("L")]
    return f"L{max(nums, default=0) + 1}"


def cmd_list(a, lessons):
    want = split_tags(a.tags)
    for l in lessons:
        if a.tier and l.tier != a.tier:
            continue
        if want and not (want & {t.lower() for t in l.tags}):
            continue
        print(l.one_line())
    return 0


def cmd_select(a, lessons):
    want = split_tags(a.tags)
    always = [l for l in lessons if l.tier in ("pinned", "core")]
    scoped = [l for l in lessons if l.tier == "scoped" and want & {t.lower() for t in l.tags}]
    skipped = [l for l in lessons if l.tier == "scoped" and l not in scoped]
    print(f"# Lessons to apply: {len(always)} always + {len(scoped)} matching tags {sorted(want) or '-'}")
    print("# Record each id's result (caught, clear, n/a, false_alarm) in gate_summary.json under \"lessons\".\n")
    for l in always + scoped:
        print("\n".join(l.block()))
    if skipped:
        tags = sorted({t for l in skipped for t in l.tags})
        print(f"\n# Not selected: {len(skipped)} scoped lessons. Their tags: {', '.join(tags)}")
    return 0


def cmd_similar(a, lessons, archived):
    pool = [(l, "") for l in lessons] + [(l, " (archived)") for l in archived]
    scored = sorted(((similarity(a.text, l.text + " " + " ".join(l.sub)), l, tag) for l, tag in pool), key=lambda x: -x[0])
    for s, l, tag in scored[: a.top]:
        print(f"{s:.2f}  {l.id}{tag} [{l.tier}] {l.text[:120]}")
    if not scored:
        print("no lessons yet")
    return 0


def archive_block(l, reason):
    today = dt.date.today().isoformat()
    return [l.header() + f"  <!-- archived {today}: {reason} -->"] + l.sub


def cmd_apply(a, profile):
    lp, ap, _ = paths(profile)
    lines = read_lines(lp)
    with open(a.plan, encoding="utf-8") as fh:
        plan = json.load(fh)
    if isinstance(plan, dict):
        plan = plan.get("ops", [])
    archived_lines = read_lines(ap)
    to_archive, log = [], []
    # U-refs always mean the numbering at the start of the plan, even after earlier ops
    umap = {l.id: l.text for l in parse(lines) if l.unmarked}
    for k, op in enumerate(plan, 1):
        lessons = parse(lines)
        archived = parse(archived_lines)
        by_id = {l.id: l for l in lessons if not l.unmarked}
        for l in lessons:
            if l.unmarked:
                for ref, text in umap.items():
                    if text == l.text and ref not in by_id:
                        by_id[ref] = l
                        break
        kind = op.get("op")
        if kind == "add":
            tier = op.get("tier", "scoped")
            if tier not in TIERS or not str(op.get("text", "")).strip():
                raise SystemExit(f"op {k}: add needs text and a tier in {TIERS}")
            new = Lesson(next_id(lessons, archived), tier, list(op.get("tags", [])),
                         0, 0, 0, op["text"].strip(), ["  - " + s for s in op.get("sub", [])], 0, 0)
            at = len(lines)
            placed = not op.get("section")
            if op.get("section"):
                for i, line in enumerate(lines):
                    if line.lstrip("#").strip() == op["section"].strip() and line.startswith("#"):
                        at = i + 1
                        while at < len(lines) and not lines[at].startswith("#"):
                            at += 1
                        while at > i + 1 and not lines[at - 1].strip():
                            at -= 1
                        placed = True
                        break
            if not placed:
                log.append(f"NOTE section {op['section']!r} not found; added at the end")
            while at == len(lines) and lines and not lines[-1].strip():
                lines.pop()
                at = len(lines)
            lines[at:at] = new.block()
            log.append(f"ADD {new.id} [{new.tier}] {new.text[:80]}")
        elif kind in ("edit", "adopt"):
            ref = op.get("id") or op.get("ref")
            l = by_id.get(ref)
            if not l:
                raise SystemExit(f"op {k}: {ref!r} not found")
            if kind == "adopt":
                if not l.unmarked:
                    raise SystemExit(f"op {k}: {ref} already has an id")
                l.id = next_id(lessons, archived)
                l.unmarked = False
            if "text" in op:
                l.text = op["text"].strip()
            if "tier" in op:
                if op["tier"] not in TIERS:
                    raise SystemExit(f"op {k}: tier must be one of {TIERS}")
                l.tier = op["tier"]
            if "tags" in op:
                l.tags = list(op["tags"])
            if "sub" in op:
                l.sub = ["  - " + s for s in op["sub"]]
            lines[l.start:l.end] = l.block()
            log.append(f"{kind.upper()} {ref}" + (f" -> {l.id}" if kind == "adopt" else "") + f" [{l.tier}] {l.text[:70]}")
        elif kind == "archive":
            ref = op.get("id") or op.get("ref")
            l = by_id.get(ref)
            if not l:
                raise SystemExit(f"op {k}: {ref!r} not found")
            if not op.get("reason"):
                raise SystemExit(f"op {k}: archive needs a reason")
            if l.unmarked:
                l.id, l.unmarked = next_id(lessons, archived), False
            del lines[l.start:l.end]
            to_archive.append(l)
            archived_lines += archive_block(l, op["reason"])
            log.append(f"ARCHIVE {ref}" + (f" (as {l.id})" if ref != l.id else "") + f": {op['reason']}")
        elif kind == "merge":
            into = by_id.get(op.get("into"))
            ids = op.get("ids") or []
            if not into or not ids or any(i not in by_id or by_id[i].unmarked or i == into.id for i in ids):
                raise SystemExit(f"op {k}: merge needs an existing 'into' id and other existing 'ids'")
            for i in ids:
                into.h += by_id[i].h; into.x += by_id[i].x; into.n += by_id[i].n
                into.tags = into.tags + [t for t in by_id[i].tags if t not in into.tags]
            if op.get("text"):
                into.text = op["text"].strip()
            new_into = into.block()
            for i in sorted(ids, key=lambda i: -by_id[i].start):
                l = by_id[i]
                archived_lines += archive_block(l, f"merged into {into.id}")
                to_archive.append(l)
            # replace blocks from the bottom up so positions stay valid
            spans = sorted([(by_id[i].start, by_id[i].end, None) for i in ids] + [(into.start, into.end, new_into)],
                           key=lambda x: -x[0])
            for s0, e0, repl in spans:
                lines[s0:e0] = repl or []
            log.append(f"MERGE {', '.join(ids)} -> {into.id}")
        else:
            raise SystemExit(f"op {k}: unknown op {kind!r}")
    for entry in log:
        print(("DRY-RUN " if a.dry_run else "") + entry)
    if a.dry_run:
        return 0
    with open(lp, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines).rstrip("\n") + "\n")
    if to_archive:
        if not any(l.startswith("# ") for l in archived_lines):
            archived_lines = ["# Archived lessons", "", "Moved here by lessons.py; never applied. "
                              "Restore one by copying it back into lessons.md.", ""] + archived_lines
        with open(ap, "w", encoding="utf-8") as fh:
            fh.write("\n".join(archived_lines).rstrip("\n") + "\n")
    return 0


def cmd_tally(a, profile, lessons_lines):
    lp, _, sp = paths(profile)
    state = load_state(sp)
    lessons = parse(lessons_lines)
    by_id = {l.id: l for l in lessons}
    changed = False
    for out in a.out_dirs:
        path = os.path.join(out, "gate_summary.json") if os.path.isdir(out) else out
        try:
            with open(path, "rb") as fh:
                raw = fh.read()
        except FileNotFoundError:
            print(f"SKIP {out}: no gate_summary.json")
            continue
        digest = hashlib.sha256(raw).hexdigest()
        if digest in state["tallied"]:
            print(f"SKIP {out}: already tallied")
            continue
        summary = json.loads(raw)
        counts = {"caught": 0, "clear": 0, "false_alarm": 0, "n/a": 0}
        for r in summary.get("lessons") or []:
            l, res = by_id.get(r.get("id")), r.get("result")
            if res not in RESULTS:
                print(f"WARNING {out}: {r.get('id')} has result {res!r}; ignored")
                continue
            counts[res] += 1
            if not l or l.unmarked:
                continue
            if res != "n/a":
                l.n += 1
            l.h += res == "caught"
            l.x += res == "false_alarm"
            changed = True
        state["tallied"].append(digest)
        state["gates_since_review"] = state.get("gates_since_review", 0) + 1
        print(f"TALLIED {out}: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    if changed:
        lines = list(lessons_lines)
        for l in sorted(lessons, key=lambda l: -l.start):
            if not l.unmarked:
                lines[l.start:l.start + 1] = [l.header()]
        with open(lp, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines).rstrip("\n") + "\n")
    save_state(sp, state)
    reasons = due(profile, parse(read_lines(lp)), state)
    print("REVIEW DUE: " + "; ".join(reasons) if reasons else "review not due")
    return 0


def cmd_review(a, profile, lessons, state):
    t = thresholds(profile)
    found = {"due": due(profile, lessons, state), "unmarked": [], "near_duplicates": [], "never_caught": [],
             "false_alarms": [], "promote": [], "core_over_cap": []}
    for l in lessons:
        if l.unmarked:
            found["unmarked"].append({"ref": l.id, "text": l.text[:160]})
        elif l.tier != "pinned" and l.n >= 5 and l.h == 0:
            found["never_caught"].append({"id": l.id, "applied": l.n, "text": l.text[:160]})
        if not l.unmarked and l.x >= 2 and l.x >= l.h:
            found["false_alarms"].append({"id": l.id, "h": l.h, "x": l.x, "text": l.text[:160]})
        if l.tier == "scoped" and l.h >= 3:
            found["promote"].append({"id": l.id, "h": l.h, "text": l.text[:160]})
    for i, l1 in enumerate(lessons):
        for l2 in lessons[i + 1:]:
            s = similarity(l1.text + " " + " ".join(l1.sub), l2.text + " " + " ".join(l2.sub))
            if s >= DUP_MIN:
                found["near_duplicates"].append({"ids": [l1.id, l2.id], "score": round(s, 2)})
    always = [l for l in lessons if l.tier in ("pinned", "core")]
    if len(always) > t["lessons_core_cap"]:
        found["core_over_cap"] = [{"id": l.id, "h": l.h, "n": l.n, "text": l.text[:100]}
                                  for l in sorted(always, key=lambda l: (l.tier == "pinned", l.h, -l.n))]
    if a.json:
        print(json.dumps(found, ensure_ascii=False, indent=2))
        return 0
    print("Review due: " + ("; ".join(found["due"]) if found["due"] else "no"))
    print(f"{len(lessons)} active lessons ({len(always)} pinned + core, cap {t['lessons_core_cap']}); "
          f"{state.get('gates_since_review', 0)} gate runs since the last review")
    labels = {"unmarked": "Unmarked (give an id with op adopt)", "near_duplicates": "Possible duplicates (merge?)",
              "never_caught": "Applied 5+ times, never caught anything (archive, unless it guards a rare failure)",
              "false_alarms": "Raised false alarms at least as often as real catches (edit or archive?)",
              "promote": "Scoped lessons that caught 3+ times (promote to core?)",
              "core_over_cap": "Pinned + core over the cap (demote the least useful to scoped)"}
    for k, label in labels.items():
        if found[k]:
            print(f"\n## {label}")
            for item in found[k]:
                print("- " + json.dumps(item, ensure_ascii=False))
    print("\nAlso check by reading: lessons that only restate a rule the skill already enforces "
          "(archive as 'covered by the skill').")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("list"); sp.add_argument("profile"); sp.add_argument("--tier", choices=TIERS); sp.add_argument("--tags", default="")
    sp = sub.add_parser("select"); sp.add_argument("profile"); sp.add_argument("--tags", default="")
    sp = sub.add_parser("similar"); sp.add_argument("profile"); sp.add_argument("--text", required=True)
    sp.add_argument("--top", type=int, default=5)
    sp = sub.add_parser("apply"); sp.add_argument("profile"); sp.add_argument("plan"); sp.add_argument("--dry-run", action="store_true")
    sp = sub.add_parser("tally"); sp.add_argument("profile"); sp.add_argument("out_dirs", nargs="+")
    sp = sub.add_parser("review"); sp.add_argument("profile"); sp.add_argument("--json", action="store_true")
    sp = sub.add_parser("mark-reviewed"); sp.add_argument("profile")
    a = p.parse_args(argv)

    profile = os.path.abspath(os.path.expanduser(a.profile))
    lp, ap, sp_ = paths(profile)
    lines = read_lines(lp)
    lessons = parse(lines)
    if a.cmd == "list":
        return cmd_list(a, lessons)
    if a.cmd == "select":
        return cmd_select(a, lessons)
    if a.cmd == "similar":
        return cmd_similar(a, lessons, parse(read_lines(ap)))
    if a.cmd == "apply":
        return cmd_apply(a, profile)
    if a.cmd == "tally":
        return cmd_tally(a, profile, lines)
    if a.cmd == "review":
        return cmd_review(a, profile, lessons, load_state(sp_))
    if a.cmd == "mark-reviewed":
        state = load_state(sp_)
        state["gates_since_review"] = 0
        state["last_review"] = dt.date.today().isoformat()
        save_state(sp_, state)
        print("review recorded; counter reset")
        return 0


if __name__ == "__main__":
    sys.exit(main())
