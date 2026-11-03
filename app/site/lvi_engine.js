// Loan vs Invest engine: the monthly recurrence from a classic loan-vs-invest spreadsheet "Calc Engine".
// Same math as the spreadsheet (verified to the cent), any number of loans/investments.
// g.fxCurrency: the one foreign currency a loan can be in (e.g. "INR"); its balance converts at g.fxNow, drifting by the
//   observed (or overridden) annual change. g.fxAwareForeignLoans (off = spreadsheet behaviour) tracks those loans in
//   their own currency so a weakening currency also shrinks a reducing-balance ("Compound") loan in your currency.
const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
function lviFx(g) {
  if (!g.fxCurrency) return { years: 0, dep: 0, monthly: 1 };
  const years = (g.curYear - g.startYear) + (MONTHS.indexOf(g.curMonth) - MONTHS.indexOf(g.startMonth)) / 12;
  const dep = g.fxDepOverride != null ? g.fxDepOverride : Math.pow(g.fxNow / g.fxStart, 1 / years) - 1;
  return { years, dep, monthly: Math.pow(1 + dep, 1 / 12) };
}
function lviRun(g, loans, invs, scen, N) {
  const fx = lviFx(g);
  let rate = g.fxNow;
  const bal = loans.map(l => l.currency === g.fxCurrency ? l.outstanding / g.fxNow : l.outstanding);
  // Optional fix (off by default = spreadsheet behaviour): track foreign-currency loans in their own currency.
  const fc = loans.map(l => l.currency === g.fxCurrency ? l.outstanding : null);
  const val = invs.map(() => 0);
  const mret = invs.map(i => Math.pow(1 + i.ret, 1 / 12) - 1);
  let invested = 0, cumInt = 0;
  const rows = [{ m: 0, loans: bal.reduce((a, b) => a + b, 0), inv: 0, invested: 0, nw: -bal.reduce((a, b) => a + b, 0), cumInt: 0, bal: [...bal] }];
  const payoff = loans.map(() => null);
  for (let m = 1; m <= N; m++) {
    const y = Math.floor((m - 1) / 12) + 1;
    rate *= fx.monthly;
    loans.forEach((l, k) => {
      const prev = bal[k];
      if (prev <= 0) return;
      if (g.fxAwareForeignLoans && l.currency === g.fxCurrency) {
        const iF = l.type.startsWith("Simple") ? l.principal * l.rate / 12 : fc[k] * l.rate / 12;
        const pmtUSD = Math.min(scen.loans[k].amt * Math.pow(1 + scen.loans[k].step, y - 1), (fc[k] + iF) / rate);
        const pF = pmtUSD * rate;
        let nF = l.type.startsWith("Simple-flat") ? fc[k] - pF : l.type.startsWith("Simple-rebate") ? fc[k] - (pF - iF) : fc[k] + iF - pF;
        fc[k] = Math.max(0, nF); bal[k] = fc[k] / rate; if (bal[k] < 0.005) bal[k] = fc[k] = 0;
        cumInt += iF / rate;
        if (bal[k] === 0 && payoff[k] == null) payoff[k] = m;
        return;
      }
      const interest = l.type.startsWith("Simple") ? l.principal * l.rate / 12 / (l.currency === g.fxCurrency ? rate : 1) : prev * l.rate / 12;
      const pmt = Math.min(scen.loans[k].amt * Math.pow(1 + scen.loans[k].step, y - 1), prev + interest);
      let nb;
      if (l.type.startsWith("Simple-flat")) nb = prev - pmt;
      else if (l.type.startsWith("Simple-rebate")) nb = prev - (pmt - interest);
      else nb = prev + interest - pmt;
      bal[k] = Math.max(0, nb);
      cumInt += interest;
      if (bal[k] === 0 && payoff[k] == null) payoff[k] = m;
    });
    invs.forEach((inv, j) => {
      let c = scen.invs[j].amt * Math.pow(1 + scen.invs[j].step, y - 1);
      if (j === 0) loans.forEach((l, k) => { if (bal[k] === 0) c += scen.loans[k].amt * Math.pow(1 + scen.loans[k].step, y - 1); });
      val[j] = val[j] * (1 + mret[j]) + c;
      invested += c;
    });
    const L = bal.reduce((a, b) => a + b, 0), U = val.reduce((a, b) => a + b, 0);
    rows.push({ m, loans: L, inv: U, invested, nw: U - L, cumInt, bal: [...bal] });
  }
  return { rows, payoff, fx };
}
if (typeof module !== "undefined") module.exports = { lviRun, lviFx };
