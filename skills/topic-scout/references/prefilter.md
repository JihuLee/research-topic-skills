# Pre-filter: drop on facts, annotate on judgment

The pre-filter shrinks the list before the expensive gate. It may only drop for **objective** reasons. Anything that is a judgment call gets annotated and passed on. The gate's evidence decides those.

## Drop (record the reason)

| Reason | Test |
|---|---|
| Profile exclusion | The topic falls in an `exclusions` area. |
| Ground-truth policy | The primary metric would need ground truth the policy forbids, such as new human ratings or LLM judgments. |
| Budget | A credible B0 cannot fit the largest budget tier. Effects visible only at scales beyond the budget count here. |
| Data unavailable | The required data or weights are provably not obtainable under the profile (non-public, or a license conflict). |
| Ledger duplicate | `ledger.py check` finds a past topic with verdict `killed`, `closed` or `dropped` that names a killer or a reason, and the candidate does not state what changed. |

## Flag and annotate (do not drop)

These are the classic ways an idea turns out empty. Flag them so the gate checks them first.

1. **Naive A + B:** a module or loss from one line of work attached to another, with no analysis of how the two interact or conflict. Keep it only if the interaction itself is the question.
2. **Unexplained extra term:** `L + λ·L_new` without a reason the terms are compatible, or a description of how they trade off.
3. **Trivial domain swap:** an existing method moved to new data with no defined failure point of the naive transfer. It needs lens 3 (breakdown-first).
4. **Standard tool already solves it:** recalibration, a known estimator, a data split, or a classical algorithm. If so, the tool becomes a baseline, not the contribution.
5. **Theory-forced finding:** the claimed result may be a mathematical necessity. The gate checks it.
6. **Crowded area:** recent activity nearby. This is information for the gate, not a verdict.

## Quick novelty signal

Run 1–2 targeted searches for the top survivors within the run's query budget (see `levels.md`), and attach what looks related, with links. Mark the others "not checked". Drop the idea only when a named paper clearly already contains its result, and say which paper. Everything else goes to ranking.
