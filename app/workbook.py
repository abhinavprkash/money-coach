"""Excel workbook: one sheet per plan month (budget + expense tracker), Goal, Guide, Lists.

All rows come from config.json; dashboard edits (settings.json) and logged expenses (expenses.csv) are applied.
Inputs are blue on yellow; everything else is a formula. The file is set to recalculate on open.
"""
import os
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

F = "Arial"
TITLE = Font(name=F, size=16, bold=True, color="1F3864")
SUB = Font(name=F, size=9, italic=True, color="595959")
SEC = Font(name=F, size=11, bold=True, color="FFFFFF")
SEC_FILL = PatternFill("solid", fgColor="1F3864")
HDR = Font(name=F, size=9, bold=True, color="1F3864")
HDR_FILL = PatternFill("solid", fgColor="D9E1F2")
BODY = Font(name=F, size=10)
INPUT = Font(name=F, size=10, color="0000FF")
INPUT_FILL = PatternFill("solid", fgColor="FFF9DB")
BOLD = Font(name=F, size=10, bold=True)
ROAST = Font(name=F, size=9, italic=True, color="C00000")
INFO = Font(name=F, size=9, italic=True, color="7F7F7F")
TOTAL_FILL = PatternFill("solid", fgColor="EDEDED")
RED_FILL = PatternFill("solid", fgColor="F8CBAD")
GREEN_FILL = PatternFill("solid", fgColor="C6EFCE")
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)
USD = '$#,##0.00;($#,##0.00);"-"'
PCT = '0.0%;(0.0%);"-"'
TR_FIRST, TR_LAST = 5, 204
CAT, AMT, CARD, DESC = (f"${c}${TR_FIRST}:${c}${TR_LAST}" for c in "LMNK")
WRAP = Alignment(wrap_text=True, vertical="top")


def q(s, n=240):
    """Text safe to embed in an Excel formula string literal."""
    return str(s or "").replace('"', "'")[:n]


def put(ws, ref, value, font=BODY, fmt=None, fill=None, align=None, border=True):
    c = ws[ref]
    c.value, c.font = value, font
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    if align:
        c.alignment = align
    if border:
        c.border = BOX
    return c


def section(ws, row, text, first="A", last="G"):
    ws.merge_cells(f"{first}{row}:{last}{row}")
    c = ws[f"{first}{row}"]
    c.value, c.font, c.fill = text, SEC, SEC_FILL


def headers(ws, row, labels, first_col=1):
    for i, lab in enumerate(labels):
        if lab is not None:
            put(ws, f"{get_column_letter(first_col + i)}{row}", lab, HDR, fill=HDR_FILL, align=Alignment(horizontal="center", wrap_text=True))


def voice_formula(row, base, tone, priority):
    v = "gentle" if priority == "protect" else ("savage" if priority == "cut" and tone != "gentle" else tone)
    over = {"gentle": '"$"&TEXT(E{r}-D{r},"0")&" over. Tomorrow is a new day."',
            "honest": '"Over by $"&TEXT(E{r}-D{r},"0")&". Pause this category."',
            "savage": '"OVER by $"&TEXT(E{r}-D{r},"0")&". Card goes in the drawer."'}[v].format(r=row)
    zero = {"gentle": '"You planned $0 here."', "honest": '"Budget was $0; you spent $"&TEXT(E{r},"0")&"."',
            "savage": '"Budget was $0 and you spent $"&TEXT(E{r},"0")&". Explain yourself."'}[v].format(r=row)
    b = q(base) or "On track."
    return (f'=IF(D{row}=0,IF(E{row}>0,{zero},"{b}"),IF(E{row}>D{row},{over},'
            f'IF(E{row}>=0.8*D{row},"80%+ used. Slow down.","{b}")))')


