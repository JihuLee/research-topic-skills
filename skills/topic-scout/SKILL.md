---
name: topic-scout
description: Finds research topics tailored to one researcher. Reads their own corpus (papers, code, notes, past reviews) and preference profile; generates candidates through explicit lenses (heuristic-to-principle, assumption relaxation, breakdown-first transfer to a new domain, evaluations that would change a conclusion, contradictions, owned-asset reuse, near-miss revival); drops only objectively infeasible or already-killed ideas (via a ledger); and sends a shortlist through the novelty gate. Returns zero or more vetted topics plus near-misses with the cheapest evidence that would revive them. Use it whenever someone asks to find, brainstorm, scout or propose research topics, follow-ups to their own paper or code, or "what should I work on next", including 연구 주제 탐색, 후속 연구 아이디어, 주제 찾아줘, 다음 연구 뭐 하지. For interactive use with a researcher, not for autonomous research pipelines.
compatibility: Claude Code or Codex, used together with the novelty-gate skill. Needs web access. Python 3.8+ stdlib scripts; pymupdf optional for scanning PDFs.
metadata:
  version: "0.1"
---

# Topic scout

Generate broadly. Filter early only on objective facts. Let the gate do the killing with evidence.

Ideas that come out of a researcher's own assets — their code, data, unexplained tricks, near-misses — carry an edge that generic brainstorming lacks. That is why this skill starts from the corpus. Topics generated from field keywords alone tend to land in crowded areas, where a recent paper already exists.

## Who may use this skill
Use is allowed when a researcher asked for it, directly or through an agent working for them in the same session; subagents spawned for that request count. It is not for autonomous research frameworks or other unattended pipelines. Those runs follow their own frozen workflow, cannot answer the approval questions this skill asks, and would leave extra folders behind.

First run `python3 scripts/guard.py`. If it exits non-zero, stop and report its message. Also stop without doing anything if you are running as a stage of such a pipeline rather than for a person's request.

## Inputs
- **Profile directory:** see [references/data_contract.md](references/data_contract.md). Interests, exclusions and budgets are the minimum.
- **Corpus:** one or more paths with papers (`.tex`, `.pdf`, `.md`), code repositories, notes and past gate reports. Optional, but strongly recommended.
- **Run options:** an optional direction sentence, the contribution types wanted, and the number of finalists to gate (default 3).
- **Literature cutoff** (default today) and **output directory**.

## Paths
`scripts/…` and `references/…` are relative to this skill's own directory. Your working directory is usually the user's project, so call scripts by absolute path, for example `python3 <this-skill-dir>/scripts/ledger.py …`. Write outputs to the output directory, never into the skill directory.

## Ground rules
- Same limits as the gate: no experiments or data/weight downloads without approval, and the evidence rules in [references/evidence_rules.md](references/evidence_rules.md) apply. "No topic passes" is a valid result.
- **Before the gate, drop only for objective reasons:** a profile exclusion, an infeasible budget, provably unavailable data, or a ledger duplicate with a named killer. Annotate everything else instead of killing it. Judging novelty or impact from your own expectations is exactly the kind of quick verdict that loses good ideas and keeps fashionable ones.

## Workflow

### 1. Audit the corpus
- Run `python3 scripts/corpus_scan.py <paths> --out <out>/corpus_scan.md`. It lists leads only:
  - assumptions and approximations in papers and notes;
  - code-only tricks (clamps, detaches, epsilons, magic constants, schedules);
  - heavy calls inside loops;
  - recorded verdicts, priors, lessons and pilots.
- Read the hits that matter, following [references/corpus_audit.md](references/corpus_audit.md).
- Write `<out>/corpus_manifest.md` with these sections:
  - theoretical compromises;
  - code–theory discrepancies (file:line);
  - bottlenecks;
  - abstract core operator(s): input space → output space, guarantee, assumptions;
  - owned assets that make a B0 cheap;
  - past near-misses with the evidence that would flip them (from the ledger).

### 2. Generate, breadth first
- Apply the lenses in [references/generation_lenses.md](references/generation_lenses.md). Aim for 10–20 raw candidates in the record format given there.
- If subagents are available, fix the lens list first, then fan out about 4–6 lenses in parallel. Merge the results and deduplicate them mechanically, by hypothesis. Never drop an idea here for being "weak".

### 3. Pre-filter objectively
- Apply [references/prefilter.md](references/prefilter.md):
  - profile exclusions and ground-truth policy;
  - budget tiers;
  - data, weight and license availability;
  - `python3 scripts/ledger.py check <ledger> --claim "<claim in English>"` for duplicates of killed topics;
  - the negative patterns, which are flagged with the specific reason, not silently removed.
- Keep a dropped list with reasons.
- For each survivor, run 2–3 quick searches (`scripts/lit_fetch.py`) and attach the related work as an annotation. A survivor is dropped only when a named paper clearly contains its result.

### 4. Shortlist
Rank the survivors by:
- information value of the B0 regardless of its outcome;
- edge from the researcher's own assets or insight;
- fit with the profile;
- cost.

Take the top N (default 3).

### 5. Gate
Run the **novelty-gate** skill on the shortlist. Candidates in one area can share a gate run; unrelated ones are clearer in separate runs. The gate writes its own report, evidence and ledger proposals.

### 6. Report
Write `<out>/scout_report.md` in the profile's output language:
1. **Candidates table:** every generated idea, with id, one line, lens, status (dropped / annotated / gated), novelty and feasibility if gated, and the reason.
2. **Passed topics, if any.** Suggest the **research-brief** skill as the next step.
3. **If nothing passed:** up to 3 near-misses, each with
   - (a) the direct prior,
   - (b) the cheap baselines,
   - (c) the gate it failed,
   - (d) the minimal B0 evidence that would flip it.
4. **Dropped ideas with reasons.** Dead ends are worth keeping; they save the next run's time.
5. **Decision for the user:** approve a B0, change the direction, or close.

Do not append to the ledger yourself. The gate proposes ledger entries for gated candidates, and the user confirms them. For dropped ideas, offer optional `dropped` entries.

## Why this order
- Execution studies of LLM-generated research ideas found that they look more novel before execution than after.
- Most topics die from a missed recent prior or a cheap baseline, not from a lack of ideas.

So generation stays cheap and broad, and killing happens late, against evidence.
