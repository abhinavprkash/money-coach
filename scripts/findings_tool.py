"""Check findings files and lock down the data folder. Agents run this after editing anything by hand.

    python3 findings_tool.py check [agent ...] [--workspace DIR]

- Validates money-coach-data/findings/<agent>.json (all of them if no agent given) against
  schemas/findings.schema.json essentials: required keys, severity values, evidence as a list, numeric amount.
- Sets owner-only permissions on everything in money-coach-data/ (files 600, folders 700).
Exit 1 if any findings file is invalid; the message says exactly what to fix.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mc_common import data_dir, secure_tree  # noqa: E402

SEVERITIES = {"critical", "serious", "warning", "verify", "opp", "good"}
LEVERS = {"caps", "split", "subs", "goal", "lvi"}


def problems_in(doc, name):
    out = []
    if not isinstance(doc, dict) or not isinstance(doc.get("findings"), list):
        return [f"{name}: top level must be an object with a 'findings' list"]
    for i, f in enumerate(doc["findings"]):
        where = f"{name} finding #{i + 1}"
        for k in ("severity", "title", "amount_at_stake", "evidence", "action"):
            if k not in f:
                out.append(f"{where}: missing '{k}'")
        if f.get("severity") not in SEVERITIES:
            out.append(f"{where}: severity must be one of {sorted(SEVERITIES)}")
        if "evidence" in f and not isinstance(f["evidence"], list):
            out.append(f"{where}: evidence must be a list of strings")
        if "amount_at_stake" in f and not isinstance(f["amount_at_stake"], (int, float)):
            out.append(f"{where}: amount_at_stake must be a number")
        if f.get("lever") and f["lever"] not in LEVERS:
            out.append(f"{where}: lever must be one of {sorted(LEVERS)}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["check"])
    ap.add_argument("agents", nargs="*")
    ap.add_argument("--workspace")
    a = ap.parse_args(argv)
    ddir = data_dir(a.workspace)
    fdir = ddir / "findings"
    files = [fdir / f"{n}.json" for n in a.agents] if a.agents else sorted(fdir.glob("*.json"))
    problems = []
    for f in files:
        if not f.exists():
            problems.append(f"{f.name}: missing")
            continue
        try:
            problems += problems_in(json.loads(f.read_text(encoding="utf-8")), f.name)
        except json.JSONDecodeError as e:
            problems.append(f"{f.name}: invalid JSON ({e})")
    fixed = secure_tree(ddir)
    print(json.dumps({"checked": [f.name for f in files], "problems": problems, "permissions_fixed": fixed}, indent=1))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
