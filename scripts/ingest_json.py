"""Import transactions from JSON (e.g. pulled through the Cashflow MCP or another aggregator).

    python3 ingest_json.py rows.json [--workspace DIR] [--append] [--source cashflow-mcp]

rows.json: a list of objects. Accepted keys (first match wins):
    date|dt|posted   account|acct|account_name   institution|inst|bank   description|desc|raw|name
    merchant|party|payee   amount|amt (negative = money out)   category|cat   group|grp   kind (optional)
Rows without a category/kind are categorized with the taxonomy, same as CSV import.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mc_common import KINDS, PLUGIN_ROOT, data_dir, read_json, read_transactions, secure_tree, write_json, write_transactions  # noqa: E402
from ingest_csv import ALIASES, Categorizer, clean_merchant, parse_date  # noqa: E402

GROUP_KIND = {"Income": "income", "Transfers": "transfer", "Investment": "investment", "Financing": "financing", "Debt": "financing"}


def pick(o, *keys):
    for k in keys:
        if o.get(k) not in (None, ""):
            return o[k]
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--workspace")
    ap.add_argument("--append", action="store_true")
    ap.add_argument("--source", default="json")
    a = ap.parse_args(argv)
    ddir = data_dir(a.workspace)
    tax = read_json(ddir / "taxonomy.json") or read_json(PLUGIN_ROOT / "schemas" / "taxonomy.json")
    cat = Categorizer(tax)
    ALIASES.update(sorted(tax.get("merchant_aliases", {}).items(), key=lambda kv: -len(kv[0])))
    rows = []
    for o in json.loads(Path(a.file).read_text(encoding="utf-8")):
        if o.get("pending"):
            continue
        desc = str(pick(o, "description", "desc", "raw", "name") or "")
        amt = float(pick(o, "amount", "amt") or 0)
        c, g, k = pick(o, "category", "cat"), pick(o, "group", "grp"), o.get("kind")
        if not c:
            c, g, k = cat(desc, amt)
        k = k if k in KINDS else GROUP_KIND.get(g, "expense")
        rows.append({"date": parse_date(str(pick(o, "date", "dt", "posted"))[:10]), "account": pick(o, "account", "acct", "account_name") or "Unknown",
                     "institution": pick(o, "institution", "inst", "bank") or "", "description": desc,
                     "merchant": pick(o, "merchant", "party", "payee") or clean_merchant(desc), "amount": round(amt, 2),
                     "category": c, "group": g or "Other", "kind": k, "source": a.source})
    target = ddir / "transactions.csv"
    if a.append and target.exists():
        rows = read_transactions(target) + rows
    seen, out = set(), []
    for r in rows:
        key = (r["date"], r["account"], r["description"], f"{float(r['amount']):.2f}")
        if key not in seen:
            seen.add(key); out.append(r)
    write_transactions(target, out)
    rep = {"written": str(target), "rows": len(out), "source": a.source,
           "range": [min(r["date"] for r in out), max(r["date"] for r in out)] if out else None}
    write_json(ddir / "findings" / "ingest.json", rep)
    secure_tree(ddir)
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
