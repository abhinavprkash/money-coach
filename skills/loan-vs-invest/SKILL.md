---
name: loan-vs-invest
description: >-
  Should I pay off my loans faster or invest? Asks what loans the user has (student, auto, mortgage, personal,
  credit card, BNPL, family, foreign-currency), their balances, rates and interest type, then compares
  minimum-pay, crush-loans, current-plan and balanced scenarios with a spreadsheet-exact engine, a stress
  test and a red pen of risky assumptions. Use when the user asks "pay off loan or invest", "should I prepay
  my student loan", "loan vs invest", or "/loan-vs-invest".
---

# loan-vs-invest

- `PLUGIN_ROOT` = this skill's base directory, two levels up. `WORKSPACE` = the user's current directory.

1. If `money-coach-data/config.json` has `loans` and `investments`, show them and ask "Still accurate?". Otherwise, onboard just these two sections:
   - `python3 $PLUGIN_ROOT/scripts/config_tool.py init --workspace $WORKSPACE`. This is safe if the file already exists.
   - **Read `$PLUGIN_ROOT/docs/onboarding/loans.md` and `investments.md`.** Ask exactly as in the money-review skill, table rows 7 and 8: loan types (multiSelect), then per loan currency, balance, rate, interest type (explain flat vs reducing), minimum and current payment; then the monthly loans+investing budget, what they invest today, the funds with expected returns, and the stress-test return.
   - Save every answer with `config_tool.py set|append`. Never fill in a value the user didn't give or confirm.
   - No loans → say there's nothing to compare, and stop.
2. Dispatch the **loan-vs-invest-analyst** agent (`subagent_type: "money-coach:loan-vs-invest-analyst"`) with `PLUGIN_ROOT` and `WORKSPACE`.
3. Report:
   - the winner and the gap versus what they pay now
   - whether the winner survives the stress test
   - the red pen, in plain words
   Close with: arithmetic on their assumptions, not investment advice.
4. If a full config exists, offer `/money-dashboard` for the interactive tab, where they can edit rates and types and watch the result change.
