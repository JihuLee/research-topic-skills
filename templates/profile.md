# Research profile

Copy `templates/` to your own profile directory, for example `~/research-profile/`, and replace every `<...>` value and every example number. The skills read the prose for taste and the JSON block for constants.

This file describes you. Keep your filled-in copy private, outside any public repository.

## Taste (prose)
- What kinds of results excite you, and why:
- What you are unusually good at (methods, domains, data or instrument access):
- What you never want to work on again, and why:
- How you like to be told "no" (for example, a short verdict first, then the evidence):

## Constants

The numbers below are placeholders, not recommendations.

```json profile
{
  "output_language": "en",
  "interests": ["<research area, most preferred first>", "<second area>"],
  "preferred_contributions": ["method", "benchmark", "analysis"],
  "target_venues": ["<venue or track>"],
  "exclusions": ["<topic area you never want proposed>"],
  "ground_truth_policy": "public data and verifiable ground truth only; simulators allowed; no new human ratings or LLM judgments as the primary metric",
  "budgets": {
    "tiers": {
      "small": {"gpu_hours": 10, "download_gb": 10},
      "large": {"gpu_hours": 100, "download_gb": 100}
    },
    "wall_clock_hours": 48,
    "hardware": "<your hardware>"
  },
  "novelty_entry_threshold": 4,
  "recency_window_months": 6,
  "approval_required_for": ["downloads", "experiments", "gpu"],
  "report_dir_pattern": "./gate-{slug}-{date}/",
  "scout_level": "medium",
  "scout_depth": "standard",
  "corpus_paths": [],
  "handoff_template": null,
  "content_check_command": null
}
```
