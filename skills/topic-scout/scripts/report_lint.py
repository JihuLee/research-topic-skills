#!/usr/bin/env python3
"""report_lint.py - completeness and readability checks for the skills' outputs (stdlib only).

  gate OUT_DIR [--evidence evidence.jsonl] [--threshold N]
      Validates a novelty-gate output folder: gate_summary.json (scores, statuses, named
      evidence for kills, four baselines and a full B0 for PASS and NEAR-MISS candidates,
      search coverage), details.md, evidence ids and tags against evidence.jsonl, and the
      human reports report.md / report.<lang>.md. A single .md file with a ```json
      gate-summary block is still accepted (older layout).
  scout OUT_DIR
      Validates a topic-scout output folder: candidates.jsonl, details.md and the human
      reports.
  human REPORT.md
      Readability checks for any human report (see references/report_style.md): no internal
      codes, raw status words or evidence tags; length; sentence length (warnings).
  brief BRIEF.md [--thresholds thresholds.json] [--min-urls N] [--sections a,b,c]
      Checks a research brief: every <!-- section:ID --> marker present and filled, no
      placeholders (TODO, TBD, ???, {{...}}, <fill ...>), a literature section with enough
      URLs, and the sha256 of the frozen thresholds quoted in the brief.

Exit code 1 if any ERROR. WARNINGs never fail the lint.
"""
import argparse
import json
import os
import re
import sys

STATUSES = {"pass", "near-miss", "killed", "dropped"}
TAGS = {"FT", "ABS", "SEC", "FAIL"}
KILLER_TYPES = {"paper", "classical-equivalence", "theory-forced", "budget", "profile", "ledger", "data", "none"}
BASELINES = ["native", "common_default", "simplest_key_info", "equal_compute"]
B0_KEYS = ["cost", "primary_endpoint", "promote_if", "kill_if", "inconclusive_if", "blocked_if", "known_good"]
FAMILIES = ["A", "B", "C", "D", "E", "F"]
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PLACEHOLDER = re.compile(r"(\bTODO\b|\bTBD\b|\?\?\?|\{\{[^}]*\}\}|<fill[^>]*>|<YYYY-MM-DD>|<(?!!--)[A-Z][A-Za-z /-]{1,40}>)")
LIST_ITEM = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+(.*)$")
LABELS = {"pass": "Recommended", "near-miss": "Near miss", "killed": "Rejected", "dropped": "Removed"}
# Bracketed codes are certainly internal; bare ones may be ordinary words ("full FT", "E5 embeddings").
HUMAN_ERRORS = [
    (re.compile(r"[\[(]\s*E\d{1,3}(?:\s*[,;]\s*E\d{1,3})*\s*[\])]"), "evidence id"),
    (re.compile(r"\[(?:FT|ABS|SEC|FAIL|UNVERIFIED)\]"), "evidence tag"),
    (re.compile(r"\b(?:NEAR-MISS|KILLED|DROPPED)\b"), "raw status word (use the term list)"),
    (re.compile(r"killer_type|gate-summary|gate_summary|coverage matrix"), "internal field name"),
]
HUMAN_WARNINGS = [
    (re.compile(r"(?<![\[(])\bE\d{1,3}\b(?!\s*[\])])"), "possible evidence id"),
    (re.compile(r"(?<!\[)\b(?:FT|SEC)\b(?!\])"), "possible evidence tag"),
    (re.compile(r"\b(?:ledger|lens|lenses|annotated)\b", re.I), "workflow word"),
]
DEFAULT_SECTIONS = ["meta", "problem", "baselines", "reported", "benchmark", "splits", "metrics",
                    "constraints", "resources", "literature", "cutoff", "novelty", "gates", "ops"]


