---
name: novelty-gate
description: Adversarial novelty-and-feasibility gate for a research idea, topic or proposal, run before any experiment. Breaks the idea into claims; hunts the closest recent prior work (same input contract, same claim, same computation under classical names, same benchmark, recent-months sweep, forward citations); verifies decisive quotes in full text; checks for classical equivalents and theory-forced results; scores novelty and feasibility 1-5 separately; and designs the cheapest falsifying pre-experiment (B0) with four baselines and frozen thresholds. Returns PASS, NEAR-MISS or NONE backed by named evidence. Use it whenever someone wants to vet, desk-review, novelty-check or prior-art-check a research idea, asks "has this been done", wants a go/no-go or kill test before implementing, or says G0, 신규성 검토, 선행 연구 확인, 연구 주제 검증, 제안서 심사, even for a rough pasted idea. For interactive use with a researcher, not for autonomous research pipelines.
compatibility: Claude Code or Codex. Needs web access for literature search. Python 3.8+ stdlib scripts; pymupdf or pdftotext optional for PDF text.
metadata:
  version: "0.3"
---

# Novelty gate

Decide, with named evidence, whether an idea deserves a pilot. If it does not, report the cheapest evidence that would change that.

Most research ideas die for one of three reasons:
- a recent paper nobody looked for (often weeks old);
- a classical result under another name;
- a cheap baseline that already does the job.

This gate looks for those three first. LLM-generated ideas tend to look more novel before execution than after, so the gate leans on evidence, not plausibility.

## Who may use this skill
Use is allowed when a researcher asked for it, directly or through an agent working for them in the same session; subagents spawned for that request count. It is not for autonomous research frameworks or other unattended pipelines. Those runs follow their own frozen workflow, cannot answer the approval questions this skill asks, and would leave extra folders behind.

First run `python3 <this-skill-dir>/scripts/guard.py`. If it exits non-zero, stop and report its message. Also stop without doing anything if you are running as a stage of such a pipeline rather than for a person's request.

## Inputs
- **The proposal:** a file, pasted text, or a list of candidates.
- **The profile directory:** taste, budgets, ledger and lessons; see [references/data_contract.md](references/data_contract.md). If none exists, ask once for the essentials or state the defaults you used.
- **Literature cutoff:** default today.
- **Output directory:** a directory named in the request wins. Otherwise use `report_dir_pattern` from the profile, else `./gate-<slug>-<date>/`.

## Paths
`scripts/…` and `references/…` are relative to this skill's own directory. Your working directory is usually the user's project, so call scripts by absolute path, for example `python3 <this-skill-dir>/scripts/ledger.py …`. Write outputs to the output directory, never into the skill directory. Do not read `evals/`: it holds the answers to the skill's tests.

## Modes
- **Full** (default): the workflow below as written.
- **Light**: for quick checks, or when topic-scout runs at depth standard, or when the user asks for a quick review.
  - No subagents.
  - Query formulations are shared across claims.
  - At most 4 decisive priors are verified in full text.
  - Everything else is the same: evidence tags, the gate-summary block and the lint.
  - State the mode in the report header.

## Ground rules
- **Design B0, do not run it.** No experiments, dataset or weight downloads, installs or GPU jobs without the user's explicit approval. Downloading paper PDFs is fine. The user decides what to spend.
- **Read [references/evidence_rules.md](references/evidence_rules.md) before searching.** Every claim in the report carries an evidence tag (FT, ABS, SEC, FAIL).
- **Score with [references/rubric.md](references/rubric.md).** "None passes" is a normal, useful outcome; padding a report with weak candidates wastes the user's next month.
- **Respect the profile.** Exclusions and the ground-truth policy apply to every candidate.

## Workflow

### 1. Set up
- Resolve the profile and read `profile.md`, `lessons.md` and `assets.md`.
- If a ledger exists, run `python3 scripts/ledger.py check <ledger> --claim "<one-sentence claim in English>"` for each candidate. A strong match with a named killer gets reported right away. Continue only if the proposal says what changed since then.
- Create the output directory with `notes/`, `lit/` and an empty `evidence.jsonl`.

### 2. Decompose each candidate
Write down:
- **Atomic claims (3–6):** what is computed; under which input contract (what is available at test time, supervision, data); what is claimed to improve; how it is measured.
- **The core computation in its most reduced mathematical form.** This is what you will test for classical equivalence. Renamed classics hide behind new vocabulary.
- **The kill condition per claim:** which kind of prior would make it non-novel.
- **The conclusion at stake:** which conclusion or ranking would change if the idea works. If none would, novelty is at most 3.

### 3. Plan the search as a coverage matrix
Rows are claims. Columns are the query families A–F from [references/search_playbook.md](references/search_playbook.md):

| Family | Covers |
|---|---|
| A | Same input contract |
| B | Same claim or conclusion |
| C | Same computation under other names |
| D | Same benchmark or protocol |
| E | Recency sweep plus forward citations |
| F | Strongest cheap baseline |

Use at least three query formulations per family. A query may serve several claims; record which ones. The matrix goes into the report, because coverage is what makes "not found" meaningful.

