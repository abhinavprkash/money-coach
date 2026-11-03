#!/usr/bin/env node
// Loan vs Invest for the loan-vs-invest-analyst subagent.
//   node scripts/lvi_cli.js --workspace DIR [--stress]
// Reads money-coach-data/config.json (loans, investments, lvi), writes findings/lvi.json.
// --stress also runs: currency drift 0, every expected return capped at config.lvi.stress_return.
const fs = require("fs"), path = require("path");
const eng = require("../app/site/lvi_engine.js");
global.lviRun = eng.lviRun; global.lviFx = eng.lviFx;
const S = require("../app/site/lvi_scenarios.js");

const arg = (k) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : null; };
let ws = arg("--workspace") || process.env.MONEY_COACH_HOME || process.cwd();
const ddir = path.basename(ws) === "money-coach-data" ? ws : path.join(ws, "money-coach-data");
const cfg = JSON.parse(fs.readFileSync(path.join(ddir, "config.json"), "utf8"));
if (!(cfg.loans || []).length) {
  const out = { agent: "lvi", skipped: "No loans in config.json (onboarding said none), so there's nothing to compare.", findings: [] };
  fs.mkdirSync(path.join(ddir, "findings"), { recursive: true });
  fs.writeFileSync(path.join(ddir, "findings", "lvi.json"), JSON.stringify(out, null, 1), { mode: 0o600 });
  console.log(out.skipped); process.exit(0);
}
for (const k of ["monthly_budget", "years"]) if (!(cfg.lvi || {})[k]) { console.error(`config.lvi.${k} is missing (see docs/onboarding/loans.md)`); process.exit(2); }

function run(c) {
  const g = S.lviSettings(c), sc = S.lviScenarios(c, g), cmp = S.lviCompare(c, g, sc);
  const N = Math.round(g.years * 12);
  return {
    settings: g, scenarios: sc, red_pen: S.lviRedPen(c, g), best: cmp.best.id, comparable: cmp.comparable,
    results: cmp.res.map(x => ({ id: x.id, name: x.name, monthly: +x.total.toFixed(2), net_worth_y5: +x.y5.nw.toFixed(2),
      net_worth_end: +x.yN.nw.toFixed(2), portfolio_end: +x.yN.inv.toFixed(2), loans_left_end: +x.yN.loans.toFixed(2),
      interest_paid_end: +x.yN.cumInt.toFixed(2), payoff_month: x.payoff, years: g.years })),
  };
}
const base = run(cfg);
const out = { agent: "lvi", as_of: new Date().toISOString().slice(0, 10), ...base, findings: [] };
const C = base.results.find(r => r.id === "C"), B = base.results.find(r => r.id === base.best);
if (C && B) {
  const gap = B.net_worth_end - C.net_worth_end;
  out.findings.push({ severity: gap > 0.05 * Math.abs(C.net_worth_end) ? "warning" : "good",
    title: `${B.name} wins at ${base.settings.years} years; what you pay now is ${gap <= 0 ? "the winner" : `$${Math.round(gap).toLocaleString()} behind`}`,
    amount_at_stake: Math.max(0, +gap.toFixed(2)), evidence: base.results.map(r => `${r.id}: $${Math.round(r.net_worth_end).toLocaleString()}`),
    action: "Read the red pen before acting on the winner; it's only as good as the return and loan-type assumptions.", lever: "lvi" });
}
if (process.argv.includes("--stress") && cfg.lvi.stress_return != null) {
  const c2 = JSON.parse(JSON.stringify(cfg));
  c2.investments.forEach(i => i.expected_return = Math.min(+i.expected_return, +cfg.lvi.stress_return));
  if (c2.lvi.fx) c2.lvi.fx.annual_change_override = 0;
  const st = run(c2);
  out.stress = { stress_return: +cfg.lvi.stress_return, best: st.best, results: st.results };
}
base.red_pen.forEach(n => out.findings.push({ severity: n.sev, title: n.text.split(". ")[0], amount_at_stake: 0, evidence: [n.text], action: "See the red pen in the Loan vs Invest tab.", lever: "lvi" }));
fs.mkdirSync(path.join(ddir, "findings"), { recursive: true });
fs.writeFileSync(path.join(ddir, "findings", "lvi.json"), JSON.stringify(out, null, 1), { mode: 0o600 });
console.log(JSON.stringify({ best: out.best, results: out.results.map(r => [r.id, r.monthly, r.net_worth_y5, r.net_worth_end]), stress: out.stress && out.stress.results.map(r => [r.id, r.net_worth_end]), red_pen: out.red_pen.length }, null, 1));
