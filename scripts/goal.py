"""Goal planner: month-end checkpoints toward the savings goal.

    python3 goal.py [--workspace DIR]   -> findings/goal.json

Counts, per plan month (all from config.json, nothing assumed):
  * savings split + windfalls routed to savings          (split.accounts kind=savings, income.extra_pay)
  * sinking-fund leftover x goal.sinking_unspent_pct     (0 if not set: conservative)
  * payroll contributions with counts_toward_goal=true   (only if goal.counts_retirement)
  * growth at goal.expected_annual_return                (0 if not set)
Start = sum of goal.balances (retirement ones only if counts_retirement) - goal.card_debt.
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mc_common import data_dir, load_config, month_budget, month_label, plan_months, write_json  # noqa: E402


def project(cfg):
    g = cfg["goal"]
    counts_ret = bool(g.get("counts_retirement"))
    start = sum(float(b["amount"]) for b in g.get("balances", []) if counts_ret or not b.get("retirement")) - float(g.get("card_debt", 0))
    r = float(g.get("expected_annual_return", 0)) / 12
    unspent = float(g.get("sinking_unspent_pct", 0))
    deadline = g["deadline"][:7]
    bal, pts, parts = start, [], {}
    add = lambda k, v: parts.__setitem__(k, parts.get(k, 0) + v)
    for ym in plan_months(cfg):
        if ym > deadline:
            break
        b = month_budget(cfg, ym)
        c = b["savings"] + b["sinking"] * unspent
        add("Savings split + windfalls", b["savings"]); add("Unspent sinking fund", b["sinking"] * unspent)
        if counts_ret:
            for p in cfg.get("payroll", []):
                if p.get("counts_toward_goal") and (not p.get("from") or p["from"] <= ym):
                    c += float(p["monthly"]); add(p["label"], float(p["monthly"]))
        growth = bal * r
        add("Market return", growth)
        bal += growth + c
        pts.append({"month": ym, "label": f"End of {month_label(ym)}", "plan_balance": round(bal, 2)})
    target = float(g["target"])
    n = max(1, len(pts))
    out = {"start": round(start, 2), "target": target, "deadline": g["deadline"], "checkpoints": pts,
           "projected": round(bal, 2), "gap": round(target - bal, 2), "required_per_month": round((target - start) / n, 2),
           "parts": {k: round(v, 2) for k, v in parts.items() if abs(v) > 0.005}}
    pct = bal / target if target else 0
    sev = "good" if pct >= 1 else "warning" if pct >= 0.9 else "serious" if pct >= 0.75 else "critical"
    title = (f"On track: projected ${bal:,.0f} vs ${target:,.0f} by {g['deadline']}" if pct >= 1 else
             f"Projected ${bal:,.0f} by {g['deadline']}: ${target - bal:,.0f} short ({pct*100:.0f}%)")
    ev = [f"Start ${start:,.0f}", f"Needs ${out['required_per_month']:,.0f}/mo; plan delivers ${(bal - start)/n:,.0f}/mo"]
    if not g.get("sinking_unspent_pct"):
        ev.append("Sinking fund counted as fully spent (set goal.sinking_unspent_pct to count leftovers)")
    for e in cfg["income"].get("extra_pay", []):
        if not e.get("confirmed"):
            ev.append(f"Unconfirmed windfall counted: {e['label']} ${float(e['amount_after_tax']):,.0f} in {e['month']}")
    out["findings"] = [{"severity": sev, "title": title, "amount_at_stake": round(max(0, target - bal), 2), "evidence": ev,
                        "action": "Pull levers on the dashboard until the line crosses the target; confirm windfall dates.", "lever": "goal"}]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace")
    a = ap.parse_args(argv)
    ddir = data_dir(a.workspace)
    res = project(load_config(ddir))
    res.update({"agent": "goal", "as_of": date.today().isoformat()})
    write_json(ddir / "findings" / "goal.json", res)
    print(json.dumps({k: res[k] for k in ("start", "projected", "target", "gap", "checkpoints")}, indent=1))


if __name__ == "__main__":
    main()
