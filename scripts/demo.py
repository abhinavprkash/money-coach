"""Try money-coach on fictional data in ~10 seconds, with no AI calls and none of your data.

    python3 scripts/demo.py [--workspace ./money-coach-demo] [--open] [--port 8765]

Builds a complete demo workspace from examples/demo (five fictional bank exports + a finished onboarding),
runs the same scripts the subagents use, builds the dashboard and workbook, and with --open serves it locally.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "examples" / "demo"
ACCOUNTS = (("chase_checking", "Chase Checking"), ("ally_savings", "Ally Savings"), ("bills_checking", "Bills Checking"),
            ("chase_sapphire", "Chase Sapphire"), ("amex_gold", "Amex Gold"))


def step(label, *cmd):
    print(f"  · {label}")
    subprocess.run(list(map(str, cmd)), check=True, stdout=subprocess.DEVNULL)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default="money-coach-demo")
    ap.add_argument("--open", action="store_true", help="start the local dashboard and open it")
    ap.add_argument("--port", default="8765")
    a = ap.parse_args(argv)
    ws = Path(a.workspace).resolve()
    data = ws / "money-coach-data"
    if data.exists():
        shutil.rmtree(data)
    py = sys.executable
    print(f"Building the money-coach demo (fictional data) in {ws}")
    for f, acct in ACCOUNTS:
        step(f"import {f}.csv", py, ROOT / "scripts/ingest_csv.py", DEMO / "bank" / f"{f}.csv", "--account", acct, "--workspace", ws, "--append")
    step("summary", py, ROOT / "scripts/analyze.py", "summary", "--workspace", ws)
    shutil.copy(DEMO / "config.json", data / "config.json")
    for c in ("audit", "recurring", "spending"):
        step(f"{c} findings", py, ROOT / "scripts/analyze.py", c, "--workspace", ws)
    step("budget caps + split check", py, ROOT / "scripts/plan_budget.py", "caps", "--workspace", ws)
    step("goal checkpoints", py, ROOT / "scripts/goal.py", "--workspace", ws)
    if shutil.which("node"):
        step("loan vs invest", "node", ROOT / "scripts/lvi_cli.js", "--workspace", ws, "--stress")
    step("dashboard + Excel", py, ROOT / "app/build.py", "--workspace", ws)
    print(f"\nDone. Workbook: {data / 'output' / 'Budget.xlsx'}")
    if a.open:
        print(f"Dashboard: http://localhost:{a.port}  (Ctrl+C to stop)")
        subprocess.run([py, ROOT / "app/server.py", "--workspace", ws, "--port", a.port, "--open"])
    else:
        print(f"Open it: python3 {ROOT / 'app/server.py'} --workspace {ws} --open")


if __name__ == "__main__":
    main()
