# Spending priorities and caps

Not all spending is equal. You choose what to **protect** (it matters to you) and what you're **willing to cut**. That decides each category's cap and how hard the coach roasts it.

## What onboarding asks
1. **Which categories must be protected?** (multi-select) These get a cap equal to your recent average and a gentle voice.
2. **Which are you willing to cut?** (multi-select) These get a tight cap and the savage voice, if you chose that tone.
3. Everything else is **normal**.
4. **Multipliers** applied to your recent 3-month average. They're shown with a suggestion, which you confirm or change: protect × 1.0, normal × 0.85, cut × 0.5.
5. The planner proposes each cap from your own history, rounded to $25. **You confirm or edit every cap.**

## Where the numbers come from
Your last 3 complete months versus the 3 before (equal windows), net of refunds. The spending-critic shows the trend for each category.

## Example (fictional)
Protect: Groceries, Gas. Cut: Food Delivery, Online Shopping, Coffee, Clothing. Dining was $425/mo, so as "normal" its cap is $350.

## Common mistakes
- Protecting everything. Then nothing changes.
- Caps below what you can actually live with. A cap you'll break every month is useless; start realistic, then tighten.

**Writes:** `categories[] {name, card, priority, cap}`, `cap_multipliers {protect, normal, cut}`
