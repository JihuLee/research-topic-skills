# Generation lenses

Each lens is a different way to look for candidates. Which lenses run depends on the level (see [levels.md](levels.md)):
- **own-material lenses** (1, 2, 3, 8, 9) read the corpus, `assets.md` and the ledger;
- **landscape lenses** (4, 5, 6, 7, applied to `landscape.md`) read recent literature;
- at level low only the landscape lenses run.

Fix the list before generating; skip lenses the profile excludes. Compute or systems optimization is **not** a default lens. Add it only when the profile allows such topics.

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
{"id": "C7", "lens": "assumption-relaxation", "source": "corpus", "level": "medium",
 "hypothesis": "one sentence, falsifiable",
 "mechanism": "why it would be true",
 "conclusion_at_stake": "which conclusion or ranking changes if true",
 "contribution": "method | benchmark | analysis | theory | dataset",
 "b0_sketch": "cheapest test, one or two lines",
 "assets": ["owned asset names used, if any"],
 "seed": "corpus file:line, ledger id, or landscape.md entry that inspired it",
 "dedup_key": "short slug of the hypothesis",
 "status": "generated | dropped | annotated | gated",
 "flags": ["negative patterns from prefilter.md, if any"],
 "related": [{"title": "...", "url": "...", "tag": "ABS"}],
 "reason": "why dropped, or the gate verdict",
 "rank": 3.6}
```

Write records in English so they match the ledger; the report uses the profile's language. `source` is one of `corpus`, `assets`, `ledger`, `landscape` or `profile`. Ids are `C1`, `C2`, … in generation order and stay fixed for the whole run, so follow-up requests such as "gate C3" can refer to them.

A good candidate:
- matters whichever way its B0 turns out;
- names its conclusion at stake;
- can be killed by a specific paper or experiment.
