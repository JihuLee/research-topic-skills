---
name: novelty-gate
description: Adversarial novelty and feasibility check for a research idea or proposal, before any experiment. Hunts the closest recent prior work and classical equivalents, verifies decisive quotes in full text, scores novelty and feasibility 1-5, and designs the cheapest experiment that could prove the idea wrong (B0). Use it when someone wants to know whether a research idea is new or already done, or asks whether anyone has done it, for a novelty or prior-work check, or for a go/no-go before implementing, in any language. For interactive use with a researcher, not for autonomous research pipelines.
compatibility: Claude Code or Codex. Needs web access for literature search. Python 3.8+ stdlib scripts; pymupdf or pdftotext optional for PDF text.
metadata:
  version: "0.5.1"
---

# Novelty gate

Decide, with named evidence, whether an idea deserves a pilot. If not, report the cheapest evidence that would change that. Ideas usually die from a recent paper nobody looked for (often weeks old), a classical result under another name, or a cheap baseline that already works; look for those three first.

**Who may use it:** a researcher, directly or through agents working for them in this session; not autonomous pipelines. First run `python3 <this-skill-dir>/scripts/guard.py` and stop if it exits non-zero. Call scripts by absolute path (`<this-skill-dir>/scripts/…`) and write only to the output directory. Do not read `evals/`; it holds the answers to the skill's tests.

## Inputs and modes
- **Proposal:** a file, pasted text, or a list of candidates.
- **Profile:** taste, budgets, ledger, lessons; see [references/data_contract.md](references/data_contract.md). Without one, ask once for the essentials or state the defaults used.
- **Cutoff:** default today. **Output directory:** the one named in the request, else the profile's `report_dir_pattern`, else `./gate-<slug>-<date>/`.
- **Full mode** (default) follows every step. **Light mode** (quick checks, topic-scout depth standard, or on request): no subagents, query formulations shared across claims, at most 4 decisive priors read in full text; everything else unchanged. State the mode in the report.

## Ground rules
- **Design B0, do not run it.** No experiments, dataset or weight downloads, installs or GPU jobs without explicit approval. Paper PDFs are fine.
- Read [references/evidence_rules.md](references/evidence_rules.md) before searching and [references/rubric.md](references/rubric.md) before scoring. "None passes" is a normal outcome; never pad.
- Profile exclusions and the ground-truth policy apply to every candidate.
- **File search scope.** Search files only inside the profile directory, the working directory, and folders the user names. Never run a recursive search (`grep -r`, `rg`, `find`, `ls -R`, `du`) on the home directory (`$HOME`), the filesystem root, or any folder that contains them. If the working directory is the home directory itself, do not search it; ask for a project folder. Find the profile only at the fixed locations in [references/data_contract.md](references/data_contract.md), never by searching.

## Workflow
1. **Set up.** Read `profile.md`, `assets.md` and `ledger_index.md` (not the whole ledger). Give each candidate 1–3 tags, using the index's tags where they fit. For each candidate run `python3 scripts/ledger.py check <ledger> --claim "<one English sentence>" --also "<the same idea in other words>"`; the check is word-based, so the extra wordings matter. A match with a named killer is reported at once; continue only if the proposal says what changed. Get the lessons to apply with `python3 scripts/lessons.py select <profile> --tags <tags>`. If the run belongs to a topic track (from topic-scout or the user), add `--track <track>` to the check, treat hits from other tracks only as duplicate evidence, and write `"track": "<track>"` into `gate_summary.json`. Create `<out>/notes/`, `<out>/lit/` and an empty `evidence.jsonl`.
2. **Decompose.** For each candidate write 3–6 atomic claims (what is computed, under which input contract, what improves, how it is measured); the core computation in its most reduced math; the kill condition per claim; and the conclusion at stake. If no conclusion would change, novelty is at most 3.
3. **Plan coverage.** Rows are claims; columns are query families A–F in [references/search_playbook.md](references/search_playbook.md), with at least three formulations each. The matrix goes into `details.md`; coverage is what makes "not found" meaningful.
4. **Search.** With subagents, split by claim or family (at most about 7) and brief each with [references/subagent_brief.md](references/subagent_brief.md); their findings are SEC until you check them. Tools: `scripts/lit_fetch.py` (`arxiv`, `openalex`, `citing`, `resolve`, `pdf`; see `--help`) and the host's web search. On arXiv HTTP 429, continue with OpenAlex and log a FAIL.
5. **Verify.** Pick the 3–6 priors that decide the verdict. Fetch full text (`lit_fetch.py pdf <id or url> --out <out>/lit`, abstracts with `--save-abstracts <out>/lit`), log exact quotes to `evidence.jsonl`, and run `python3 scripts/quote_check.py <out>/evidence.jsonl`; fix or downgrade every failure. Resolve every cited paper.
6. **Attack, then adjudicate.** Write the strongest rejection memo you can (about 200 words, evidence only; a fresh subagent with the evidence files works well). Keep an attack only if FT/ABS evidence or a checkable derivation supports it, then state the surviving difference in one verifiable sentence. Always run the classical-equivalence and theory-forced checks (playbook sections 3–4) and every selected lesson; record each lesson's result in `gate_summary.json` under `lessons`.
7. **Score** novelty and feasibility separately per the rubric, citing evidence ids; feasibility includes the rubric's data-hygiene checks.
8. **Design B0** for Recommended and Near-miss candidates per [references/b0_design.md](references/b0_design.md), freezing thresholds with `scripts/freeze.py`. For a near miss, the B0 is the minimal evidence that would lift it.
9. **Write the outputs.**
   - `details.md` (audit record, English) per [references/details_template.md](references/details_template.md). Killed candidates get evidence and a one-line revival condition, no B0.
   - `gate_summary.json`, schema in the same template.
   - `report.md` (human report, English) per [references/report_template.md](references/report_template.md) and [references/report_style.md](references/report_style.md), plus `report.<code>.md` if an extra language is set.
   - Run `python3 scripts/report_lint.py gate <out>` and fix every ERROR.
10. **Close the loop.** Show ledger proposals with `python3 scripts/ledger.py add <ledger> --from-summary <out> --dry-run` and append after the user confirms (verdict `pending` if they asked for unattended use; set `parent` for a revised topic). Then run `python3 scripts/lessons.py tally <profile> <out>`, propose at most two lesson changes, and offer a tidy-up if it says "REVIEW DUE", all per [references/profile_maintenance.md](references/profile_maintenance.md). In the chat give, in the user's language, the verdict, the main reason with the closest paper's link, the first test for a near miss, and the file paths. Ask before running any B0.

## Pitfalls seen in practice
- Family E is not optional: forward citations of the closest prior find the weeks-old competitor that keyword search misses.
- Abstracts rarely decide anything; the dropped term or restrictive assumption sits in the method section or appendix.
- "Rankings flip under a better metric" counts only if theory does not force the flip. "Apply X to Y" passes only if the failure point of naive transfer is defined.
- A second model family, if available, is a good adversary for step 6.