def month_sheet(wb, plan, m, ov, expenses, lists):
    ws = wb.create_sheet(m["label"])
    for col, w in {"A": 4, "B": 34, "C": 27, "D": 13, "E": 13, "F": 13, "G": 58, "H": 2, "I": 5, "J": 11, "K": 30, "L": 30,
                   "M": 12, "N": 24, "O": 40}.items():
        ws.column_dimensions[col].width = w
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A4"
    tone = plan["tone"]
    put(ws, "A1", f"{m['label']} Budget", TITLE, border=False)
    put(ws, "A2", "Blue on yellow = you type. Black = formulas. Red italics = the roast. See the Guide sheet for every section.", SUB, border=False)
    put(ws, "I1", f"{m['name']} Expense Tracker", TITLE, border=False)
    put(ws, "I2", "Log every purchase here. Every Actual / Spent column updates itself.", SUB, border=False)

    r = 4
    section(ws, r, "INCOME & BANK ALLOCATION")
    headers(ws, r + 1, ["#", "Description", "Source", "Amount", None, None, "Notes"])
    per = float(ov.get("per_paycheck", m["per_paycheck"]))
    put(ws, f"A{r+2}", 1); put(ws, f"B{r+2}", "Take-home per paycheck"); put(ws, f"C{r+2}", "Payroll")
    put(ws, f"D{r+2}", per, INPUT, USD, INPUT_FILL)
    put(ws, f"A{r+3}", 2); put(ws, f"B{r+3}", "Paychecks this month"); put(ws, f"C{r+3}", "")
    put(ws, f"D{r+3}", round(m["paychecks"], 4), INPUT, "0.00", INPUT_FILL)
    extra_vals = ov.get("extra") or [e["amount"] for e in m["extra"]]
    extra_total = sum(float(x) for x in extra_vals)
    put(ws, f"A{r+4}", 3); put(ws, f"B{r+4}", "Extra pay (after tax)"); put(ws, f"C{r+4}", ", ".join(e["label"] for e in m["extra"]) or "None planned")
    put(ws, f"D{r+4}", extra_total, INPUT, USD, INPUT_FILL)
    put(ws, f"G{r+4}", "Windfalls go straight to savings the day they land.", INFO)
    inc = r + 5
    put(ws, f"B{inc}", "TOTAL INCOME", BOLD, fill=TOTAL_FILL)
    put(ws, f"D{inc}", f"=D{r+2}*D{r+3}+D{r+4}", BOLD, USD, TOTAL_FILL)
    PER, NPAY, EXTRA, INC = f"$D${r+2}", f"$D${r+3}", f"$D${r+4}", f"$D${inc}"

    r = inc + 2
    headers(ws, r, ["#", "Account (direct-deposit split)", "Job", "Per Paycheck", "Monthly", "% of Pay", "Notes"])
    accts = plan["split"]["accounts"]
    first_sav = next((a["name"] for a in accts if a.get("kind") == "savings"), None)
    rows = {}
    for i, a in enumerate(accts):
        row = r + 1 + i
        rows[a["name"]] = row
        put(ws, f"A{row}", i + 1); put(ws, f"B{row}", a["name"]); put(ws, f"C{row}", a.get("job", a.get("kind", "")), align=WRAP)
        put(ws, f"D{row}", float(ov.get("split", {}).get(a["name"], a["per_paycheck"])), INPUT, USD, INPUT_FILL)
        put(ws, f"E{row}", f"=D{row}*{NPAY}" + (f"+{EXTRA}" if a["name"] == first_sav else ""), BODY, USD)
        put(ws, f"F{row}", f"=IF({INC}=0,0,E{row}/{INC})", BODY, PCT)
        put(ws, f"G{row}", a.get("kind", "").title(), INFO)
    ch = r + 1 + len(accts)
    put(ws, f"A{ch}", len(accts) + 1); put(ws, f"B{ch}", plan["split"]["remainder"])
    put(ws, f"C{ch}", plan["split"].get("remainder_job", "Gets the rest"), align=WRAP)
    others = "+".join(f"D{v}" for v in rows.values()) or "0"
    put(ws, f"D{ch}", f"={PER}-({others})", BODY, USD)
    put(ws, f"E{ch}", f"={INC}-SUM(E{r+1}:E{ch-1})" if accts else f"={INC}", BODY, USD)
    put(ws, f"F{ch}", f"=IF({INC}=0,0,E{ch}/{INC})", BODY, PCT)
    put(ws, f"G{ch}", f'=IF(D{ch}<0,"The split is bigger than the paycheck.","Pays every card bill in full.")', ROAST, align=WRAP)

    r = ch + 2
    section(ws, r, "FIXED & RECURRING EXPENSES")
    headers(ws, r + 1, ["#", "Expense", "Paid From", "Budgeted", "Actual", "Difference", "Notes"])
    f0 = r + 2
    for i, b in enumerate(plan["fixed"]):
        row = f0 + i
        amt = float(ov.get("fixed", {}).get(b["name"], b["amount"] if b["name"] in m["fixed_active"] else 0))
        put(ws, f"A{row}", i + 1); put(ws, f"B{row}", b["name"]); put(ws, f"C{row}", b["paid_from"])
        put(ws, f"D{row}", amt, INPUT, USD, INPUT_FILL)
        put(ws, f"E{row}", f"=SUMIFS({AMT},{CAT},B{row})", BODY, USD)
        put(ws, f"F{row}", f"=D{row}-E{row}", BODY, USD)
        put(ws, f"G{row}", b.get("roast") or ("" if b["name"] in m["fixed_active"] else "Not active this month."), ROAST, align=WRAP)
    f1 = f0 + max(len(plan["fixed"]), 1) - 1
    ft = f1 + 1
    put(ws, f"B{ft}", "TOTAL FIXED", BOLD, fill=TOTAL_FILL)
    for col in "DEF":
        put(ws, f"{col}{ft}", f"=SUM({col}{f0}:{col}{f1})", BOLD, USD, TOTAL_FILL)

    r = ft + 2
    section(ws, r, "SUBSCRIPTIONS")
    headers(ws, r + 1, ["#", "Service", "Card", "Cost", "Active?", "Actual (Tracker)", "Roast"])
    s0 = r + 2
    yn = DataValidation(type="list", formula1='"Yes,No"', allow_blank=False)
    ws.add_data_validation(yn)
    for i, s in enumerate(plan["subs"]):
        row = s0 + i
        so = ov.get("subs", {}).get(s["name"], {})
        put(ws, f"A{row}", i + 1); put(ws, f"B{row}", s["name"]); put(ws, f"C{row}", s.get("card", ""))
        put(ws, f"D{row}", float(so.get("cost", s["amount"])), INPUT, USD, INPUT_FILL)
        act = so.get("active", "Yes" if s.get("active") else "No")
        put(ws, f"E{row}", act if act in ("Yes", "No") else ("Yes" if act else "No"), INPUT, fill=INPUT_FILL, align=Alignment(horizontal="center"))
        yn.add(f"E{row}")
        put(ws, f"F{row}", f'=SUMIFS({AMT},{CAT},"Subscriptions",{DESC},B{row})', BODY, USD)
        put(ws, f"G{row}", f'=IF(AND(E{row}="No",F{row}>0),"Marked No and STILL charged $"&TEXT(F{row},"0.00")&". Cancel it for real.","{q(s.get("roast"))}")',
            ROAST, align=WRAP)
    s1 = s0 + max(len(plan["subs"]), 1) - 1
    st = s1 + 1
    put(ws, f"B{st}", "TOTAL SUBSCRIPTIONS (active)", BOLD, fill=TOTAL_FILL)
    put(ws, f"D{st}", f'=SUMIFS(D{s0}:D{s1},E{s0}:E{s1},"Yes")', BOLD, USD, TOTAL_FILL)
    put(ws, f"F{st}", f"=SUM(F{s0}:F{s1})", BOLD, USD, TOTAL_FILL)
    put(ws, f"G{st}", "Log subscription charges with Category = Subscriptions and Description = the service name.", INFO, align=WRAP)

    r = st + 2
    section(ws, r, "SAVINGS (from take-home)")
    headers(ws, r + 1, ["#", "Where", "Account", "Budgeted", "Actual (you confirm)", "Difference", "Notes"])
    v0, i = r + 2, 0
    saved = ov.get("saved", {})
    for a in accts:
        if a.get("kind") != "savings":
            continue
        row = v0 + i
        put(ws, f"A{row}", i + 1); put(ws, f"B{row}", f"{a['name']} (split + windfalls)"); put(ws, f"C{row}", a["name"])
        put(ws, f"D{row}", f"=E{rows[a['name']]}", BODY, USD)
        put(ws, f"E{row}", float(saved.get(a["name"], 0)), INPUT, USD, INPUT_FILL)
        put(ws, f"F{row}", f"=D{row}-E{row}", BODY, USD)
        put(ws, f"G{row}", f'=IF(E{row}=0,"Still $0. Did the split happen?",IF(E{row}<D{row},"Less than planned. Fix the split.","Saved on plan. Respect."))', ROAST, align=WRAP)
        i += 1
    bills = [a["name"] for a in accts if a.get("kind") == "bills"]
    row = v0 + i
    sink = "+".join(f'E{rows[n]}-SUMIFS($D${f0}:$D${f1},$C${f0}:$C${f1},"{q(n)}")' for n in bills) or "0"
    put(ws, f"A{row}", i + 1); put(ws, f"B{row}", "Sinking fund (left in bills accounts)"); put(ws, f"C{row}", ", ".join(bills) or "-")
    put(ws, f"D{row}", f"=MAX(0,{sink})", BODY, USD)
    put(ws, f"E{row}", float(saved.get("sinking", 0)), INPUT, USD, INPUT_FILL)
    put(ws, f"F{row}", f"=D{row}-E{row}", BODY, USD)
    put(ws, f"G{row}", "Repairs, travel and annual bills only. It's not a second checking account.", ROAST, align=WRAP)
    v1 = row
    vt = v1 + 1
    put(ws, f"B{vt}", "TOTAL SAVINGS", BOLD, fill=TOTAL_FILL)
    for col in "DEF":
        put(ws, f"{col}{vt}", f"=SUM({col}{v0}:{col}{v1})", BOLD, USD, TOTAL_FILL)
    pr = vt + 1
    if plan["payroll"]:
        put(ws, f"B{pr}", "Already out of your paycheck (not in totals):", INFO, border=False)
        for k, p in enumerate(plan["payroll"]):
            put(ws, f"B{pr+1+k}", p["label"], INFO, border=False); put(ws, f"D{pr+1+k}", float(p["monthly"]), INFO, USD, border=False)
        pr += len(plan["payroll"])

    r = pr + 2
    section(ws, r, "VARIABLE SPENDING (caps from your priorities)")
    headers(ws, r + 1, ["#", "Category", "Default Card", "Budgeted", "Spent (Auto)", "Remaining", "Status / Roast"])
    a0 = r + 2
    for i, c in enumerate(plan["categories"]):
        row = a0 + i
        put(ws, f"A{row}", i + 1); put(ws, f"B{row}", c["name"]); put(ws, f"C{row}", c.get("card", ""))
        put(ws, f"D{row}", float(ov.get("variable", {}).get(c["name"], c["cap"])), INPUT, USD, INPUT_FILL)
        put(ws, f"E{row}", f"=SUMIFS({AMT},{CAT},B{row})", BODY, USD)
        put(ws, f"F{row}", f"=D{row}-E{row}", BODY, USD)
        put(ws, f"G{row}", voice_formula(row, c.get("roast"), plan["tone"], c.get("priority", "normal")), ROAST, align=WRAP)
    a1 = a0 + len(plan["categories"]) - 1
    at = a1 + 1
    put(ws, f"B{at}", "TOTAL VARIABLE", BOLD, fill=TOTAL_FILL)
    for col in "DEF":
        put(ws, f"{col}{at}", f"=SUM({col}{a0}:{col}{a1})", BOLD, USD, TOTAL_FILL)
    sk = at + 1
    put(ws, f"B{sk}", "Paid from sinking fund", INFO)
    put(ws, f"E{sk}", f'=SUMIFS({AMT},{CAT},"Sinking fund spend")', INFO, USD)
    for rng in (f"F{a0}:F{a1}", f"F{f0}:F{f1}"):
        ws.conditional_formatting.add(rng, CellIsRule(operator="lessThan", formula=["0"], fill=RED_FILL))

    r = sk + 2
    section(ws, r, "MONTHLY SUMMARY")
    headers(ws, r + 1, [None, "Category", None, "Budgeted", "Actual", "Difference", "Status / Roast"])
    lines = [("Total Income", INC, INC), ("Fixed", f"$D${ft}", f"$E${ft}"), ("Subscriptions", f"$D${st}", f"$F${st}"),
             ("Savings", f"$D${vt}", f"$E${vt}"), ("Variable", f"$D${at}", f"$E${at}")]
    for i, (lab, b, a) in enumerate(lines):
        row = r + 2 + i
        put(ws, f"B{row}", lab); put(ws, f"D{row}", f"={b}", BODY, USD); put(ws, f"E{row}", f"={a}", BODY, USD)
        put(ws, f"F{row}", f"=D{row}-E{row}", BODY, USD)
    te = r + 2 + len(lines)
    put(ws, f"B{te}", "TOTAL OUT", BOLD, fill=TOTAL_FILL)
    put(ws, f"D{te}", f"=SUM(D{r+3}:D{te-1})", BOLD, USD, TOTAL_FILL)
    put(ws, f"E{te}", f"=SUM(E{r+3}:E{te-1})", BOLD, USD, TOTAL_FILL)
    nr = te + 1
    put(ws, f"B{nr}", f"NET REMAINING ({plan['split']['remainder']} buffer)", BOLD, fill=TOTAL_FILL)
    put(ws, f"D{nr}", f"=D{r+2}-D{te}", BOLD, USD, TOTAL_FILL)
    put(ws, f"E{nr}", f"=E{r+2}-E{te}", BOLD, USD, TOTAL_FILL)
    put(ws, f"G{nr}", f'=IF(D{nr}<0,"Budget is in DEFICIT. Savings are not an ATM. Cut something now.",IF(D{nr}<50,"Razor thin: $"&TEXT(D{nr},"0")&". Zero impulse buys.","Planned buffer $"&TEXT(D{nr},"0")&". Leftover goes to savings at month end."))',
        ROAST, align=WRAP)
    ws.conditional_formatting.add(f"D{nr}:E{nr}", CellIsRule(operator="lessThan", formula=["0"], fill=RED_FILL))
    ws.conditional_formatting.add(f"D{nr}:E{nr}", CellIsRule(operator="greaterThanOrEqual", formula=["0"], fill=GREEN_FILL))

    r = nr + 2
    section(ws, r, "CARD SPENDING SUMMARY")
    headers(ws, r + 1, ["#", "Card", None, None, "Total Charged"])
    c0 = r + 2
    for i, card in enumerate(plan["cards"]):
        put(ws, f"A{c0+i}", i + 1); put(ws, f"B{c0+i}", card); put(ws, f"E{c0+i}", f"=SUMIFS({AMT},{CARD},B{c0+i})", BODY, USD)
    un = c0 + len(plan["cards"])
    put(ws, f"B{un}", "No card picked", INFO); put(ws, f"E{un}", f"=SUM({AMT})-SUM(E{c0}:E{un-1})" if plan["cards"] else f"=SUM({AMT})", INFO, USD)
    put(ws, f"B{un+1}", "TOTAL CHARGED", BOLD, fill=TOTAL_FILL); put(ws, f"E{un+1}", f"=SUM(E{c0}:E{un})", BOLD, USD, TOTAL_FILL)

    headers(ws, 4, ["#", "Date", "Description", "Category", "Amount", "Card", "Notes"], first_col=9)
    dv_cat = DataValidation(type="list", formula1=f"=Lists!$A$2:$A${lists['cat_last']}", allow_blank=True)
    dv_card = DataValidation(type="list", formula1=f"=Lists!$B$2:$B${lists['card_last']}", allow_blank=True)
    ws.add_data_validation(dv_cat); ws.add_data_validation(dv_card)
    dv_cat.add(f"L{TR_FIRST}:L{TR_LAST}"); dv_card.add(f"N{TR_FIRST}:N{TR_LAST}")
    exp = expenses or []
    if len(exp) > TR_LAST - TR_FIRST + 1:
        print(f"WARNING: {m['label']} has {len(exp)} expenses; the sheet holds {TR_LAST - TR_FIRST + 1}.")
    for i in range(TR_LAST - TR_FIRST + 1):
        row = TR_FIRST + i
        e = exp[i] if i < len(exp) else {}
        d = e.get("date")
        put(ws, f"I{row}", i + 1, INFO, align=Alignment(horizontal="center"))
        put(ws, f"J{row}", date.fromisoformat(d) if d else None, INPUT, "mm/dd", INPUT_FILL)
        put(ws, f"K{row}", e.get("description") or None, INPUT, fill=INPUT_FILL)
        put(ws, f"L{row}", e.get("category") or None, INPUT, fill=INPUT_FILL)
        put(ws, f"M{row}", float(e["amount"]) if e.get("amount") else None, INPUT, USD, INPUT_FILL)
        put(ws, f"N{row}", e.get("card") or None, INPUT, fill=INPUT_FILL)
        put(ws, f"O{row}", e.get("notes") or None, INFO, fill=INPUT_FILL)
    if not exp:
        ws[f"K{TR_FIRST}"].comment = Comment("Example: 03/14 | Corner Grocery | Groceries | 42.10 | <your card>", "money-coach")


