# B0 design: the cheapest falsifying pre-experiment

B0 runs before any implementation of the proposed method. It answers one question: is there enough room for the claimed effect, and would the result change a conclusion? Many ideas die here, cheaply: an hour spent measuring the best achievable gain can save weeks of building a method whose ceiling is too low.

Design it so that it is **informative in both directions**. A negative result should also teach something.

## Checklist

1. **Question.** Write one sentence: "B0 decides whether …".

2. **Allowed-family oracle.** Find the best achievable result within the method family, using ground truth, exhaustive search or an exact posterior where allowed. If oracle headroom < margin × minimum effect (margin usually 2), the hypothesis is KILLED and the method is never built.

3. **Four baselines.** Pre-register all four. Choose the best one, B*, on the dev split, and compare only against B*.
   - **Native / no intervention:** the pipeline without the proposed component. It is often the strongest.
   - **Most common default:** the library default or standard practice.
   - **Simplest use of the key information:** for example drop, clamp, threshold, recalibrate, or nearest neighbour.
   - **Equal-compute alternative:** spend the same compute differently, for example more samples, more steps, or an ensemble.

4. **One primary endpoint.** Set its direction, the resampling unit (image, scene, sequence), the CI method (for example paired bootstrap with 10,000 resamples at 95%), the seeds, and the rerun tolerance. Report secondary metrics, but they decide nothing.

5. **Minimum effect and margin.** Choose the smallest effect worth a paper, justified by the field's typical gains or by a downstream consequence. Require oracle headroom ≥ margin × that effect.

6. **Known-good attainability.** Build a synthetic or fixture input where the effect certainly exists, and a null fixture where it certainly does not. A known-good implementation must reach the thresholds on the first and not on the second. Unattainable thresholds are a classic way to kill a true hypothesis. Check them with the dtype, resolution and noise you will actually use.
   - The gate **describes** these fixtures. Running them is part of B0 and needs the user's approval.
   - Freezing the thresholds before the fixture runs is fine. A failed fixture means BLOCKED, not KILLED.

7. **Freeze before seeing results.**
   - Write `thresholds.json` with numbers as JSON numbers, not prose.
   - Run `python3 scripts/freeze.py freeze thresholds.json`.
   - Quote the hash in the report.
   - After results, thresholds may only be tightened: `freeze.py amend --after-results` refuses anything else.

8. **Outcome classes.**
   - **PROMOTE:** the evidence for the upgrade holds; raise novelty to the threshold, or proceed.
   - **KILLED:** the hypothesis failed.
   - **INCONCLUSIVE:** not enough power or samples. State the sample size that would be needed.
   - **BLOCKED:** access, installation or implementation failure. This says nothing about the hypothesis.

9. **Data hygiene.** Apply the feasibility checks in [rubric.md](rubric.md) to the B0 data. In addition, split by salted hash of IDs in fixed ranges, and keep sealed and final sets outside anything an automated executor can read.

10. **Cost.** Count GPU-hours, download GB and wall-clock time against the profile's tiers. Prefer the cheaper tier. Owned assets (`assets.md`) can make B0 nearly free.

11. **Scope statement.** Say what B0 cannot show. For example, simulated ground truth is not real-sensor ground truth, and a toy prior does not represent a learned one.

## thresholds.json skeleton

Get a starting point with `python3 scripts/freeze.py template`, then edit it. At minimum keep these keys:
- `question`, `primary_endpoint`, `resampling`, `min_effect`, `headroom_multiplier`
- `promote_if`, `kill_if`, `inconclusive_if`, `blocked_if`
- `known_good`, `null_fixture`, `baselines`, `budget`
