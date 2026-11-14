---
tags: [novelty-gate]
max_turns: 120
timeout_seconds: 3600
allowed_tools: [Read, Glob, Grep, Write, Edit, Bash, WebSearch, WebFetch, Agent, Skill]
---

Can you vet this paper idea? Cutoff 2026-11-14, defaults.

We took the top 5 of 200 submitted models ranked by validation accuracy on a public benchmark. On a fresh test set drawn from the same distribution, all 5 score 1 to 3 points lower than on validation. We want to publish this drop as new evidence that the benchmark is overfit.
