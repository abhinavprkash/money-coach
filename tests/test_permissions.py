import json
import os
import stat
import subprocess

from conftest import PY, ROOT


def mode(p):
    return stat.S_IMODE(os.stat(p).st_mode)


def test_everything_private_after_build(demo_ws):
    loose = [str(p) for p in [demo_ws, *demo_ws.rglob("*")] if mode(p) != (0o700 if p.is_dir() else 0o600)]
    assert not loose, loose[:5]


def test_findings_tool_fixes_agent_written_files(tmp_path, demo_ws):
    # simulate an agent using a Write/Edit tool (default umask) and a scratch folder
    ws = tmp_path / "w"
    d = ws / "money-coach-data"
    (d / "findings").mkdir(parents=True)
    (d / ".scratch").mkdir()
    f = d / "findings" / "audit.json"
    f.write_text(json.dumps({"agent": "audit", "findings": [{"severity": "critical", "title": "t", "amount_at_stake": 1, "evidence": ["e"], "action": "a"}]}))
    os.chmod(f, 0o644); os.chmod(d / ".scratch", 0o755)
    r = subprocess.run([PY, ROOT / "scripts/findings_tool.py", "check", "--workspace", ws], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout
    assert mode(f) == 0o600 and mode(d / ".scratch") == 0o700


def test_findings_tool_rejects_bad_findings(tmp_path):
    d = tmp_path / "money-coach-data" / "findings"
    d.mkdir(parents=True)
    (d / "spending.json").write_text(json.dumps({"findings": [{"severity": "meh", "title": "t", "evidence": "not a list"}]}))
    r = subprocess.run([PY, ROOT / "scripts/findings_tool.py", "check", "--workspace", tmp_path], capture_output=True, text=True)
    out = json.loads(r.stdout)
    assert r.returncode == 1 and any("severity" in p for p in out["problems"]) and any("evidence" in p for p in out["problems"])
