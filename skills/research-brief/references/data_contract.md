# Data contract

These skills are generic. Everything personal (taste, limits, history, owned assets) lives in a **profile directory** that the user owns, outside the skills. Read it at the start of every run.

## Where to find the profile directory

Use the first match:
1. A path the user gives in the request (for example "profile: ~/research-profile").
2. The environment variable `RESEARCH_PROFILE_DIR`.
3. `./research-profile/` in the current working directory.
4. `~/research-profile/` in the home directory.

If none is found, ask once for the three essentials: interests and exclusions, compute and download budgets, and the novelty entry threshold. Otherwise proceed with the defaults below and state them in the report.

## Files

| File | Required | Content |
|---|---|---|
| `profile.md` | yes | Free text about taste, plus one fenced `json profile` block of constants |
| `ledger.jsonl` | recommended | One JSON line per past topic, with its verdict and killers |
| `lessons.md` | optional | Checklist of recurring lessons; each bullet is a check |
| `assets.md` | optional | Owned datasets, weights, caches and tools, with paths, sizes, licenses and provenance |
| `corpus/` | optional | Papers, code, notes and past reports; can also be paths given in the request |

## `profile.md` constants (the `json profile` block)

| Key | Type | Default | Used for |
|---|---|---|---|
| `output_language` | string | language of the request | report language |
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

Write `title` and `claim` in English, even when reports are in another language. The similarity search compares words and character trigrams, so mixed languages do not match.

Use `scripts/ledger.py` to validate, search and append. A ledger match with a named killer is a strong signal. It is not automatic: the candidate may state what changed.

## How each skill uses the files

- **topic-scout** reads all files. `corpus/` and `assets.md` drive generation. `exclusions`, `budgets` and the ledger drive pre-filtering.
- **novelty-gate** reads `profile.md`, `lessons.md` (applied as a checklist) and the ledger (duplicate check). It appends a ledger entry after the user confirms the verdict.
- **research-brief** reads `profile.md` (budgets, `handoff_template`, `content_check_command`) and `assets.md`.
