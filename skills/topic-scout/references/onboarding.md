# Onboarding: first use without a profile

If no profile directory is found (see [data_contract.md](data_contract.md)), do not fail and do not ask a long questionnaire. Ask once, in one message, in the user's language:

1. Your research areas, most preferred first (one line).
2. Areas you never want proposed (one line, or "none").
3. A rough compute and download budget for a first experiment, for example "about 10 GPU-hours and 10 GB", plus your hardware.
4. The language for reports.

Then create the profile and continue with the original request:

```bash
python3 <this-skill-dir>/scripts/profile_init.py --dir ~/research-profile \
  --interests "area one; area two" --exclusions "area x" \
  --gpu-hours 10 --download-gb 10 --hardware "1 GPU, 24 GB" --language en
```

- It writes `profile.md` (with a `json profile` block), an empty `ledger.jsonl`, a starter `lessons.md` and an `assets.md` header.
- It never overwrites an existing `profile.md` unless `--force` is passed.
- Tell the user the profile's location in one line, and say that the prose sections (taste, strengths, things to avoid) improve the results when filled in later.
- If the user declines to answer, proceed with the defaults in `data_contract.md` and say so in the report.
