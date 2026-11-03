"""Build the dashboard (site/index.html) and the Excel workbook from the user's workspace.

    python3 app/build.py [--workspace DIR] [--no-excel]

Reads   money-coach-data/config.json, findings/*.json, expenses.csv + settings.json (saved by the dashboard)
Writes  money-coach-data/site/index.html, money-coach-data/output/Budget.xlsx
Fails loudly (exit 2) if config.json is incomplete. There are no hidden defaults.
"""
import argparse
import csv
import json
import os
import sys
from datetime import date
from pathlib import Path

APP = Path(__file__).resolve().parent
ROOT = APP.parent
sys.path.insert(0, str(ROOT / "scripts"))
from mc_common import (ConfigError, active, data_dir, ensure_dir, load_config, month_label, month_name,  # noqa: E402
                       plan_months, ppm, read_json, take_home)
import roast as R  # noqa: E402

DOCS = {"income": "income.md", "split": "bank-split.md", "fixed": "fixed-bills.md", "subs": "subscriptions.md",
        "variable": "spending-priorities.md", "goal": "savings-goal.md", "loans": "loans.md", "investments": "investments.md",
        "tax": "taxes.md", "cards": "cards-and-tone.md"}


def load_findings(ddir):
    out = {}
    for f in sorted((ddir / "findings").glob("*.json")) if (ddir / "findings").exists() else []:
        out[f.stem] = read_json(f)
    return out


def sub_roast(name, findings):
    for f in (findings.get("recurring") or {}).get("findings", []):
        if name.lower() in f["title"].lower():
            return f["title"]
    return ""


def plan_data(cfg, findings, an):
    tone = cfg["tone"]
    hist = {c["name"]: c for c in (an or {}).get("categories", [])}
    roasts = (findings.get("spending") or {}).get("roasts", {})
    months = []
    for ym in plan_months(cfg):
        months.append({"key": ym, "label": month_label(ym), "name": month_name(ym), "per_paycheck": take_home(cfg, ym),
                       "paychecks": ppm(cfg),
                       "extra": [{"label": e["label"], "amount": float(e["amount_after_tax"]), "route_to": e.get("route_to"),
                                  "confirmed": bool(e.get("confirmed"))} for e in cfg["income"].get("extra_pay", []) if e.get("month") == ym],
                       "fixed_active": [b["name"] for b in cfg["fixed_bills"] if active(b, ym)],
                       "subs_active": [s["name"] for s in cfg["subscriptions"] if active(s, ym)]})
    cats = []
    for c in cfg["categories"]:
        h = hist.get(c["name"])
        line = roasts.get(c["name"]) or (R.category_line(h, c.get("priority", "normal"), tone) if h else "")
        cats.append({**c, "cap": float(c["cap"]), "roast": line, "history": h["recent_avg"] if h else None})
    all_f = []
    for agent, doc in findings.items():
        for f in (doc or {}).get("findings", []):
            all_f.append({**f, "agent": agent})
    order = {"critical": 0, "serious": 1, "warning": 2, "verify": 3, "opp": 4, "good": 5}
    all_f.sort(key=lambda f: (order.get(f["severity"], 9), -float(f.get("amount_at_stake") or 0)))
    goal = findings.get("goal") or {}
    return {
        "generated": date.today().isoformat(), "currency": cfg.get("currency", "USD"), "tone": tone, "months": months,
        "split": cfg["split"], "fixed": [{**b, "amount": float(b["amount"]), "roast": b.get("note", "")} for b in cfg["fixed_bills"]],
        "subs": [{**s, "amount": float(s["amount"]), "roast": sub_roast(s["name"], findings)} for s in cfg["subscriptions"]],
        "categories": cats, "cards": cfg["cards"], "payroll": cfg.get("payroll", []),
        "extraCats": ["Subscriptions", "Sinking fund spend"],
        "goal": {"target": float(cfg["goal"]["target"]), "deadline": cfg["goal"]["deadline"], "start": goal.get("start"),
                 "checkpoints": goal.get("checkpoints", []), "projected": goal.get("projected")},
        "windfalls": [{"label": e["label"], "month": e["month"], "amount": float(e["amount_after_tax"])} for e in cfg["income"].get("extra_pay", [])],
        "findings": all_f,
        "lvi": {"loans": cfg.get("loans", []), "investments": cfg.get("investments", []), "lvi": cfg.get("lvi", {})} if cfg.get("loans") else None,
        "docs": {k: f"/docs/onboarding/{v}" for k, v in DOCS.items()},
    }


def build_site(ddir, plan):
    tpl = (APP / "site" / "template.html").read_text(encoding="utf-8")
    js = "\n".join((APP / "site" / f).read_text(encoding="utf-8") for f in ("lvi_engine.js", "lvi_scenarios.js", "lvi_view.js"))
    html = tpl.replace("/*__PLAN__*/null", json.dumps(plan)).replace("/*__LVI_CODE__*/", js if plan["lvi"] else "")
    out = ensure_dir(ddir / "site") / "index.html"
    out.write_text(html, encoding="utf-8")
    os.chmod(out, 0o600)
    return out


def load_saved(ddir):
    exp, settings = None, read_json(ddir / "settings.json", {}) or {}
    f = ddir / "expenses.csv"
    if f.exists():
        exp = {}
        with f.open(newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                exp.setdefault(r["month"], []).append(r)
    return exp, settings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace")
    ap.add_argument("--no-excel", action="store_true")
    a = ap.parse_args(argv)
    ddir = data_dir(a.workspace)
    try:
        cfg = load_config(ddir)
    except ConfigError as e:
        print(f"Can't build yet:\n{e}", file=sys.stderr)
        sys.exit(2)
    findings = load_findings(ddir)
    plan = plan_data(cfg, findings, read_json(ddir / "analysis.json"))
    site = build_site(ddir, plan)
    print("wrote", site)
    if not a.no_excel:
        import workbook
        print("wrote", workbook.build(ddir, cfg, plan, *load_saved(ddir)))


if __name__ == "__main__":
    sys.path.insert(0, str(APP))
    main()
