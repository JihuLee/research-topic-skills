# Corpus audit

`scripts/corpus_scan.py` points at lines. This file explains what to extract from them. Extract specifics: file, line, equation, constant. A good manifest entry names exactly where the seed is, so the gate can check it later.

## Papers and drafts (.tex, .pdf, .md)
- **Assumptions and approximations:** "we assume", "for simplicity", first-order or Taylor steps, isotropy or independence, known noise or operator. Note which result depends on each one.
- **Limitations and future work:** authors often list the next paper themselves.
- **Weakly supported claims:** a conclusion resting on one dataset, one seed, or a metric with known blind spots.
- **Proof conditions:** strong conditions in a theorem that the experiments may violate.

## Code (.py, notebooks)
- **Tricks absent from the paper:** clamps, `detach`, hard-coded epsilons, rescaling factors, warm-up, EMA, special-case branches. Each is a candidate for the heuristic → principle lens.
- **Paper ↔ code mismatches:** signs, normalizations, where gradients are stopped, which expectation is approximated by a single sample or a mean.
- **Bottlenecks:** heavy linear algebra or search inside loops (the scan lists them). Treat these as lenses only when the profile allows compute topics.
- **Disabled or TODO branches:** abandoned directions are sometimes promising ones.

## Notes, lab logs and past gate reports
- **Crowding map:** which areas killed earlier ideas, and by which papers. Avoid regenerating those ideas unless something changed.
- **Near-misses and their flip evidence:** the cheapest revivals.
- **Lessons:** add them to the checklist the gate applies.
- **Assets built along the way:** datasets, caches, trained weights, tools.

## Abstract core operator
Write each core method as an operator in at most three sentences:

> T maps <input space> to <output space>, guarantees <property>, and assumes <conditions>.

This is what breakdown-first transfer starts from, and what the gate's classical-equivalence check reduces against.

## Manifest layout (`corpus_manifest.md`)
1. Theoretical compromises (with locations)
2. Code–theory discrepancies (file:line)
3. Bottlenecks
4. Abstract core operator(s)
5. Owned assets useful for B0
6. Past near-misses and the evidence that would flip them
