import json
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_js_engine_matches_reference_spreadsheet():
    r = subprocess.run(["node", HERE / "lvi_engine.test.js"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_golden_regenerates_from_formulas(tmp_path):
    """Rebuild the reference spreadsheet from its formulas and confirm the stored golden numbers (needs pycel)."""
    pytest.importorskip("pycel")
    import sys
    sys.path.insert(0, str(HERE))
    import lvi_reference_workbook as R
    g = json.loads((HERE / "fixtures" / "lvi_golden.json").read_text())
    res = R.evaluate(g["case"], tmp_path / "ref.xlsx")
    assert abs(res[0]["120"]["nw"] - g["results"][0]["120"]["nw"]) < 0.01


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_no_loans_hides_lvi(tmp_path):
    d = tmp_path / "money-coach-data"; d.mkdir()
    (d / "config.json").write_text(json.dumps({"loans": [], "lvi": {}}))
    subprocess.run(["node", HERE.parent / "scripts/lvi_cli.js", "--workspace", tmp_path], check=True, capture_output=True)
    assert "skipped" in json.loads((d / "findings" / "lvi.json").read_text())
