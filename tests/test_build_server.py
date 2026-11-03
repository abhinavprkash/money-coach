import http.client
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from conftest import PY, ROOT
from openpyxl import load_workbook


def test_build_outputs(demo_ws):
    html = (demo_ws / "site" / "index.html").read_text()
    assert "/*__PLAN__*/" not in html and "Loan vs Invest" in html
    wb = load_workbook(demo_ws / "output" / "Budget.xlsx")
    assert wb.sheetnames[:2] == ["Goal", "Guide"] and "Nov 2026" in wb.sheetnames and wb.sheetnames[-1] == "Lists"
    guide = [c.value for c in wb["Guide"]["A"] if c.value]
    assert len(guide) >= 11                                           # title + 10 onboarding docs
    assert oct(os.stat(demo_ws / "output" / "Budget.xlsx").st_mode)[-3:] == "600"


def test_build_refuses_incomplete_config(tmp_path):
    d = tmp_path / "money-coach-data"
    d.mkdir()
    subprocess.run([PY, ROOT / "scripts/config_tool.py", "init", "--workspace", tmp_path], check=True)
    r = subprocess.run([PY, ROOT / "app/build.py", "--workspace", tmp_path], capture_output=True, text=True)
    assert r.returncode == 2 and "income.take_home_per_paycheck" in r.stderr


def test_workbook_formulas_evaluate(demo_ws):
    pycel = pytest.importorskip("pycel")
    xl = pycel.ExcelCompiler(filename=str(demo_ws / "output" / "Budget.xlsx"))
    wb = load_workbook(demo_ws / "output" / "Budget.xlsx")
    ws = wb["Nov 2026"]
    errs = []
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value, str) and c.value.startswith("="):
                v = xl.evaluate(f"'Nov 2026'!{c.coordinate}")
                if isinstance(v, str) and v.startswith("#"):
                    errs.append(c.coordinate)
    assert not errs


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


@pytest.fixture()
def server(demo_ws):
    port = free_port()
    p = subprocess.Popen([PY, ROOT / "app/server.py", "--workspace", demo_ws.parent, "--port", str(port)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), 0.1).close(); break
        except OSError:
            time.sleep(0.1)
    yield port
    p.terminate(); p.wait(5)


def req(port, method, path, body=None, headers=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    h = {"Host": f"localhost:{port}", **(headers or {})}
    c.request(method, path, body=body, headers=h)
    r = c.getresponse()
    return r.status, r.read()


def test_server_security_and_saving(server, demo_ws):
    port = server
    assert req(port, "GET", "/api/state")[0] == 200
    assert req(port, "GET", "/api/state", headers={"Host": "evil.example"})[0] == 403
    payload = json.dumps({"expenses": [{"month": "2026-11", "date": "2026-11-05", "desc": "Test grocer", "cat": "Groceries", "amt": 12.5, "card": "Amex Gold", "notes": ""}],
                          "settings": {"seeded": True, "months": {}}})
    assert req(port, "PUT", "/api/state", payload, {"Content-Type": "application/json", "Origin": "http://evil.example"})[0] == 403
    assert req(port, "PUT", "/api/state", payload, {"Content-Type": "text/plain"})[0] == 415
    assert req(port, "PUT", "/api/state", payload, {"Content-Type": "application/json", "Origin": f"http://localhost:{port}"})[0] == 200
    csv_text = (demo_ws / "expenses.csv").read_text()
    assert "Test grocer" in csv_text and oct(os.stat(demo_ws / "expenses.csv").st_mode)[-3:] == "600"
    assert req(port, "GET", "/docs/onboarding/loans.md")[0] == 200
    assert req(port, "GET", "/docs/../app/server.py")[0] in (403, 404)
    st, body = req(port, "POST", "/api/export-excel", b"", {"Origin": f"http://localhost:{port}"})
    assert st == 200 and json.loads(body)["ok"]
    wb = load_workbook(demo_ws / "output" / "Budget.xlsx")
    assert wb["Nov 2026"]["K5"].value == "Test grocer"
