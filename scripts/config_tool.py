"""Read/write money-coach-data/config.json safely during onboarding.

    python3 config_tool.py init                       [--workspace DIR]  # empty skeleton (every value null/[])
    python3 config_tool.py set  <dotted.key> '<json>' [--workspace DIR]  # e.g. set income.frequency '"semimonthly"'
    python3 config_tool.py append <dotted.key> '<json>'                  # add an item to a list, e.g. loans
    python3 config_tool.py get  [<dotted.key>]                            # print a value (or the whole config)
    python3 config_tool.py missing                                        # what onboarding still has to ask (exit 1 if any)
    python3 config_tool.py recap                                          # plain-English summary for the user to confirm

Values are JSON, so strings need quotes: '"Chase Checking"'. Nothing is ever filled in automatically.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mc_common import ConfigError, data_dir, ensure_dir, read_json, secure_tree, validate_config, write_json  # noqa: E402

SKELETON = {
    "version": 1, "currency": "USD", "tone": None,
    "plan": {"start_month": None, "months": None},
    "income": {"frequency": None, "take_home_per_paycheck": None, "changes": [], "extra_pay": []},
    "split": {"accounts": [], "remainder": None, "remainder_job": None},
    "cards": [], "fixed_bills": [], "subscriptions": [],
    "cap_multipliers": None, "categories": [], "payroll": [],
    "goal": {"target": None, "deadline": None, "counts_retirement": None, "balances": [], "card_debt": None,
             "sinking_unspent_pct": None, "expected_annual_return": None},
    "tax": {"federal_marginal": None, "state_marginal": None, "payroll_tax_exempt": None, "hsa_state_taxed": None},
    "loans": [], "investments": [], "lvi": {},
}


def walk(cfg, key, create=False):
    parts = key.split(".")
    cur = cfg
    for p in parts[:-1]:
        idx = int(p) if p.isdigit() else p
        if isinstance(cur, dict) and idx not in cur and create:
            cur[idx] = {}
        cur = cur[idx]
    last = parts[-1]
    return cur, int(last) if last.isdigit() else last


def recap(c):
    m = lambda x: "?" if x is None else f"${float(x):,.2f}"
    L = []
    i = c.get("income", {})
    L.append(f"Pay: {m(i.get('take_home_per_paycheck'))} per paycheck, {i.get('frequency') or '?'}; plan {c['plan'].get('months') or '?'} months from {c['plan'].get('start_month') or '?'}")
    for e in i.get("extra_pay", []):
        L.append(f"  Extra pay: {e.get('label')} {m(e.get('amount_after_tax'))} in {e.get('month')} ({'confirmed' if e.get('confirmed') else 'unconfirmed'})")
    s = c.get("split", {})
    L.append("Split: " + ", ".join(f"{a['name']} ({a.get('kind')}) {m(a.get('per_paycheck'))}" for a in s.get("accounts", [])) + f"; rest to {s.get('remainder') or '?'}")
    L.append(f"Fixed bills: {len(c.get('fixed_bills', []))} totaling {m(sum(float(b.get('amount') or 0) for b in c.get('fixed_bills', [])))}/mo")
    act = [x for x in c.get("subscriptions", []) if x.get("active")]
    L.append(f"Subscriptions: {len(act)} active ({m(sum(float(x.get('amount') or 0) for x in act))}/mo), {len(c.get('subscriptions', [])) - len(act)} to cancel")
    pr = {p: [x["name"] for x in c.get("categories", []) if x.get("priority") == p] for p in ("protect", "normal", "cut")}
    L.append(f"Protect: {', '.join(pr['protect']) or '-'} | Cut: {', '.join(pr['cut']) or '-'}")
    g = c.get("goal", {})
    L.append(f"Goal: {m(g.get('target'))} by {g.get('deadline') or '?'} ({'incl.' if g.get('counts_retirement') else 'excl.'} retirement)")
    L.append(f"Loans: {', '.join(l['name'] for l in c.get('loans', [])) or 'none'} | Investments: {', '.join(x['name'] for x in c.get('investments', [])) or 'none'}")
    t = c.get("tax", {})
    L.append(f"Tax: federal {t.get('federal_marginal')}, state {t.get('state_marginal')} | Tone: {c.get('tone') or '?'} | Cards: {', '.join(c.get('cards', [])) or '-'}")
    return "\n".join(L)


def main(argv=None):
    try:
        _main(argv)
    finally:
        secure_tree(data_dir(_ws(argv)))


def _ws(argv):
    args = list(argv if argv is not None else sys.argv[1:])
    return args[args.index("--workspace") + 1] if "--workspace" in args else None


def _main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["init", "set", "append", "get", "missing", "recap"])
    ap.add_argument("key", nargs="?")
    ap.add_argument("value", nargs="?")
    ap.add_argument("--workspace")
    a = ap.parse_args(argv)
    ddir = ensure_dir(data_dir(a.workspace))
    path = ddir / "config.json"
    cfg = read_json(path)
    if a.cmd == "init":
        if cfg is not None:
            print(f"{path} already exists; not overwriting.")
            return
        write_json(path, SKELETON)
        print(f"created {path}")
        return
    if cfg is None:
        sys.exit(f"No {path}. Run: config_tool.py init")
    if a.cmd in ("set", "append"):
        val = json.loads(a.value)
        parent, k = walk(cfg, a.key, create=True)
        if a.cmd == "set":
            parent[k] = val
        else:
            parent.setdefault(k, []).append(val)
        write_json(path, cfg)
        print(f"{a.key} updated")
    elif a.cmd == "get":
        if a.key:
            parent, k = walk(cfg, a.key)
            print(json.dumps(parent[k], indent=1))
        else:
            print(json.dumps(cfg, indent=1))
    elif a.cmd == "missing":
        try:
            validate_config(cfg)
            print("complete")
        except ConfigError as e:
            print(e)
            sys.exit(1)
    else:
        print(recap(cfg))


if __name__ == "__main__":
    main()
