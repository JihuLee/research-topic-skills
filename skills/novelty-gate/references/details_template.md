# details.md template (novelty gate audit record)

`details.md` is the audit record. Write it in English, whatever the report language. Keep the section order. Prose can be concise; the evidence cannot be. The human summary goes in `report.md` (see [report_template.md](report_template.md)).

```markdown
# <short title> — novelty gate details (<YYYY-MM-DD>)

- Literature cutoff: <date>. Input: <proposal path or summary>.
- Done / not done: literature and source review only. No experiments; no data or weight downloads (paper PDFs only).
- **Verdict: PASS | NONE** (one sentence why)
- Evidence tags: FT full text verified · ABS abstract only · SEC secondary/unverified · FAIL access failure

## 1. Candidates (novelty and feasibility scored separately)
| id | candidate (one line) | novelty | feasibility | closest prior | status / reason |
|---|---|---:|---:|---|---|

## 2. Why this verdict
The common reasons: landscape, theory-forced points, crowding by recent work. 3–6 bullets.

## 3. Candidate details
Full detail for PASS and NEAR-MISS. Three lines for KILLED and DROPPED.

For a KILLED candidate, give the killer evidence and, if one exists, a one-line revival condition: what would have to be different. Do not design a B0 for it.

### <id> — <title>
- Question and atomic claims; reduced computation
- (a) Closest priors: per prior, URL, tag, exact quote, location, what overlaps, what does not
- Classical-equivalence and theory-forced checks (runner derivations labeled)
- (b) Cheap baselines: native · common default · simplest key information · equal compute
- (c) Failing gate (if not PASS): which gate and why, in one sentence
- (d) B0: question, oracle, endpoint, minimum effect × margin, known-good, frozen thresholds (file + sha256), PROMOTE / KILLED / INCONCLUSIVE / BLOCKED conditions, cost vs budget
- Feasibility: data, weights and overlap, licenses per asset, downloads, ground-truth honesty

## 4. Search coverage
claims × families A–F (done / failed: reason / n/a: reason)

## 5. Lessons applied
One line per lesson from `lessons.py select`: id, how it was applied, result (caught, clear, n/a, false_alarm)

## 6. Access failures and unread items
Not evidence of novelty.

## 7. Decision for the user
What to approve, close or change. Smallest next step.
```

## gate_summary.json

Write the machine-readable summary to `<out>/gate_summary.json`, not into any markdown file. `scripts/report_lint.py gate <out>` validates it, and `scripts/ledger.py add --from-summary <out>` turns it into ledger entries.

```json
{
  "schema": "novelty-gate/v1",
  "date": "2026-01-31",
  "literature_cutoff": "2026-01-31",
  "entry_threshold": 4,
  "verdict": "none",
  "candidates": [
    {
      "id": "C1",
      "title": "Short title",
      "claim": "One-sentence claim.",
      "novelty": 3,
      "feasibility": 5,
      "status": "near-miss",
      "killer_type": "none",
      "closest_prior": [
        {"title": "Paper title", "url": "https://arxiv.org/abs/0000.00000", "tag": "FT", "evidence": "E1", "overlap": "what it already shows"}
      ],
      "baselines": {"native": "...", "common_default": "...", "simplest_key_info": "...", "equal_compute": "..."},
      "b0": {"cost": "≤ 8 GPU-h, 2 GB", "primary_endpoint": "...", "promote_if": "...", "kill_if": "...",
             "inconclusive_if": "...", "blocked_if": "...", "known_good": "...", "thresholds_file": "thresholds.json"},
      "failing_gate": "novelty 3 < 4: scale-up of known evaluation; promote only if B0 shows ..."
    }
  ],
  "coverage": [
    {"claim": "C1.a", "A": "done", "B": "done", "C": "done", "D": "done", "E": "done", "F": "done"}
  ],
  "lessons": [
    {"id": "L3", "result": "clear"},
    {"id": "L7", "result": "caught"}
  ]
}
```

## Field rules

- `status`:
  - `pass`: novelty ≥ threshold, feasibility ≥ 3, and at least one closest prior tagged FT.
  - `near-miss`: usually novelty = threshold − 1.
  - `killed`: needs `killer_type` of `paper` (with a named prior), or `classical-equivalence` / `theory-forced` (with a `derivation` field).
  - `dropped`: needs an objective `killer_type` (`budget`, `profile`, `ledger`, `data`).
- `baselines` and `b0` are required for `pass` and `near-miss`.
- `verdict` is `pass` if any candidate passes, else `none`.
- `track` (optional): the topic track this run belongs to; `ledger.py add --from-summary` copies it into the entries.
- `lessons` (optional): one item per lesson selected for this run, with `result` in `caught`, `clear`, `n/a`, `false_alarm`. `lessons.py tally` reads it.
- Every URL in `closest_prior` should also appear in `details.md`.
