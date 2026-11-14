# <Title> — research brief (<YYYY-MM-DD>)

<!-- section:meta -->
## 0. Meta
- Title / working title:
- Target venue or track; its known review criteria:
- Run scope: (a) up to selection, then a sealed decision outside the run / (b) up to ablations / (c) full paper
- Selection rule (decided before the run): eligibility filter → pre-registered primary endpoint → cost → id
- Roles (who builds, who audits, who opens the sealed set):
- Source gate report and verdict:

<!-- section:problem -->
## 1. Problem
- Research question (1–3 sentences):
- Target limitation of the current best method:
- Isolated hypotheses (numbered); for each, the result that would refute it:
- Is the condition inside the base model's training distribution (same noise, resolution, data)? If yes, expect little headroom.
- Does a standard tool already fix it (recalibration, data split, known estimator)? If yes, that tool is a baseline, not the contribution.

<!-- section:baselines -->
## 2. Baselines
- Paper; code URL, commit or tag, license:
- Weights: name, official location, terms of use (checked separately from the code license):
- Exact training data and split of the weights; overlap with every evaluation pool:
- Extra downloads triggered by default configs:
- Allowed modification scope (for example, inference-time only, frozen weights):
- Four cheap baselines, all pre-registered (pick B* on dev):
  1. Native / no intervention:
  2. Most common default:
  3. Simplest use of the key information:
  4. Equal-compute alternative:

<!-- section:reported -->
## 3. Reported results
- Same-protocol numbers from the original papers (table, figure, setting), or "none". The real comparison is against B* measured in the same pipeline.

<!-- section:benchmark -->
## 4. Benchmark
- Datasets, splits, sizes:
- Overlap with the base model's training and validation data (dev, selection, sealed):
- Licenses, separately for images, annotations and software:
- Download size; what is already available locally:
- Protocol and official evaluator (with its reading rules):

<!-- section:splits -->
## 5. Splits
| Use | Size | Notes |
|---|---:|---|
| Development | | diagnostics, G1 |
| Selection | | used by the selector |
| Sealed pilot | | outside the run; opened once by the auditor |
| Final confirmation | | untouched |
- Assignment rule (salted hash, rank ranges):
- Near-duplicate and same-source grouping (done before looking at performance):

<!-- section:metrics -->
## 6. Metrics
- Primary endpoint (exactly one), its direction and reporting unit:
- Secondary metrics (they decide nothing):
- Resampling unit, number of bootstrap samples, seeds, CI method:
- Rerun tolerance (same-cache re-evaluation; model re-run):

<!-- section:constraints -->
## 7. Constraints
- GPU-hours, download GB and wall clock (one budget tier; tiers do not add up):
- Prohibitions (for example retraining, paid APIs, tuning on sealed data, human or LLM judgments as the primary metric):
- Availability of human evaluation:

<!-- section:resources -->
## 8. Resources
- Hardware and how to check it is free before each job:
- Environment (isolated per project; no installs into shared environments):
- Assets already available (paths):

<!-- section:literature -->
## 9. Literature
Inline facts, because the executor may lack web access.
- Closest priors: title — URL — exact fact or quote — what differs:
- Cheap-baseline sources:
- Search expressions used:

<!-- section:cutoff -->
## 10. Literature cutoff
- Date:

<!-- section:novelty -->
## 11. Novelty
- Score (1–5), rubric used, and reasons, citing the gate report:

<!-- section:gates -->
## 12. Pre-registered gates
- Frozen thresholds: `thresholds.json`, sha256:
- B0 (before the run): oracle headroom ≥ margin × minimum effect, otherwise stop:
- G1 validity (failing it means BLOCKED): metric known-good, adapter equals native, rerun tolerance, applied config verified:
- G1 headroom (failing it means KILLED): oracle ≥ minimum effect × multiplier; precision and recall of any practical proxy; minimum sample size (below it, INCONCLUSIVE):
- G2 sealed decision (once, right after selection): minimum effect versus B*; paired CI lower bound > 0; cost-ratio cap; guardrail on catastrophic cases; must beat every pre-registered cheap baseline:
- Final confirmation: untouched set, one-sided lower bound:
- Known-good and null fixtures:
- Outcome classes: BLOCKED (access or installation) / INCONCLUSIVE (power) / KILLED (hypothesis failed):

<!-- section:ops -->
## 13. Operations
- Monitoring, schedule, people, copies for advisors, anything unusual:

## Open items (need a decision)
-
