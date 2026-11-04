"""Deterministic analysis over money-coach-data/transactions.csv. One subcommand per subagent.

    python3 analyze.py summary    [--workspace DIR]   -> analysis.json (monthly, categories, merchants, windows)
    python3 analyze.py audit      [--workspace DIR]   -> findings/audit.json      (ledger-auditor)
    python3 analyze.py recurring  [--workspace DIR]   -> findings/recurring.json  (recurring-analyst)
    python3 analyze.py spending   [--workspace DIR]   -> findings/spending.json   (spending-critic)

Rules that keep it honest:
  * Only complete months are averaged. Trends compare EQUAL windows (last 3 full months vs the 3 before).
  * Outflow = money out of the category net of refunds in that category; transfers are never spending.
  * Every finding carries evidence (counts, amounts, dates) and says what is unverified.
"""
import argparse
import json
import statistics
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mc_common import data_dir, month_add, read_json, read_transactions, secure_tree, write_json  # noqa: E402
import roast as R  # noqa: E402

SEVERITY_ORDER = {"critical": 0, "serious": 1, "warning": 2, "verify": 3, "opp": 4, "good": 5}


def r2(x):
    return round(x + 0.0, 2)


def full_months(rows):
    """Months fully covered by the data (first/last partial months dropped)."""
    ds = sorted(r["date"] for r in rows)
    first, last = date.fromisoformat(ds[0]), date.fromisoformat(ds[-1])
    start = first.strftime("%Y-%m") if first.day <= 3 else month_add(first.strftime("%Y-%m"), 1)
    nxt = last + timedelta(days=1)
    end = last.strftime("%Y-%m") if nxt.month != last.month else month_add(last.strftime("%Y-%m"), -1)
    out, cur = [], start
    while cur <= end:
        out.append(cur); cur = month_add(cur, 1)
    return out


def spend_rows(rows):
    return [r for r in rows if r["kind"] in ("expense", "financing")]


def summary(rows, cfg=None):
    months = full_months(rows)
    mset = set(months)
    recent, prior = months[-3:], months[-6:-3]
    by_month = defaultdict(lambda: {"income": 0.0, "spend": 0.0, "groups": defaultdict(float)})
    cats = defaultdict(lambda: {"group": "", "net": defaultdict(float), "count": defaultdict(int)})
    merchants = defaultdict(lambda: {"net": 0.0, "count": defaultdict(int), "category": ""})
    for r in rows:
        ym = r["date"][:7]
        if ym not in mset:
            continue
        a = r["amount"]
        if r["kind"] == "income":
            by_month[ym]["income"] += a
        elif r["kind"] in ("expense", "financing"):
            by_month[ym]["spend"] += -a
            by_month[ym]["groups"][r["group"]] += -a
            c = cats[r["category"]]
            c["group"] = r["group"]; c["net"][ym] += -a
            if a < 0:
                c["count"][ym] += 1
            m = merchants[r["merchant"]]
            m["net"] += -a; m["category"] = r["category"]
            if a < 0:
                m["count"][ym] += 1
    avg = lambda d, ms: sum(d.get(m, 0) for m in ms) / max(1, len(ms))
    categories = []
    for name, c in cats.items():
        categories.append({"name": name, "group": c["group"], "total": r2(sum(c["net"].values())),
                           "monthly_avg": r2(avg(c["net"], months)), "recent_avg": r2(avg(c["net"], recent)),
                           "prior_avg": r2(avg(c["net"], prior)), "count": sum(c["count"].values()),
                           "recent_count": sum(c["count"].get(m, 0) for m in recent),
                           "prior_count": sum(c["count"].get(m, 0) for m in prior),
                           "by_month": {m: r2(c["net"].get(m, 0)) for m in months}})
    categories.sort(key=lambda x: -x["total"])
    mer = sorted(({"merchant": k, "category": v["category"], "total": r2(v["net"]), "count": sum(v["count"].values()),
                   "recent_count": sum(v["count"].get(m, 0) for m in recent), "prior_count": sum(v["count"].get(m, 0) for m in prior)}
                  for k, v in merchants.items()), key=lambda x: -x["total"])[:40]
    pay = [r for r in rows if r["category"] == "Paycheck"]
    paydays = sorted({r["date"] for r in pay})
    gaps = [(date.fromisoformat(b) - date.fromisoformat(a)).days for a, b in zip(paydays, paydays[1:])]
    g = statistics.median(gaps) if gaps else None
    freq = None if g is None else ("weekly" if g <= 8 else "biweekly" if g <= 14.5 else "semimonthly" if g <= 17 else "monthly")
    return {
        "range": [min(r["date"] for r in rows), max(r["date"] for r in rows)], "full_months": months,
        "windows": {"recent": recent, "prior": prior},
        "monthly": [{"month": m, "income": r2(by_month[m]["income"]), "spend": r2(by_month[m]["spend"]),
                     "groups": {k: r2(v) for k, v in by_month[m]["groups"].items()}} for m in months],
        "categories": categories, "merchants": mer,
        "paycheck": {"deposits": len(pay), "median_amount": r2(statistics.median([r["amount"] for r in pay])) if pay else None,
                     "frequency_guess": freq, "accounts": sorted({r["account"] for r in pay})},
        "accounts": sorted({r["account"] for r in rows}),
    }


