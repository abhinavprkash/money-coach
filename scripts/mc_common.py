"""Shared helpers for money-coach scripts: workspace paths, config loading/validation, month math.

Nothing personal lives here. Every number comes from the user's workspace:
    <workspace>/money-coach-data/config.json        (written by onboarding)
    <workspace>/money-coach-data/transactions.csv   (written by data-ingest)
"""
import csv
import json
import os
from datetime import date
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
PAYCHECKS_PER_MONTH = {"weekly": 52 / 12, "biweekly": 26 / 12, "semimonthly": 2, "monthly": 1}
TX_FIELDS = ["date", "account", "institution", "description", "merchant", "amount", "category", "group", "kind", "source"]
KINDS = {"income", "expense", "transfer", "investment", "financing"}


class ConfigError(ValueError):
    """Raised when config.json is missing something the build needs. Never silently defaulted."""


def data_dir(workspace=None):
    ws = Path(workspace or os.environ.get("MONEY_COACH_HOME") or Path.cwd())
    return ws / "money-coach-data" if ws.name != "money-coach-data" else ws


def ensure_dir(p):
    p = Path(p)
    p.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(p, 0o700)
    except OSError:
        pass
    return p


def write_private(path, text):
    path = Path(path)
    ensure_dir(path.parent)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def write_json(path, obj):
    write_private(path, json.dumps(obj, indent=1, ensure_ascii=False))


def read_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8") or "null")


# ---------- transactions ----------
def read_transactions(path):
    rows = []
    with Path(path).open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            r["amount"] = float(r["amount"])
            rows.append(r)
    return rows


def write_transactions(path, rows):
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=TX_FIELDS, extrasaction="ignore")
    w.writeheader()
    for r in sorted(rows, key=lambda x: (x["date"], x.get("account", ""), x.get("description", ""))):
        w.writerow({**r, "amount": f"{float(r['amount']):.2f}"})
    write_private(path, buf.getvalue())


# ---------- months ----------
def month_add(ym, n):
    y, m = map(int, ym.split("-"))
    m += n
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return f"{y:04d}-{m:02d}"


def month_label(ym):
    y, m = map(int, ym.split("-"))
    return date(y, m, 1).strftime("%b %Y")


def month_name(ym):
    y, m = map(int, ym.split("-"))
    return date(y, m, 1).strftime("%B")


def months_between(start_ym, end_ym):
    out, cur = [], start_ym
    while cur <= end_ym:
        out.append(cur)
        cur = month_add(cur, 1)
    return out


def active(item, ym):
    """Is a bill/subscription active in month ym? Uses optional 'start'/'end' (YYYY-MM, inclusive)."""
    return (not item.get("start") or item["start"] <= ym) and (not item.get("end") or ym <= item["end"])


# ---------- config ----------
REQUIRED = {
    "income.frequency": lambda c: c["income"]["frequency"] in PAYCHECKS_PER_MONTH,
    "income.take_home_per_paycheck": lambda c: float(c["income"]["take_home_per_paycheck"]) > 0,
    "plan.start_month": lambda c: len(c["plan"]["start_month"]) == 7,
    "plan.months": lambda c: int(c["plan"]["months"]) >= 1,
    "split.accounts": lambda c: isinstance(c["split"]["accounts"], list),
    "split.remainder": lambda c: bool(c["split"]["remainder"]),
    "fixed_bills": lambda c: isinstance(c["fixed_bills"], list),
    "subscriptions": lambda c: isinstance(c["subscriptions"], list),
    "categories": lambda c: isinstance(c["categories"], list) and len(c["categories"]) > 0,
    "cards": lambda c: isinstance(c["cards"], list),
    "goal.target": lambda c: float(c["goal"]["target"]) > 0,
    "goal.deadline": lambda c: len(c["goal"]["deadline"]) == 10,
    "tax.federal_marginal": lambda c: 0 <= float(c["tax"]["federal_marginal"]) < 1,
    "tax.state_marginal": lambda c: 0 <= float(c["tax"]["state_marginal"]) < 1,
    "tone": lambda c: c["tone"] in ("gentle", "honest", "savage"),
}
SECTION_DOC = {
    "income": "income.md", "plan": "income.md", "split": "bank-split.md", "fixed_bills": "fixed-bills.md",
    "subscriptions": "subscriptions.md", "categories": "spending-priorities.md", "cards": "cards-and-tone.md",
    "goal": "savings-goal.md", "tax": "taxes.md", "tone": "cards-and-tone.md", "loans": "loans.md",
    "investments": "investments.md",
}


