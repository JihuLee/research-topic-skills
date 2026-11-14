---
tags: [novelty-gate]
max_turns: 120
timeout_seconds: 3600
allowed_tools: [Read, Glob, Grep, Write, Edit, Bash, WebSearch, WebFetch, Agent, Skill]
---

Desk review with literature cutoff 2017-05-31; treat anything published later as unknown. Idea: a sequence-to-sequence model for machine translation that drops recurrence and convolution entirely and relies only on attention, including self-attention within the encoder and the decoder.
