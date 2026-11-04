#!/usr/bin/env python3
"""quote_check.py - verify that logged quotes really occur in the cited full text (stdlib only).

  quote_check.py EVIDENCE.jsonl [--base DIR] [--min-ratio 0.92]

Each evidence line has at least: id, tag, quote, source (path of the extracted text,
relative to --base, default: the evidence file's directory). Text is normalised before
matching (Unicode NFKC so ligatures like "fi" match, quotes and dashes unified, hyphenated
line breaks joined, whitespace collapsed, case folded). If there is no exact match, a fuzzy
window search reports the best ratio.

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


def best_fuzzy(quote, text):
    """Best SequenceMatcher ratio of quote against windows anchored on its rarest long words."""
    words = sorted(set(re.findall(r"\w{6,}", quote)), key=len, reverse=True)[:4]
    n = len(quote)
    best = 0.0
    anchors = []
    for w in words:
        start = 0
        while True:
            i = text.find(w, start)
            if i < 0 or len(anchors) > 400:
                break
            anchors.append(i)
            start = i + 1
    if not anchors:
        anchors = range(0, max(1, len(text) - n), max(1, n // 3))
    for a in anchors:
        for lo in (a - n, a - n // 2, a - n // 4, a):
            lo = max(0, lo)
            r = SequenceMatcher(None, quote, text[lo:lo + n + n // 5]).ratio()
            if r > best:
                best = r
    return best


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
        ratio = best_fuzzy(q, text)
        if ratio >= a.min_ratio:
            print(f"OK    {rid} [{tag}]: fuzzy {ratio:.2f}")
        else:
            failures += tag == "FT"
            print(f"{'FAIL' if tag == 'FT' else 'WARN'}  {rid} [{tag}]: not found (best {ratio:.2f}) in {src}")
    print("tags: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) + f"; FT failures: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
