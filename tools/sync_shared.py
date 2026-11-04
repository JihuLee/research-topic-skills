#!/usr/bin/env python3
"""Copy shared/ files into each skill so every skill stays self-contained (Agent Skills
references must live under the skill's own directory).

  python3 tools/sync_shared.py          copy
  python3 tools/sync_shared.py --check  exit 1 if any copy differs from shared/ (use in CI)

Edit files in shared/, never the copies inside skills/.
"""
import argparse
import filecmp
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARED_REFS = ["data_contract.md", "rubric.md", "evidence_rules.md", "onboarding.md"]
SHARED_SCRIPTS = {
    "novelty-gate": ["guard.py", "profile_init.py", "lit_fetch.py", "ledger.py", "freeze.py", "report_lint.py",
                     "quote_check.py"],
    "topic-scout": ["guard.py", "profile_init.py", "lit_fetch.py", "ledger.py", "quote_check.py"],
    "research-brief": ["guard.py", "profile_init.py", "freeze.py", "report_lint.py", "ledger.py"],
}


def pairs():
    for skill, scripts in SHARED_SCRIPTS.items():
        for f in SHARED_REFS:
            yield (os.path.join(ROOT, "shared", "references", f),
                   os.path.join(ROOT, "skills", skill, "references", f))
        for f in scripts:
            yield (os.path.join(ROOT, "shared", "scripts", f),
                   os.path.join(ROOT, "skills", skill, "scripts", f))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--check", action="store_true")
    a = p.parse_args(argv)
    bad = 0
    for src, dst in pairs():
        if a.check:
            if not os.path.exists(dst) or not filecmp.cmp(src, dst, shallow=False):
                print(f"OUT OF SYNC: {os.path.relpath(dst, ROOT)}")
                bad += 1
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            if dst.endswith(".py"):
                os.chmod(dst, 0o755)
    if a.check:
        print("shared copies in sync" if not bad else f"{bad} file(s) out of sync; run tools/sync_shared.py")
        return 1 if bad else 0
    print("synced shared/ into skills/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