def goal_sheet(wb, plan, gs):
    ws = wb.create_sheet("Goal", 0)
    for col, w in {"A": 28, "B": 18, "C": 20, "D": 16, "E": 62}.items():
        ws.column_dimensions[col].width = w
    ws.sheet_view.showGridLines = False
    g = plan["goal"]
    actuals, wf = gs.get("actuals", {}), gs.get("windfalls", {})
    put(ws, "A1", f"Road to ${g['target']:,.0f} by {g['deadline']}", TITLE, border=False)
    put(ws, "A2", "Enter your real total at each month end. The plan line comes from the goal-planner.", SUB, border=False)
    put(ws, "A4", "Target", BOLD); put(ws, "B4", g["target"], INPUT, USD, INPUT_FILL)
    section(ws, 6, "MONTHLY CHECKPOINTS", "A", "E")
    headers(ws, 7, ["Checkpoint", "Plan says", "Your actual (enter)", "Ahead / Behind", "Roast"])
    pts = ([{"label": "Start", "plan_balance": g["start"]}] if g.get("start") is not None else []) + g["checkpoints"]
    for i, p in enumerate(pts):
        row = 8 + i
        a = actuals.get(p["label"])
        put(ws, f"A{row}", p["label"]); put(ws, f"B{row}", p["plan_balance"], BODY, USD)
        put(ws, f"C{row}", None if a in (None, "") else float(a), INPUT, USD, INPUT_FILL)
        put(ws, f"D{row}", f'=IF(C{row}="","",C{row}-B{row})', BODY, USD)
        put(ws, f"E{row}", f'=IF(C{row}="","Fill this in at month end.",IF(C{row}>=$B$4,"Target HIT.",IF(D{row}>=0,"Ahead by $"&TEXT(D{row},"#,##0")&". Do not celebrate with shopping.","Behind by $"&TEXT(-D{row},"#,##0")&". Check the split and the caps.")))',
            ROAST, align=WRAP)
    last = 8 + max(len(pts), 1) - 1
    ws.conditional_formatting.add(f"D8:D{last}", CellIsRule(operator="lessThan", formula=["0"], fill=RED_FILL))
    r = last + 2
    section(ws, r, "WINDFALLS: ROUTE 100% TO SAVINGS", "A", "E")
    headers(ws, r + 1, ["Windfall", "Estimate (after tax)", "Arrived?", "Moved to savings?", "Roast"])
    yn = DataValidation(type="list", formula1='"Yes,No"', allow_blank=True)
    ws.add_data_validation(yn)
    for i, w in enumerate(plan["windfalls"]):
        row = r + 2 + i
        st = wf.get(w["label"], {})
        put(ws, f"A{row}", f"{w['label']} ({w['month']})"); put(ws, f"B{row}", w["amount"], INPUT, USD, INPUT_FILL)
        put(ws, f"C{row}", st.get("arrived") or None, INPUT, fill=INPUT_FILL); put(ws, f"D{row}", st.get("moved") or None, INPUT, fill=INPUT_FILL)
        yn.add(f"C{row}"); yn.add(f"D{row}")
        put(ws, f"E{row}", f'=IF(C{row}<>"Yes","Not here yet.",IF(D{row}="Yes","Moved the same day.","It ARRIVED and it is NOT in savings? Move it now."))', ROAST, align=WRAP)


