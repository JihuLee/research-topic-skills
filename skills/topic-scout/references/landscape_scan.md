# Landscape scan (exploratory sources)

Used for the landscape share of candidates: all of them at level low, half at medium, a fifth at high. The goal is an **open-problems list** for the researcher's areas, built from recent literature rather than from their own files.

## Inputs
- `interests` from the profile, plus the `direction` from the request if one was given.
- Taste prose (what excites the researcher, what to avoid).
- The recency window: `--since` = cutoff minus `recency_window_months` (default 6; up to 12 for a quiet area), `--until` = the cutoff from the settings card.

## Steps
1. **Frame the areas.** Turn each interest (and the direction) into 2–3 concrete frames: problem plus setting plus constraint. For example, "medical imaging" becomes "segmentation under label noise", "reconstruction from few views" and "evaluation of foundation models on rare findings". Keep the frames that fit the taste prose.
2. **Collect signals per frame** with `scripts/lit_fetch.py openalex "<terms>" --since <date> --save-abstracts <out>/lit`, `scripts/lit_fetch.py arxiv` (2–3 exact terms) and the host's web search. Stay within the depth's query budget (`levels.md`). If OpenAlex answers HTTP 429, its daily budget is spent: continue with arXiv and web search, and suggest setting `OPENALEX_API_KEY`.
   - **Surveys and position papers:** their "open challenges" sections.
   - **Limitations and future-work statements** of the most cited recent papers. Pick the top 5–10 by citations within the window. OpenAlex gives citation counts; without it, pick by venue and recency and say so.
   - **Saturated or criticised benchmarks:** leaderboards near ceiling, and papers that question a protocol.
   - **Contradictions:** two recent results that disagree.
   - **Untested assumptions:** something every method assumes and nobody has measured.
   - **Calls and challenges:** workshop topics and competition tasks of the current year.
3. **Write `<out>/landscape.md`**, one entry per open problem:
   - the problem in one sentence;
   - the evidence (URL plus the quoted sentence);
   - why it is open;
   - which taste or interest it matches.

   Tag an entry ABS when its sentence matches the saved abstract (`scripts/quote_check.py`), otherwise SEC.
4. **Generate candidates from the entries** with the landscape lenses in [generation_lenses.md](generation_lenses.md). Set `source: "landscape"` and point `seed` to the entry.

## Cautions
- Landscape ideas sit where many people are looking. Expect more of them to die at the gate. That is why the ledger check and the gate's recency sweep stay on at every level.
- Do not open the researcher's corpus at level low, even to "check fit". Fit is judged from the profile prose only.
- Keep the scan proportional: stay within the depth's query budget in [levels.md](levels.md).
