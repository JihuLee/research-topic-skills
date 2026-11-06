---
tags: [novelty-gate]
max_turns: 120
timeout_seconds: 3600
allowed_tools: [Read, Glob, Grep, Write, Edit, Bash, WebSearch, WebFetch, Agent, Skill]
---

Can you vet this paper idea? Cutoff 2026-11-06, defaults.

On 256x256 image denoising, the 95% per-pixel credible intervals from our diffusion posterior sampler cover the truth 94% of the time, but the 95% joint credible region over the whole image covers it only 40% of the time. We want to publish this gap as a new diagnostic that reveals a previously unknown kind of miscalibration in diffusion posteriors.
