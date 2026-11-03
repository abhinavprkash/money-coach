# Taxes

money-coach doesn't know tax law and never assumes it. You enter your own marginal rates. They're used to show what a bigger 401(k) or HSA contribution really costs your take-home pay.

## What onboarding asks
1. **Federal marginal rate**: your top bracket.
2. **State marginal rate**: 0 if your state has no income tax.
3. **Do you pay payroll taxes (Social Security/Medicare)?** Some visa holders and some public employees don't. Your paystub shows it.
4. **Does your state tax HSA contributions?** A few states do; check your paystub or a tax professional.

## Where to find it
Your paystub (which lines appear), last year's tax return, or tax software. If you're unsure, a tax professional can tell you.

## Example (fictional)
22% federal, 6% state, payroll taxes yes, HSA not state-taxed. A $100 extra 401(k) contribution costs about $72 of take-home.

## Common mistakes
- Using the *average* tax rate instead of the *marginal* one.
- Ignoring that bonuses are withheld at a flat supplemental rate, so your real tax can differ when you file.

**Writes:** `tax {federal_marginal, state_marginal, payroll_tax_exempt, hsa_state_taxed}`
