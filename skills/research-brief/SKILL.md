---
name: research-brief
description: Turns a research idea that passed the novelty-gate skill into an execution-ready study specification (hypothesis, baselines, leakage-safe splits, one primary endpoint, thresholds frozen with a hash, go/no-go gates, compute limits, inline literature) for a human team or an autonomous agent. Use it when someone asks for the study plan, brief, handoff or pre-registration of a vetted candidate, for example "write the study plan for C1", in any language. Not for a general proposal of an unvetted idea. For interactive use with a researcher, not for autonomous research pipelines.
compatibility: Claude Code or Codex. Python 3.8+ stdlib scripts.
metadata:
  version: "0.5.1"
---

# Research brief

Make the next stage able to run the study without re-deciding anything, and unable to move the goalposts quietly. Most failures after a good idea are specification failures: an unregistered baseline, an unreachable threshold, an evaluation set that leaked into selection, or an executor with no web access and no literature facts.

**Who may use it:** a researcher, directly or through agents working for them in this session; not autonomous pipelines. First run `python3 <this-skill-dir>/scripts/guard.py` and stop if it exits non-zero. Call scripts by absolute path (`<this-skill-dir>/scripts/…`) and write only to the output directory.

## Inputs
- **A novelty-gate output folder** (`details.md`, `gate_summary.json`, `evidence.jsonl`; older runs have one `gate_report.md`) with a Recommended (PASS) candidate. If there is none, offer to run novelty-gate first. If the user still wants a brief, record that override in it.
- **Profile** ([references/data_contract.md](references/data_contract.md)): budgets, ground-truth policy, optional `handoff_template` and `content_check_command`.
- **Decisions only the user can make:** target venue, run scope, selection rule, roles. Ask for them.

## Workflow
1. **Template.** Use the profile's `handoff_template` if set (keep its headings), else [assets/brief_template.md](assets/brief_template.md).
2. **Fill each section from the gate evidence** per [references/brief_sections.md](references/brief_sections.md). Never invent a number: write "unknown — measured in B0/G1" and list it under Open items. Put the user's own execution lessons into the gates and operations sections: `python3 scripts/lessons.py select <profile> --tags execution,b0,<topic tags>`.
3. **Literature.** Copy the decisive facts with exact URLs, quotes and search expressions from `evidence.jsonl`; the executor may have no web search.
4. **Splits** per [references/split_rules.md](references/split_rules.md).
5. **Pre-registration.** Write `thresholds.json` (from the gate's B0 or `python3 scripts/freeze.py template`), run `python3 scripts/freeze.py freeze thresholds.json`, quote the sha256, and describe the known-good and null fixtures.
6. **Checks.** Run the profile's `content_check_command` if set (never copy matched secrets anywhere). Run `python3 scripts/report_lint.py brief <brief.md> --thresholds thresholds.json`; with a custom template, put `<!-- section:ID -->` markers and pass `--sections`. Fix every ERROR.
7. **Ledger.** `python3 scripts/ledger.py update <ledger> --id <id> --set stage=brief`, if the entry exists.
8. **Human report.** `report.md` in English per [references/report_style.md](references/report_style.md): what the study tests (two sentences), the first test with its stop and continue rules, cost against the budget, and the open decisions; plus `report.<code>.md` if an extra language is set. Check with `python3 scripts/report_lint.py human <file>`. In the chat, give a short version in the user's language and the file paths.

## Output
`brief.md` (English, or the language of the user's template), `report.md` (plus `report.<code>.md`), `thresholds.json` and `thresholds.json.sha256`.
