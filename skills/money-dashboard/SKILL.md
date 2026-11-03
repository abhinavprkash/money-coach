---
name: money-dashboard
description: >-
  Open the money-coach budget dashboard: a local, private page with monthly budgets, an expense tracker,
  paycheck split planner, savings-goal checkpoints, findings and Loan vs Invest. Every edit saves to
  money-coach-data/ (CSV + JSON) and the "Update Excel" button rebuilds the workbook. Use when the user says
  "open my budget", "show the dashboard", "log an expense", "update the Excel", or "/money-dashboard".
argument-hint: "[stop | rebuild]"
---

# money-dashboard

- `PLUGIN_ROOT` = this skill's base directory, two levels up. `WORKSPACE` = the user's current directory, unless they name another.
- If `$WORKSPACE/money-coach-data/config.json` is missing, say so and offer `/money-review` (onboarding). Don't build with guesses.

## Open
1. If `money-coach-data/site/index.html` is missing, or the user said `rebuild`:
   `python3 $PLUGIN_ROOT/app/build.py --workspace $WORKSPACE`. If it prints missing config keys, offer `/money-review onboard <section>` for them.
2. Check whether something is already listening: `lsof -iTCP:8765 -sTCP:LISTEN`.
   - If it's already running, just give the URL.
   - If not, start the server **in the background**:
     `python3 $PLUGIN_ROOT/app/server.py --workspace $WORKSPACE --open`
     If port 8765 is taken by something else, add `--port 8766`.
3. Tell the user:
   - the URL (`http://localhost:8765`)
   - that it only listens on this machine
   - that edits save to `money-coach-data/expenses.csv` and `settings.json`, with a daily backup in `money-coach-data/backups/`
   - that "Update Excel" refreshes `money-coach-data/output/Budget.xlsx`

## Stop
Stop the background server process you started. The data is already saved to files.

## Logging expenses from chat
If the user says something like "log $42 groceries on Chase today", tell them to add it in the dashboard's tracker so there's one source of truth. Or, if the server is running, PUT the updated state through the page. Never edit `expenses.csv` while the server is running.
