---
tags: [novelty-gate]
max_turns: 120
timeout_seconds: 3600
allowed_tools: [Read, Glob, Grep, Write, Edit, Bash, WebSearch, WebFetch, Agent, Skill]
---

Can you vet this idea before I spend time on it? Literature cutoff 2026-11-01, no profile, use defaults.

Idea: keep dropout switched on at test time, run the network several times and average the predictions; the spread of the outputs gives Bayesian uncertainty estimates for a trained classifier without any retraining.
