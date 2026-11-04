# Brief sections: what each needs, and how it usually goes wrong

| Section | Needs | Common failure |
|---|---|---|
| 0 Meta | Run scope and a selection rule fixed before the run | A selector that looks at many metrics and picks post hoc. Fix the order: eligibility → primary endpoint → cost → id. |
| 1 Problem | Isolated hypotheses, each with its refutation | Hypotheses that cannot fail. A condition inside the base model's training distribution, so there is no headroom. A "fix" that a standard tool already provides. |
| 2 Baselines | Code commit, weights terms, exact training split, extra downloads, four cheap baselines | The native, no-intervention pipeline is missing and turns out strongest. Weights were trained on the evaluation images. A default config silently downloads a backbone. |
| 3 Reported | Same-protocol numbers or "none" | Comparing against numbers from a different protocol instead of B* measured in the same pipeline. |
| 4 Benchmark | Licenses per asset, overlap check, official evaluator rules | Ignoring the evaluator's reading rules (for example, min-over-references). Mixing licenses. |
| 5 Splits | Hash assignment, grouping before splitting, sealed sets outside the run | Near-duplicates across splits. Sealed data readable by the executor. |
| 6 Metrics | One primary endpoint, resampling unit, CI, rerun tolerance | Several "primary" metrics. Pooled-only reporting that hides per-group failures. Report both pooled and macro. |
| 7 Constraints | One budget tier and the prohibitions | Adding tiers together. Wall clock that forgets waiting and evaluation time. |
| 8 Resources | Isolated environment, free-hardware check | Installing into shared environments. Jobs launched on hardware another job is using. |
| 9 Literature | Inline facts and URLs, search expressions | Pointing to papers without the facts, for an executor that cannot browse. |
| 10 Cutoff | A date | Silent post-cutoff citations. |
| 11 Novelty | Score with reasons | A score without the rubric, or without the closest prior. |
| 12 Gates | Frozen thresholds, known-good attainability, outcome classes | Thresholds no correct implementation can reach. Relaxing thresholds after seeing results. Treating BLOCKED as KILLED. |
| 13 Ops | Monitoring that also catches "waiting for intervention" states | Runs that stall silently. |

## Executor-facing hygiene (general lessons)
- Run inference without gradient tracking. Out-of-memory crashes from forgotten gradient graphs are common.
- Compute geometric predicates in float64 when the thresholds are tight. Run the known-good check in the dtype you will actually use.
- Verify, line by line, the executor's implementation of every frozen formula before launch. Executors sometimes re-implement a frozen statistic differently, for example a percentile as a mean.
- Write frozen constants as machine-readable values, not prose.
- Do not trust a file's ETag as a content hash.
