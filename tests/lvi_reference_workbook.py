"""Reference spreadsheet for Loan vs Invest parity tests.

Writes an .xlsx whose "Calc" sheet uses the same per-month formulas as the classic loan-vs-invest
"Calc Engine" (2 loans, up to 5 investments, any number of scenarios), then evaluates it with pycel.
tests/test_lvi_parity.py and tests/lvi_engine.test.js compare the JS engine against these numbers.

    python3 tests/lvi_reference_workbook.py   # regenerates tests/fixtures/lvi_golden.json (needs pycel)
"""
import json
from pathlib import Path

from openpyxl import Workbook

HERE = Path(__file__).resolve().parent
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Fictional inputs only.
CASE = {
    "settings": {"fxStart": 70.0, "startMonth": "Mar", "startYear": 2021, "fxNow": 80.0, "curMonth": "Sep", "curYear": 2024,
                 "fxCurrency": "INR"},
    "loans": [
        {"name": "Overseas tuition loan", "currency": "INR", "principal": 3000000, "outstanding": 2800000, "rate": 0.09, "type": "Simple-flat"},
        {"name": "Car loan", "currency": "USD", "principal": 21000, "outstanding": 16000, "rate": 0.065, "type": "Compound"},
    ],
    "invs": [{"name": "Index A", "ret": 0.09}, {"name": "Index B", "ret": 0.11}, {"name": "Bond fund", "ret": 0.045}],
    "scenarios": [
        {"name": "Min pay", "loans": [{"amt": 450, "step": 0}, {"amt": 400, "step": 0}], "invs": [{"amt": 900, "step": 0.03}, {"amt": 500, "step": 0.03}, {"amt": 200, "step": 0}]},
        {"name": "Crush", "loans": [{"amt": 1800, "step": 0}, {"amt": 650, "step": 0}], "invs": [{"amt": 0, "step": 0}, {"amt": 0, "step": 0}, {"amt": 0, "step": 0}]},
        {"name": "Balanced", "loans": [{"amt": 900, "step": 0.02}, {"amt": 400, "step": 0}], "invs": [{"amt": 700, "step": 0.03}, {"amt": 350, "step": 0.03}, {"amt": 100, "step": 0}]},
        {"name": "Rebate variant", "loans": [{"amt": 700, "step": 0}, {"amt": 500, "step": 0}], "invs": [{"amt": 600, "step": 0}, {"amt": 400, "step": 0}, {"amt": 300, "step": 0}]},
    ],
    "months": 120,
}


