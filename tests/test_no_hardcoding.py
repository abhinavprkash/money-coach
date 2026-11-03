"""Guards against personal data or hidden constants in shipped code.

Generic checks always run. A private list of extra strings (names, employers, exact amounts) can be supplied
WITHOUT committing it: set MONEY_COACH_SCRUB_FILE=/path/outside/repo.txt (one string per line).
"""
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE_DIRS = ["app", "scripts", "skills", "agents"]
CODE_EXT = {".py", ".js", ".html", ".md"}


def files(dirs=CODE_DIRS, exts=CODE_EXT):
    for d in dirs:
        for p in (ROOT / d).rglob("*"):
            if p.is_file() and p.suffix in exts and "__pycache__" not in p.parts:
                yield p


def test_no_money_literals_in_code():
    """Amount-like literals (e.g. 1234.56 or $1,234) must come from config, never code. Docs' fictional examples are exempt."""
    bad = []
    for p in files():
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"(?<![\w.])\d{3,}\.\d{2}(?!\d)", line) or re.search(r"\$\d{1,3},\d{3}", line):
                bad.append(f"{p.relative_to(ROOT)}:{i}: {line.strip()[:80]}")
    assert not bad, "\n".join(bad)


def test_no_personal_identifiers():
    pats = [r"[\w.+-]+@(gmail|yahoo|outlook|hotmail|icloud)\.com", r"\b\d{9,}\b"]
    extra_file = os.environ.get("MONEY_COACH_SCRUB_FILE")
    extra = [l.strip() for l in Path(extra_file).read_text().splitlines() if l.strip()] if extra_file else []
    hits = []
    for p in files(CODE_DIRS + ["docs", "examples", "schemas", "tests"], CODE_EXT | {".json", ".csv"}):
        text = p.read_text(encoding="utf-8", errors="ignore")
        for pat in pats:
            for m in re.finditer(pat, text):
                if "golden" in p.name and pat == pats[1]:
                    continue
                hits.append(f"{p.relative_to(ROOT)}: {m.group(0)}")
        low = text.lower()
        hits += [f"{p.relative_to(ROOT)}: <private term>" for s in extra if s.lower() in low]
    assert not hits, "\n".join(hits[:20])


def test_no_user_data_files_in_repo():
    bad = [str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts and (
        "money-coach-data" in p.parts or p.suffix in {".xlsx", ".xls"} or p.name in {"expenses.csv", "settings.json"})]
    assert not bad, bad
