# Scoring rubric

Score novelty and feasibility separately. A single blended score hides the usual failure: an idea that is novel but cannot be tested, or testable but already done.

## Novelty (1–5)

| Score | Meaning |
|---|---|
| 5 | No close prior. Neither the question nor its expected answer appears in prior work. |
| 4 | A closest prior exists, but the difference can change a conclusion or a ranking that the field relies on, and a cheap experiment within budget (B0) can test it. |
| 3 | Incremental: new scale, domain, combination or instantiation of known pieces. Also a would-be 4 whose conclusion-changing effect has not been shown yet. |
| 2 | The same computation or claim already exists under another name or in a close paper. This includes classical equivalents and results forced by theory. |
| 1 | Duplicate. |

How to apply it:
- Judge the idea, not each component. Known parts arranged to reveal something unknown can be novel. If the method is not novel but the finding would be, say so explicitly.
- Check the novelty of the method and of the experimental setting or evaluation separately.
- A score of 2 or below must name the paper (URL plus where in it) or give the derivation (classical equivalence or theory-forced result). No name, no kill.
- "Not found" never raises a score. "This area is crowded" never lowers one by itself.
- Work inside the recency window is reported as a race. If it already contains the result, the result is not novel.
- Ignore work dated after the literature cutoff when scoring. Mention it separately as post-cutoff.
- **2 versus 3.**
  - Score 2 when the core computation reduces to a known one **and** the claimed finding is already shown or forced by theory.
  - Score 3 when the parts are known but their specific combination makes a new, checkable claim that no paper shows.
  - A 3 becomes 4 only when that claim would change a conclusion the field relies on, and a cheap B0 can show it.

## Feasibility (1–5)

| Score | Meaning |
|---|---|
| 5 | Public data and weights. Fits the cheapest budget tier in the profile. Ground truth is verifiable and licenses are compatible. |
| 4 | Fits a higher budget tier (for example, small training), or has a minor license or setup caveat. |
| 3 | Fits the budget but carries one major risk: simulator engineering, unmeasured runtime, license uncertainty, or a download near the limit. |
| 2 | Likely exceeds the budget, or the ground truth is weak or unverifiable under the profile's policy. |
| 1 | Not doable under the profile. |

Check each of these separately and report what you found:
- Overlap between the training data of any pretrained weights and the evaluation pools.
- Near-duplicate and same-source items, which must be grouped before splitting.
- License of each asset separately: images, annotations, code, weights.
- Extra downloads triggered by default configs, such as pretrained backbones.
- Whether synthetic or simulated ground truth is being presented as real-sensor truth. It must not be.

A widely used public dataset that lacks a license file is a caveat to report. It lowers feasibility only when the plan needs to redistribute the data or derived assets.

## Verdict classes

| Class | Condition |
|---|---|
| PASS | Novelty ≥ the profile's entry threshold (default 4). Defended against at least one closest prior verified in full text (tag FT). Feasibility ≥ 3. A B0 is designed. |
| NEAR-MISS | Novelty = threshold − 1, and a cheap B0 exists whose positive result would raise it to the threshold. State that evidence exactly. |
| KILLED | Novelty ≤ threshold − 2; or a named paper already contains the result; or a classical or theory-forced reduction exists. |
| DROPPED | Scout only, decided before the gate: excluded by the profile, budget-infeasible, data provably unavailable, or a ledger duplicate with a named killer. |

If a runner derivation predicts that a NEAR-MISS candidate's B0 will fail:
- If the derivation needs extra assumptions, keep the candidate as NEAR-MISS and list the derivation as its main risk.
- If the derivation holds without extra assumptions, mark the candidate KILLED (theory-forced).

The overall verdict of a run is **PASS** if any candidate passes. Otherwise it is **NONE**, and the near-misses are listed. Never promote a candidate to fill a quota.