def guide_sheet(wb, docs_dir):
    ws = wb.create_sheet("Guide", 1)
    ws.column_dimensions["A"].width = 28; ws.column_dimensions["B"].width = 100
    put(ws, "A1", "How to fill this in", TITLE, border=False)
    put(ws, "A2", "Each section has a full guide in the plugin's docs/onboarding folder. Run /money-review onboard <section> to redo one.", SUB, border=False)
    row = 4
    for f in sorted(Path(docs_dir).glob("*.md")):
        lines = [l.strip() for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        title = lines[0].lstrip("# ") if lines else f.stem
        para = next((l for l in lines[1:] if not l.startswith("#")), "")
        put(ws, f"A{row}", title, BOLD); put(ws, f"B{row}", f"{para}  (docs/onboarding/{f.name})", BODY, align=WRAP)
        row += 1


def build(ddir, cfg, plan, expenses, settings):
    wb = Workbook()
    wb.remove(wb.active)
    ls = wb.create_sheet("Lists")
    cats = [b["name"] for b in plan["fixed"]] + [c["name"] for c in plan["categories"]] + plan["extraCats"]
    ls["A1"], ls["B1"] = "Categories", "Cards"
    for i, c in enumerate(cats):
        ls[f"A{i+2}"] = c
    for i, c in enumerate(plan["cards"]):
        ls[f"B{i+2}"] = c
    lists = {"cat_last": len(cats) + 1, "card_last": max(len(plan["cards"]), 1) + 1}
    for m in plan["months"]:
        month_sheet(wb, plan, m, (settings.get("months") or {}).get(m["key"], {}), (expenses or {}).get(m["key"], []), lists)
    goal_sheet(wb, plan, settings.get("goal") or {})
    guide_sheet(wb, Path(__file__).resolve().parent.parent / "docs" / "onboarding")
    wb.move_sheet("Lists", offset=len(wb.sheetnames))
    wb.active = 0
    wb.calculation.fullCalcOnLoad = True
    out = Path(ddir) / "output" / "Budget.xlsx"
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    os.chmod(out, 0o600)
    return out
