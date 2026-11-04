# Grounding levels and depth

## Level: how much the scout draws on the researcher's own material

The level changes only **where candidates come from** and **how they are ranked**. These never change with the level:
- profile exclusions, budgets and ground-truth policy;
- the ledger duplicate check;
- the novelty-gate's standards.

| | high | medium (default) | low |
|---|---|---|---|
| Candidate quota (own material : landscape) | 80 : 20 | 50 : 50 | 0 : 100 |
| Read | corpus (full audit), `assets.md`, ledger, profile | profile, ledger, `assets.md`, a light corpus pass (top leads only) | profile (interests and taste prose) and the ledger, for the duplicate check only. The corpus and `assets.md` are **not opened** |
| Lenses ([generation_lenses.md](generation_lenses.md)) | own-material lenses 1, 2, 3, 8, 9, plus a few landscape lenses | both groups | landscape lenses 4–7 applied to `landscape.md` entries |
| Ranking weights (info value, own-asset edge, taste fit, low cost) | 0.35, 0.35, 0.15, 0.15 | 0.35, 0.25, 0.25, 0.15 | 0.35, 0, 0.50, 0.15 |

For ranking, score each criterion 1–5 and store the weighted sum in the record's `rank` field. The landscape signal types (open problems, saturated benchmarks, contradictions and so on) are inputs to the lenses, not lenses themselves.

The quota is a target share of the raw candidates. With 12 raw candidates at medium, aim for about 6 from own material and 6 from the landscape. If one source runs dry, say so; do not pad it.

**What counts as own material:** the corpus, `assets.md`, the ledger's near-misses, and the researcher's core operator.

**What counts as landscape:** recent literature found by [landscape_scan.md](landscape_scan.md).

**Profile prose:** taste, strengths and things to avoid steer every level. At low it is the only personal input besides interests.

## Depth: how far each run goes

| depth | Candidates | Gate | Query budget for the scout (landscape plus quick signals, excluding the gate) | Typical cost |
|---|---|---|---|---|
| quick | generate, pre-filter, quick novelty signals for the top ~5 | none; the user picks what to gate | ~20 | ~10 min |
| standard (default) | same, signals for the top ~8 | top 1, novelty-gate in light mode | ~30 | ~30 min |
| full | same, signals for all survivors | top 3, novelty-gate in full mode | ~50 | an hour or more |

Light mode of the gate:
- no subagents;
- query formulations shared across claims;
- at most 4 decisive priors verified in full text.

Full mode follows the gate's normal workflow.

## Recording

Every candidate record carries `source` (`corpus`, `assets`, `ledger`, `landscape` or `profile`) and the run's `level`. The report states the level, the depth and the actual source mix, so the user can see that, for example, a low run never touched the corpus.
