---
name: topic-scout
description: Finds research topics tailored to one researcher. A level sets how much it draws on their own material (high = papers, code, notes and past reviews; low = only their field and taste, exploring recent literature), and a depth sets how far it goes (quick = candidates only; standard = vet the top one; full = vet the top three). Generates candidates through explicit lenses, drops only objectively infeasible or already-killed ideas (via a ledger), and sends a shortlist through the novelty gate. Returns numbered candidates, vetted topics and near-misses with the cheapest evidence that would revive them. Use it whenever someone asks to find, brainstorm, scout or propose research topics, follow-ups to their work, or "what should I work on next", including 연구 주제 탐색, 주제 찾아줘, 탐색적으로, 내 코드 기반으로, 후속 연구, 다음 연구 뭐 하지. For interactive use with a researcher, not for autonomous research pipelines.
compatibility: Claude Code or Codex, used together with the novelty-gate skill. Needs web access. Python 3.8+ stdlib scripts; pymupdf optional for scanning PDFs.
metadata:
  version: "0.3"
---

# Topic scout

Generate broadly. Filter early only on objective facts. Let the gate do the killing with evidence.

How much to lean on the researcher's own material is their choice; that is the **level**:
- Ideas grown from their own code, data, unexplained tricks and near-misses carry an edge that generic brainstorming lacks.
- Exploring the field's recent literature finds directions they would not reach from their own files.

## Who may use this skill
Use is allowed when a researcher asked for it, directly or through an agent working for them in the same session; subagents spawned for that request count. It is not for autonomous research frameworks or other unattended pipelines. Those runs follow their own frozen workflow, cannot answer the approval questions this skill asks, and would leave extra folders behind.

First run `python3 <this-skill-dir>/scripts/guard.py`. If it exits non-zero, stop and report its message. Also stop without doing anything if you are running as a stage of such a pipeline rather than for a person's request.

## Paths
`scripts/…` and `references/…` are relative to this skill's own directory. Your working directory is usually the user's project, so call scripts by absolute path, for example `python3 <this-skill-dir>/scripts/ledger.py …`. Write outputs to the output directory, never into the skill directory.

## Quick start: settle the settings first
Users should be able to say just "find me a topic", "탐색적으로 빠르게 주제 찾아줘", or "내 코드 기반으로 꼼꼼하게". Turn the request into settings with the script, not by guessing, so the same words always mean the same thing:

```bash
python3 <this-skill-dir>/scripts/scout_settings.py --request "<the user's request, verbatim>"
```

- **Show the card.** Paste its 3–5 lines to the user, translated into their language, and proceed without asking. It shows level, depth, gate count, corpus, direction, cutoff, output directory and profile, each with its source (request, profile or default).
- **No profile** (exit code 4, profile `missing`): follow [references/onboarding.md](references/onboarding.md). Ask four short questions once, run `scripts/profile_init.py`, rerun the settings script, then continue.
- **Notes on the card** (for example "no corpus found"): act on them. At level high or medium with no corpus, ask once for a path, or offer level low.
- **Changing settings:** the user can override anything by repeating it explicitly, for example "level: low", "depth: full", "field: medical imaging", "cutoff 2026-01-31", "out: ./scout", or by naming a path.

Level and depth are explained in [references/levels.md](references/levels.md):

| level | Draws on | | depth | Goes until |
|---|---|---|---|---|
| high | mostly own material (80%) | | quick | candidates with quick novelty signals |
| medium (default) | half own material, half landscape | | standard (default) | the top 1 vetted by novelty-gate in light mode |
| low | landscape only; the corpus is never opened | | full | the top 3 vetted by novelty-gate in full mode |

Never changed by the level: profile exclusions, budgets, the ground-truth policy, the ledger duplicate check, and the gate's standards.

## Ground rules
- Same limits as the gate: no experiments or data/weight downloads without approval, and the evidence rules in [references/evidence_rules.md](references/evidence_rules.md) apply. "No topic passes" is a valid result.
- **Before the gate, drop only for objective reasons:** a profile exclusion, an infeasible budget, provably unavailable data, or a ledger duplicate with a named killer. Annotate everything else instead of killing it. Judging novelty or impact from your own expectations is exactly the kind of quick verdict that loses good ideas and keeps fashionable ones.
- **Respect the level.** At low, do not open the corpus, not even to "check fit".

## Workflow

### 1. Gather material (by level)
**Own material** (high: full; medium: light; low: skip):
- Run `python3 scripts/corpus_scan.py <corpus paths> --out <out>/corpus_scan.md`. It lists leads:
  - assumptions and approximations in papers and notes;
  - code-only tricks;
  - heavy calls inside loops;
  - recorded verdicts and lessons.
