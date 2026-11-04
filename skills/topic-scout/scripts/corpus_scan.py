#!/usr/bin/env python3
"""corpus_scan.py - index a researcher's corpus for idea generation (stdlib; PDFs need pymupdf).

  corpus_scan.py PATH [PATH ...] [--out FILE] [--max-per-pattern 25] [--exclude SUBSTR ...]

Finds leads, not findings:
  theory  : assumptions, simplifications, approximations, distributional assumptions,
            limitations / future work, empirical or hand-tuned choices (papers, notes)
  code    : clamps/clips, stop-gradients, epsilons, magic constants, schedules, scaling knobs,
            hack markers, special-case guards (Python, notebooks)
  hotspot : heavy linear-algebra or search calls inside loops (Python AST)
  record  : verdicts, closest priors, lessons, pilots/B0 in notes and past reports
Read the hits that matter; the scan only tells you where to look.
"""
import argparse
import ast
import json
import os
import re
import sys
from collections import defaultdict

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "env", "build", "dist",
             ".ipynb_checkpoints", ".mypy_cache", ".pytest_cache", "site-packages", "wandb", "outputs"}
TEXT_EXT = {".tex", ".md", ".txt", ".rst", ".org"}
CODE_EXT = {".py"}
MAX_BYTES = 3_000_000

THEORY = [
    ("assumption", r"\b(we assume|assume that|assumption|under the assumption|is assumed)\b|가정"),
    ("simplification", r"\b(for simplicity|without loss of generality|w\.l\.o\.g\.|we ignore|we neglect|we omit)\b|단순화"),
    ("approximation", r"\b(approximat\w*|first[- ]order|second[- ]order|taylor|lineari[sz]\w*|surrogate|relax\w*|upper bound|lower bound)\b|근사"),
    ("distributional", r"\b(i\.i\.d\.|iid|isotropic|homoscedastic|stationar\w*)\b"),
    ("limitation", r"\b(limitations?|we leave|future work|beyond the scope|does not (?:hold|handle|apply)|fails? when)\b|한계|향후"),
    ("empirical-choice", r"\b(empirically|in practice|heuristic\w*|we found that|ad[- ]hoc|hand[- ]tuned)\b|경험적"),
]
CODE = [
    ("clamp/clip", r"\b(clamp|clip|clip_grad\w*|nan_to_num|isfinite|isnan)\b"),
    ("stop-gradient", r"\b(detach|stop_gradient|no_grad|requires_grad\s*=\s*False)\b"),
    ("epsilon", r"\b(eps|epsilon)\s*=|\b1e-\d+\b"),
    ("magic-constant", r"(?<![\w.])\d+\.\d{3,}(?![\w.])"),
    ("schedule", r"\b(warmup|warm_up|anneal\w*|lr_scheduler|scheduler|ema_decay|ema)\b"),
    ("scaling-knob", r"\b(scale|temperature|tau|alpha|beta|gamma|lambda_\w+|weight)\s*=\s*[\d.]"),
    ("hack-marker", r"\b(TODO|FIXME|XXX|HACK|workaround|kludge)\b|\b(unstable|stabili[sz]\w*)\b"),
    ("special-case", r"^\s*if\b.*\b(nan|inf|isnan|isinf|== ?0(\.0)?\b|< ?1e-)"),
]
RECORD = [
    ("verdict", r"\b(killed|near[- ]miss|abandon\w*|verdict|go/no-go)\b|탈락|종료|판정|근접 후보"),
    ("prior", r"\b(closest prior|direct prior|prior work|killer)\b|선행"),
    ("lesson", r"\b(lessons?|pitfalls?|post[- ]mortem)\b|교훈"),
    ("pilot", r"\b(B0|pilot|oracle|headroom|kill condition|sealed)\b"),
]
HEAVY = {"inv", "inverse", "pinv", "solve", "lstsq", "eig", "eigh", "svd", "cholesky", "det", "logdet",
         "cdist", "pdist", "matmul", "einsum", "bmm", "fft", "fft2", "ifft", "rfft", "sort", "argsort",
         "topk", "kneighbors", "knn", "nearest", "unique", "expm", "slogdet"}


