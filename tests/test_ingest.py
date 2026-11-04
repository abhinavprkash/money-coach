import csv
from pathlib import Path

import pytest
from ingest_csv import Categorizer, PROFILES, detect, read_file
from mc_common import PLUGIN_ROOT, read_json

CAT = Categorizer(read_json(PLUGIN_ROOT / "schemas" / "taxonomy.json"))

SAMPLES = {   # profile -> (header, one purchase row, expected amount)
    "chase_card": (["Transaction Date", "Post Date", "Description", "Category", "Type", "Amount", "Memo"], ["03/14/2026", "03/15/2026", "TRADER JOE S #1", "Groceries", "Sale", "-42.10", ""], -42.10),
    "chase_checking": (["Details", "Posting Date", "Description", "Amount", "Type", "Balance", "Check or Slip #"], ["DEBIT", "03/14/2026", "RENT PAYMENT", "-1500.00", "ACH", "100.00", ""], -1500.0),
    "amex": (["Date", "Description", "Amount"], ["03/14/2026", "NETFLIX.COM", "15.49"], -15.49),
    "capital_one": (["Transaction Date", "Posted Date", "Card No.", "Description", "Category", "Debit", "Credit"], ["2026-03-14", "2026-03-15", "1234", "SHELL OIL", "Gas", "40.00", ""], -40.0),
    "discover": (["Trans. Date", "Post Date", "Description", "Amount", "Category"], ["03/14/2026", "03/15/2026", "UBER *TRIP", "18.20", "Travel"], -18.20),
    "bofa_checking": (["Date", "Description", "Amount", "Running Bal."], ["03/14/2026", "VERIZON WIRELESS", "-65.00", "900.00"], -65.0),
    "bofa_card": (["Posted Date", "Reference Number", "Payee", "Address", "Amount"], ["03/14/2026", "x", "STARBUCKS", "", "-6.25"], -6.25),
    "apple_card": (["Transaction Date", "Clearing Date", "Description", "Merchant", "Category", "Type", "Amount (USD)"], ["03/14/2026", "03/15/2026", "AMZN MKTP", "Amazon", "Shopping", "Purchase", "23.99"], -23.99),
    "citi": (["Status", "Date", "Description", "Debit", "Credit"], ["Cleared", "03/14/2026", "SPOTIFY USA", "11.99", ""], -11.99),
}


@pytest.mark.parametrize("profile", sorted(SAMPLES))
def test_profiles_detect_and_sign(tmp_path, profile):
    header, row, amt = SAMPLES[profile]
    f = tmp_path / f"{profile}.csv"
    with f.open("w", newline="") as fh:
        csv.writer(fh).writerows([header, row])
    assert detect(header) == profile
    rows, name = read_file(f, categorize=CAT)
    assert name == profile and len(rows) == 1
    assert rows[0]["amount"] == pytest.approx(amt)
    assert rows[0]["date"] == "2026-03-14"


def test_generic_layout_not_mistaken_for_amex(tmp_path):
    f = tmp_path / "savings.csv"
    f.write_text("Date,Time,Amount,Type,Description\n2026-03-14,09:00:00,400.00,Deposit,ACME PAYROLL\n")
    rows, name = read_file(f, categorize=CAT)
    assert name == "auto" and rows[0]["amount"] == 400.0 and rows[0]["category"] == "Paycheck"


def test_wells_noheader_and_generic(tmp_path):
    w = tmp_path / "wells.csv"
    w.write_text('"03/14/2026","-12.50","*","","CHIPOTLE 123"\n')
    rows, name = read_file(w, categorize=CAT)
    assert name == "wells_noheader" and rows[0]["amount"] == -12.5 and rows[0]["category"] == "Dining"
    g = tmp_path / "other.csv"
    g.write_text("Posted On,Payee Name,Withdrawal,Deposit\n2026-03-14,LYFT RIDE,22.00,\n")
    rows, name = read_file(g, categorize=CAT)
    assert name == "auto" and rows[0]["amount"] == -22.0 and rows[0]["category"] == "Rideshare"


def test_categorizer_rules():
    assert CAT("Payment Thank You-Mobile", 500)[2] == "transfer"
    assert CAT("ACME CORP PAYROLL", 2000)[0] == "Paycheck"
    assert CAT("ZELLE PAYMENT TO FRIEND", -40)[0] == "P2P"
    assert CAT("UBER EATS ORDER", -30)[0] == "Food Delivery"      # before Rideshare
    assert CAT("HERTZ RENT A CAR", -200)[0] == "Car Rental"       # not "Rent & Housing"
    assert CAT("CURRENT ACCOUNT INTEREST", -1)[0] != "Rent & Housing"  # word boundary: 'rent' inside 'current'


def test_demo_ingest_quality(demo_ws):
    rows = list(csv.DictReader((demo_ws / "transactions.csv").open()))
    assert len(rows) > 500
    assert sum(r["category"] == "Other" for r in rows) / len(rows) < 0.02
    assert sum(r["category"] == "Rent & Housing" for r in rows) == 12
    assert all(r["kind"] in {"income", "expense", "transfer", "investment", "financing"} for r in rows)
