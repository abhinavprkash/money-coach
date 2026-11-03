# Income

Your take-home pay is the starting point for everything: what lands in your bank after taxes, retirement and insurance deductions. We plan in months, so we also need how often you're paid and any one-off pay you expect (bonus, PTO payout, tax refund).

## What onboarding asks
1. **How often are you paid?** Weekly, every two weeks, twice a month, or monthly. The CLI shows what it detected from your deposits; confirm or correct it.
2. **Take-home per paycheck.** The *net* amount on your paystub ("Net pay"), not gross salary.
3. **Will your take-home change soon?** For example, a raise, or a bigger 401(k)/HSA deduction from January. Each change is a date plus the new amount.
4. **Extra pay you expect**, one at a time: label, month, after-tax amount, and whether it's confirmed. Unconfirmed windfalls are counted but flagged everywhere.
5. **Plan window:** first month and how many months to plan (usually until your goal deadline).

## Where to find it
- Paystub or payroll portal: "Net pay" per check, and deductions.
- Bonus timing and proration: your offer letter or HR portal. If you joined mid-year, bonuses are often prorated.
- For after-tax estimates of a bonus, use your payroll's supplemental withholding. The CLI asks you for the rates; nothing is assumed.

## Example (fictional)
Paid twice a month, $2,850 per check, bonus of $3,000 after tax expected in March (unconfirmed).

## Common mistakes
- Entering gross salary instead of net pay.
- Counting a bonus before you know the payout month.

**Writes:** `income.frequency`, `income.take_home_per_paycheck`, `income.changes[]`, `income.extra_pay[]`, `plan.start_month`, `plan.months`
