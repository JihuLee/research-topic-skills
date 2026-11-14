# Data contract

These skills are generic. Everything personal (taste, limits, history, owned assets) lives in a **profile directory** that the user owns, outside the skills. Read it at the start of every run.

## Where to find the profile directory

Use the first match:
1. A path the user gives in the request (for example "profile: ~/research-profile").
2. The environment variable `RESEARCH_PROFILE_DIR`.
3. `./research-profile/` in the current working directory.
4. `~/research-profile/` in the home directory.

If none is found, follow [onboarding.md](onboarding.md): ask four short questions once, create the profile with `scripts/profile_init.py`, and continue. If the user declines, proceed with the defaults below and state them in the report.

## Files

| File | Required | Content |
|---|---|---|
| `profile.md` | yes | Free text about taste, plus one fenced `json profile` block of constants |
| `ledger.jsonl` | recommended | One JSON line per past topic, with its verdict and killers |
| `ledger_index.md` | generated | One line per topic family, written by `ledger.py`; read this instead of the whole ledger |
| `lessons.md` | optional | Your own checks, one bullet each, with an id, tier, tags and counters (format below) |
| `lessons_archive.md` | generated | Lessons moved out by `lessons.py apply`; never applied, never deleted |
| `lessons_state.json` | generated | Gate runs already tallied and the count since the last review |
| `tracks/<name>.json` | optional | A topic track: one fixed topic (focus sentence, tags) and the candidates its scout runs produced |
| `assets.md` | optional | Owned datasets, weights, caches and tools, with paths, sizes, licenses and provenance |
| `corpus/` | optional | Papers, code, notes and past reports; can also be paths given in the request |

## `profile.md` constants (the `json profile` block)

| Key | Type | Default | Used for |
|---|---|---|---|
| `extra_report_language` | ISO 639-1 code or `null` | `null` | also write the human report in this language (`report.<code>.md`); reports are English by default, and `details.md` is always English. A request such as "also in Korean" or `lang: ko` sets it for one run. The older key `output_language`, if not `en`, is read as this |
| `interests` | list of strings, ranked | — | generation lenses, ranking |
| `preferred_contributions` | list | `["method","benchmark","analysis"]` | ranking |
| `target_venues` | list | — | framing and venue criteria |
| `exclusions` | list | `[]` | drop rule (scout) and flag (gate) |
| `ground_truth_policy` | string | "public, verifiable ground truth; no human or LLM judgment as the primary metric" | feasibility |
| `budgets` | object | — | feasibility, B0 cost check |
| `novelty_entry_threshold` | int | 4 | PASS / NEAR-MISS boundary |
| `recency_window_months` | int | 6 | recency sweep |
| `approval_required_for` | list | `["downloads","experiments","gpu"]` | actions never taken without the user's approval |
| `report_dir_pattern` | string | `./gate-{slug}-{date}/` | output location |
| `scout_level` | `high` / `medium` / `low` | `medium` | topic-scout: how much it draws on your own material |
| `scout_depth` | `quick` / `standard` / `full` | `standard` | topic-scout: candidates only / gate the top 1 (light) / gate the top 3 |
| `scout_scope` | `global` / `track` | `global` | topic-scout: ideas from all topics, or only from one named track (the duplicate check is global either way) |
| `corpus_paths` | list of paths | `[]` | topic-scout corpus when the request names none |
| `lessons_core_cap` | int | 20 | at most this many pinned + core lessons |
| `lessons_review_every_gates` | int | 20 | offer a tidy-up after this many gate runs |
| `lessons_max_active` | int | 40 | offer a tidy-up when active lessons exceed this |
| `handoff_template` | path | none | research-brief template |
| `content_check_command` | string | none | command research-brief runs on a brief before handoff |

Recommended shape for `budgets`:

```json
{"tiers": {"small": {"gpu_hours": 10, "download_gb": 10},
           "large": {"gpu_hours": 100, "download_gb": 100}},
 "wall_clock_hours": 48, "hardware": "2 GPUs, 24 GB each"}
```

## `ledger.jsonl`

One object per line. Required keys: `id`, `date` (YYYY-MM-DD), `title`, `claim` (one sentence), `verdict`.

`verdict` is one of `pass`, `near-miss`, `killed`, `dropped`, `closed`, `none`, `pending`.

Optional keys:
- `stage`: one of `idea`, `gate`, `b0`, `pilot`, `sealed`, `brief`, `done`.
- `novelty`, `feasibility`: ints.
- `killers`: list of `{title, url, why}`.
- `near_miss_b0`: string.
- `tags`: list.
- `report`: path or URL.
- `notes`: string.
- `parent`: the id of an earlier entry for the same topic (a revision or a re-check). The index shows each family once, with its latest entry.
- `history`: earlier values, appended by `ledger.py update`. Never edit or delete entries by hand.
- `track`: the topic track the entry belongs to (lowercase name). In a track, topic-scout uses only that track's entries as material; the duplicate check still covers every entry.

Write `title` and `claim` in English, even when reports are in another language. The similarity search compares words and character trigrams, so mixed languages do not match.

Use `scripts/ledger.py` to validate, search and append. A ledger match with a named killer is a strong signal. It is not automatic: the candidate may state what changed.

## `lessons.md`

One top-level bullet per lesson; indented lines below it belong to it:

```
- [L12|scoped|diffusion,metrics|h3/x0/n7] Check: <one checkable sentence>
  - optional details
```

- **Tier:** `pinned` (always applied, never proposed for archiving), `core` (always applied), or `scoped` (applied only when a candidate shares a tag).
- **h/x/n:** times the check caught something, raised a false alarm, or was applied. `lessons.py tally` updates them from each gate run.
- **Unmarked bullets** (no bracket header) are applied as core until a tidy-up gives them an id.
- Change lessons only through `lessons.py apply` (add, edit, adopt, merge, archive). Never rewrite the whole file.

## How each skill uses the files

- **topic-scout** reads by level (see its `levels.md`):
  - `profile.md` and the ledger at every level; the ledger is for the duplicate check (`ledger_index.md` plus `ledger.py check`).
  - In a track (`scout_scope: track` or a named track), only the track's focus, its `tracks/<name>.json` and its ledger entries serve as material; the duplicate check stays global.
  - The corpus and `assets.md` at high and medium only.
  - It does not need `lessons.md`; the gate applies it.
- **novelty-gate** reads `profile.md`, the lessons selected by `lessons.py select`, and the ledger through `ledger_index.md` and `ledger.py check`. After the user confirms, it appends ledger entries, tallies lesson results, and proposes lesson changes.
- **research-brief** reads `profile.md` (budgets, `handoff_template`, `content_check_command`), `assets.md`, and the lessons tagged `execution` or `b0` (plus the topic's tags), which go into the brief's gates and operations sections.
