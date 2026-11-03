// Builds Loan vs Invest inputs, scenarios and red-pen notes from config.json. Shared by the CLI and the dashboard.
// Every number comes from the user's onboarding answers; thresholds are explained in the notes they produce.
(function (root) {
  function lviSettings(cfg) {
    const L = cfg.lvi || {}, fx = L.fx || null;
    return {
      budget: +L.monthly_budget || 0, years: +L.years || 10,
      fxCurrency: fx ? fx.currency : null, fxStart: fx ? +fx.start_rate : 1, startMonth: fx ? fx.start_month : "Jan",
      startYear: fx ? +fx.start_year : 2000, fxNow: fx ? +fx.current_rate : 1, curMonth: fx ? fx.current_month : "Jan",
      curYear: fx ? +fx.current_year : 2001, fxDepOverride: fx && fx.annual_change_override != null ? +fx.annual_change_override : null,
      fxAwareForeignLoans: !!(fx && fx.track_in_loan_currency),
    };
  }
  const lviLoans = cfg => (cfg.loans || []).map(l => ({ name: l.name, kind: l.kind, currency: l.currency, principal: +l.principal || +l.outstanding,
    outstanding: +l.outstanding, rate: +l.rate, type: l.type, emi: +l.min_payment || +l.current_payment, min: +l.min_payment || +l.current_payment, current: +l.current_payment }));
  const lviInvs = cfg => (cfg.investments || []).map(i => ({ name: i.name, kind: i.kind, ret: +i.expected_return, risk: i.risk || "", weight: i.weight == null ? null : +i.weight }));

  function weights(invs) {
    const w = invs.map(i => i.weight), have = w.filter(x => x != null && x > 0), tot = have.reduce((a, b) => a + b, 0);
    return tot > 0 ? w.map(x => (x || 0) / tot) : invs.map(() => 1 / Math.max(1, invs.length));
  }

  function lviScenarios(cfg, g) {
    const loans = lviLoans(cfg), invs = lviInvs(cfg), w = weights(invs), step = +((cfg.lvi || {}).step_up || 0);
    const budget = g.budget, dep = (typeof lviFx === "function" ? lviFx(g).dep : 0);
    const inv = amt => invs.map((_, j) => ({ amt: Math.max(0, amt) * w[j], step }));
    const sumMin = loans.reduce((a, l) => a + l.min, 0), sumCur = loans.reduce((a, l) => a + l.current, 0);
    const effRate = l => l.rate - (g.fxCurrency && l.currency === g.fxCurrency ? dep : 0);
    const top = loans.map((l, k) => [effRate(l), k]).sort((a, b) => b[0] - a[0])[0];
    const S = [];
    S.push({ id: "A", name: "A: Minimum payments, invest the rest", loans: loans.map(l => ({ amt: l.min, step: 0 })), invs: inv(budget - sumMin) });
    S.push({ id: "B", name: "B: Crush loans first", loans: loans.map((l, k) => ({ amt: l.min + (top && k === top[1] ? Math.max(0, budget - sumMin) : 0), step: 0 })), invs: inv(0) });
    S.push({ id: "C", name: "C: What you pay now, invest the rest", loans: loans.map(l => ({ amt: l.current, step: 0 })), invs: inv(budget - sumCur) });
    const cur = (cfg.lvi || {}).current_investing_monthly;
    if (cur != null) S.push({ id: "D", name: "D: Your actual plan today", loans: loans.map(l => ({ amt: l.current, step: 0 })), invs: inv(+cur) });
    return S;
  }

  function lviRedPen(cfg, g) {
    const notes = [], loans = lviLoans(cfg), invs = lviInvs(cfg), L = cfg.lvi || {};
    loans.forEach(l => {
      if (/^Simple-flat/.test(l.type) && /student|education|mortgage|home|auto|personal/i.test(l.kind || l.name))
        notes.push({ sev: "serious", text: `${l.name} is set to "Simple-flat", which counts every payment as principal. Most ${l.kind || "such"} loans are reducing-balance: part of each payment is interest. Check your statement (docs/onboarding/loans.md shows how), then pick "Compound" if interest is charged on the remaining balance.` });
      if (g.fxCurrency && l.currency === g.fxCurrency && l.type === "Compound" && !g.fxAwareForeignLoans)
        notes.push({ sev: "warning", text: `${l.name} is in ${l.currency}, but currency drift isn't applied to reducing-balance loans unless "Track foreign loans in their own currency" is on.` });
    });
    const hi = invs.filter(i => i.ret > 0.10);
    if (hi.length) notes.push({ sev: "warning", text: `Expected returns above 10%/yr (${hi.map(i => `${i.name} ${(i.ret * 100).toFixed(1)}%`).join(", ")}) are best-decade numbers, not a plan. Use the stress test to see how much the winner depends on them.` });
    if (g.fxCurrency && g.fxDepOverride == null) {
      const f = lviFx(g);
      notes.push({ sev: "verify", text: `${g.fxCurrency} moving ${(f.dep * 100).toFixed(1)}%/yr is extrapolated from ${f.years.toFixed(1)} years of history. If it stops, the loan costs its full rate. Set an override to test.` });
    }
    if (+L.step_up > 0) notes.push({ sev: "verify", text: `Contributions step up ${(+L.step_up * 100).toFixed(1)}%/yr. That assumes a raise every year.` });
    const tot = loans.reduce((a, l) => a + l.current, 0) + (+L.current_investing_monthly || 0);
    if (L.current_investing_monthly != null && g.budget > tot * 1.1)
      notes.push({ sev: "warning", text: `Scenarios A–C spend $${Math.round(g.budget).toLocaleString()}/mo, but today you put $${Math.round(tot).toLocaleString()}/mo into loans + investing. Compare D (your real plan) honestly.` });
    return notes;
  }

  function lviCompare(cfg, g, scenarios) {
    const N = Math.round(g.years * 12), loans = lviLoans(cfg), invs = lviInvs(cfg);
    const res = scenarios.map(s => {
      const r = lviRun(g, loans, invs, s, Math.max(N, 60));
      const total = s.loans.reduce((a, x) => a + x.amt, 0) + s.invs.reduce((a, x) => a + x.amt, 0);
      return { id: s.id, name: s.name, total, y5: r.rows[60], yN: r.rows[N], payoff: r.payoff, rows: r.rows };
    });
    const maxT = Math.max(...res.map(x => x.total)), cmp = res.filter(x => x.total >= 0.9 * maxT);
    const best = cmp.reduce((a, b) => (b.yN.nw > a.yN.nw ? b : a), cmp[0]);
    return { res, best, comparable: cmp.map(x => x.id) };
  }

  const api = { lviSettings, lviLoans, lviInvs, lviScenarios, lviRedPen, lviCompare };
  if (typeof module !== "undefined") module.exports = api; else Object.assign(root, api);
})(typeof window !== "undefined" ? window : globalThis);
