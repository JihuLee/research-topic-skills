# report.md template (novelty gate, human report)

Follow [report_style.md](report_style.md): short sentences, the fixed term list, no internal codes. Write it in English. If an extra report language is set, also write `report.<code>.md` with the same structure, translating the prose only.

Put one block per candidate. For a single idea that is the whole report. Keep the order.

```markdown
# Novelty check: <short title>

<YYYY-MM-DD> · cutoff <YYYY-MM-DD> · <light | full> check · details: details.md

## Result
<One sentence. For example: "No idea is recommended. One idea is a near miss.">

## <id> · <short title> — <Recommended | Near miss | Rejected>
novelty score <n>/5 · feasibility score <n>/5

**Idea.** <One or two sentences in plain words.>

**Why.** <Two or three sentences. Name the closest paper and say what it already does and what it does not do.>

**Closest papers**
1. <Title> (<first author> et al., <year>). <URL>
   <It already does X. It does not do Y.> <How sure: confirmed in the full text | seen in the abstract only>
2. ...

**First test** (only for Recommended and Near miss)
<What to run, in one or two sentences.> Cost: <about N GPU-hours, N GB>.
Continue if <result>. Stop if <result>.

**Baselines to beat:** <three or four short names>

## Next step
- Say: "<the follow-up the user can type>"
```

Example of one candidate block:

```markdown
## C1 · Label smoothing vs temperature scaling under distribution shift — Near miss
novelty score 3/5 · feasibility score 5/5

**Idea.** Train with label smoothing and compare its calibration with temperature scaling on shifted test data.

**Why.** The closest paper shows that label smoothing improves calibration on in-distribution data. It does not compare the two methods under shift. We did not yet search all robustness benchmarks.

**Closest papers**
1. When Does Label Smoothing Help? (Müller et al., 2019). https://arxiv.org/abs/1906.02629
   It already shows better calibration in distribution. It does not test shifted data. Seen in the abstract only.

**First test**
Train a small CNN on CIFAR-10 with and without label smoothing. Measure calibration error on CIFAR-10-C. Cost: about 2 GPU-hours, 3 GB download.
Continue if label smoothing beats temperature scaling by at least 1 point of calibration error. Stop if not.

**Baselines to beat:** temperature scaling, plain training, focal loss
```
