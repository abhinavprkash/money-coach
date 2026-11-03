# Savings goal

One number and one date: how much you want in savings (and optionally investments) by when. The goal-planner projects each month's balance, and you enter your real total at each month end.

## What onboarding asks
1. **Target amount and deadline.**
2. **What counts?** Accessible cash only, or retirement accounts too (401(k), IRA, HSA)? Retirement money is usually locked until retirement age.
3. **Current balances**, account by account, marked retirement or not, plus **card balances owed**. These are subtracted so the start is honest.
4. **Payroll contributions** (your 401(k), employer match, HSA): monthly amounts and whether they count toward the goal.
5. **Sinking-fund leftovers:** what share of the sinking fund usually goes unspent (0% if unsure).
6. **Expected annual return:** 0% is the honest default for a goal under 2 years.

## Where to find it
Bank and brokerage apps for balances; your benefits portal for contributions and the employer match formula.

## Example (fictional)
$22,000 by 2027-04-30, counting the 401(k). Start: $2,100 savings + $900 checking + $6,400 401(k) − $1,100 card balances = $8,300.

## Common mistakes
- Forgetting card balances. They're debt, not savings.
- Counting market returns you haven't earned.

**Writes:** `goal {target, deadline, counts_retirement, balances[], card_debt, sinking_unspent_pct, expected_annual_return}`, `payroll[]`
