import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "app"))
PY = sys.executable
DEMO = ROOT / "examples" / "demo"


def run(*args, cwd=ROOT):
    return subprocess.run([PY, *map(str, args)], cwd=cwd, check=True, capture_output=True, text=True).stdout


@pytest.fixture(scope="session")
def demo_ws(tmp_path_factory):
    """A fully processed demo workspace: ingest -> analyze -> onboarding config -> plan -> goal -> lvi -> build."""
    ws = tmp_path_factory.mktemp("demo")
    for f, acct in (("chase_checking", "Chase Checking"), ("chase_sapphire", "Chase Sapphire"), ("amex_gold", "Amex Gold")):
        run(ROOT / "scripts/ingest_csv.py", DEMO / "bank" / f"{f}.csv", "--account", acct, "--workspace", ws, "--append")
    run(ROOT / "scripts/analyze.py", "summary", "--workspace", ws)
    shutil.copy(DEMO / "config.json", ws / "money-coach-data" / "config.json")
    for c in ("audit", "recurring", "spending"):
        run(ROOT / "scripts/analyze.py", c, "--workspace", ws)
    run(ROOT / "scripts/plan_budget.py", "caps", "--workspace", ws)
    run(ROOT / "scripts/goal.py", "--workspace", ws)
    if shutil.which("node"):
        subprocess.run(["node", ROOT / "scripts/lvi_cli.js", "--workspace", ws, "--stress"], check=True, capture_output=True)
    run(ROOT / "app/build.py", "--workspace", ws)
    return ws / "money-coach-data"


def load(p):
    return json.loads(Path(p).read_text())
