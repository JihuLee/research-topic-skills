# Lessons (checklist)

The novelty gate applies every bullet as a check and reports the result. Phrase each lesson as something you can verify. Add your own as you learn them; the starters below are general.

## Novelty
- Check: the closest work from the last 6–12 months with the **same input contract** was searched for, including forward citations of the closest prior.
- Check: the core computation was reduced to its simplest math and compared with classical methods under other names.
- Check: the claimed finding is not forced by theory (for example, the perception–distortion trade-off, or a convexity argument).
- Check: "data is scarce", "generalization is hard" or "existing metrics are insufficient" is not the whole contribution. Some new evaluation actually changes a conclusion or ranking, and that is falsifiable.
- Check: no new name for an existing method or combination is presented as a contribution.

## Baselines and pre-experiments
- Check: the native, no-intervention pipeline is a registered baseline. It is often the strongest.
- Check: the four cheap baselines are registered: native, common default, simplest use of the key information, equal compute.
- Check: an oracle or upper bound of the allowed method family is measured before building anything (B0).
- Check: thresholds are reachable on a known-good input in the dtype and resolution actually used, and are frozen before results.
- Check: blocked (access or installation), inconclusive (power) and killed (hypothesis) outcomes are kept apart.

## Data and claims
- Check: train/dev/test overlap, near-duplicates, same-source groups and pretrained-weight training data were checked against the evaluation pools.
- Check: licenses were checked separately for images, annotations, code and weights; extra downloads triggered by defaults were found.
- Check: synthetic or simulated ground truth is not claimed to be real-sensor ground truth.