class Lint:
    def __init__(self):
        self.errors, self.warnings = [], []

    def err(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def report(self):
        for w in self.warnings:
            print("WARNING: " + w)
        for e in self.errors:
            print("ERROR: " + e)
        print(f"{len(self.errors)} error(s), {len(self.warnings)} warning(s)")
        return 1 if self.errors else 0


def nonempty(x):
    return x is not None and str(x).strip() != ""


def extract_summary(text):
    m = re.search(r"```json\s+gate-summary\s*\n(.*?)```", text, re.S)
    if not m:
        return None, "no ```json gate-summary block found"
    try:
        return json.loads(m.group(1)), None
    except json.JSONDecodeError as e:
        return None, f"gate-summary is not valid JSON: {e}"


def load_evidence(path):
    ev = {}
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if line.strip():
                o = json.loads(line)
                ev[o.get("id")] = o
    return ev


def strip_code(text):
    return re.sub(r"```.*?```", "", text, flags=re.S)


def check_human(L, path, ids=(), labels=(), english=True):
    name = os.path.basename(path)
    if not os.path.exists(path):
        L.err(f"{name} missing (the human report)")
        return
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    lines = text.count("\n") + 1
    if lines > 150:
        L.err(f"{name}: {lines} lines; keep the human report short (aim for about 60 per candidate)")
    elif lines > 90:
        L.warn(f"{name}: {lines} lines; aim for about 60")
    body = strip_code(text)
    for pat, what in HUMAN_ERRORS:
        for m in pat.finditer(body):
            line = body.count("\n", 0, m.start()) + 1
            L.err(f"{name}:{line}: {what} {m.group(0)!r}; keep it in details.md")
    for pat, what in HUMAN_WARNINGS:
        for m in pat.finditer(body):
            line = body.count("\n", 0, m.start()) + 1
            L.warn(f"{name}:{line}: {what} {m.group(0)!r}; say it in plain words")
    for i in ids:
        if not re.search(r"\b" + re.escape(i) + r"\b", body):
            L.err(f"{name}: candidate {i} not mentioned")
    for lab in labels:
        if lab not in body:
            L.err(f"{name}: verdict label {lab!r} missing (keep the English term in every language)")
    if english:
        prose = re.sub(r"https?://\S+", "", body)
        for sent in re.split(r"(?<=[.!?])\s+|\n", prose):
            words = re.findall(r"[A-Za-z0-9][\w'’-]*", sent)
            if len(words) > 30 and not sent.lstrip().startswith(("|", "#")):
                L.warn(f"{name}: sentence of {len(words)} words; split it (STE: at most 20-25)")


def load_gate_inputs(path):
    """Return (summary, problem, details_text, out_dir) for a folder or a single file."""
    if os.path.isdir(path):
        out = path
        details = os.path.join(out, "details.md")
        dtext = ""
        if os.path.exists(details):
            with open(details, encoding="utf-8") as fh:
                dtext = fh.read()
        js = os.path.join(out, "gate_summary.json")
        if os.path.exists(js):
            try:
                with open(js, encoding="utf-8") as fh:
                    return json.load(fh), None, dtext, out
            except json.JSONDecodeError as e:
                return None, f"gate_summary.json is not valid JSON: {e}", dtext, out
        s, problem = extract_summary(dtext)
        return s, problem, dtext, out
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    s, problem = extract_summary(text)
    return s, problem, text, None


def lint_gate(path, evidence_path=None, threshold=None):
    L = Lint()
    s, problem, text, out = load_gate_inputs(path)
    if out is not None and not os.path.exists(os.path.join(out, "details.md")):
        L.err("details.md missing (the audit record)")
    if problem:
        L.err(problem)
        return L.report()
    if evidence_path is None and out is not None and os.path.exists(os.path.join(out, "evidence.jsonl")):
        evidence_path = os.path.join(out, "evidence.jsonl")
    if s.get("schema") != "novelty-gate/v1":
        L.err("schema must be 'novelty-gate/v1'")
    for k in ("date", "literature_cutoff"):
        if not DATE.match(str(s.get(k, ""))):
            L.err(f"{k} must be YYYY-MM-DD")
    thr = threshold if threshold is not None else s.get("entry_threshold")
    if not (isinstance(thr, int) and 1 <= thr <= 5):
        L.err("entry_threshold must be an int 1-5")
        thr = 4
    cands = s.get("candidates") or []
    if not cands:
        L.err("candidates is empty (report every candidate, including killed ones)")
    ev = load_evidence(evidence_path) if evidence_path else None

    any_pass = False
    for c in cands:
        cid = c.get("id", "?")
        p = f"candidate {cid}: "
        for k in ("id", "title", "claim"):
            if not nonempty(c.get(k)):
                L.err(p + f"missing {k}")
        for k in ("novelty", "feasibility"):
            v = c.get(k)
            if not (isinstance(v, int) and 1 <= v <= 5):
                L.err(p + f"{k} must be an int 1-5")
        st = c.get("status")
        if st not in STATUSES:
            L.err(p + f"status must be one of {sorted(STATUSES)}")
            continue
        kt = c.get("killer_type", "none")
        if kt not in KILLER_TYPES:
            L.err(p + f"killer_type must be one of {sorted(KILLER_TYPES)}")
        nov = c.get("novelty") if isinstance(c.get("novelty"), int) else 0
        priors = c.get("closest_prior") or []
        for pr in priors:
            if pr.get("tag") not in TAGS:
                L.err(p + f"closest_prior {pr.get('title')!r} has tag {pr.get('tag')!r}; use one of {sorted(TAGS)}")
            if not str(pr.get("url", "")).startswith("http"):
                L.err(p + f"closest_prior {pr.get('title')!r} needs an http(s) url")
            elif pr["url"] not in text.split("```json")[0]:
                L.warn(p + f"url of {pr.get('title')!r} is not cited in details.md")
            if ev is not None and pr.get("evidence"):
                e = ev.get(pr["evidence"])
                if not e:
                    L.err(p + f"evidence id {pr['evidence']} not in evidence file")
                elif e.get("tag") != pr.get("tag"):
                    L.err(p + f"evidence {pr['evidence']} tag {e.get('tag')} != report tag {pr.get('tag')}")
        bl = c.get("baselines") or {}
        b0 = c.get("b0") or {}
        if st == "pass":
            any_pass = True
            if nov < thr:
                L.err(p + f"status pass but novelty {nov} < entry_threshold {thr}")
            if isinstance(c.get("feasibility"), int) and c["feasibility"] < 3:
                L.err(p + "status pass needs feasibility >= 3")
            if not any(pr.get("tag") == "FT" for pr in priors):
                L.err(p + "a PASS must be defended against at least one closest prior verified in full text (FT)")
        if st in ("pass", "near-miss"):
            for k in BASELINES:
                if not nonempty(bl.get(k)):
                    L.err(p + f"baselines.{k} missing")
            for k in B0_KEYS:
                if not nonempty(b0.get(k)):
                    L.err(p + f"b0.{k} missing")
            if not priors:
                L.err(p + "closest_prior is empty")
        if st == "near-miss":
            if nov != thr - 1:
                L.warn(p + f"near-miss usually has novelty = entry_threshold - 1 ({thr - 1}); got {nov}")
            if not nonempty(c.get("failing_gate")):
                L.err(p + "failing_gate missing")
        if st == "killed":
            if nov >= thr:
                L.err(p + f"status killed but novelty {nov} >= entry_threshold {thr}")
            if kt == "paper":
                if not priors:
                    L.err(p + "killed by a paper but no closest_prior named (no name, no kill)")
                elif not any(pr.get("tag") in ("FT", "ABS") for pr in priors):
                    L.warn(p + "kill rests only on SEC/FAIL evidence; verify or mark provisional")
            elif kt in ("classical-equivalence", "theory-forced"):
                if not nonempty(c.get("derivation")):
                    L.err(p + f"killer_type {kt} needs a derivation")
            else:
                L.err(p + "killed needs killer_type paper, classical-equivalence or theory-forced")
            if not nonempty(c.get("failing_gate")):
                L.err(p + "failing_gate missing")
        if st == "dropped":
            if kt not in ("budget", "profile", "ledger", "data"):
                L.err(p + "dropped needs an objective killer_type: budget, profile, ledger or data")
            if not nonempty(c.get("failing_gate")):
                L.err(p + "failing_gate missing (state the objective reason)")

    verdict = s.get("verdict")
    if verdict not in ("pass", "none"):
        L.err("verdict must be 'pass' or 'none'")
    elif (verdict == "pass") != any_pass:
        L.err(f"verdict {verdict!r} inconsistent with candidate statuses")

    if out is not None:
        ids = [c.get("id") for c in cands if c.get("id")]
        labels = sorted({LABELS[c["status"]] for c in cands if c.get("status") in LABELS})
        check_human(L, os.path.join(out, "report.md"), ids, labels, english=True)
        for f in sorted(os.listdir(out)):
            if re.match(r"^report\.[a-z]{2}\.md$", f):
                check_human(L, os.path.join(out, f), ids, labels, english=False)

    cov = s.get("coverage") or []
    if not cov:
        L.err("coverage is empty (record claims x query families A-F)")
    for row in cov:
        for f in FAMILIES:
            v = str(row.get(f, ""))
            if not v:
                L.err(f"coverage {row.get('claim', '?')}: family {f} missing")
            elif v.startswith("failed") and len(v) < 8:
                L.warn(f"coverage {row.get('claim', '?')}: family {f} failed without a reason")
            elif not (v.startswith("done") or v.startswith("failed") or v.startswith("n/a")):
                L.warn(f"coverage {row.get('claim', '?')}: family {f} value {v!r} should start with done/failed/n/a")
    return L.report()


def unfilled_fields(body):
    """Labels ending with ':' that have no content, and empty table cells."""
    out = []
    lines = [l.rstrip() for l in body.splitlines()]
    nonblank = [(i, l) for i, l in enumerate(lines) if l.strip() and not l.strip().startswith("<!--")]
    for k, (i, l) in enumerate(nonblank):
        s = l.strip()
        if s.startswith("|"):
            if re.match(r"^\|[\s:|-]+\|$", s):
                continue  # header separator
            cells = [c.strip() for c in s.strip("|").split("|")]
            if any(c == "" for c in cells):
                out.append(f"empty table cell: {s[:70]}")
            continue
        if s.startswith("#") or not s.endswith(":"):
            continue
        nxt = nonblank[k + 1][1] if k + 1 < len(nonblank) else ""
        if nxt and not nxt.strip().startswith("#"):
            cur_indent = len(l) - len(l.lstrip())
            nxt_indent = len(nxt) - len(nxt.lstrip())
            m_cur, m_nxt = LIST_ITEM.match(l), LIST_ITEM.match(nxt)
            if nxt_indent > cur_indent:
                continue  # indented child content (sub-list or continuation)
            if m_cur is None and (m_nxt is not None or nxt.strip().startswith("|")):
                continue  # plain label introducing a list or a table
            if m_cur is None and m_nxt is None and not nxt.strip().endswith(":"):
                continue  # plain label followed by a paragraph
        out.append(f"unfilled field: {s[:70]}")
    return out


def lint_scout(out):
    L = Lint()
    cpath = os.path.join(out, "candidates.jsonl")
    cands = []
    if not os.path.exists(cpath):
        L.err("candidates.jsonl missing")
    else:
        with open(cpath, encoding="utf-8") as fh:
            for n, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                try:
                    c = json.loads(line)
                except json.JSONDecodeError as e:
                    L.err(f"candidates.jsonl:{n}: invalid JSON: {e}")
                    continue
                for k in ("id", "source", "level", "status", "hypothesis"):
                    if not nonempty(c.get(k)):
                        L.err(f"candidates.jsonl:{n}: missing {k}")
                cands.append(c)
        idl = [c.get("id") for c in cands]
        if len(set(idl)) != len(idl):
            L.err("candidates.jsonl: duplicate ids")
    if not os.path.exists(os.path.join(out, "details.md")):
        L.err("details.md missing (the audit record)")
    ranked = sorted((c for c in cands if c.get("status") != "dropped"), key=lambda c: -(c.get("rank") or 0))
    top = [c["id"] for c in ranked[:3] if c.get("id")]
    gated = [c["id"] for c in cands if c.get("status") == "gated" and c.get("id")]
    ids = sorted(set(top + gated))
    check_human(L, os.path.join(out, "report.md"), ids, (), english=True)
    if os.path.isdir(out):
        for f in sorted(os.listdir(out)):
            if re.match(r"^report\.[a-z]{2}\.md$", f):
                check_human(L, os.path.join(out, f), ids, (), english=False)
    return L.report()


def lint_human(path):
    L = Lint()
    lang = re.match(r"^report\.([a-z]{2})\.md$", os.path.basename(path))
    check_human(L, path, english=not lang)
    return L.report()


def lint_brief(path, thresholds=None, min_urls=3, sections=None):
    L = Lint()
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    sections = sections or DEFAULT_SECTIONS
    marks = list(re.finditer(r"<!--\s*section:([\w-]+)\s*-->", text))
    if not marks:
        L.warn("no <!-- section:ID --> markers; only placeholder and URL checks were run")
    found = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        found[m.group(1)] = text[m.end():end]
    if marks:
        for sid in sections:
            if sid not in found:
                L.err(f"section {sid!r} missing")
            else:
                body = re.sub(r"<!--.*?-->", "", found[sid], flags=re.S)
                stripped = re.sub(r"^#+.*$", "", body, flags=re.M).strip()
                if len(stripped) < 20:
                    L.err(f"section {sid!r} looks empty")
                for problem in unfilled_fields(body):
                    L.err(f"section {sid!r}: {problem}")
    for m in PLACEHOLDER.finditer(text):
        line = text.count("\n", 0, m.start()) + 1
        L.err(f"placeholder {m.group(0)!r} at line {line}")
    lit = found.get("literature", text)
    urls = set(re.findall(r"https?://[^\s)>\]]+", lit))
    if len(urls) < min_urls:
        L.err(f"literature section has {len(urls)} URL(s); need >= {min_urls} (downstream agents may lack web access)")
    if thresholds:
        sha_file = thresholds + ".sha256"
        if not os.path.exists(sha_file):
            L.err(f"{sha_file} not found; run freeze.py freeze {thresholds}")
        else:
            with open(sha_file, encoding="utf-8") as fh:
                h = fh.read().split()[0]
            if h not in text:
                L.err(f"frozen thresholds hash {h[:12]}... not quoted in the brief")
    return L.report()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("gate"); sp.add_argument("report", help="output folder (or an older single report file)")
    sp.add_argument("--evidence"); sp.add_argument("--threshold", type=int)
    sp = sub.add_parser("brief"); sp.add_argument("brief")
    sp.add_argument("--thresholds"); sp.add_argument("--min-urls", type=int, default=3)
    sp.add_argument("--sections", help="comma-separated section ids (default: the bundled template's)")
    sp = sub.add_parser("scout"); sp.add_argument("out_dir")
    sp = sub.add_parser("human"); sp.add_argument("report")
    a = p.parse_args(argv)
    if a.cmd == "scout":
        return lint_scout(a.out_dir)
    if a.cmd == "human":
        return lint_human(a.report)
    if a.cmd == "gate":
        return lint_gate(a.report, a.evidence, a.threshold)
    secs = [x.strip() for x in a.sections.split(",")] if a.sections else None
    return lint_brief(a.brief, a.thresholds, a.min_urls, secs)


if __name__ == "__main__":
    sys.exit(main())
