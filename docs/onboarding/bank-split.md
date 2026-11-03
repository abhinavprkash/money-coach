# Paycheck split

Where each paycheck lands. Splitting your direct deposit is the most reliable way to save: money that never hits your spending account doesn't get spent. You choose one account to get "the rest" (the remainder).

## What onboarding asks
1. **Which accounts get part of your paycheck, and how much per paycheck?** For each one, choose its job:
   - **savings:** goal money, never withdrawn before the deadline.
   - **bills:** fixed bills on autopay. Whatever is left over becomes your sinking fund for repairs, travel and annual bills.
   - **spending:** day-to-day spending.
2. **Which account gets the remainder?** Usually your main checking.
3. **Fee waivers:** does any account need a minimum deposit to avoid a monthly fee?

The budget-planner checks the split against your bills and caps. If your savings slice is more than the budget leaves, you'll be told to lower it. Otherwise you'd end up pulling it back out, which is the #1 reason savings never grow.

## Where to find it
Your payroll portal's direct-deposit page.

## Example (fictional)
Ally Savings (savings) $400/paycheck; Bills Checking (bills) $1,400/paycheck; Chase Checking gets the rest.

## Common mistakes
- Sending more to savings than the budget supports, then withdrawing it every month.
- Forgetting that the bills account's leftover is your sinking fund, not extra fun money.

**Writes:** `split.accounts[] {name, kind, per_paycheck, job}`, `split.remainder`, `split.remainder_job`
