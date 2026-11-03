# Fixed and recurring bills

Bills that come every month at roughly the same amount: rent or mortgage, loan payments, insurance, utilities, phone, gym, buy-now-pay-later plans. They're planned first because they aren't optional this month.

## What onboarding asks
The recurring-analyst has already found repeating charges in your transactions. The CLI shows each one and asks:
1. **Is this a fixed bill?** Keep, edit the amount, or skip.
2. **Paid from which account or card?** It must be one of your split accounts or cards.
3. **Does it end?** For example, a BNPL plan with 3 payments left: enter the last month.
4. **Anything missing?** Add bills paid outside the accounts you exported, such as rent paid by check or a loan paid from another bank.

## Where to find it
Loan statements, lease, insurance policy, utility bills, your bank's autopay list.

## Example (fictional)
Rent $1,650 from Bills Checking · Student loan $420 from Bills Checking · Phone $65 on Chase Sapphire.

## Common mistakes
- Counting rent twice: once as a bill, and again because it went through a card or PayPal. Log it once.
- Leaving finished BNPL plans active. Set an end month.

**Writes:** `fixed_bills[] {name, paid_from, amount, start?, end?, note?}`
