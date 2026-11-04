#!/usr/bin/env python3
"""Validate skills/ against the Agent Skills specification (https://agentskills.io/specification)
plus this repository's portability rules. Stdlib only.

Checks per skill: SKILL.md exists; frontmatter has name and description; name is 1-64
chars of [a-z0-9-], no leading/trailing/double hyphen, equal to the directory name;
description 1-1024 chars; compatibility <= 500 chars; body under 500 lines; every
relative link or script path mentioned in SKILL.md exists; no '../' references (skills
must not reach outside their own directory). Also runs tools/sync_shared.py --check.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def parse_frontmatter(text):
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 4)
    if end < 0:
        return None, text
    block, body = text[4:end], text[end + 4:].lstrip("\n")
    fm, key = {}, None
    for line in block.splitlines():
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if m and not line.startswith(" "):
            key, val = m.group(1), m.group(2).strip()
            fm[key] = val.strip('"').strip("'") if val else {}
        elif key and line.startswith(" ") and isinstance(fm.get(key), dict):
            mm = re.match(r"^\s+([A-Za-z_-]+):\s*(.*)$", line)
            if mm:
                fm[key][mm.group(1)] = mm.group(2).strip().strip('"')
    return fm, body


def check_skill(d):
    errs = []
    name = os.path.basename(d)
    path = os.path.join(d, "SKILL.md")
    if not os.path.exists(path):
        return [f"{name}: SKILL.md missing"]
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    fm, body = parse_frontmatter(text)
    if fm is None:
        return [f"{name}: missing YAML frontmatter"]
    n = fm.get("name", "")
    if not n:
        errs.append("name missing")
    else:
        if not (1 <= len(n) <= 64 and NAME_RE.match(n)):
            errs.append(f"name {n!r} violates [a-z0-9-], 1-64 chars, no leading/trailing/double hyphen")
        if n != name:
            errs.append(f"name {n!r} != directory {name!r}")
    desc = fm.get("description", "")
    if not desc or not isinstance(desc, str):
        errs.append("description missing")
    elif len(desc) > 1024:
        errs.append(f"description is {len(desc)} chars (> 1024)")
    comp = fm.get("compatibility")
    if isinstance(comp, str) and len(comp) > 500:
        errs.append(f"compatibility is {len(comp)} chars (> 500)")
    nlines = body.count("\n") + 1
    if nlines >= 500:
        errs.append(f"SKILL.md body has {nlines} lines (keep under 500)")
    if "../" in text:
        errs.append("references outside the skill directory ('../') break portability")
    refs = set(re.findall(r"\]\(((?:references|scripts|assets)/[^)\s#]+)\)", body))
    refs |= set(re.findall(r"(?<![\w/])((?:scripts|references|assets)/[\w.\-]+\.(?:py|md|json|sh))", body))
    for r in sorted(refs):
        if not os.path.exists(os.path.join(d, r)):
            errs.append(f"referenced file missing: {r}")
    return [f"{name}: {e}" for e in errs], len(desc) if isinstance(desc, str) else 0, nlines


def main():
    skills_dir = os.path.join(ROOT, "skills")
    all_errs = []
    for entry in sorted(os.listdir(skills_dir)):
        d = os.path.join(skills_dir, entry)
        if not os.path.isdir(d):
            continue
        res = check_skill(d)
        if isinstance(res, list):
            all_errs += res
            continue
        errs, dlen, nlines = res
        all_errs += errs
        print(f"{entry}: description {dlen} chars, body {nlines} lines" + ("" if errs else " - ok"))
    rc = subprocess.call([sys.executable, os.path.join(ROOT, "tools", "sync_shared.py"), "--check"])
    for e in all_errs:
        print("ERROR: " + e)
    return 1 if (all_errs or rc) else 0


if __name__ == "__main__":
    sys.exit(main())