def finding(sev, title, amount, evidence, action, lever=None, category=None):
    f = {"severity": sev, "title": title, "amount_at_stake": r2(amount or 0), "evidence": evidence, "action": action}
    if lever:
        f["lever"] = lever
    if category:
        f["category"] = category
    return f


def audit(rows, a):
    out = []
    xfers = [r for r in rows if r["kind"] == "transfer"]
    unmatched, used = [], set()
    for i, r in enumerate(xfers):
        if i in used:
            continue
        d0 = date.fromisoformat(r["date"])
        mate = next((j for j, s in enumerate(xfers) if j not in used and j != i and s["account"] != r["account"]
                     and abs(s["amount"] + r["amount"]) < 0.01 and abs((date.fromisoformat(s["date"]) - d0).days) <= 5), None)
        if mate is None:
            unmatched.append(r)
        else:
            used |= {i, mate}
    if unmatched:
        out_amt = -sum(r["amount"] for r in unmatched if r["amount"] < 0)
        in_amt = sum(r["amount"] for r in unmatched if r["amount"] > 0)
        out.append(finding("verify", f"{len(unmatched)} transfers have no matching other side in your files",
                           out_amt + in_amt, [f"Out ${out_amt:,.2f}, in ${in_amt:,.2f}", "Usually an account you didn't export (savings, brokerage, another bank)"],
                           "Export the missing accounts, or confirm these are moves between your own accounts."))
    sweep_keys = ("robinhood", "fidelity", "vanguard", "schwab", "brokerage", "etrade", "webull", "acorns", "betterment",
                  "wealthfront", "savings", "ally", "marcus", "sofi", "high yield")
    pulled = [r for r in rows if r["amount"] > 0 and r["kind"] == "transfer" and "savings" not in r["account"].lower()
              and any(k in r["description"].lower() for k in sweep_keys)]
    if len(pulled) >= 3:
        tot = sum(r["amount"] for r in pulled)
        out.append(finding("critical", f"${tot:,.0f} moved back OUT of savings/investments ({len(pulled)} transfers)",
                           tot, [f"{r['date']} {r['description'][:40]} ${r['amount']:,.2f}" for r in pulled[-5:]],
                           "If this is a paycheck split you sweep back each month, your savings never accumulate. Change the split instead of withdrawing.",
                           lever="split"))
    seen = defaultdict(list)
    for r in rows:
        if r["kind"] == "expense" and r["amount"] < 0:
            seen[(r["date"], r["account"], r["merchant"], r["amount"])].append(r)
    dups = [v for v in seen.values() if len(v) > 1]
    if dups:
        amt = sum(-v[0]["amount"] * (len(v) - 1) for v in dups)
        out.append(finding("verify", f"{len(dups)} possible duplicate charges", amt,
                           [f"{v[0]['date']} {v[0]['merchant']} ${-v[0]['amount']:,.2f} ×{len(v)}" for v in dups[:6]],
                           "Check your statements; dispute real duplicates with the card issuer."))
    p2p = [r for r in rows if r["category"] == "P2P"]
    if p2p:
        o, i = -sum(r["amount"] for r in p2p if r["amount"] < 0), sum(r["amount"] for r in p2p if r["amount"] > 0)
        out.append(finding("verify", f"P2P: ${o:,.0f} sent, ${i:,.0f} received", o - i,
                           [f"{len(p2p)} Zelle/Venmo/Cash App transactions", "Shared bills and reimbursements hide here"],
                           "Tell the budget which P2P payments are rent/bills you share, so they aren't counted as fun money."))
    other = [r for r in rows if r["category"] == "Other" and r["amount"] < 0]
    if other:
        amt = -sum(r["amount"] for r in other)
        out.append(finding("warning", f"{len(other)} charges couldn't be categorized", amt,
                           sorted({r["merchant"] for r in other})[:8], "Add keywords to money-coach-data/taxonomy.json and re-run ingest."))
    return out


