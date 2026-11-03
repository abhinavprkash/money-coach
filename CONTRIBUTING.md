# Contributing

- **New bank format?** Add a profile to `PROFILES` in `scripts/ingest_csv.py` and a one-row sample to `tests/test_ingest.py`. Never commit real statements; invent the row.
- **Better categories?** Edit `schemas/taxonomy.json`. More specific rules go first; keywords match on word boundaries.
- **New finding?** Add it to the matching agent's subcommand in `scripts/analyze.py` (or its own script). It must carry evidence, a dollar amount and an action, and its test uses the demo data.
- **No personal data or hidden constants.** `tests/test_no_hardcoding.py` fails on amount literals in code. Values belong in `config.json` via onboarding.
- Run `python3 -m pytest -q`, `node tests/lvi_engine.test.js` and `python3 scripts/prepublish_check.py` before opening a PR.