- Read the hits that matter, following [references/corpus_audit.md](references/corpus_audit.md). At medium, read only the strongest few.
- Write `<out>/corpus_manifest.md` with these sections:
  - theoretical compromises;
  - code–theory discrepancies (file:line);
  - bottlenecks;
  - abstract core operator(s);
  - owned assets that make a B0 cheap;
  - ledger near-misses with their flip evidence.

**Landscape** (low: full; medium: half; high: a fifth):
- Follow [references/landscape_scan.md](references/landscape_scan.md) and write `<out>/landscape.md`: open problems in the researcher's areas, each with evidence.

### 2. Generate, breadth first
- Apply the lenses in [references/generation_lenses.md](references/generation_lenses.md) in the level's quota. Aim for 10–20 raw candidates.
- Number them C1, C2, … and save them as `<out>/candidates.jsonl` in the record format given there, including `source` and `level`.
- If subagents are available, fix the lens list first, then fan out about 4–6 lenses in parallel. Merge, and deduplicate mechanically by hypothesis. Never drop an idea here for being "weak".

### 3. Pre-filter objectively
- Apply [references/prefilter.md](references/prefilter.md) at every level:
  - profile exclusions and ground-truth policy;
  - budget tiers;
  - data, weight and license availability;
  - `python3 scripts/ledger.py check <ledger> --claim "<claim in English>"`;
  - the negative patterns, flagged with the specific reason.
- For each survivor, run 2–3 quick searches (`scripts/lit_fetch.py`) and attach the related work as an annotation. Drop a survivor only when a named paper clearly contains its result.
- Update each record's `status` in `candidates.jsonl`: `dropped`, `annotated` or `gated`.

### 4. Shortlist
Rank the survivors by:
- information value of the B0 regardless of its outcome;
- edge from the researcher's own assets or insight (weighted by level);
- fit with the profile's taste and interests;
- cost.

### 5. Gate (by depth)
- quick: skip; the user picks.
- standard: run **novelty-gate** in light mode on the top 1.
- full: run it in full mode on the top 3.

Candidates in one area can share a gate run. The gate writes its own report, evidence and ledger proposals.

### 6. Report
Write two files. The audit record keeps everything; the human report keeps only what a reader needs.

**`<out>/details.md`** (audit record, English):
1. **Settings:** the card, plus the actual source mix (for example "7 landscape, 5 corpus") and the query count.
2. **Candidates table:** every candidate with id, one line, lens, source, status, rank, novelty and feasibility if gated, and the reason.
3. **Dropped ideas with reasons.** Dead ends save the next run's time.
4. **Evidence notes:** related work per candidate, with tags.

**`<out>/report.md`** (human report, English): follow [references/report_style.md](references/report_style.md). Plain words, short sentences, the fixed terms (Recommended, Near miss, Rejected, Removed, Not checked), no internal codes. In this order:
1. **Result:** one or two sentences.
2. **One short card per top candidate** (the top 3, plus any that were checked):
   - title and verdict term;
   - Idea;
   - Why it looks promising or weak;
   - the closest paper with its link;
   - the first test with its cost;
   - the next thing to say.
3. **Other candidates:** one line each.
4. **Next step:** one or two ready-to-say follow-ups.

If an extra report language is set (the settings card shows `reports: en + <code>`), also write `report.<code>.md`. Translate the prose only; keep the technical terms in English.

Then run `python3 scripts/report_lint.py scout <out>` and fix every ERROR.

What each card must carry:
- **Near miss** (checked): the closest paper, the baselines to beat, the bar it missed, and the first test that could change the verdict.
- **Not checked** (depth quick, or below the top N): the closest related paper found so far and the baselines to beat. Say plainly that it has not been checked yet.
- **Recommended:** the closest paper and why the idea still differs, the first test, and the suggestion to write a study plan.
- **Next-step phrases:** for example "check C3" (novelty-gate on C3), "write the study plan for C1" (research-brief), or "again at level low".

In the chat, show only a short summary of `report.md` in the user's language and the file paths.

Do not append to the ledger yourself. The gate proposes ledger entries for gated candidates, and the user confirms them. For dropped ideas, offer optional `dropped` entries.

## Follow-up requests
When the user refers to a candidate id ("check C3", "gate C3", "C3도 검증해줘", "write the study plan for C1", "C1로 연구 계획 써줘"), read `<out>/candidates.jsonl` from the most recent scout run in the working directory, or the run the user names. Then:
- **check / gate C3:** run novelty-gate on that record, in light mode unless the user asks for full.
- **study plan for C1:** run research-brief on that record's gate report. If the candidate has not been gated, run the gate first.

## Why this order
- Execution studies of LLM-generated research ideas found that they look more novel before execution than after.
- Most topics die from a missed recent prior or a cheap baseline, not from a lack of ideas.

So generation stays cheap and broad, and killing happens late, against evidence.
