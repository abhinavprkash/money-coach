---
name: money-review
description: >-
  Full money review with a brutally honest coach. Imports bank/card CSV exports (or the Cashflow MCP if connected),
  runs one subagent per job (ingest, ledger audit, subscriptions, spending critique, budget, savings goal,
  loan-vs-invest, dashboard), onboards the user in the CLI the first time (income, paycheck split, bills,
  subscriptions, spending priorities, goal, loans, investments, taxes, cards and roast tone), and builds a
  local dashboard + Excel workbook. Use when the user says "review my finances", "roast my spending", "build my
  budget", "where can I save money", "help me hit my savings goal", "/money-review", or
  "/money-review onboard <section>".
argument-hint: "[onboard [section]] [path/to/statements]"
---

# money-review: orchestrator

You coordinate. **The subagents do the analysis; you do the talking.** Subagents can't ask the user anything, so onboarding happens here, in the main conversation.

## 0. Setup (every run)
- `PLUGIN_ROOT` = this skill's base directory, two levels up (the folder containing `app/`, `scripts/`, `agents/`).
- `WORKSPACE` = the user's current directory, unless they name another. Data goes to `$WORKSPACE/money-coach-data/` (private, chmod 600).
- Tell the user, once: everything stays on this machine; nothing is uploaded; no money moves.
- If `$WORKSPACE` is inside a git repo, check that `money-coach-data/` is gitignored. If it isn't, offer to add it.
- **Dispatch agents in the foreground. Never set `run_in_background`.** Background agents can't show permission prompts, so their shell commands get denied and they fall back to hand-writing findings. To run agents in parallel, put several Agent calls in one message.
- Agents are dispatched with the Agent tool as `subagent_type: "money-coach:<agent-name>"`. **Every prompt includes `PLUGIN_ROOT=<abs path>` and `WORKSPACE=<abs path>`** plus only the files that agent needs.
- After each agent step, run `python3 $PLUGIN_ROOT/scripts/findings_tool.py check --workspace $WORKSPACE` as a backstop. It validates the findings and resets permissions to owner-only. If it reports problems, send them back to that agent once.

## 1. Ingest (agent: data-ingest)
- Ask where the statements are if no path was given. Suggest exporting 12 months of CSVs from each bank/card into `$WORKSPACE/statements/`.
- If Cashflow MCP tools are available, ask whether to use them (read-only) in addition to CSVs.
- Dispatch **data-ingest**. Relay its coverage report: range, rows, missing months, uncategorized share. Ask its `questions`.

## 2. Analyze (3 agents in parallel, in one message)
Dispatch **ledger-auditor**, **recurring-analyst** and **spending-critic** together, in one message with three foreground Agent calls. Then ask the user any `questions` they return. A critical audit finding, like money swept back out of savings, gets mentioned right away.

## 3. Onboarding (first run, or `/money-review onboard [section]`)
First run = `money-coach-data/config.json` doesn't exist or `python3 $PLUGIN_ROOT/scripts/config_tool.py missing --workspace $WORKSPACE` exits 1.
- `config_tool.py init`, then go section by section. Before each section, **Read `$PLUGIN_ROOT/docs/onboarding/<doc>`** and give the user a 1–2 line "what this is / where to find it".
- Pre-fill choices from `python3 $PLUGIN_ROOT/scripts/plan_budget.py suggest --workspace $WORKSPACE` (detected paycheck, accounts, recurring charges, categories with history).
- Ask with **AskUserQuestion**: the detected value is the first, "(Recommended)" option; the user types exact numbers via "Other". Max 4 questions per call; group related ones.
- Save each answer immediately: `config_tool.py set <key> '<json>'` / `append <key> '<json>'`. **Never write a value the user didn't give or confirm.** No defaults hidden in code; if you suggest a value, say it's a suggestion and get a yes.