def build(case, path):
    """Inputs sheet + Calc sheet (one block per scenario) using the spreadsheet's formulas."""
    s, loans, invs = case["settings"], case["loans"], case["invs"]
    wb = Workbook()
    I = wb.active
    I.title = "Inputs"
    I["A1"], I["B1"] = "fxStart", s["fxStart"]
    I["A2"], I["B2"] = "fxNow", s["fxNow"]
    I["A3"], I["B3"] = "years elapsed", (s["curYear"] - s["startYear"]) + (MONTHS.index(s["curMonth"]) - MONTHS.index(s["startMonth"])) / 12
    I["A4"], I["B4"] = "annual dep", "=(B2/B1)^(1/B3)-1"
    I["A5"], I["B5"] = "monthly fx", "=(1+B4)^(1/12)"
    for k, l in enumerate(loans):          # loans in rows 10-11: currency, principal, outstanding, rate, type
        r = 10 + k
        I[f"A{r}"], I[f"B{r}"], I[f"C{r}"], I[f"D{r}"], I[f"E{r}"], I[f"F{r}"] = l["name"], l["currency"], l["principal"], l["outstanding"], l["rate"], l["type"]
    for j, v in enumerate(invs):           # investments in rows 20+: name, expected, monthly
        r = 20 + j
        I[f"A{r}"], I[f"B{r}"], I[f"C{r}"] = v["name"], v["ret"], f"=(1+B{r})^(1/12)-1"
    S = wb.create_sheet("Scen")           # scenario s: loans amt/step at row 2+k, investments at 10+j; columns 2s+1, 2s+2
    col = lambda n: chr(ord("A") + n)
    for si, sc in enumerate(case["scenarios"]):
        a, st = col(1 + 2 * si), col(2 + 2 * si)
        for k, x in enumerate(sc["loans"]):
            S[f"{a}{2+k}"], S[f"{st}{2+k}"] = x["amt"], x["step"]
        for j, x in enumerate(sc["invs"]):
            S[f"{a}{10+j}"], S[f"{st}{10+j}"] = x["amt"], x["step"]
    C = wb.create_sheet("Calc")
    N = case["months"]
    starts = []
    for si, sc in enumerate(case["scenarios"]):
        a, st = col(1 + 2 * si), col(2 + 2 * si)
        top = 1 + si * (N + 3)
        r0 = top + 1                       # month-0 row
        starts.append(r0)
        C[f"A{top}"] = sc["name"]
        C[f"A{r0}"], C[f"B{r0}"], C[f"C{r0}"] = 0, 0, "=Inputs!B2"
        # columns: loan k -> pmt D/G, int E/H, bal F/I; J total loans; investments K.. pairs; U total; V invested; W NW; X cum int
        C[f"F{r0}"] = '=IF(Inputs!B10="INR",Inputs!D10/Inputs!B2,Inputs!D10)'
        C[f"I{r0}"] = '=IF(Inputs!B11="INR",Inputs!D11/Inputs!B2,Inputs!D11)'
        C[f"J{r0}"] = f"=F{r0}+I{r0}"
        inv_cols = [("K", "L"), ("M", "N"), ("O", "P"), ("Q", "R"), ("S", "T")][:len(invs)]
        for c1, c2 in inv_cols:
            C[f"{c1}{r0}"], C[f"{c2}{r0}"] = 0, 0
        C[f"U{r0}"], C[f"V{r0}"], C[f"W{r0}"], C[f"X{r0}"] = 0, 0, f"=U{r0}-J{r0}", 0
        for m in range(1, N + 1):
            r, p = r0 + m, r0 + m - 1
            C[f"A{r}"] = m
            C[f"B{r}"] = f"=INT((A{r}-1)/12)+1"
            C[f"C{r}"] = f"=C{p}*Inputs!$B$5"
            for k, (pc, ic, bc) in enumerate([("D", "E", "F"), ("G", "H", "I")]):
                L = 10 + k
                C[f"{ic}{r}"] = (f'=IF({bc}{p}<=0,0,IF(LEFT(Inputs!$F${L},6)="Simple",Inputs!$C${L}*Inputs!$E${L}/12/IF(Inputs!$B${L}="INR",C{r},1),'
                                 f'{bc}{p}*Inputs!$E${L}/12))')
                C[f"{pc}{r}"] = f"=IF({bc}{p}<=0,0,MIN(Scen!${a}${2+k}*(1+Scen!${st}${2+k})^(B{r}-1),{bc}{p}+{ic}{r}))"
                C[f"{bc}{r}"] = (f'=MAX(0,IF(LEFT(Inputs!$F${L},13)="Simple-flat",{bc}{p}-{pc}{r},IF(LEFT(Inputs!$F${L},13)="Simple-rebate",'
                                 f'{bc}{p}-({pc}{r}-{ic}{r}),{bc}{p}+{ic}{r}-{pc}{r})))')
            C[f"J{r}"] = f"=F{r}+I{r}"
            for j, (c1, c2) in enumerate(inv_cols):
                base = f"Scen!${a}${10+j}*(1+Scen!${st}${10+j})^(B{r}-1)"
                if j == 0:
                    base += f"+IF(F{r}=0,Scen!${a}$2*(1+Scen!${st}$2)^(B{r}-1),0)+IF(I{r}=0,Scen!${a}$3*(1+Scen!${st}$3)^(B{r}-1),0)"
                C[f"{c1}{r}"] = "=" + base
                C[f"{c2}{r}"] = f"={c2}{p}*(1+Inputs!$C${20+j})+{c1}{r}"
            C[f"U{r}"] = "=" + "+".join(f"{c2}{r}" for _, c2 in inv_cols)
            C[f"V{r}"] = f"=V{p}+" + "+".join(f"{c1}{r}" for c1, _ in inv_cols)
            C[f"W{r}"] = f"=U{r}-J{r}"
            C[f"X{r}"] = f"=X{p}+E{r}+H{r}"
    wb.save(path)
    return starts


def evaluate(case, path):
    from pycel import ExcelCompiler
    starts = build(case, path)
    xl = ExcelCompiler(filename=str(path))
    out = []
    for si, r0 in enumerate(starts):
        res = {}
        for m in (12, 60, case["months"]):
            r = r0 + m
            res[str(m)] = {"nw": xl.evaluate(f"Calc!W{r}"), "loans": xl.evaluate(f"Calc!J{r}"), "inv": xl.evaluate(f"Calc!U{r}"),
                           "cumInt": xl.evaluate(f"Calc!X{r}")}
        out.append(res)
    return out


def case_with_rebate(case):
    c = json.loads(json.dumps(case))
    c["loans"][0]["type"] = "Simple-rebate"   # 4th check: rebate interest type on the foreign loan
    return c


if __name__ == "__main__":
    tmp = HERE / "fixtures"
    tmp.mkdir(exist_ok=True)
    golden = {"case": CASE, "results": evaluate(CASE, tmp / "_ref.xlsx"),
              "rebate_case": case_with_rebate(CASE), "rebate_results": evaluate(case_with_rebate(CASE), tmp / "_ref2.xlsx")}
    for f in ("_ref.xlsx", "_ref2.xlsx"):
        (tmp / f).unlink()
    (tmp / "lvi_golden.json").write_text(json.dumps(golden, indent=1))
    print("wrote", tmp / "lvi_golden.json")
