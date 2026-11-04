# Generation lenses

Each lens is a different way to look at the corpus. Fix the list before generating; skip lenses the profile excludes. Compute or systems optimization is **not** a default lens. Add it only when the profile allows such topics.

## Lenses

1. **Heuristic → principle.**
   - Start from a code-only trick: a clamp, stop-gradient, epsilon, rescaling, warm-up or special case.
   - Ask why it works. Derive the objective, constraint or estimator it implicitly implements.
   - Predict where it fails. The candidate is "make the implicit thing explicit, and show the regime where the trick breaks."

2. **Assumption relaxation.**
   - Pick one strong assumption: isotropy, independence, linearization, stationarity, known noise, known operator, or a single mode.
   - Derive the error term when it breaks, and find a tractable correction.
   - Check that the breaking regime actually occurs in data people care about. Without that, the correction has no audience.

3. **Breakdown-first transfer** (to a new domain or task). Work through four steps in order:
   1. **Structural mapping:** what the core operator needs (continuity, a metric, calibrated uncertainty, a known likelihood) versus what the target domain offers.
   2. **Naive transplant failure:** show or predict why applying it unchanged breaks — exploding variance, a missing Jacobian, violated symmetry, collapse.
   3. **Minimal bridge:** the smallest change that fixes the failure, such as a projection, a surrogate or a reparameterization.
   4. **Target-domain value:** which problem that the target community already has gets solved.

   Without step 2, the idea is a trivial application.

4. **Evaluation that changes a conclusion.**
   - An existing benchmark or protocol whose ranking or conclusion could flip under a verifiable alternative.
   - State the mechanism of the flip.
   - Check first that the flip is not forced by theory; see the gate's playbook.

5. **Contradiction.** Two published findings that disagree. Design the experiment that tells them apart.

6. **Untested assumption.** Something everyone assumes and nobody has measured against verifiable ground truth.

7. **Regime shift.** An unexplored regime (noise level, resolution, data size, dimension, compute), with a stated reason to expect the known answer to change there.

8. **Owned-asset reuse.**
   - Datasets, weights, caches or tools listed in `assets.md` that make a B0 nearly free.
   - Questions those assets uniquely enable.

9. **Near-miss revival.** Ledger near-misses whose flipping evidence has become cheaper: new public data, new code, or a newly released model.

## Candidate record

One record per idea. These fields feed the pre-filter and the gate.

```json
{"id": "S07", "lens": "assumption-relaxation",
 "hypothesis": "one sentence, falsifiable",
 "mechanism": "why it would be true",
 "conclusion_at_stake": "which conclusion or ranking changes if true",
 "contribution": "method | benchmark | analysis | theory | dataset",
 "b0_sketch": "cheapest test, one or two lines",
 "assets": ["owned asset names used, if any"],
 "source": "corpus file:line or ledger id that inspired it",
 "dedup_key": "short slug of the hypothesis"}
```

A good candidate:
- matters whichever way its B0 turns out;
- names its conclusion at stake;
- can be killed by a specific paper or experiment.