def validate_config(cfg):
    problems = []
    for key, check in REQUIRED.items():
        try:
            ok = check(cfg)
        except (KeyError, TypeError, ValueError):
            ok = False
        if not ok:
            sec = key.split(".")[0]
            problems.append(f"{key} (re-run: /money-review onboard {sec}; see docs/onboarding/{SECTION_DOC.get(sec, 'income.md')})")
    names = {a["name"] for a in cfg.get("split", {}).get("accounts", [])} | {cfg.get("split", {}).get("remainder")}
    for b in cfg.get("fixed_bills", []):
        for f in ("name", "paid_from", "amount"):
            if b.get(f) in (None, ""):
                problems.append(f"fixed_bills[{b.get('name', '?')}].{f}")
    for c in cfg.get("categories", []):
        if c.get("cap") is None:
            problems.append(f"categories[{c.get('name', '?')}].cap")
    for l in cfg.get("loans", []):
        for f in ("name", "currency", "outstanding", "rate", "type", "current_payment"):
            if l.get(f) in (None, ""):
                problems.append(f"loans[{l.get('name', '?')}].{f} (see docs/onboarding/loans.md)")
    for b in cfg.get("fixed_bills", []):
        if b.get("paid_from") and b["paid_from"] not in names and b["paid_from"] not in cfg.get("cards", []):
            problems.append(f"fixed_bills[{b['name']}].paid_from '{b['paid_from']}' is not a split account or card")
    if problems:
        raise ConfigError("config.json is incomplete. Missing or invalid:\n  - " + "\n  - ".join(problems))
    return cfg


def load_config(ddir, validate=True):
    path = Path(ddir) / "config.json"
    if not path.exists():
        raise ConfigError(f"No config at {path}. Run /money-review to onboard first.")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    return validate_config(cfg) if validate else cfg


def ppm(cfg):
    return PAYCHECKS_PER_MONTH[cfg["income"]["frequency"]]


def plan_months(cfg):
    start = cfg["plan"]["start_month"]
    return [month_add(start, i) for i in range(int(cfg["plan"]["months"]))]


def take_home(cfg, ym):
    """Take-home per paycheck in month ym, applying dated changes (income.changes: [{from, take_home_per_paycheck}])."""
    v = float(cfg["income"]["take_home_per_paycheck"])
    for ch in sorted(cfg["income"].get("changes", []), key=lambda x: x["from"]):
        if ch["from"] <= ym:
            v = float(ch["take_home_per_paycheck"])
    return v


def extra_pay(cfg, ym):
    return [e for e in cfg["income"].get("extra_pay", []) if e.get("month") == ym and e.get("counted", True)]


def month_budget(cfg, ym):
    """The monthly budget arithmetic shared by the goal model, the planner and the tests.

    Bills accounts' leftover (after the fixed bills paid from them) becomes the sinking fund.
    Savings-kind split accounts are the savings line. The remainder account gets the rest.
    """
    p = ppm(cfg)
    per = take_home(cfg, ym)
    extras = extra_pay(cfg, ym)
    extra_total = sum(float(e["amount_after_tax"]) for e in extras)
    income = per * p + extra_total
    accts = cfg["split"]["accounts"]
    split_m = {a["name"]: float(a["per_paycheck"]) * p for a in accts}
    for e in extras:  # windfalls route to the chosen account (default: first savings account)
        dest = e.get("route_to") or next((a["name"] for a in accts if a.get("kind") == "savings"), cfg["split"]["remainder"])
        split_m[dest] = split_m.get(dest, 0) + float(e["amount_after_tax"])
    remainder_m = income - sum(split_m.values())
    split_m[cfg["split"]["remainder"]] = split_m.get(cfg["split"]["remainder"], 0) + remainder_m
    bills = [b for b in cfg["fixed_bills"] if active(b, ym)]
    fixed = sum(float(b["amount"]) for b in bills)
    subs = sum(float(s["amount"]) for s in cfg["subscriptions"] if s.get("active") and active(s, ym))
    variable = sum(float(c["cap"]) for c in cfg["categories"])
    kinds = {a["name"]: a.get("kind", "spending") for a in accts}
    savings = sum(v for n, v in split_m.items() if kinds.get(n) == "savings")
    bills_accts = [n for n, k in kinds.items() if k == "bills"]
    sinking = sum(split_m[n] for n in bills_accts) - sum(float(b["amount"]) for b in bills if b["paid_from"] in bills_accts)
    sinking = max(0.0, sinking)
    out = fixed + subs + variable + savings + sinking
    return {"month": ym, "per_paycheck": per, "paychecks": p, "income": income, "extra": extra_total, "split": split_m,
            "fixed": fixed, "subs": subs, "variable": variable, "savings": savings, "sinking": sinking,
            "total_out": out, "buffer": income - out,
            "spend_need_per_paycheck": (fixed + subs + variable + sinking) / p,
            "savings_supported_per_paycheck": per - (fixed + subs + variable + sinking) / p}
