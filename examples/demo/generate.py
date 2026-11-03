"""Generate a fully fictional demo dataset (seeded, reproducible) in three real bank CSV layouts.

    python3 examples/demo/generate.py   -> examples/demo/bank/*.csv

"Jordan Demo" is made up. Every merchant and amount below is invented for testing.
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent / "bank"
START, END = date(2025, 11, 1), date(2026, 10, 31)
rng = random.Random(42)


def days():
    d = START
    while d <= END:
        yield d
        d += timedelta(days=1)


def month_iter():
    y, m = START.year, START.month
    while date(y, m, 1) <= END:
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


checking, sapphire, amex = [], [], []   # (date, description, amount: negative = out)

for y, m in month_iter():
    pay1, pay2 = date(y, m, 15), (date(y, m + 1, 1) - timedelta(days=1)) if m < 12 else date(y, 12, 31)
    for p in (pay1, pay2):
        checking.append((p, "ACME CORP PAYROLL PPD ID: 000111", 2850.00))
    checking.append((date(y, m, 1), "ONLINE PAYMENT TO SUNRISE APARTMENTS RENT", -1650.00))
    checking.append((date(y, m, 5), "STUDENT LN NELNET PAYMENT", -420.00))
    checking.append((date(y, m, 8), "CITYCU AUTO LOAN PAYMENT", -390.00))
    checking.append((date(y, m, 12), "PG&E ELECTRIC WEB ONLINE", -round(rng.uniform(55, 110), 2)))
    checking.append((date(y, m, 20), "VERIZON WIRELESS PAYMENTS", -65.00))
    checking.append((date(y, m, 22), "GEICO AUTO INSURANCE", -142.00))
    checking.append((date(y, m, 3), "ZELLE PAYMENT TO ROOMMATE UTILITIES", -round(rng.uniform(40, 70), 2)))
    # subscriptions on the Amex (price hike for one in month 5; a "cancelled" one that keeps charging)
    amex.append((date(y, m, 9), "NETFLIX.COM", -15.49))
    amex.append((date(y, m, 11), "SPOTIFY USA", -11.99))
    amex.append((date(y, m, 16), "HULU 877-8244858 CA", -(7.99 if (y, m) < (2026, 4) else 9.99)))
    amex.append((date(y, m, 2), "PLANET FITNESS CLUB FEES", -24.99))
    amex.append((date(y, m, 18), "OPENAI CHATGPT SUBSCR", -20.00))

for d in days():
    late = d >= date(2026, 8, 1)   # spending creeps up in the last quarter
    if rng.random() < (0.22 if late else 0.15):
        sapphire.append((d, rng.choice(["DOORDASH*THAI GARDEN", "UBER EATS ORDER", "DOORDASH*BURGER BARN"]),
                         -round(rng.uniform(22, 48), 2)))
    if rng.random() < 0.28:
        sapphire.append((d, rng.choice(["TST* CORNER BISTRO", "SQ *TACO STAND", "PIZZA PALACE", "SUSHI KITCHEN"]),
                         -round(rng.uniform(14, 65 if late else 45), 2)))
    if d.weekday() == 5:
        sapphire.append((d, rng.choice(["TRADER JOE S #123", "SAFEWAY STORE 456", "COSTCO WHSE #789"]), -round(rng.uniform(55, 160), 2)))
    if rng.random() < (0.25 if late else 0.12):
        amex.append((d, "AMAZON MKTPL*AB12CD34", -round(rng.uniform(9, 85), 2)))
    if rng.random() < 0.09:
        sapphire.append((d, rng.choice(["SHELL OIL 5744", "CHEVRON 0091", "COSTCO GAS #789"]), -round(rng.uniform(38, 62), 2)))
    if rng.random() < 0.10:
        sapphire.append((d, "UBER *TRIP", -round(rng.uniform(12, 34), 2)))
    if rng.random() < 0.06:
        sapphire.append((d, "STARBUCKS STORE 1234", -round(rng.uniform(5, 9), 2)))
    if rng.random() < 0.03:
        amex.append((d, rng.choice(["NIKE.COM", "UNIQLO USA", "TARGET 00012345"]), -round(rng.uniform(25, 120), 2)))
    if rng.random() < 0.02:
        amex.append((d, "AMC THEATRES 0456", -round(rng.uniform(14, 32), 2)))

sapphire.append((date(2026, 3, 14), "UNITED AIRLINES 0162345", -486.20))
sapphire.append((date(2026, 3, 20), "MARRIOTT DOWNTOWN", -612.44))
amex.append((date(2026, 5, 2), "AMAZON MKTPL*REFUND", 64.10))

# monthly card payments from checking (so the auditor can pair transfers)
for y, m in month_iter():
    pay_day = date(y, m, 25)
    s_total = round(-sum(a for d, _, a in sapphire if d.year == y and d.month == m), 2)
    a_total = round(-sum(a for d, _, a in amex if d.year == y and d.month == m), 2)
    checking.append((pay_day, "CHASE CREDIT CRD AUTOPAY", -s_total))
    checking.append((pay_day, "AMEX EPAYMENT ACH PMT", -a_total))
    sapphire.append((pay_day, "Payment Thank You-Mobile", s_total))
    amex.append((pay_day, "ONLINE PAYMENT - THANK YOU", a_total))

OUT.mkdir(parents=True, exist_ok=True)
with (OUT / "chase_checking.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Details", "Posting Date", "Description", "Amount", "Type", "Balance", "Check or Slip #"])
    bal = 3200.0
    for d, desc, a in sorted(checking):
        bal += a
        w.writerow(["CREDIT" if a > 0 else "DEBIT", d.strftime("%m/%d/%Y"), desc, f"{a:.2f}", "ACH", f"{bal:.2f}", ""])
with (OUT / "chase_sapphire.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Transaction Date", "Post Date", "Description", "Category", "Type", "Amount", "Memo"])
    for d, desc, a in sorted(sapphire):
        w.writerow([d.strftime("%m/%d/%Y"), (d + timedelta(days=1)).strftime("%m/%d/%Y"), desc, "", "Sale" if a < 0 else "Payment", f"{a:.2f}", ""])
with (OUT / "amex_gold.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Date", "Description", "Amount"])           # Amex: charges are POSITIVE
    for d, desc, a in sorted(amex):
        w.writerow([d.strftime("%m/%d/%Y"), desc, f"{-a:.2f}"])
print("wrote", *sorted(p.name for p in OUT.glob("*.csv")))
