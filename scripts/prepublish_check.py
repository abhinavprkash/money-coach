"""Pre-publish gate: run before every push. Exit 0 = safe to publish.

    MONEY_COACH_SCRUB_FILE=~/private-terms.txt python3 scripts/prepublish_check.py

1. Runs the test suite (pytest + node engine parity).
2. Fails if any tracked file is user data (money-coach-data/, *.xlsx, expenses.csv, settings.json).
3. Searches every tracked file AND the full git history for the private terms in MONEY_COACH_SCRUB_FILE
   (one per line: your name, employer, friends, exact balances...). Keep that file OUTSIDE the repo.
4. Warns if commits are authored with a personal email instead of a GitHub noreply address.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sh(*cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def main():
    ok = True
    r = sh(sys.executable, "-m", "pytest", "-q", "-p", "no:warnings")
    print("tests:", "PASS" if r.returncode == 0 else "FAIL"); ok &= r.returncode == 0
    if r.returncode:
        print(r.stdout[-2000:])
    if shutil.which("node"):
        r = sh("node", "tests/lvi_engine.test.js")
        print("engine parity:", r.stdout.strip() or r.stderr.strip()); ok &= r.returncode == 0
    tracked = sh("git", "ls-files").stdout.split()
    bad = [f for f in tracked if "money-coach-data/" in f or f.endswith((".xlsx", ".xls")) or Path(f).name in ("expenses.csv", "settings.json")]
    print("user-data files tracked:", bad or "none"); ok &= not bad
    sf = os.environ.get("MONEY_COACH_SCRUB_FILE")
    if not sf:
        print("WARNING: MONEY_COACH_SCRUB_FILE not set; private-term scan skipped.")
    else:
        terms = [t.strip() for t in Path(sf).expanduser().read_text().splitlines() if t.strip() and not t.startswith("#")]
        hist = sh("git", "log", "--all", "-p", "--no-color").stdout.lower()
        files_text = "\n".join((ROOT / f).read_text(encoding="utf-8", errors="ignore") for f in tracked if (ROOT / f).is_file()).lower()
        leaked = sorted({t for t in terms if t.lower() in files_text or t.lower() in hist})
        print(f"private terms ({len(terms)} checked):", "none found" if not leaked else f"FOUND {len(leaked)} (not printed)")
        ok &= not leaked
    emails = set(sh("git", "log", "--format=%ae").stdout.split())
    personal = [e for e in emails if not e.endswith("users.noreply.github.com") and not e.endswith("anthropic.com")]
    if personal:
        print("WARNING: commits use a personal author email; consider a GitHub noreply address.")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
