---
tags: [novelty-gate]
max_turns: 120
timeout_seconds: 3600
allowed_tools: [Read, Glob, Grep, Write, Edit, Bash, WebSearch, WebFetch, Agent, Skill]
---

Novelty check before I implement: literature cutoff 2026-11-06, no profile.

Idea: an EM algorithm for blind image deblurring with a pretrained diffusion prior. The E-step computes the posterior mean of the sharp image with the diffusion model, given the current blur kernel. The M-step updates the kernel by least squares between the blurry image and the kernel applied to that posterior-mean image. Repeat until convergence.
