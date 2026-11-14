# Keeping the ledger and lessons small

The ledger and `lessons.md` grow with every run. Keep them useful with three rules:

1. **Change by delta, never by rewrite.** Apply single operations with the scripts (`lessons.py apply`, `ledger.py update`). Never ask a model to rewrite a whole file: a full rewrite tends to drop the specific details that make a lesson useful.
2. **Archive, never delete.** Archived lessons go to `lessons_archive.md`. Ledger entries are permanent; `update` keeps their old values in `history`.
3. **Propose, then apply after the user approves.** Show the plan, wait for approval, then run the script.

The file formats are in [data_contract.md](data_contract.md).

## In every gate run

**Read less.**
- Read `ledger_index.md`, not `ledger.jsonl`. If it is missing, run `python3 scripts/ledger.py index <ledger>`.
- Get the lessons to apply from `python3 scripts/lessons.py select <profile> --tags <candidate tags>`. Use tags from the ledger index where they fit.

**Check duplicates with more than one wording.** `ledger.py check` compares words, so a renamed idea can slip through. Pass the claim in two or three other wordings:

```bash
python3 scripts/ledger.py check <ledger> --claim "<claim>" --also "<the same idea in other words>" --also "<…>" --tags <tags>
```

Then read the top hits and decide yourself whether one is the same idea.

**Record lesson results.** In `gate_summary.json`, add `"lessons": [{"id": "L12", "result": "caught"}, …]`, one item per selected lesson. Results:

| Result | Meaning |
|---|---|
| `caught` | the check found a real problem |
| `clear` | the check was applied and passed |
| `n/a` | the check did not apply to this candidate |
| `false_alarm` | the check flagged something that turned out fine |

**After the user confirms the verdict:**
1. Run `python3 scripts/lessons.py tally <profile> <out>`. A run is counted only once.
2. Optionally propose **at most two** lesson changes, only for things this run actually taught. For each one, first run `python3 scripts/lessons.py similar <profile> --text "<draft>"`. Then pick one action:
   - **add:** nothing similar exists;
   - **edit:** sharpen or widen an existing lesson;
   - **no change:** a similar lesson already covers it.
3. Write a check, not a story: one sentence that a later run can verify, plus 1–3 tags. Tag lessons about running experiments (tooling, monitoring, numerics) `execution`: research-brief puts those into the brief.
4. Show the plan as JSON and apply it after approval with `python3 scripts/lessons.py apply <profile> plan.json`. Use `--dry-run` first to show the result.
5. For a revised or re-checked topic, add the new ledger entry with `"parent": "<earlier id>"`.

## Tidy-up (when `tally` says "REVIEW DUE")

A review is due after `lessons_review_every_gates` gate runs (default 20). It is also due when active lessons exceed `lessons_max_active` (default 40), or when pinned plus core lessons exceed `lessons_core_cap` (default 20). Ask the user once whether to tidy up now. If they agree:

1. Run `python3 scripts/lessons.py review <profile>`. It lists candidates:

   | Candidate | Proposal |
   |---|---|
   | Unmarked lessons | `adopt`, with a tier and tags |
   | Near-duplicates | `merge` into the clearer one; the others are archived as "merged into" |
   | Applied five or more times and never caught anything | `archive` |
   | False alarms at least as often as catches | `edit` to narrow, or `archive` |
   | Scoped lessons that caught three or more times | promote to core (`edit` the tier) |
   | Pinned plus core over the cap | demote the least useful to scoped |

   Do not archive a lesson that never caught anything if it guards a rare but costly failure. Make it `pinned` instead.

2. Also read the lessons for ones that only restate a rule the skill already enforces. Examples: input-contract search, classical equivalence, theory-forced results, the four baselines, oracle first, data hygiene. Archive them with the reason "covered by the skill".
3. Look at old near-miss entries in `ledger_index.md` and list the ones whose revival evidence may now exist.
4. Show one plan with every operation and its reason. Apply it after approval, then run `python3 scripts/lessons.py mark-reviewed <profile>`.
