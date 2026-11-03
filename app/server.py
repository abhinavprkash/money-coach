"""money-coach local server: serves your dashboard and saves edits to files in your workspace.

    python3 app/server.py --workspace DIR [--open] [--port 8765]

Files (the single source of truth for the dashboard and the Excel build), in DIR/money-coach-data/:
    expenses.csv    one row per expense: month,date,description,category,amount,card,notes
    settings.json   dashboard edits (caps, split, subscriptions, goal checkpoints, loan-vs-invest inputs)
    backups/        one copy of each file per day, taken before the first save of that day

Listens on 127.0.0.1 only. Requests whose Host or Origin isn't this machine are refused. Standard library only.
"""
import csv
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import webbrowser
from datetime import date
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP = Path(__file__).resolve().parent
DOCS = APP.parent / "docs"
FIELDS = ["month", "date", "description", "category", "amount", "card", "notes"]
LOCK = threading.Lock()
DATA = SITE = EXPENSES = SETTINGS = BACKUPS = None
PORT = 8765
ALLOWED_HOSTS = set()


def configure(workspace, port):
    global DATA, SITE, EXPENSES, SETTINGS, BACKUPS, PORT, ALLOWED_HOSTS
    ws = Path(workspace).resolve()
    DATA = ws if ws.name == "money-coach-data" else ws / "money-coach-data"
    SITE, EXPENSES, SETTINGS, BACKUPS = DATA / "site", DATA / "expenses.csv", DATA / "settings.json", DATA / "backups"
    PORT = port
    ALLOWED_HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}


def read_expenses():
    if not EXPENSES.exists():
        return []
    with EXPENSES.open(newline="", encoding="utf-8") as f:
        rows = []
        for r in csv.DictReader(f):
            try:
                amt = float(r.get("amount") or 0)
            except ValueError:
                amt = 0.0
            rows.append({"month": r.get("month", ""), "date": r.get("date", ""), "desc": r.get("description", ""),
                         "cat": r.get("category", ""), "amt": amt, "card": r.get("card", ""), "notes": r.get("notes", "")})
        return rows


def read_settings():
    if not SETTINGS.exists():
        return {}
    return json.loads(SETTINGS.read_text(encoding="utf-8") or "{}")


def backup_once_today(path):
    if not path.exists():
        return
    BACKUPS.mkdir(parents=True, exist_ok=True)
    target = BACKUPS / f"{path.stem}-{date.today().isoformat()}{path.suffix}"
    if not target.exists():
        shutil.copy2(path, target)
        os.chmod(target, 0o600)


def atomic_write(path, text):
    DATA.mkdir(parents=True, exist_ok=True)
    backup_once_today(path)
    fd, tmp = tempfile.mkstemp(dir=DATA, prefix=".tmp-")
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def write_expenses(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS)
    w.writeheader()
    for r in rows:
        w.writerow({"month": r.get("month", ""), "date": r.get("date", ""), "description": r.get("desc", ""),
                    "category": r.get("cat", ""), "amount": f"{float(r.get('amt') or 0):.2f}",
                    "card": r.get("card", ""), "notes": r.get("notes", "")})
    atomic_write(EXPENSES, buf.getvalue())


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(SITE), **k)

    def log_request(self, code="-", size="-"):  # quiet: only log failed requests
        if str(code).startswith(("4", "5")):
            super().log_request(code, size)

    def _local_only(self):
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin")
        if host not in ALLOWED_HOSTS or (origin and origin.split("//", 1)[-1] not in ALLOWED_HOSTS):
            self.send_error(403, "Local requests only")
            return False
        return True

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 20_000_000:
            raise ValueError("too large")
        return json.loads(self.rfile.read(n) or b"null")

    def do_GET(self):
        if not self._local_only():
            return
        if self.path == "/api/state":
            with LOCK:
                return self._json({"expenses": read_expenses(), "settings": read_settings(),
                                   "files": {"expenses": str(EXPENSES), "settings": str(SETTINGS)}})
        if self.path.startswith("/docs/"):
            target = (DOCS / self.path[len("/docs/"):].split("?")[0]).resolve()
            if DOCS.resolve() in target.parents and target.suffix == ".md" and target.exists():
                body = target.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            return self.send_error(404)
        if self.path in ("/", ""):
            self.path = "/index.html"
        return super().do_GET()

    def do_PUT(self):
        if not self._local_only():
            return
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.send_error(415, "JSON only")
        try:
            data = self._body()
            with LOCK:
                if self.path == "/api/state":
                    if not isinstance(data, dict) or not isinstance(data.get("expenses"), list) or not isinstance(data.get("settings"), dict):
                        return self.send_error(400, "Expected {expenses: [], settings: {}}")
                    write_expenses(data["expenses"])
                    atomic_write(SETTINGS, json.dumps(data["settings"], indent=1))
                    return self._json({"ok": True, "expenses": len(data["expenses"])})
            return self.send_error(404)
        except (ValueError, json.JSONDecodeError) as e:
            return self.send_error(400, str(e))

    def do_POST(self):
        if not self._local_only():
            return
        if self.path == "/api/export-excel":
            try:
                with LOCK:
                    for p in (str(APP), str(APP.parent / "scripts")):
                        if p not in sys.path:
                            sys.path.insert(0, p)
                    import importlib
                    import build
                    import workbook
                    importlib.reload(build); importlib.reload(workbook)
                    from mc_common import load_config
                    cfg = load_config(DATA)
                    plan = build.plan_data(cfg, build.load_findings(DATA), json.loads((DATA / "analysis.json").read_text()) if (DATA / "analysis.json").exists() else None)
                    path = workbook.build(DATA, cfg, plan, *build.load_saved(DATA))
                return self._json({"ok": True, "path": str(path)})
            except Exception as e:  # report build problems to the page
                return self._json({"ok": False, "error": f"{type(e).__name__}: {e}"}, 500)
        return self.send_error(404)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="money-coach dashboard server")
    ap.add_argument("--workspace", default=os.environ.get("MONEY_COACH_HOME") or os.getcwd())
    ap.add_argument("--port", type=int, default=int(os.environ.get("MONEY_COACH_PORT", "8765")))
    ap.add_argument("--open", action="store_true")
    a = ap.parse_args()
    configure(a.workspace, a.port)
    if not (SITE / "index.html").exists():
        sys.exit(f"{SITE / 'index.html'} is missing. Build it first: python3 {APP / 'build.py'} --workspace {a.workspace}")
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}/"
    print(f"money-coach running at {url}  (data: {DATA})\nPress Ctrl+C to stop.")
    if a.open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