def iter_files(paths, excludes):
    for root in paths:
        if os.path.isfile(root):
            yield root
            continue
        for d, dirs, files in os.walk(root):
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.endswith(".egg-info")]
            for f in files:
                path = os.path.join(d, f)
                if any(e in path for e in excludes):
                    continue
                yield path


def read_text(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        try:
            try:
                import pymupdf as fitz
            except ImportError:
                import fitz
            return "\n".join(p.get_text() for p in fitz.open(path)), "theory"
        except Exception:
            return None, None
    if ext == ".ipynb":
        try:
            with open(path, encoding="utf-8") as fh:
                nb = json.load(fh)
            code = "\n".join("".join(c.get("source", "")) for c in nb.get("cells", []) if c.get("cell_type") == "code")
            return code, "code"
        except Exception:
            return None, None
    if ext not in TEXT_EXT | CODE_EXT:
        return None, None
    if os.path.getsize(path) > MAX_BYTES:
        return None, None
    with open(path, "rb") as fh:
        raw = fh.read()
    if b"\x00" in raw[:4096]:
        return None, None
    return raw.decode("utf-8", errors="replace"), ("code" if ext in CODE_EXT else "theory")


def grep(text, patterns, path, hits, limit):
    for n, line in enumerate(text.splitlines(), 1):
        for name, pat in patterns:
            if len(hits[name]) >= limit:
                continue
            if re.search(pat, line, re.I):
                hits[name].append(f"{path}:{n}: {line.strip()[:160]}")


def hotspots(text, path, out, limit):
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return

    class V(ast.NodeVisitor):
        depth = 0

        def generic_loop(self, node):
            self.depth += 1
            self.generic_visit(node)
            self.depth -= 1

        visit_For = visit_While = visit_comprehension = generic_loop

        def visit_Call(self, node):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            if self.depth > 0 and name in HEAVY and len(out) < limit:
                out.append(f"{path}:{node.lineno}: {name}() inside loop depth {self.depth}")
            self.generic_visit(node)

    V().visit(tree)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("paths", nargs="+")
    p.add_argument("--out")
    p.add_argument("--max-per-pattern", type=int, default=25)
    p.add_argument("--exclude", nargs="*", default=[])
    a = p.parse_args(argv)

    hits = defaultdict(list)
    hot = []
    nfiles = defaultdict(int)
    for path in iter_files(a.paths, a.exclude):
        text, kind = read_text(path)
        if text is None:
            continue
        nfiles[kind] += 1
        if kind == "code":
            grep(text, CODE, path, hits, a.max_per_pattern)
            if path.endswith(".py"):
                hotspots(text, path, hot, a.max_per_pattern * 2)
        else:
            grep(text, THEORY, path, hits, a.max_per_pattern)
            grep(text, RECORD, path, hits, a.max_per_pattern)

    lines = ["# Corpus scan (leads, not findings)", "",
             f"Files scanned: {dict(nfiles)}. At most {a.max_per_pattern} hits per pattern.", ""]
    for title, group in (("Theory compromises", THEORY), ("Code-only tricks", CODE), ("Records: verdicts, priors, lessons, pilots", RECORD)):
        lines.append(f"## {title}")
        for name, _ in group:
            lines.append(f"### {name} ({len(hits[name])})")
            lines += [f"- {h}" for h in hits[name]] or ["- (none)"]
        lines.append("")
    lines.append(f"## Hotspots: heavy calls inside loops ({len(hot)})")
    lines += [f"- {h}" for h in hot] or ["- (none)"]
    out = "\n".join(lines) + "\n"
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(out)
        print(f"wrote {a.out}")
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