def recurring(rows, cfg):
    by = defaultdict(list)
    for r in rows:
        if r["kind"] in ("expense", "financing") and r["amount"] < 0:
            by[r["merchant"]].append(r)
    found, out = [], []
    for m, rs in by.items():
        months = defaultdict(list)
        for r in rs:
            months[r["date"][:7]].append(-r["amount"])
        if len(months) < 3:
            continue
        per = [sum(v) for _, v in sorted(months.items())]
        if max(len(v) for v in months.values()) > 2:
            continue
        med = statistics.median(per)
        spread = (statistics.pstdev(per) / med) if med else 1
        if spread > 0.25:
            continue
        last = per[-1]
        cat = rs[0]["category"]
        item = {"merchant": m, "category": cat, "monthly": r2(last), "median": r2(med), "months": len(months),
                "first": min(months), "last": max(months), "price_change": r2(last - per[0]) if abs(last - per[0]) > 0.5 else 0}
        found.append(item)
        if item["price_change"] > 0 and cat == "Subscriptions":
            out.append(finding("warning", f"{m} went up ${item['price_change']:.2f}/mo", item["price_change"] * 12,
                               [f"Was ${per[0]:.2f}, now ${last:.2f}"], "Decide if it's still worth it at the new price.", lever="subs"))
    subs = [f for f in found if f["category"] == "Subscriptions"]
    if subs:
        tot = sum(f["monthly"] for f in subs)
        out.append(finding("warning", f"Subscriptions: ${tot:,.2f}/mo (${tot*12:,.0f}/yr) across {len(subs)} services", tot * 12,
                           [f"{f['merchant']} ${f['monthly']:.2f}" for f in subs], "Keep the ones you used this month. Cancel the rest today.",
                           lever="subs"))
    if cfg:
        last_date = max(r["date"] for r in rows)
        cutoff = (date.fromisoformat(last_date) - timedelta(days=45)).isoformat()
        for s in cfg.get("subscriptions", []):
            if s.get("active") is False:
                hits = [r for r in rows if r["date"] >= cutoff and r["amount"] < 0 and s["name"].lower()[:6] in (r["merchant"] + r["description"]).lower()]
                if hits:
                    amt = -sum(r["amount"] for r in hits)
                    out.append(finding("serious", f"{s['name']} is marked cancelled but charged ${amt:.2f} in the last 45 days", amt * 12,
                                       [f"{r['date']} {r['description'][:40]}" for r in hits], "Cancel it at the source and ask for a refund.", lever="subs"))
    return found, out


def spending(rows, a, cfg):
    out, tone = [], (cfg or {}).get("tone", "honest")
    prio = {c["name"]: c.get("priority", "normal") for c in (cfg or {}).get("categories", [])}
    lines = {}
    for c in a["categories"]:
        if c["group"] in ("Housing", "Debt", "Bills", "Income", "Transfers") or c["recent_avg"] <= 0:
            continue
        lines[c["name"]] = R.category_line(c, prio.get(c["name"], "normal"), tone)
        up = c["recent_avg"] - c["prior_avg"]
        if c["name"] != "Food Delivery" and c["prior_avg"] > 0 and up / c["prior_avg"] > 0.2 and up > 50:
            sev = "serious" if up > 200 else "warning"
            out.append(finding(sev, f"{c['name']} up {up/c['prior_avg']*100:.0f}%: ${c['prior_avg']:,.0f} → ${c['recent_avg']:,.0f}/mo",
                               up * 3, [f"Purchases: {c['prior_count']} → {c['recent_count']} (equal 3-month windows)",
                                        "Shared costs or reimbursements could explain part of it (unverified)"],
                               R.action_for(c["name"], tone), lever="caps", category=c["name"]))
    for m in a["merchants"][:15]:
        if m["recent_count"] >= 20:
            per_week = m["recent_count"] / 13
            out.append(finding("warning", f"{m['merchant']}: {m['recent_count']} charges in 3 months ({per_week:.1f}/week)", m["total"] / 4,
                               [f"${m['total']:,.0f} over the full period"], R.cadence_line(m, tone), lever="caps", category=m["category"]))
    for c in a["categories"]:
        if c["name"] == "Food Delivery" and c["total"] > 0:
            out.append(finding("serious", f"Food delivery: ${c['total']:,.0f} over {c['count']} orders", c["recent_avg"] * 3,
                               [f"Recent ${c['recent_avg']:,.0f}/mo vs ${c['prior_avg']:,.0f}/mo before"], R.delivery_line(c, tone),
                               lever="caps", category=c["name"]))
    return out, lines


def write_findings(ddir, agent, findings, extra=None):
    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f["severity"], 9), -f["amount_at_stake"]))
    doc = {"agent": agent, "as_of": date.today().isoformat(), "findings": findings}
    if extra:
        doc.update(extra)
    write_json(ddir / "findings" / f"{agent}.json", doc)
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["summary", "audit", "recurring", "spending"])
    ap.add_argument("--workspace")
    a = ap.parse_args(argv)
    ddir = data_dir(a.workspace)
    rows = read_transactions(ddir / "transactions.csv")
    cfg = read_json(ddir / "config.json")
    an = read_json(ddir / "analysis.json")
    if a.cmd == "summary" or an is None:
        an = summary(rows, cfg)
        write_json(ddir / "analysis.json", an)
        if a.cmd == "summary":
            print(json.dumps({"full_months": an["full_months"], "categories": len(an["categories"]), "paycheck": an["paycheck"]}, indent=1))
            return
    if a.cmd == "audit":
        doc = write_findings(ddir, "audit", audit(rows, an))
    elif a.cmd == "recurring":
        items, f = recurring(rows, cfg)
        doc = write_findings(ddir, "recurring", f, {"recurring": items})
    else:
        f, lines = spending(rows, an, cfg)
        doc = write_findings(ddir, "spending", f, {"roasts": lines})
    secure_tree(ddir)
    print(json.dumps({"agent": doc["agent"], "findings": [f"[{x['severity']}] {x['title']}" for x in doc["findings"]]}, indent=1))


if __name__ == "__main__":
    main()
