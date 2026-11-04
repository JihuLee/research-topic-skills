# Example — novelty gate (2026-01-31)

- Literature cutoff: 2026-01-31.
- **Verdict: NONE**

## 1. Candidates
| id | candidate | novelty | feasibility | closest prior | status |
|---|---|---:|---:|---|---|
| C1 | label smoothing vs temperature scaling under shift | 3 | 5 | https://arxiv.org/abs/2501.01234 | near-miss |
| C2 | temperature scaling changes AUROC | 2 | 5 | theory-forced | killed |

## 3. Details
C1 closest prior: https://arxiv.org/abs/2501.01234 (FT, E1).

```json gate-summary
{
  "schema": "novelty-gate/v1",
  "date": "2026-01-31",
  "literature_cutoff": "2026-01-31",
  "entry_threshold": 4,
  "verdict": "none",
  "candidates": [
    {"id": "C1", "title": "Label smoothing vs temperature scaling under shift", "claim": "Label smoothing during fine-tuning improves calibration under shift more than temperature scaling.",
     "novelty": 3, "feasibility": 5, "status": "near-miss", "killer_type": "none",
     "closest_prior": [{"title": "A Test Paper on Calibration", "url": "https://arxiv.org/abs/2501.01234", "tag": "FT", "evidence": "E1", "overlap": "in-distribution only"}],
     "baselines": {"native": "no recalibration", "common_default": "temperature scaling", "simplest_key_info": "histogram binning", "equal_compute": "2-member ensemble"},
     "b0": {"cost": "4 GPU-h", "primary_endpoint": "ECE on the shifted split", "promote_if": "ECE gain >= 1 point with paired CI > 0", "kill_if": "gain < 0.5 point",
            "inconclusive_if": "CI width > 2 points", "blocked_if": "shifted split unavailable", "known_good": "synthetic miscalibrated logits recovered"},
     "failing_gate": "novelty 3 < 4"},
    {"id": "C2", "title": "Temperature scaling changes AUROC", "claim": "Temperature scaling of a binary classifier changes its AUROC.",
     "novelty": 2, "feasibility": 5, "status": "killed", "killer_type": "theory-forced",
     "derivation": "AUROC depends only on the ranking of scores, and one monotone transform preserves the ranking.",
     "closest_prior": [], "failing_gate": "theory-forced"}
  ],
  "coverage": [
    {"claim": "C1.a", "A": "done", "B": "done", "C": "done", "D": "done", "E": "done: arXiv since 2025-08-01", "F": "done"},
    {"claim": "C2.a", "A": "done", "B": "done", "C": "n/a: derivation", "D": "done", "E": "done", "F": "done"}
  ]
}
```
