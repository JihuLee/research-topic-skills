#!/usr/bin/env python3
"""guard.py - keep the research-topic skills out of autonomous research pipelines (stdlib only).

  guard.py [--cwd DIR]      exit 0 = allowed here; exit 3 = disabled, stop and report the message

These skills are for a researcher working with an agent, directly or through subagents the
agent spawns for that request. Autonomous research frameworks (systems that run agent stages
unattended) should not use them. Such runs follow their own frozen workflow, cannot answer
the approval questions the skills ask, and would leave extra folders behind.

The skills are disabled when either of these holds:
  1. The environment variable RESEARCH_TOPIC_SKILLS_DISABLE is 1, true, yes or on.
     Set it in the launch environment of every autonomous framework.
  2. A sentinel file named .no-research-topic-skills exists in the working directory or in
     any parent directory. Put one at the root of a framework's workspace.
RESEARCH_TOPIC_SKILLS_ALLOW=1 overrides both, for a deliberate supervised use.

This is a cooperative guard: it works because the skills tell the agent to run it first.
For hard isolation, run autonomous frameworks under a separate OS user or install these
skills at project level only.
"""
import argparse
import os
import sys

TRUE = {"1", "true", "yes", "on"}
SENTINEL = ".no-research-topic-skills"


def find_sentinel(start):
    d = os.path.abspath(start)
    while True:
        p = os.path.join(d, SENTINEL)
        if os.path.exists(p):
            return p
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def check(cwd, env):
    if env.get("RESEARCH_TOPIC_SKILLS_ALLOW", "").strip().lower() in TRUE:
        return True, "allowed: RESEARCH_TOPIC_SKILLS_ALLOW is set"
    if env.get("RESEARCH_TOPIC_SKILLS_DISABLE", "").strip().lower() in TRUE:
        return False, ("disabled: RESEARCH_TOPIC_SKILLS_DISABLE is set in this environment "
                       "(autonomous pipeline). Do not use the research-topic skills here.")
    s = find_sentinel(cwd)
    if s:
        return False, (f"disabled: sentinel {s} marks this tree as an autonomous-pipeline workspace. "
                       "Do not use the research-topic skills here.")
    return True, "allowed"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cwd", default=os.getcwd())
    a = p.parse_args(argv)
    ok, msg = check(a.cwd, os.environ)
    print(msg)
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
