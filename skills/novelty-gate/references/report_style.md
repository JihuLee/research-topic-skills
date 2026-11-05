# Human report style

Every run writes two kinds of output:
- **`report.md`:** the human report. Short and plain. It is in English by default.
- **`details.md` plus machine-readable files:** the audit record, with evidence, coverage, settings and JSON. It is always in English. Someone who wants to check a verdict reads this.

Write the human report in the style of ASD-STE100 (Simplified Technical English). The reader is a busy researcher who wants the decision, the reason and the next action.

## Rules for report.md
1. **One idea per sentence.** Keep sentences to at most 20 words for instructions and 25 words for descriptions.
2. **Active voice, present tense.** Write "This paper already does X", not "X has already been done by this paper".
3. **Use the same word for the same thing.** Use the term list below and do not vary it.
4. **No internal codes or workflow words.** Leave these in `details.md`:
   - evidence ids (E1, F2);
   - evidence tags (FT, ABS, SEC, FAIL);
   - ledger, lens, landscape, annotated, killer_type, coverage matrix;
   - query counts, setting sources, file-system paths other than the output files.
5. **Say how sure you are in words.** For example "confirmed in the paper's full text" or "seen in the abstract only".
6. **Numbers carry units.** Write "about 4 GPU-hours", "6 points of macro-AP".
7. **Short lists.** Use at most 5 items per list and at most 3 closest papers per candidate.
8. **Short report.** Aim for at most about 60 lines, or one screen per candidate.
9. **End with the next action**, as a sentence the user can say, for example "Say: check C3".

## Term list (use exactly these words, in every language)

| Term | Meaning |
|---|---|
| **Recommended** | passed the novelty check (PASS) |
| **Near miss** | one point below the bar; a first test could change the verdict (NEAR-MISS) |
| **Rejected** | a named paper, a known method, or a mathematical fact already covers it (KILLED) |
| **Removed** | taken out before the novelty check for a practical reason: excluded field, budget, data, or checked before (DROPPED) |
| **Not checked** | a candidate that was not sent to the novelty check yet |
| **novelty score**, **feasibility score** | 1–5 scores from the rubric |
| **closest paper** | the prior work nearest to the idea |
| **first test** | the cheapest experiment that could change the verdict (B0 in `details.md`) |
| **baseline** | a simple method the idea must beat |
| **cutoff** | the literature cutoff date |

## Extra language

The default is English only. When an extra report language is set (profile `extra_report_language`, or a request such as "also in Korean"), also write `report.<code>.md` with an ISO 639-1 code, for example `report.ko.md`. Follow these rules:
- **Same content.** It has the same structure and content as `report.md`; only the prose is translated.
- **Keep in English:**
  - technical terms;
  - the term list above (for example "Verdict: Near miss");
  - method, model, dataset and metric names;
  - paper titles;
  - commands, file names, numbers and units.
- **Keep it short.** The translation follows the same brevity: short sentences, one idea each.
- **Never translate the rest.** `details.md` and the JSON files stay in English.
