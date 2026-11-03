"""Import bank/card CSV exports into money-coach-data/transactions.csv (normalized, categorized).

    python3 ingest_csv.py FILE.csv [FILE2.csv ...] [--account "Chase Sapphire"] [--profile chase_card]
                          [--charges-positive] [--workspace DIR] [--append]

Each file is matched to a bank profile by its header row (or --profile). Unknown layouts fall back to
auto-detecting date / description / amount (or debit + credit) columns. Amount sign is normalized so
NEGATIVE = money out. Prints a coverage report as JSON (files, rows, date range, unknown rows).
"""
import argparse
import csv
import io
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mc_common import PLUGIN_ROOT, data_dir, read_json, read_transactions, write_json, write_transactions  # noqa: E402

# header signature (lowercased, subset) -> how to read it. sign: +1 means file uses negative = outflow.
PROFILES = {
    "chase_card": {"match": {"transaction date", "post date", "description", "category", "type", "amount"},
                   "date": "transaction date", "desc": "description", "amount": "amount", "sign": 1, "institution": "Chase"},
    "chase_checking": {"match": {"details", "posting date", "description", "amount", "type", "balance"},
                       "date": "posting date", "desc": "description", "amount": "amount", "sign": 1, "institution": "Chase"},
    "amex": {"match": {"date", "description", "amount"}, "exclude": {"debit", "credit", "running bal."},
             "date": "date", "desc": "description", "amount": "amount", "sign": -1, "institution": "American Express"},
    "capital_one": {"match": {"transaction date", "posted date", "description", "debit", "credit"},
                    "date": "transaction date", "desc": "description", "debit": "debit", "credit": "credit", "institution": "Capital One"},
    "discover": {"match": {"trans. date", "post date", "description", "amount", "category"},
                 "date": "trans. date", "desc": "description", "amount": "amount", "sign": -1, "institution": "Discover"},
    "bofa_checking": {"match": {"date", "description", "amount", "running bal."},
                      "date": "date", "desc": "description", "amount": "amount", "sign": 1, "institution": "Bank of America"},
    "bofa_card": {"match": {"posted date", "reference number", "payee", "amount"},
                  "date": "posted date", "desc": "payee", "amount": "amount", "sign": 1, "institution": "Bank of America"},
    "apple_card": {"match": {"transaction date", "clearing date", "description", "merchant", "amount (usd)"},
                   "date": "transaction date", "desc": "description", "merchant": "merchant", "amount": "amount (usd)", "sign": -1,
                   "institution": "Apple Card"},
    "citi": {"match": {"status", "date", "description", "debit", "credit"},
             "date": "date", "desc": "description", "debit": "debit", "credit": "credit", "institution": "Citi"},
}
DATE_FORMATS = ["%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y", "%d/%m/%Y", "%Y/%m/%d", "%b %d, %Y", "%d %b %Y"]


def parse_date(s):
    s = (s or "").strip()
    for f in DATE_FORMATS:
        try:
            return datetime.strptime(s, f).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"Unrecognized date: {s!r}")


def parse_amount(s):
    s = (s or "").strip().replace("$", "").replace(",", "")
    if s in ("", "-"):
        return 0.0
    neg = s.startswith("(") and s.endswith(")")
    v = float(s.strip("()"))
    return -v if neg else v


def detect(header):
    h = {c.strip().lower() for c in header}
    best = None
    for name, p in PROFILES.items():
        if p["match"] <= h and not (p.get("exclude", set()) & h):
            if best is None or len(p["match"]) > len(PROFILES[best]["match"]):
                best = name
    return best


def auto_profile(header):
    h = [c.strip().lower() for c in header]
    pick = lambda *keys: next((c for c in h if any(k in c for k in keys)), None)
    p = {"date": pick("date", "posted"), "desc": pick("description", "payee", "merchant", "details", "name", "memo"),
         "amount": pick("amount"), "debit": pick("debit", "withdrawal"), "credit": pick("credit", "deposit"), "sign": 1,
         "institution": ""}
    if not p["date"] or not p["desc"] or not (p["amount"] or (p["debit"] and p["credit"])):
        raise ValueError(f"Can't find date/description/amount columns in header: {header}")
    if p["amount"]:
        p.pop("debit"); p.pop("credit")
    return p


class Categorizer:
    def __init__(self, taxonomy):
        self.t = taxonomy
        comp = lambda kws: [re.compile(r"(?<![a-z0-9])" + re.escape(k.lower())) for k in kws]
        self.transfer = comp(taxonomy["transfer_keywords"])
        self.income = comp(taxonomy["income_keywords"])
        self.p2p = comp(taxonomy["p2p_keywords"])
        self.cats = [(c, comp(c["keywords"])) for c in taxonomy["categories"]]

    @staticmethod
    def hit(pats, text):
        return any(p.search(text) for p in pats)

    def __call__(self, desc, amount):
        t = desc.lower()
        if self.hit(self.transfer, t):
            return "Transfer", "Transfers", "transfer"
        if self.hit(self.p2p, t):
            return "P2P", "P2P", "expense"
        if amount > 0 and self.hit(self.income, t):
            return "Paycheck" if any(k in t for k in ("payroll", "direct dep", "dir dep", "salary", "paycheck")) else "Other Income", "Income", "income"
        for c, pats in self.cats:
            if self.hit(pats, t):
                kind = "financing" if c["group"] == "Debt" else "expense"
                return c["name"], c["group"], kind
        if amount > 0:
            return "Refund/Credit", "Other", "expense"
        fb = self.t["fallback"]
        return fb["name"], fb["group"], "expense"


