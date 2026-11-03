// ---------- Loan vs Invest tab: built only from the loans/investments you gave in onboarding ----------
const lviClone = o => JSON.parse(JSON.stringify(o));
const pct = v => (v * 100).toFixed(2).replace(/\.?0+$/, "") + "%";
const k0 = v => (v < 0 ? "-$" : "$") + (Math.abs(v) >= 1e6 ? (Math.abs(v) / 1e6).toFixed(2) + "M" : Math.round(Math.abs(v) / 1000) + "K");
const SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#d29a00", "#e87ba4"];
const lviCfg = () => (LV ||= { ...lviClone(PLAN.lvi), sel: 0 });

function lviChart(res, N) {
  const W = 820, H = 280, m = { l: 60, r: 170, t: 12, b: 26 };
  const all = res.flatMap(x => x.rows.slice(0, N + 1).map(r => r.nw));
  const lo = Math.min(0, ...all), hi = Math.max(1, ...all), raw = (hi - lo) / 5, p = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map(f => f * p).find(s => s >= raw);
  const y0 = Math.floor(lo / step) * step, y1 = Math.ceil(hi / step) * step;
  const X = i => m.l + i * (W - m.l - m.r) / N, Y = v => m.t + (H - m.t - m.b) * (1 - (v - y0) / (y1 - y0));
  let s = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto" role="img" aria-label="Net worth by scenario">`;
  for (let v = y0; v <= y1 + 1; v += step) s += `<line x1="${m.l}" x2="${W - m.r}" y1="${Y(v)}" y2="${Y(v)}" stroke="${v === 0 ? "#999" : "#e5e5e5"}"/><text x="${m.l - 6}" y="${Y(v) + 4}" font-size="10" text-anchor="end" fill="#777">${k0(v)}</text>`;
  for (let yr = 0; yr <= N / 12; yr++) s += `<text x="${X(yr * 12)}" y="${H - 8}" font-size="10" text-anchor="middle" fill="#777">${yr ? "Y" + yr : "Now"}</text>`;
  const ends = [];
  res.forEach((x, i) => { s += `<path d="${x.rows.slice(0, N + 1).map((r, j) => `${j ? "L" : "M"}${X(j).toFixed(1)},${Y(r.nw).toFixed(1)}`).join("")}" fill="none" stroke="${SERIES[i % 5]}" stroke-width="2"/>`; ends.push({ y: Y(x.yN.nw), i, v: x.yN.nw, id: x.id }); });
  ends.sort((a, b) => a.y - b.y); let prev = -1e9;
  ends.forEach(e => { const ly = Math.max(e.y, prev + 14); prev = ly;
    s += `<circle cx="${X(N)}" cy="${e.y}" r="4" fill="${SERIES[e.i % 5]}" stroke="#fff" stroke-width="2"/>` + (Math.abs(ly - e.y) > 2 ? `<line x1="${X(N) + 5}" y1="${e.y}" x2="${W - m.r + 6}" y2="${ly}" stroke="#bbb"/>` : "")
      + `<text x="${W - m.r + 8}" y="${ly + 4}" font-size="11" fill="#333">${e.id}: ${k0(e.v)}</text>`; });
  return s + "</svg>";
}

