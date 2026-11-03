# Loans

Your loans decide the Loan vs Invest tab. It's built **only** from what you enter here; with no loans, the tab is hidden.

## What onboarding asks
1. **What kinds of loans do you have?** (multi-select) Student/education, auto, mortgage, personal, credit card balance you carry, buy-now-pay-later, family loan, none.
2. For each loan:
   - **Currency:** the currency you owe in. A loan in another country's currency adds exchange-rate questions: rate at the start, rate now, and dates.
   - **Outstanding balance and interest rate.**
   - **Interest type:**
     - *Reducing balance* ("Compound"): interest is charged on what you still owe. Most student, auto, home and personal loans work this way.
     - *Flat* ("Simple-flat"): interest is charged on the original amount for the whole term.
     - *Rebate* ("Simple-rebate"): flat interest that stops when you close early.
   - **Minimum payment, what you actually pay now, and your payoff goal** (for example, 3 years).
3. **Monthly budget for loans plus investing**, and what you invest today.

## How to tell flat from reducing balance
Look at two statements a few months apart. If the interest part of your payment **shrinks** as the balance falls, it's reducing-balance. If it stays the same, it's flat. When unsure, ask the lender. This choice changes the answer a lot.

## Example (fictional)
Student loan, USD, $23,400 at 6.8%, reducing-balance, minimum $300, paying $420. Auto loan, USD, $9,800 at 5.9%, paying $390.

## Common mistakes
- Picking "flat" for a reducing-balance loan. That makes every payment look like pure principal.
- Assuming a foreign currency will keep weakening at its historical pace.

**Writes:** `loans[] {name, kind, currency, principal, outstanding, rate, type, min_payment, current_payment, tenure_years?, payoff_goal_years?}`, `lvi {monthly_budget, current_investing_monthly, years, step_up, stress_return, fx?}`