ALIASES = {}


def clean_merchant(desc):
    low = desc.lower()
    for k, v in ALIASES.items():
        if k in low:
            return v
    d = re.sub(r"\s+", " ", desc).strip()
    d = re.sub(r"\*[A-Za-z0-9]{6,}", "", d)
    d = re.sub(r"^(sq \*|tst\* ?|sp \*|pp\*|paypal \*|aplpay |pos |debit card purchase )", "", d, flags=re.I)
    d = re.sub(r"[#*]?\d{3,}.*$", "", d).strip(" -*#")
    return d.title()[:40] or desc[:40]


def read_file(path, profile=None, account=None, charges_positive=False, categorize=None):
    raw = Path(path).read_text(encoding="utf-8-sig")
    rows = list(csv.reader(io.StringIO(raw)))
    rows = [r for r in rows if any(c.strip() for c in r)]
    header = rows[0]
    name = profile or detect(header)
    if name is None and re.match(r"^\s*\d", header[0] or ""):
        name = "wells_noheader"   # Wells Fargo style: no header row; date, amount, *, *, description
    if name == "wells_noheader":
        p = {"institution": "Wells Fargo"}
        body = [{"date": r[0], "amount": r[1], "desc": r[4] if len(r) > 4 else r[-1]} for r in rows]
        mapped = [(b["date"], b["desc"], parse_amount(b["amount"]), "") for b in body]
    else:
        p = PROFILES[name] if name else auto_profile(header)
        hdr = [c.strip().lower() for c in header]
        body = [dict(zip(hdr, r)) for r in rows[1:]]
        mapped = []
        for b in body:
            if not b.get(p["date"]):
                continue
            if "amount" in p and p.get("amount"):
                amt = parse_amount(b.get(p["amount"])) * p.get("sign", 1)
            else:
                amt = parse_amount(b.get(p["credit"])) - parse_amount(b.get(p["debit"]))
            mapped.append((b[p["date"]], b.get(p["desc"], ""), amt, b.get(p.get("merchant") or "", "")))
    if charges_positive:
        mapped = [(d, s, -a, m) for d, s, a, m in mapped]
    acct = account or (Path(path).stem.replace("_", " ").title())
    out = []
    for d, s, a, m in mapped:
        cat, grp, kind = categorize(f"{s} {m}", a)
        out.append({"date": parse_date(d), "account": acct, "institution": p.get("institution", ""), "description": s.strip(),
                    "merchant": (m.strip() or clean_merchant(s)), "amount": round(a, 2), "category": cat, "group": grp,
                    "kind": kind, "source": f"csv:{Path(path).name}:{name or 'auto'}"})
    return out, (name or "auto")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--account", help="Account name to use (default: file name). One per run if given.")
    ap.add_argument("--profile", choices=sorted(PROFILES) + ["wells_noheader"])
    ap.add_argument("--charges-positive", action="store_true", help="File shows purchases as positive numbers")
    ap.add_argument("--workspace")
    ap.add_argument("--append", action="store_true", help="Add to existing transactions.csv (dedupes exact repeats)")
    a = ap.parse_args(argv)
    ddir = data_dir(a.workspace)
    tax = read_json(ddir / "taxonomy.json") or read_json(PLUGIN_ROOT / "schemas" / "taxonomy.json")
    cat = Categorizer(tax)
    ALIASES.update(sorted(tax.get("merchant_aliases", {}).items(), key=lambda kv: -len(kv[0])))
    rows, report = [], {"files": []}  # type: dict
    for f in a.files:
        got, prof = read_file(f, a.profile, a.account, a.charges_positive, cat)
        rows += got
        report["files"].append({"file": str(f), "profile": prof, "rows": len(got),
                                "range": [min((r["date"] for r in got), default=None), max((r["date"] for r in got), default=None)]})
    target = ddir / "transactions.csv"
    if a.append and target.exists():
        old = read_transactions(target)
        rows = old + rows
    seen, dedup = set(), []
    for r in rows:
        k = (r["date"], r["account"], r["description"], f"{float(r['amount']):.2f}")
        if k in seen:
            continue
        seen.add(k); dedup.append(r)
    write_transactions(target, dedup)
    report.update({"written": str(target), "rows": len(dedup), "duplicates_dropped": len(rows) - len(dedup),
                   "range": [min(r["date"] for r in dedup), max(r["date"] for r in dedup)] if dedup else None,
                   "uncategorized": sum(1 for r in dedup if r["category"] in ("Other",)),
                   "by_kind": {k: sum(1 for r in dedup if r["kind"] == k) for k in ("income", "expense", "transfer", "financing", "investment")}})
    write_json(ddir / "findings" / "ingest.json", report)
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
