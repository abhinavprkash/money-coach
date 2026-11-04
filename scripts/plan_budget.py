"""Budget planner (used by onboarding and the budget-planner subagent).

    python3 plan_budget.py suggest [--workspace DIR]   # JSON of detected values to PRE-FILL onboarding questions
    python3 plan_budget.py caps    [--workspace DIR]   # fill empty category caps from history x priority, then check
    python3 plan_budget.py check   [--workspace DIR]   # month-by-month budget + split feasibility -> findings/budget.json

Cap proposal (only for categories whose cap is empty; confirmed caps are never overwritten):
    cap = recent 3-month average x multiplier[priority], rounded to $25.
Multipliers live in config.json -> "cap_multipliers" (onboarding confirms them; shown with the proposal).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mc_common import data_dir, load_config, month_budget, month_label, plan_months, read_json, secure_tree, write_json  # noqa: E402

NON_VARIABLE_GROUPS = {"Housing", "Debt", "Bills", "Income", "Transfers", "Fees"}


def suggest(ddir):
    an = read_json(ddir / "analysis.json")
    rec = read_json(ddir / "findings" / "recurring.json", {}) or {}
    if not an:
        raise SystemExit("Run analyze.py summary first.")
    cats = [{"name": c["name"], "group": c["group"], "recent_avg": c["recent_avg"], "prior_avg": c["prior_avg"],
             "monthly_avg": c["monthly_avg"]} for c in an["categories"] if c["group"] not in NON_VARIABLE_GROUPS and c["monthly_avg"] > 1]
    items = rec.get("recurring", [])
    subs = [i for i in items if i["category"] == "Subscriptions"]
    bills = [i for i in items if i["category"] != "Subscriptions"]
    bills += [{"merchant": c["name"], "category": c["name"], "monthly": c["recent_avg"], "from_category": True}
              for c in an["categories"] if c["group"] in ("Housing", "Debt", "Bills") and c["name"] not in {b["category"] for b in bills} and c["recent_avg"] > 0]
    return {"paycheck": an["paycheck"], "accounts": an["accounts"], "variable_categories": cats,
            "fixed_bill_candidates": bills, "subscription_candidates": subs, "data_range": an["range"]}


def round25(x):
    return max(0.0, round(x / 25) * 25)


def fill_caps(cfg, an):
    mult = cfg.get("cap_multipliers")
    if not mult:
        raise SystemExit("config.cap_multipliers is missing (onboarding: spending-priorities). Example: "
                         '{"protect": 1.0, "normal": 0.85, "cut": 0.5}')
    hist = {c["name"]: c for c in an["categories"]}
    changed = []
    for c in cfg["categories"]:
        if c.get("cap") in (None, ""):
            h = hist.get(c["name"], {})
            base = h.get("recent_avg", c.get("history_monthly", 0)) or 0
            c["history_monthly"] = base
            c["cap"] = round25(base * float(mult[c.get("priority", "normal")]))
            changed.append({"category": c["name"], "history": base, "priority": c.get("priority", "normal"), "proposed_cap": c["cap"]})
    return changed


def check(cfg):
    rows, findings = [], []
    for ym in plan_months(cfg):
        b = month_budget(cfg, ym)
        sav_pp = sum(float(a["per_paycheck"]) for a in cfg["split"]["accounts"] if a.get("kind") == "savings")
        b["savings_slice_per_paycheck"] = sav_pp
        b["split_gap_per_paycheck"] = sav_pp - b["savings_supported_per_paycheck"]
        rows.append(b)
    worst = max(rows, key=lambda r: r["split_gap_per_paycheck"])
    if worst["split_gap_per_paycheck"] > 50:
        g = worst["split_gap_per_paycheck"]
        findings.append({"severity": "critical", "title": f"Your savings split is ${g:,.0f}/paycheck more than the budget leaves",
                         "amount_at_stake": round(g * worst["paychecks"], 2),
                         "evidence": [f"{month_label(worst['month'])}: budget supports ${worst['savings_supported_per_paycheck']:,.0f}/paycheck, split sends ${worst['savings_slice_per_paycheck']:,.0f}"],
                         "action": "Lower the savings slice to what's supported, or cut caps by the gap. Otherwise you'll end up withdrawing it.",
                         "lever": "split"})
    neg = [r for r in rows if r["buffer"] < 0]
    if neg:
        findings.append({"severity": "critical", "title": f"Budget is in deficit in {len(neg)} month(s)",
                         "amount_at_stake": round(-sum(r["buffer"] for r in neg), 2),
                         "evidence": [f"{month_label(r['month'])}: {r['buffer']:,.0f}" for r in neg], "action": "Cut caps or the savings split until every month is ≥ $0.", "lever": "caps"})
    thin = [r for r in rows if 0 <= r["buffer"] < 50]
    if thin:
        findings.append({"severity": "warning", "title": f"{len(thin)} month(s) have under $50 of buffer", "amount_at_stake": 0,
                         "evidence": [f"{month_label(r['month'])}: ${r['buffer']:,.0f}" for r in thin], "action": "Leave a little slack for surprises.", "lever": "caps"})
    return rows, findings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["suggest", "caps", "check"])
    ap.add_argument("--workspace")
    a = ap.parse_args(argv)
    ddir = data_dir(a.workspace)
    if a.cmd == "suggest":
        print(json.dumps(suggest(ddir), indent=1))
        return
    if a.cmd == "caps":
        cfg = read_json(ddir / "config.json")
        changed = fill_caps(cfg, read_json(ddir / "analysis.json"))
        write_json(ddir / "config.json", cfg)
        print(json.dumps({"proposed_caps": changed}, indent=1))
    cfg = load_config(ddir)
    rows, findings = check(cfg)
    write_json(ddir / "findings" / "budget.json", {"agent": "budget", "months": rows, "findings": findings})
    secure_tree(ddir)
    print(json.dumps({"months": [{"month": r["month"], "income": round(r["income"]), "buffer": round(r["buffer"]),
                                  "supported_savings_per_paycheck": round(r["savings_supported_per_paycheck"])} for r in rows],
                      "findings": [f["title"] for f in findings]}, indent=1))


if __name__ == "__main__":
    main()
