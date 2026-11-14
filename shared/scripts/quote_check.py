#!/usr/bin/env python3
"""quote_check.py - verify that logged quotes really occur in the cited full text (stdlib only).

  quote_check.py EVIDENCE.jsonl [--base DIR] [--min-ratio 0.92]

Each evidence line has at least: id, tag, quote, source (path of the extracted text,
relative to --base, default: the evidence file's directory). Text is normalised before
matching (Unicode NFKC so ligatures like "fi" match, quotes and dashes unified, hyphenated
line breaks joined, whitespace collapsed, case folded). If there is no exact match, the quote
is aligned to the closest passage and scored as 2*matched/(len(quote)+len(passage)). A fuzzy
match is rejected whatever its ratio when the differing words include a negation, a number or
a comparison word ("not", "15%", "lower"), because those flip the meaning.

Exit 1 if any FT quote is not found at --min-ratio or better: fix the quote or downgrade
the tag to SEC. ABS entries are checked when a source is given; SEC and FAIL entries are
only counted.
"""
import argparse
import json
import os
import re
import sys
import unicodedata
from collections import Counter
from difflib import SequenceMatcher

TRANS = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-",
    "−": "-", " ": " ", "­": "",
})


def normalise(s):
    s = unicodedata.normalize("NFKC", s).translate(TRANS)
    s = re.sub(r"=== page \d+ ===", " ", s)
    s = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


NEGATIONS = {"not", "no", "never", "none", "nor", "neither", "without", "cannot", "unlike", "except", "fails", "fail"}
POLARITY = {"more", "less", "fewer", "higher", "lower", "better", "worse", "larger", "smaller", "above", "below",
            "increase", "increases", "decrease", "decreases", "improves", "degrades", "outperforms", "underperforms"}


def best_fuzzy(quote, text):
    """Best alignment of quote against passages around its rarest long words: (ratio, passage)."""
    words = sorted(set(re.findall(r"\w{6,}", quote)), key=len, reverse=True)[:4]
    n = len(quote)
    anchors = []
    for w in words:
        start = 0
        while len(anchors) <= 400:
            i = text.find(w, start)
            if i < 0:
                break
            anchors.append(i)
            start = i + 1
    if not anchors:
        anchors = range(0, max(1, len(text) - n) + 1, max(1, n // 3))
    best, passage, seen = 0.0, "", set()
    for a in anchors:
        lo, hi = max(0, a - n - 40), min(len(text), a + n + 40)
        if (lo, hi) in seen:
            continue
        seen.add((lo, hi))
        region = text[lo:hi]
        blocks = [b for b in SequenceMatcher(None, quote, region, autojunk=False).get_matching_blocks() if b.size]
        while len(blocks) > 1 and blocks[0].size < 3:
            blocks.pop(0)
        while len(blocks) > 1 and blocks[-1].size < 3:
            blocks.pop()
        if not blocks:
            continue
        matched = sum(b.size for b in blocks)
        span = region[blocks[0].b:blocks[-1].b + blocks[-1].size]
        r = 2.0 * matched / (n + len(span))
        if r > best:
            best, passage = r, span
    return best, passage


def risky_differences(quote, passage):
    """Words that differ between quote and passage and can flip the meaning."""
    tok = lambda s: re.findall(r"[\w%.]+", s)
    q, p = tok(quote), tok(passage)
    diff = []
    for op, i1, i2, j1, j2 in SequenceMatcher(None, q, p, autojunk=False).get_opcodes():
        if op != "equal":
            diff += q[i1:i2] + p[j1:j2]
    return sorted({w for w in diff if w in NEGATIONS or w in POLARITY or w.endswith("n't") or re.search(r"\d", w)})


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("evidence")
    p.add_argument("--base")
    p.add_argument("--min-ratio", type=float, default=0.92)
    a = p.parse_args(argv)
    base = a.base or os.path.dirname(os.path.abspath(a.evidence))
    cache = {}
    counts = Counter()
    failures = 0
    with open(a.evidence, encoding="utf-8") as fh:
        rows = [json.loads(l) for l in fh if l.strip()]
    for r in rows:
        tag = r.get("tag", "?")
        counts[tag] += 1
        rid = r.get("id", "?")
        if tag not in ("FT", "ABS"):
            continue
        src, quote = r.get("source"), r.get("quote")
        if not src or not quote:
            msg = f"{rid} [{tag}]: no source or quote; cannot verify"
            if tag == "FT":
                failures += 1
                print("FAIL  " + msg)
            else:
                print("WARN  " + msg)
            continue
        path = src if os.path.isabs(src) else os.path.join(base, src)
        if path not in cache:
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    cache[path] = normalise(fh.read())
            except FileNotFoundError:
                cache[path] = None
        text = cache[path]
        if text is None:
            failures += tag == "FT"
            print(f"{'FAIL' if tag == 'FT' else 'WARN'}  {rid} [{tag}]: source not found: {path}")
            continue
        q = normalise(quote)
        if q in text:
            print(f"OK    {rid} [{tag}]: exact")
            continue
        ratio, passage = best_fuzzy(q, text)
        risky = risky_differences(q, passage) if ratio >= a.min_ratio else []
        if ratio >= a.min_ratio and not risky:
            print(f"OK    {rid} [{tag}]: fuzzy {ratio:.2f}")
        elif risky:
            failures += tag == "FT"
            print(f"{'FAIL' if tag == 'FT' else 'WARN'}  {rid} [{tag}]: close ({ratio:.2f}) but differs in "
                  f"{', '.join(risky)}; quote the passage exactly")
        else:
            failures += tag == "FT"
            print(f"{'FAIL' if tag == 'FT' else 'WARN'}  {rid} [{tag}]: not found (best {ratio:.2f}) in {src}")
    print("tags: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) + f"; FT failures: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
