# research-topic-skills

[Korean](README.ko.md)

Agent Skills that help you **find research topics, check whether they are really new, and turn the good ones into a ready-to-run study plan.** They work in Claude Code, Codex and other agents that support [Agent Skills](https://agentskills.io/specification).

| Skill | You say | You get |
|---|---|---|
| `topic-scout` | "Find me a research topic" | Numbered candidate topics from your field (and, if you want, from your own papers and code), with the best one already vetted |
| `novelty-gate` | "Has anyone done this already?" | A verdict (Recommended, Near miss or Rejected) with the closest prior papers, linked, plus the cheapest first test that could prove the idea wrong |
| `research-brief` | "Write the study plan for C1" | An execution-ready study specification with baselines, data splits and thresholds frozen before any result |

They chain as **topic-scout → novelty-gate → research-brief**, and each one also works on its own.

## Install

```bash
npx skills add JihuLee/research-topic-skills -g
```

- To install a single skill, add `--skill novelty-gate`.
- Update with `npx skills update -g`.
- The helper scripts need Python 3.8 or later and no extra packages.

## Example usage

Just talk to your agent. You don't need to name the skill.

### 1. Find topics

```
Find me a research topic, field: medical imaging.
```

The scout first shows how it read your request, then works:

```
level: medium (profile) · depth: standard (default) · gate: top 1, light mode
corpus: - (none)
direction: medical imaging · cutoff: 2026-11-04 · out: ./scout-2026-11-04-medium
```

You get a short report with numbered candidates (C1, C2, …) and a verdict on the top one. Steer it with plain words:

| You want | Say |
|---|---|
| Ideas from your field only, exploring recent papers | "explore broadly", "just the field" |
| Ideas built on your own work | "based on my code in ./my-project", "follow-up to my paper" |
| A quick list, no vetting yet | "quick", "candidates only" |
| Thorough vetting of the top three | "thorough", "in depth" |

### 2. Check an idea

```
Has anyone already done this? Keep dropout on at test time and average several
predictions to get uncertainty estimates for a trained classifier.
```

Abridged example report:

```
## C1 · Test-time dropout for uncertainty — Rejected
novelty score 2/5 · feasibility score 5/5

**Why.** Gal & Ghahramani (2016) already state this exact method.
Confirmed in the paper's full text.
```

### 3. Continue from the results

```
Check C3 as well.
Write the study plan for C1.
```

## What you get

Each run writes a folder:
- `report.md`: the short report for you. It gives the decision, the reason and the next step, in plain English.
- `details.md`: the full audit record, with quotes, search coverage and settings. Read it to check a verdict.

Want the report in another language too? Say "also in Korean" (or `lang: ko`). You then also get `report.ko.md`. Only the prose is translated; technical terms stay in English. To get it every time, add `"extra_report_language": "ko"` to your profile.

## Your profile

On first use the skills ask four short questions:
1. your field;
2. topics to avoid;
3. a rough compute budget;
4. whether you also want reports in another language (English is the default).

They save the answers in `~/research-profile/`. Edit `profile.md` there whenever you like, to describe your taste or change the defaults. Keep that folder private.

## Good to know

- The skills design experiments but never download datasets or run experiments without asking you.
- They are meant for working with a person, not for autonomous research pipelines. To keep a pipeline from using them, set `RESEARCH_TOPIC_SKILLS_DISABLE=1` in its environment.
- For more literature searches per day, set a free OpenAlex key: `export OPENALEX_API_KEY=...`

Everything else is in the **[reference](docs/REFERENCE.md)**: how verdicts are made, the profile format, outputs, scripts and development.

## License

[MIT](LICENSE) © 2026 Jihu Lee
