import { $, html, render } from "../dom.js";
import { api } from "../api.js";
import { inr0, monthLabel, monthsBack, cap } from "../format.js";

let panel, month = null, latest = null;

export function mount(el) { panel = el; }

export async function show() {
  try {
    const { digest_month } = await api.get("/api/ledger", { limit: 1, status: "all" });
    if (digest_month !== latest) { latest = digest_month; month = digest_month; }
    await load();
  } catch (err) {
    render(panel, html`<p class="err">${err.message}</p>`);
  }
}

async function load() {
  const d = await api.get("/api/digest", { month });
  const topCat = d.by_category[0];
  const maxCat = Math.max(...d.by_category.map((c) => c.amount), 1);
  const trend = [...d.previous_months].reverse().map((m) => ({ ym: m.month, v: m.total_spend, now: false }));
  trend.push({ ym: d.month, v: d.total_spend, now: true });
  const maxTrend = Math.max(...trend.map((t) => t.v), 1);

  render(panel, html`
    <div class="dhead">
      <div><p class="muted">Monthly digest</p><h3>${monthLabel(d.month)}</h3></div>
      <label class="field">Month
        <select class="in" id="m">${monthsBack(latest, 6).map((m) => html`<option value="${m}" ${m === month ? "selected" : ""}>${monthLabel(m)}</option>`)}</select>
      </label>
    </div>
    <div class="metrics">
      <div><span>Total spend</span><b>${inr0(d.total_spend)}</b><small>${d.transaction_count} transactions</small></div>
      <div class="${d.failed_count ? "is-bad" : ""}"><span>Failed or reversed</span><b>${d.failed_count}</b><small>${d.failed_count ? "left out of totals" : "clean month"}</small></div>
      <div class="${d.review_count ? "is-warn" : ""}"><span>Flagged for review</span><b>${d.review_count}</b><small>${d.review_count ? "needs a tap" : "all confident"}</small></div>
      <div><span>Top category</span><b>${topCat ? cap(topCat.category) : "–"}</b><small>${topCat ? `${topCat.pct}%, ${inr0(topCat.amount)}` : ""}</small></div>
    </div>
    <div class="two">
      <div>
        <h3 class="cap">Spend by category</h3>
        <ul class="hbars">${d.by_category.map((c) => html`
          <li><span>${cap(c.category)}</span><span class="t"><i style="width:${(c.amount / maxCat) * 100}%"></i></span><b>${inr0(c.amount)}</b></li>`)}</ul>
        <h3 class="cap" style="margin-top:1.8rem">Last four months</h3>
        <div class="trend" role="img" aria-label="${trend.map((t) => `${monthLabel(t.ym)} ${inr0(t.v)}`).join(", ")}">
          ${trend.map((t) => html`<div class="${t.now ? "now" : ""}">
            <span>${t.v ? "₹" + (t.v / 1000).toFixed(1) + "k" : "–"}</span>
            <i style="height:${t.v ? Math.max((t.v / maxTrend) * 100, 6) : 0}%"></i>
            <span>${monthLabel(t.ym).slice(0, 3)}</span></div>`)}
        </div>
      </div>
      <div>
        <h3 class="cap">Against the trailing three-month average</h3>
        <ul class="deltas">${d.category_deltas.slice(0, 6).map((x) => html`
          <li><span>${cap(x.category)}</span><b>${inr0(x.this_month)}</b>${delta(x.delta_pct)}</li>`)}</ul>
        <h3 class="cap" style="margin-top:1.8rem">Top merchants</h3>
        <ol class="merch">${d.top_merchants.map((m, i) => html`
          <li><span class="n">${i + 1}</span><span>${m.vendor_raw}<br><small class="muted">${m.count} ${m.count === 1 ? "payment" : "payments"}</small></span><b>${inr0(m.amount)}</b></li>`)}</ol>
      </div>
    </div>
    <h3 class="cap" style="margin-top:1.8rem">Payment apps</h3>
    <p class="apps">${d.payment_apps.map((a) => html`<span><b>${a.app}</b> ${inr0(a.amount)}, ${d.total_spend ? Math.round((a.amount / d.total_spend) * 100) : 0}%</span>`)}</p>`);

  $("#m", panel).addEventListener("change", (e) => { month = e.target.value; load().catch((err) => render(panel, html`<p class="err">${err.message}</p>`)); });
}

function delta(p) {
  if (p == null) return html`<span class="d-new">new</span>`;
  const text = `${p > 0 ? "+" : ""}${Math.round(p)}%`;
  return html`<span class="${p > 5 ? "d-up" : p < -5 ? "d-down" : "d-flat"}">${text}</span>`;
}
