# Investments

Where your invested money goes and what return you assume. These assumptions decide the Loan vs Invest winner, so the red pen calls out optimistic ones.

## What onboarding asks
1. **Where you invest:** 401(k) (and match), IRA, HSA, brokerage. Check whether your 401(k) has a self-directed brokerage window, which gives you more choice than the default fund list.
2. **Funds or asset mix**, with a weight for each. Example: 70% total-market index, 30% international.
3. **Expected annual return for each.** The CLI suggests a conservative number and tells you why. Best-decade returns (15–25%) are not a plan.
4. **Stress-test return:** the pessimistic case the dashboard can switch to.

## Where to find it
Your brokerage and 401(k) portal (holdings, expense ratios). Long-run market history is a guide, not a promise.

## Example (fictional)
Total market index 8%/yr (weight 0.7), international index 7%/yr (weight 0.3). Stress test 6%.

## Common mistakes
- Using the last 10 years of a hot sector as the expected return.
- Investing money you need within 1–2 years. Short-term goal money usually belongs in cash.

**Writes:** `investments[] {name, kind, expected_return, risk, weight}`, `lvi.stress_return`
