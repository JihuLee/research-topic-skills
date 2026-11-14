# Subagent brief (parallel literature search)

Subagents do not see this skill. Give each one a self-contained brief: copy the template below and fill the angle brackets. Keep each brief to one claim or one query family, so that results do not overlap and gaps stay visible.

```text
Research: <claim id and one-sentence claim>, query families <A-F letters>.

Objective: act as an adversarial reviewer. Find the closest prior work that would make this
claim non-novel, and the strongest cheap baseline. Finding what already exists is the goal.

Context:
- Reduced computation: <math in one or two lines>
- Input contract: <what is available at test time / training>
- Literature cutoff: <YYYY-MM-DD>; recency window: since <YYYY-MM-DD>
- Known priors already found (do not re-report): <list>

Rules:
- Primary sources only (arXiv, proceedings, OpenReview, official code, dataset cards).
- Give the exact URL for every claim and tag it [full text read] / [abstract only] / [secondary].
- For the 3 most decisive papers, quote the exact sentence, equation or table, with its location.
- Use at least 3 query formulations per family. Chase forward citations of the closest prior inside the recency window.
- Never bypass bot protection or paywalls. Record access failures; they are not evidence of novelty.
- Do not download datasets or model weights and do not run experiments. Paper PDFs may be saved to <out>/lit/.
- Only write inside <out>/notes/ and <out>/lit/. Do not read or search unrelated directories.

Output: write <out>/notes/<name>.md with these sections:
  Takeaway (2-3 lines) | Findings (bullets: claim, URL, tag, quote) | Closest prior |
  Strongest cheap baseline | Queries used | Gaps and access failures |
  Suggested novelty 1-5 with one-line reason
Then return a 5-line summary.
```

When the summaries come back, treat every finding as SEC. Verify the decisive ones yourself (workflow step 5) before they enter the verdict.