### 4. Search
- **With subagents** (for example Claude Code's Agent tool): split the matrix by claim or family, at most about 7 at once. Brief each one with [references/subagent_brief.md](references/subagent_brief.md). Subagents do not inherit this file, so the brief restates the rules.
- **Without subagents:** work through the families yourself.
- **Tools:** `scripts/lit_fetch.py` covers arXiv and OpenAlex search, forward citations (`citing`), metadata resolution (`resolve`) and PDF retrieval (`pdf`); see `--help`. The host's web search is fine too.
- Treat subagent summaries as leads. They are SEC until you check them.
- If arXiv rate-limits you (HTTP 429), keep going with OpenAlex. `resolve` already tries OpenAlex first. Log the failure as a FAIL entry.

### 5. Verify the decisive evidence
- Pick the 3–6 priors that decide the verdict: those that would kill the idea, and the closest one that a PASS has to differ from.
- Fetch their full text (`lit_fetch.py pdf <arxiv-id or url> --out <out>/lit`) and find the exact sentence, equation or table.
- Log each to `evidence.jsonl`, then run `python3 scripts/quote_check.py <out>/evidence.jsonl`. Fix or downgrade any quote that fails.
- Save abstracts with `--save-abstracts <out>/lit`, so that ABS quotes can be checked too.
- Resolve every paper you cite (`lit_fetch.py resolve`). A citation from memory is a common way to fabricate one.

### 6. Attack, then adjudicate
- Write the strongest rejection memo you can, at most about 200 words, using only the evidence found. A fresh subagent given the evidence files works well for this: a separate context finds weaknesses its author misses.
- Adjudicate point by point. Keep an attack only if FT/ABS evidence or a checkable derivation supports it. Then state the surviving delta in one sentence a reviewer could verify.
- Run two checks every time:
  - **Classical equivalence:** is the reduced computation a known classical one? Use the trap list in the playbook and give the derivation.
  - **Theory-forced result:** is the claimed finding a mathematical necessity? For example, an exact posterior sample always has twice the posterior-mean MSE (about 3 dB lower PSNR), so "posterior samplers lose on PSNR" is not a finding.
- Apply every item in `lessons.md` as a check and note the result.

### 7. Score
Give novelty and feasibility separately per the rubric. Each gets a short justification that cites evidence ids. Feasibility includes the data hygiene checks listed in the rubric: weight/eval overlap, near-duplicates, licenses per asset, hidden downloads, and simulated versus real ground truth.

### 8. Design B0 for PASS and NEAR-MISS candidates
Follow [references/b0_design.md](references/b0_design.md):
- the oracle upper bound of the allowed method family;
- four baselines: native/no intervention, the common default, the simplest use of the key information, and an equal-compute alternative;
- one primary endpoint, a minimum effect × margin, and a known-good attainability check;
- thresholds frozen with `scripts/freeze.py`;
- outcome classes PROMOTE / KILLED / INCONCLUSIVE / BLOCKED;
- cost against the profile's budget tiers.

For a NEAR-MISS, the B0 is the minimal evidence that would lift it to the threshold. State that evidence precisely.

### 9. Write the outputs
Write three things. People read the first; the other two keep the verdict checkable.
1. **`details.md`, the audit record.** Always in English. Follow [references/details_template.md](references/details_template.md): claims, evidence with tags and quotes, checks, baselines, the full B0, coverage, lessons and access failures. For KILLED candidates, give the evidence and a one-line revival condition, and do not design a B0.
2. **`gate_summary.json`, the machine-readable summary.** Schema in `details_template.md`.
3. **`report.md`, the human report.** In English, following [references/report_template.md](references/report_template.md) and [references/report_style.md](references/report_style.md):
   - plain words and short sentences;
   - the fixed verdict terms (Recommended, Near miss, Rejected);
   - no evidence ids or tags.

   If an extra report language is set (profile `extra_report_language`, or a request such as "also in Korean"), also write `report.<code>.md`. Translate the prose only; keep the technical terms in English.

Then run `python3 scripts/report_lint.py gate <out>` and fix every ERROR. It checks all three outputs and evidence.jsonl.

### 10. Close the loop
- Show the proposed ledger entries with `python3 scripts/ledger.py add <ledger> --from-summary <out> --dry-run`. Append them once the user confirms the verdict. If the user asked for unattended operation, append them with verdict `pending` instead.
- In the chat, give the short version of `report.md` in the user's language:
  - the verdict;
  - the main reason, with the closest paper's link;
  - the first test for a near miss;
  - where the files are.
- Ask before running any B0.

## Pitfalls seen in practice
- **The killer paper is often a few weeks old.** Family E is not optional. Chase forward citations of the closest prior inside the recency window; it finds direct competitors that keyword search misses.
- **Abstracts rarely decide anything.** The dropped term, the missing experiment or the restrictive assumption usually sits in the method section or the appendix.
- **"Rankings flip under a better metric"** is a contribution only if theory does not already force the flip.
- **"Apply X to Y"** passes only if the failure point of naive transfer is defined and the result teaches something about Y.
- **Bot walls, paywalls and dead links** get recorded as FAIL. Never let them stand in for "nobody did this".
- **One-model tunnel vision.** If a second model family is available (cross-model review), it is a good adversary for step 6. Optional.

## Output files
- `report.md` (human report, English) and optionally `report.<code>.md`
- `details.md` (audit record, English)
- `gate_summary.json`
- `evidence.jsonl`
- `notes/`
- `lit/` (PDFs and extracted text; usually excluded from sharing)
- `thresholds.json` and `thresholds.json.sha256` for each designed B0
