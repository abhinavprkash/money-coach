# Subscriptions

Small recurring charges (streaming, apps, AI tools, memberships) add up and quietly change price. Onboarding goes through every subscription found in your data.

## What onboarding asks
For each detected subscription: **keep, cancel, or unsure?**
- **Keep:** it's budgeted.
- **Cancel:** it's marked inactive, and the recurring-analyst will flag it loudly if it keeps charging.
- **Unsure:** it's kept for now and listed for review.

You can also add subscriptions billed somewhere you didn't export.

## Where to find it
Card statements; App Store / Google Play subscriptions; PayPal automatic payments.

## Example (fictional)
Netflix keep · Hulu cancel (it went up $2/mo) · OpenAI keep.

## Common mistakes
- "Cancelled" in your head but not at the source. The dashboard shows "Marked No and STILL charged" when that happens.
- Two services that do the same job. Pick one.

**Writes:** `subscriptions[] {name, card, amount, active}`
