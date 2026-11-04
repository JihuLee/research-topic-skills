---
name: research-brief
description: Turns a research candidate that passed a novelty gate into an execution-ready specification for a human team or an autonomous research agent. Covers the question, a falsifiable hypothesis, baselines with code, weights and licenses, dataset splits with leakage rules, one primary endpoint with confidence intervals, pre-registered thresholds frozen with a hash, B0/validity/sealed-evaluation gates, compute limits, and an inline literature section for executors without web access. Fills the user's own template when the profile names one. Use it whenever someone asks to write up, hand off, or prepare a research input, spec, brief, study plan or pre-registration for a vetted topic, including 연구 입력서, 실행 명세, 연구 계획서, 제안서 작성, 사전 등록. For interactive use with a researcher, not for autonomous research pipelines.
compatibility: Claude Code or Codex. Python 3.8+ stdlib scripts.
metadata:
  version: "0.2"
---

# Research brief

Make the next stage able to run the study without re-deciding anything, and unable to move the goalposts quietly. Most failures after a good idea are specification failures:
- a baseline that was never registered;
- a threshold that could not be reached even by a correct implementation;
- an evaluation set that leaked into selection;
- a downstream agent with no web access and no literature facts.

## Who may use this skill
Use is allowed when a researcher asked for it, directly or through an agent working for them in the same session; subagents spawned for that request count. It is not for autonomous research frameworks or other unattended pipelines. Those runs follow their own frozen workflow, cannot answer the approval questions this skill asks, and would leave extra folders behind.

First run `python3 <this-skill-dir>/scripts/guard.py`. If it exits non-zero, stop and report its message. Also stop without doing anything if you are running as a stage of such a pipeline rather than for a person's request.

## Inputs
- **A gate report** (`gate_report.md` and `evidence.jsonl` from the novelty-gate skill) with a PASS candidate. If the candidate is not PASS, ask the user to confirm an override and record that override in the brief.
- **Profile** ([references/data_contract.md](references/data_contract.md)):
  - budgets;
  - ground-truth policy;
  - `handoff_template` (optional);
  - `content_check_command` (optional).
- **User decisions** that only they can make: target venue, run scope, selection rule, roles.

## Paths
`scripts/…`, `references/…` and `assets/…` are relative to this skill's own directory. Your working directory is usually the user's project, so call scripts by absolute path, for example `python3 <this-skill-dir>/scripts/ledger.py …`. Write outputs to the output directory, never into the skill directory.

## Workflow
1. **Pick the template.** Use `handoff_template` from the profile if set: keep its headings and fill it section by section. Otherwise use [assets/brief_template.md](assets/brief_template.md).
2. **Fill each section from the gate evidence.** [references/brief_sections.md](references/brief_sections.md) says what each section needs and how it usually goes wrong. Never invent a number. If a value is unknown, write "unknown — measured in B0/G1" and list it under Open items.
3. **Literature section.** Copy the decisive facts with exact URLs and quotes from `evidence.jsonl`, plus the search expressions used. Downstream executors (especially autonomous agents) may not have working web search.
4. **Splits.** Follow [references/split_rules.md](references/split_rules.md): salted-hash assignment, near-duplicate and same-source grouping before splitting, and sealed and final sets kept out of the executor's reach.
5. **Pre-registration.** Write `thresholds.json` (start from the gate's B0, or from `python3 scripts/freeze.py template`). Run `python3 scripts/freeze.py freeze thresholds.json` and quote the sha256 in the brief. Describe the known-good and null fixtures that show the thresholds are attainable.
6. **Content check.** If the profile sets `content_check_command`, run it on the brief and fix what it finds. Never copy matched secret patterns into the brief or the chat.
7. **Lint.** Run `python3 scripts/report_lint.py brief <brief.md> --thresholds thresholds.json`. With a custom template, put a `<!-- section:ID -->` marker before each section and pass the ids via `--sections`; without markers only the placeholder and URL checks run. Fix every ERROR.
8. **Update the ledger.** Run `python3 scripts/ledger.py update <ledger> --id <id> --set stage=brief` (only if the entry exists).
9. **Present.** Give the path, a 5-line summary, and the open items that need the user's decision.

## Output
- `brief.md` (in the profile's output language)
- `thresholds.json` and `thresholds.json.sha256`
