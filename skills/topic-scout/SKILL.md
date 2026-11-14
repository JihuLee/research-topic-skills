---
name: topic-scout
description: Finds research topics tailored to one researcher. A level sets how much it uses their own papers, code and past reviews (high) versus only their field and recent literature (low); a depth sets how far it vets (quick = candidates only, standard = top 1, full = top 3 through the novelty-gate skill). Drops only objectively infeasible or already-rejected ideas. Use it when someone asks to find, brainstorm or scout research topics, follow-ups to their work, or what to work on next, in any language. For interactive use with a researcher, not for autonomous research pipelines.
compatibility: Claude Code or Codex, used together with the novelty-gate skill. Needs web access. Python 3.8+ stdlib scripts; pymupdf optional for scanning PDFs.
metadata:
  version: "0.5.1"
---

# Topic scout

Generate broadly, drop early only on objective facts, and let the novelty gate do the killing with evidence. "No topic passes" is a valid result. No experiments or data or weight downloads without approval; the evidence rules in [references/evidence_rules.md](references/evidence_rules.md) apply.

**Who may use it:** a researcher, directly or through agents working for them in this session; not autonomous pipelines. First run `python3 <this-skill-dir>/scripts/guard.py` and stop if it exits non-zero. Call scripts by absolute path (`<this-skill-dir>/scripts/…`) and write only to the output directory.

**File search scope.** Search files only inside the profile directory, the working directory, and corpus folders the user names (request or profile `corpus_paths`). Never run a recursive search (`grep -r`, `rg`, `find`, `ls -R`, `du`) on the home directory (`$HOME`), the filesystem root, or any folder that contains them. If the working directory is the home directory itself, do not search it; ask for a project folder. Find the profile only at the fixed locations in [references/data_contract.md](references/data_contract.md), never by searching. `corpus_scan.py` refuses such folders too.

## 1. Settle the settings
Map the user's words to flags **by meaning**, in whatever language they write, then run the script so the same settings always produce the same plan:

```bash
python3 <this-skill-dir>/scripts/scout_settings.py [--level high|medium|low] [--depth quick|standard|full] \
  [--corpus PATH ...] [--field "TEXT"] [--cutoff YYYY-MM-DD] [--out DIR] [--extra-language CODE] \
  [--scope global|track] [--track NAME [--focus "one sentence"]]
```

| The user means | Flag |
|---|---|
| use my code, my paper, a follow-up | `--level high` |
| explore, just the field | `--level low` |
| quick, candidates only | `--depth quick` |
| thorough, check the top three | `--depth full` |
| also in Korean (or another language) | `--extra-language ko` (ISO 639-1) |
| stay on one topic, "fix this session on X" | `--track <short-name> --focus "<X in one sentence>"` |
| this time from all my topics | `--scope global` |

- Words inside a topic name are not settings: "depth estimation" or "fast MRI" set nothing. Omit a flag when the user did not ask; the script fills it from the profile, then the defaults (medium, standard).
- Paste the printed card (3–5 lines) to the user in their language and proceed without asking.
- **Track mode** (card says `scope: track`): follow the track rules below. If the card notes that no track is named or a new track needs a focus, ask the user once, then rerun.
- **No profile** (exit code 4): follow [references/onboarding.md](references/onboarding.md), run `scripts/profile_init.py`, then rerun.
- **Notes on the card**, for example "no corpus found": at level high or medium, ask once for a path or offer level low.

What level and depth change, with quotas, ranking weights and query budgets: [references/levels.md](references/levels.md). At level low, never open the corpus, not even to "check fit".

### Track rules
A track fixes one topic across runs; the user's scout-drop-scout loop stays inside it. Without a track, ideas may come from all topics.
- **Material:** only the track's focus and its own history: `python3 scripts/tracks.py show <profile> <track>` and `python3 scripts/ledger.py index <ledger> --track <track>`. The landscape scan stays inside the focus. Near-misses and assets from other topics are not seeds.
- **No repeats:** never propose a candidate listed by `tracks.py show` again. Number new ones from the next id it prints.
- **Duplicate check stays global:** `ledger.py check … --track <track>`. A hit marked "other track" is a one-line drop reason. Do not explore it or mention other topics otherwise, even if they appear in your own memory or notes.
- Pass the track to novelty-gate, and after the report run `python3 scripts/tracks.py record <profile> <track> <out>`.

## 2. Gather material
- **Own material** (high: full; medium: the strongest few leads; low: skip): run `python3 scripts/corpus_scan.py <paths> --out <out>/corpus_scan.md`, read the hits that matter per [references/corpus_audit.md](references/corpus_audit.md), and write `<out>/corpus_manifest.md` in the layout given there.
- **Landscape** (low: all; medium: half; high: a fifth): follow [references/landscape_scan.md](references/landscape_scan.md) and write `<out>/landscape.md`.

## 3. Generate, breadth first
Apply the lenses in [references/generation_lenses.md](references/generation_lenses.md) within the level's quota. Aim for 10–20 candidates, numbered C1, C2, … and saved to `<out>/candidates.jsonl` in the record format given there. With subagents, fix the lens list first, then fan out 4–6 lenses. Never drop an idea here for being "weak".

## 4. Pre-filter on facts
Follow [references/prefilter.md](references/prefilter.md): drop only for an exclusion, the ground-truth policy, an impossible budget, provably unavailable data, a ledger duplicate with a named killer, or a named paper that already contains the result. Flag everything else for the gate. `ledger.py check` is word-based, so pass the idea in other words too (`--also "<…>"`) and skim `ledger_index.md` (run `ledger.py index <ledger>` if it is missing), not the whole ledger. Run 1–2 quick searches (`scripts/lit_fetch.py`) per top survivor and attach what you find. Update each record's `status` (`dropped`, `annotated`, `gated`).

## 5. Rank and gate
Rank by what the first test teaches either way, own-asset edge (weighted by level), taste fit and cost. Then run **novelty-gate**: depth quick, none; standard, the top 1 in light mode; full, the top 3 in full mode.

## 6. Report
- **`<out>/details.md`** (audit record, English): the card with the actual source mix and query count; every candidate with id, one line, lens, source, status, rank, scores if gated and reason; dropped ideas with reasons; related work per candidate with evidence tags.
- **`<out>/report.md`** (human report, English, per [references/report_style.md](references/report_style.md)): a one- or two-sentence result; a short card for each of the top 3 and every checked candidate (verdict term, idea, why promising or weak, closest paper with link, first test with cost and stop rule, baselines to beat); other candidates one line each; one or two ready-to-say next steps such as "check C3" or "write the study plan for C1". A card for a **Not checked** idea says plainly that it is not checked yet.
- With an extra language on the card, also write `report.<code>.md` (prose translated, terms in English).
- Run `python3 scripts/report_lint.py scout <out>` and fix every ERROR. In the chat, give a short summary in the user's language and the file paths.
- Never append to the ledger yourself. The gate proposes entries for gated candidates; offer optional `dropped` entries.

## Follow-ups
For follow-ups that name a candidate, such as "check C3" or "write the study plan for C1" (in any language), read `candidates.jsonl` from the latest scout run in the working directory (or the one named). Run novelty-gate on that record (light mode unless asked for full), or research-brief on its gate output; gate it first if it has none.