function lviView() {
  const C = lviCfg(), cfg = { loans: C.loans, investments: C.investments, lvi: C.lvi };
  const g = lviSettings(cfg), sc = lviScenarios(cfg, g), cmp = lviCompare(cfg, g, sc), N = Math.round(g.years * 12), notes = lviRedPen(cfg, g);
  const best = cmp.best, cur = cmp.res.find(x => x.id === "C");
  const sel = cmp.res[C.sel] || cmp.res[0], yrs = [...Array(Math.floor(N / 12) + 1).keys()];
  const inp = (path, v, isPct, w = 90) => `<input class="num" style="max-width:${w}px" type="number" step="any" data-l="${path}" ${isPct ? "data-pct" : ""} value="${v == null ? "" : isPct ? +(v * 100).toFixed(4) : v}">`;
  const pick = (path, v, opts) => `<select data-l="${path}" style="width:auto">${opts.map(o => `<option ${o === v ? "selected" : ""}>${o}</option>`).join("")}</select>`;
  const sevCol = { serious: "#ec835a", warning: "#d29a00", verify: "#7a5b00" };
  $("view").innerHTML = `<h1>Loan vs Invest</h1><p class="sub">Built from your loans and investments. Same engine as the classic spreadsheet, so the numbers match it. Yellow = edit. ${help("loans")}</p>
  <div class="roastbar">🏆 ${esc(best.name)} wins at ${g.years} years: ${money(best.yN.nw)} net worth.${cur && cur.id !== best.id ? ` What you pay now (C) is ${money(best.yN.nw - cur.yN.nw)} behind.` : ""}</div>
  <div class="panel"><div class="sec">COMPARISON</div><table><tr><th>Scenario</th><th class="n">$/mo</th><th class="n">Net worth Y5</th><th class="n">Net worth Y${g.years}</th><th class="n">Interest paid</th>${C.loans.map(l => `<th class="n">${esc(l.name)} paid off</th>`).join("")}</tr>
  ${cmp.res.map((x, i) => `<tr><td style="white-space:nowrap"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${SERIES[i % 5]};margin-right:6px"></span>${esc(x.name)}${x.id === best.id ? " 🏆" : ""}${cmp.comparable.includes(x.id) ? "" : ' <span class="info">(smaller budget, not ranked)</span>'}</td>
    <td class="n">${money(x.total)}</td><td class="n">${money(x.y5.nw)}</td><td class="n"><b>${money(x.yN.nw)}</b></td><td class="n">${money(x.yN.cumInt)}</td>${x.payoff.map(p => `<td class="n">${p ? "Month " + p : "Not in " + g.years + "y"}</td>`).join("")}</tr>`).join("")}</table>
  <div style="max-width:1000px;margin-top:10px">${lviChart(cmp.res, N)}</div></div>
  <div class="cols" style="margin-top:12px"><div class="panel"><div class="sec">🖍️ RED PEN</div>
  <div style="display:flex;gap:6px;flex-wrap:wrap;margin:8px 0">${C.lvi.stress_return != null ? `<button class="btn" id="lvi-stress">Stress test: returns ≤ ${pct(+C.lvi.stress_return)}${g.fxCurrency ? ", flat currency" : ""}</button>` : ""}<button class="btn ghost" id="lvi-reset">Reset to my answers</button></div>
  <ol class="rules">${notes.map(n => `<li style="color:${sevCol[n.sev] || "#333"}">${esc(n.text)}</li>`).join("") || "<li>No red flags in your assumptions.</li>"}</ol>
  <p class="info">Not investment advice: arithmetic on your assumptions. Gains are pre-tax.</p></div>
  <div class="panel"><div class="sec">YEAR BY YEAR: <select id="lvi-sel" style="width:auto;background:#fff;color:#111">${cmp.res.map((x, i) => `<option value="${i}" ${i === C.sel ? "selected" : ""}>${esc(x.name)}</option>`).join("")}</select></div>
  <div style="overflow:auto"><table><tr><th>Metric</th>${yrs.map(y => `<th class="n">${y ? "Y" + y : "Now"}</th>`).join("")}</tr>
  ${C.loans.map((l, k) => `<tr><td>${esc(l.name)}</td>${yrs.map(y => `<td class="n">${money(sel.rows[y * 12].bal[k])}</td>`).join("")}</tr>`).join("")}
  ${[["Portfolio", r => r.inv], ["Invested", r => r.invested], ["NET WORTH", r => r.nw], ["Interest paid", r => r.cumInt]].map(([lab, f]) => `<tr class="${lab === "NET WORTH" ? "total" : ""}"><td>${lab}</td>${yrs.map(y => `<td class="n">${money(f(sel.rows[y * 12]))}</td>`).join("")}</tr>`).join("")}
  </table></div></div></div>
  <div class="cols" style="margin-top:12px"><div class="panel"><div class="sec">LOANS ${help("loans")}</div><div style="overflow:auto"><table><tr><th>Name</th><th>Cur</th><th class="n">Balance</th><th class="n">Rate %</th><th>Interest type</th><th class="n">Minimum</th><th class="n">You pay</th></tr>
  ${C.loans.map((l, k) => `<tr><td>${esc(l.name)}</td><td>${esc(l.currency)}</td><td class="n">${inp(`loans.${k}.outstanding`, l.outstanding, false, 100)}</td><td class="n">${inp(`loans.${k}.rate`, l.rate, true, 60)}</td><td>${pick(`loans.${k}.type`, l.type, ["Compound", "Simple-flat", "Simple-rebate"])}</td><td class="n">${inp(`loans.${k}.min_payment`, l.min_payment, false, 80)}</td><td class="n">${inp(`loans.${k}.current_payment`, l.current_payment, false, 80)}</td></tr>`).join("")}</table></div>
  <div class="sec">SETTINGS</div><table>
  <tr><td>Monthly budget for loans + investing</td><td class="n">${inp("lvi.monthly_budget", C.lvi.monthly_budget)}</td></tr>
  <tr><td>What you invest today ($/mo)</td><td class="n">${inp("lvi.current_investing_monthly", C.lvi.current_investing_monthly)}</td></tr>
  <tr><td>Horizon (years)</td><td class="n">${inp("lvi.years", C.lvi.years)}</td></tr>
  <tr><td>Contribution step-up per year</td><td class="n">${inp("lvi.step_up", C.lvi.step_up || 0, true, 60)}</td></tr>
  ${g.fxCurrency ? `<tr><td>${esc(g.fxCurrency)} change per year (blank = from history: ${pct(lviFx(g).dep)})</td><td class="n">${inp("lvi.fx.annual_change_override", C.lvi.fx.annual_change_override, true, 70)}</td></tr>
  <tr><td>Track ${esc(g.fxCurrency)} loans in ${esc(g.fxCurrency)}</td><td class="n"><input type="checkbox" id="lvi-fxaware" style="width:auto" ${C.lvi.fx.track_in_loan_currency ? "checked" : ""}></td></tr>` : ""}
  </table></div><div class="panel"><div class="sec">INVESTMENTS ${help("investments")}</div><table><tr><th>Name</th><th class="n">Expected return %</th><th class="n">Weight</th></tr>
  ${C.investments.map((v, j) => `<tr><td>${esc(v.name)}</td><td class="n">${inp(`investments.${j}.expected_return`, v.expected_return, true, 70)}</td><td class="n">${inp(`investments.${j}.weight`, v.weight, false, 60)}</td></tr>`).join("")}</table></div></div>`;
  document.querySelectorAll("[data-l]").forEach(el => el.onchange = () => {
    const parts = el.dataset.l.split("."), last = parts.pop(); let o = C;
    parts.forEach(p => o = o[isNaN(p) ? p : +p]);
    let v = el.tagName === "SELECT" ? el.value : (el.value === "" ? null : +el.value);
    if (v != null && el.hasAttribute("data-pct") && el.tagName !== "SELECT") v = v / 100;
    o[last] = v; save(); render();
  });
  $("lvi-sel").onchange = e => { C.sel = +e.target.value; save(); render(); };
  if ($("lvi-fxaware")) $("lvi-fxaware").onchange = e => { C.lvi.fx.track_in_loan_currency = e.target.checked; save(); render(); };
  if ($("lvi-stress")) $("lvi-stress").onclick = () => { C.investments.forEach(i => i.expected_return = Math.min(+i.expected_return, +C.lvi.stress_return)); if (C.lvi.fx) C.lvi.fx.annual_change_override = 0; save(); render(); };
  $("lvi-reset").onclick = () => { LV = { ...lviClone(PLAN.lvi), sel: 0 }; save(); render(); };
}