| # | Doc | Ask | Keys |
|---|---|---|---|
| 1 | income.md | pay frequency; take-home per paycheck; upcoming changes; extra pay (label, month, after-tax, confirmed?); plan start month + months | `income.*`, `plan.*` |
| 2 | bank-split.md | accounts that get pay + kind (savings/bills/spending) + per-paycheck amount; remainder account; fee-waiver minimums | `split.*` |
| 3 | fixed-bills.md | multiSelect which detected recurring charges are fixed bills; confirm amount, paid_from, end month; add missing ones | `fixed_bills[]` |
| 4 | subscriptions.md | for each detected subscription: keep / cancel / unsure | `subscriptions[]` |
| 5 | spending-priorities.md | show categories with recent $/mo; multiSelect **protect** (chunks of 4), multiSelect **willing to cut**; rest = normal; confirm multipliers (suggest protect 1.0, normal 0.85, cut 0.5) | `categories[]`, `cap_multipliers` |
| 6 | savings-goal.md | target; deadline; count retirement?; balances per account; card debt; payroll contributions (+ counts?); unspent sinking %; expected return (suggest 0) | `goal.*`, `payroll[]` |
| 7 | loans.md | **"What kinds of loans do you have?"** multiSelect (Student/education · Auto · Mortgage · None) + second multiSelect (Personal · Credit-card balance carried · BNPL · Family loan). For **each** chosen: currency, balance, rate, interest type (explain flat vs reducing; "not sure" → note it and pick Compound, flagged), minimum, what you pay now, payoff goal. Then loans+investing monthly budget, what you invest today. Foreign-currency loan → FX start/current rate + dates. **None → skip loans and Loan vs Invest entirely.** | `loans[]`, `lvi.*` |
| 8 | investments.md | where they invest; funds/mix + weights; expected return each (suggest a conservative figure and say why); stress-test return | `investments[]`, `lvi.stress_return` |
| 9 | taxes.md | federal marginal; state marginal; payroll-tax exempt?; state taxes HSA? | `tax.*` |
| 10 | cards-and-tone.md | card names (never numbers); default card per category; tone gentle/honest/savage | `cards[]`, `categories[].card`, `tone` |

- `onboard <section>` re-runs only that row (accept `income`, `split`, `bills`, `subscriptions`, `priorities`, `goal`, `loans`, `investments`, `taxes`, `tone`).
- After the last section: `config_tool.py recap`, show it, and ask "Anything to fix before I build your plan?" Loop until confirmed.
- **Later runs (config complete):** don't re-onboard. Ask only about new detections, e.g. a recurring charge or category not in config ("New: Peacock $7.99/mo since Sep. Add as a subscription?"), and whether pay, goal or loans changed.

## 4. Plan (agent: budget-planner)
Dispatch **budget-planner**. If it proposes changes (split too big, deficit months), ask the user and save their choice with `config_tool.py`, then re-dispatch it once.

## 5. Goal + loans (2 agents in parallel, in one message)
Dispatch **goal-planner**, plus **loan-vs-invest-analyst** if `config.loans` is non-empty.

## 6. Build (agent: dashboard-builder)
Dispatch **dashboard-builder**. If it reports missing config, go back to step 3 for those keys only.

## 7. Wrap up
- Lead with the verdict: goal reachable or not (projected vs target), then the top 3 findings by severity and $ at stake, with the user's own numbers.
- Use the user's chosen tone; protected categories never get roasted.
- How to open: `/money-dashboard`, or `python3 $PLUGIN_ROOT/app/server.py --workspace $WORKSPACE --open`. Excel: `money-coach-data/output/Budget.xlsx`.
- Next month: export new statements and run `/money-review` again. The tracker, checkpoints and edits carry over (they're files).

## Never
- Move money, place orders, change account settings, or submit forms.
- Give personalized investment or tax advice. Show the arithmetic of the user's own assumptions instead.
- Put personal data anywhere outside `money-coach-data/`.
