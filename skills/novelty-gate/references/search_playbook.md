# Search playbook

## Contents
1. Query families A–F
2. Sources and tools
3. Classical-equivalence traps
4. Theory-forced results
5. Stopping rule
6. Coverage matrix format

## 1. Query families

Run every family for every atomic claim, with at least three query formulations per family. A query that serves several claims counts for each of them; record which claims each query covers. Different communities use different words for the same thing, which is why one formulation is never enough.

**A — Same input contract.** Define what the method gets at test time and in training: inputs, references, supervision, data source, compute regime. Search for methods with that contract under any task name. For example, "few-shot segmentation with normal references" may live as "golden-template comparison", "reference-based anomaly detection", or "change detection".

**B — Same claim or conclusion.** Search for the claimed effect itself, phrased as a result: "X does not imply Y", "rankings disagree", "fails when", "is biased toward". Benchmarks and analysis papers often state your conclusion without your method.

**C — Same computation under other names.** Take the reduced math from step 2. Ask which community would have solved it twenty years ago: signal processing, statistics, numerical analysis, coding theory, operations research, physics. Search the classical names (section 3).

**D — Same benchmark or protocol.** Find who already evaluates on that dataset or protocol. Check for leaderboards, challenge reports, and papers that criticize the protocol.

**E — Recency sweep.** Covers the last `recency_window_months` (profile; default 6):
- OpenAlex relevance search with a date filter, for 3–5 keyword combinations: `lit_fetch.py openalex "<terms>" --since <date>`; then arXiv by submission date with 2–3 exact terms: `lit_fetch.py arxiv "<terms>" --since <date> --sort submitted`;
- forward citations of the 3 closest priors: `lit_fetch.py citing <id> --since <date>`;
- accepted-paper lists of the current conference cycle and open review submissions for the next venue in the area.

Recent direct competitors cluster here.

**F — Strongest cheap baseline.** The simplest method that uses the key information:
- thresholding, nearest neighbour or a linear probe;
- recalibration (temperature or variance scaling);
- test-time augmentation, or ensembling 2–3 seeds;
- an oracle-tuned version of the existing baseline;
- the native, no-intervention pipeline.

If one of these closes most of the gap, the idea's contribution shrinks to that gap.

## 2. Sources and tools

| Source | Use | Notes |
|---|---|---|
| arXiv API (`lit_fetch.py arxiv`) | newest preprints, date filters, field queries (`ti:`, `abs:`, `cat:`) | strict keyword filter: exact tokens, no stemming or synonyms. Use 2–3 distinctive terms or a quoted phrase. ~3 s between calls (the script waits) |
| OpenAlex (`lit_fetch.py openalex`, `citing`, `resolve`) | relevance search with date filters (best default for recency sweeps), venues, forward citations, DOI resolution | no key needed; abstracts rebuilt from the inverted index. Citations may sit on the preprint or on the published record, so run `citing` on both |
| PDF full text (`lit_fetch.py pdf`) | decisive quotes | arXiv IDs or direct URLs; extracted text has page markers |
| Open-access proceedings (CVF, PMLR, NeurIPS, ACL Anthology, OpenReview) | camera-ready text, supplements | |
| Official code repositories | real training splits, dropped terms, licenses | issues and READMEs often state the real split |
| Dataset and model cards | licenses, train/test splits, sizes | |
| Host web search | everything else | |

Semantic Scholar without an API key rate-limits quickly. Treat it as optional.

OpenAlex has a daily budget: about 100 searches without a key, about ten times more with a free key (`OPENALEX_API_KEY`). When it answers HTTP 429, continue with arXiv and web search, log a FAIL entry, and mention the key to the user.

## 3. Classical-equivalence traps

A starter list; extend it with the user's `lessons.md`. For each candidate, write the reduced computation and check it against these:

- **Probabilistic.**
  - Under Gaussian assumptions the posterior mean equals the MAP estimate.
  - A Gaussian log-likelihood ratio reduces to a projection or Mahalanobis distance.
  - EM with a mean-only E-step is alternating joint MAP, because it drops the covariance term.
  - Many "new" variational objectives are ELBO variants; Laplace approximations recur too.
  - Kalman/RTS smoothing is Gaussian belief propagation on a chain.
  - Particle methods degenerate in high dimension.
- **Numerical.**
  - Gauss/Radau quadrature, low-rank (Woodbury) updates, preconditioning.
  - Dynamic programming, Viterbi or forward–backward on a lattice or trellis.
  - Assignment and matching (Hungarian, min-cost flow), convex relaxations.
- **Signal processing and coding.**
  - Wiener and matched filtering, closed forms in the Fourier domain.
  - Soft-decision and iterative (turbo) decoding, joint source–channel decoding.
- **Geometry and measure.**
  - Disintegration and conditional measures.
  - Optimal transport (Sinkhorn); lifting to orientation or scale spaces.
- **Learning.**
  - kNN or memory-bank scoring; template or reference differencing ("golden template").
  - Mixup or label union for compositional classes.
  - Stop-gradient targets, which are target networks.
  - Recalibration as a post-hoc fix.

When one matches, the candidate's novelty rests on whatever is left after the reduction. Usually that is at most 2.

## 4. Theory-forced results

Before accepting "metric X disagrees with metric Y" or "method family A beats B on Z" as a finding, check whether it is a mathematical necessity:

- **Posterior samples.** An exact posterior sample x̂ ~ p(x|y) has E‖x̂ − x‖² = 2·tr Cov(x|y), twice the MMSE. It always loses about 3 dB PSNR to the posterior mean. This is the perception–distortion trade-off.
- **Joint coverage in high dimension.** A joint ℓ2/HPD credible-region coverage collapses under tiny variance mis-scaling: roughly Φ(z_α − ε·√(d_eff/2)) for relative variance error ε and effective dimension d_eff. Per-coordinate coverage can still look fine.
- **Averaging.** The squared error of an averaged prediction is at most the average of the members' squared errors (Jensen). An ensemble beating its average member is expected, not a finding.
- **Rank-based metrics.** AP, AUROC and other rank-based metrics cannot change when one monotone function is applied to all scores, as in single-temperature recalibration of a scalar score.

If the claimed finding follows from one of these, report it as theory-forced (novelty ≤ 2 for that claim). The idea may survive on another claim.

## 5. Stopping rule

Stop a family for a claim when both hold:
- three formulations return nothing new in their top 20 results;
- forward citations of the closest prior inside the recency window are exhausted.

Record the queries used.

## 6. Coverage matrix format

In the report and in the `gate-summary` JSON:

```json
{"claim": "C1.b", "A": "done: 4 queries", "B": "done", "C": "done: Wiener, EM covariance", "D": "done", "E": "done: arXiv since 2026-05-01 + citing 2 priors", "F": "done"}
```

Use `failed: <reason>` when a family could not be completed, and `n/a: <reason>` when it does not apply.
