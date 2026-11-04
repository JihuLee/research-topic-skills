# Bad example

```json gate-summary
{
  "schema": "novelty-gate/v1",
  "date": "2026-01-31",
  "literature_cutoff": "31.01.2026",
  "entry_threshold": 4,
  "verdict": "pass",
  "candidates": [
    {"id": "C1", "title": "Overclaimed", "claim": "x", "novelty": 3, "feasibility": 4, "status": "pass",
     "closest_prior": [{"title": "Some paper", "url": "https://example.org/p", "tag": "SEC"}]},
    {"id": "C2", "title": "Killed without a name", "claim": "y", "novelty": 2, "feasibility": 4, "status": "killed",
     "killer_type": "paper", "closest_prior": []}
  ],
  "coverage": []
}
```
