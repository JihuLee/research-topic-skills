---
tags: [novelty-gate]
max_turns: 120
timeout_seconds: 3600
allowed_tools: [Read, Glob, Grep, Write, Edit, Bash, WebSearch, WebFetch, Agent, Skill]
---

Novelty check before I write this up: literature cutoff 2026-11-14, no profile.

Idea: "Residual-Attention Regression", a new robust training rule for linear regression on data with outliers. At each iteration, compute a weight for every sample as 1 / max(|residual|, eps) from the current fit, then refit weighted least squares. Repeat until the weights stop changing. It ignores outliers without any tuning.
