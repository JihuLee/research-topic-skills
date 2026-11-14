# Lessons

Your own checks, learned from past reviews. The novelty gate applies pinned and core lessons in every run, and a scoped lesson only when a candidate shares one of its tags. Do not repeat rules the skills already enforce (input-contract search, classical equivalents, theory-forced results, the four baselines, oracle first, data hygiene). Add what your own history taught you.

One top-level bullet per lesson, details as indented sub-bullets. Example (inside a comment, so it is not applied):
<!--
- [L1|core|evaluation|h0/x0/n0] Check: the official evaluation script and version were used, or the difference is stated.
- [L2|scoped|benchmark|h0/x0/n0] Check: leaderboard entries from the last three months were read, not only the paper tables.
-->

Tiers: pinned (always applied, never proposed for archiving), core (always applied, at most lessons_core_cap), scoped (only when tags match). h/x/n count catches, false alarms and applications; `lessons.py tally` updates them. Change lessons only with `lessons.py apply`: the gate proposes, you approve.

## Lessons
