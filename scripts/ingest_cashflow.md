# Ingesting from the Cashflow MCP (optional, read-only)

Use this only if the user's Claude has a Cashflow MCP connected and they agreed to use it. Every call is a **read** query. Never change categories, recurring flags or anything else in Cashflow.

1. List the connected accounts (institution, account name, type, current balance). Show the user which accounts are connected and which kinds look missing (for example, a card that gets payments but has no purchases).
2. Pull posted transactions for the review window, usually the last 12 complete months plus the current month, page by page. Skip pending rows.
3. Map each transaction to the money-coach row and save the whole list as JSON in `money-coach-data/cashflow_rows.json`:

| money-coach | Cashflow field (typical) |
|---|---|
| date | `dt` / posted date |
| account | account name (mask long numbers) |
| institution | institution / bank |
| description | `desc`, or `raw` if desc is empty |
| merchant | `party` / counterparty |
| amount | `amt`, negative = money out |
| category, group | `cat`, `grp` (keep Cashflow's labels) |
| kind | from group: Income→income, Transfers→transfer, Investment→investment, Financing→financing, else expense |

4. `python3 $PLUGIN_ROOT/scripts/ingest_json.py money-coach-data/cashflow_rows.json --workspace $WORKSPACE --source cashflow-mcp` (add `--append` to merge with CSV imports).
5. Balances aren't transactions. Pass the account balances to the orchestrator so onboarding can pre-fill `goal.balances` and `goal.card_debt`, which the user still confirms.

Cashflow labels can be wrong: a payroll deposit can be labeled as a cash advance, or a loan origination counted as income. The ledger-auditor checks this. Never "fix" anything in Cashflow itself.
