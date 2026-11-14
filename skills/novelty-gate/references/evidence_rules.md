# Evidence rules

The gate is only as good as what it can show. These rules keep a report checkable by someone who was not in the session.

## Tags

Every factual claim about prior work carries one tag.

| Tag | Meaning |
|---|---|
| FT | Full text. The runner (you, not a subagent's summary) opened the full text and matched the exact sentence, equation or table. The quote is logged in `evidence.jsonl` and passes `scripts/quote_check.py`. |
| ABS | Abstract. Matched in the abstract or the official landing page only. |
| SEC | Secondary. Reported by a subagent, a search snippet, a blog, or another paper's citation. Not verified by the runner. |
| FAIL | Access failed: paywall, bot wall, 404 or timeout. Record what was tried. |

## Rules

1. **Decisive claims need FT.** A decisive claim is anything that kills, passes, or sets a score. If you cannot reach the full text, report the claim as provisional and say what is missing.
2. **Never bypass bot protection or paywalls.** Record FAIL and move on. A FAIL is never evidence of novelty.
3. **Resolve every citation.** Never cite a paper from memory without resolving it (`scripts/lit_fetch.py resolve`). A citation that cannot be resolved is marked `[UNVERIFIED]` and cannot be decisive.
4. **Quote exactly.** Label any paraphrase as a paraphrase.
5. **Attacks need ammunition.** Every criticism carries a citation (URL plus location) or a derivation the reader can check. Generic "a reviewer might say" critiques do not count.
6. **Dates matter.** Record the version and date of each prior. Work after the literature cutoff does not count for scoring.
7. **Label your own derivations.** Write "runner derivation (not a citation)". Keep them short enough to check by hand.
8. **Subagent notes are SEC** until you verify them yourself.

## evidence.jsonl format

One JSON object per line:

```json
{"id": "E3", "claim": "Prior X already reports this ablation on the same benchmark", "url": "https://arxiv.org/abs/XXXX.XXXXX", "source": "lit/XXXX.XXXXX.txt", "quote": "exact sentence copied from the text", "location": "Sec. 5, Table 4", "tag": "FT", "date": "2025-09-15"}
```

- `source` points to the extracted text file that `scripts/quote_check.py` searches.
- Keep quotes short, about 10–40 words, and distinctive. Long quotes break on line wraps and hyphenation.
- **ABS quotes are verifiable** when the abstract is saved to a file: run `lit_fetch.py … --save-abstracts <out>/lit` and point `source` to `abs_<id>.txt`.
- **Garbled PDF text.** Some PDFs extract ligatures as junk characters or contain control characters. Plain `grep` can then miss text that is there. Search with `quote_check.py` or Python instead, and choose quotes that avoid garbled words.
- **Tool failures are FAIL too.** Log them as `{"id": "F1", "tag": "FAIL", "claim": "arXiv API rate-limited (HTTP 429)", "source": "", "quote": ""}`.
