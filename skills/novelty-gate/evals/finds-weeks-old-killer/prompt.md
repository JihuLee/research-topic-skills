---
tags: [novelty-gate]
max_turns: 120
timeout_seconds: 3600
allowed_tools: [Read, Glob, Grep, Write, Edit, Bash, WebSearch, WebFetch, Agent, Skill]
---

Is this new? Literature cutoff 2026-11-06, no profile, use defaults.

Idea: in class-conditional conformal prediction on long-tailed ImageNet, classes with no calibration examples fall back to the shared marginal threshold. I want to predict each class's threshold offset from label-free descriptors of the classifier-head weights (for example weight norm and angle to the nearest class), so every class gets its own threshold while split conformal's marginal guarantee is kept.
