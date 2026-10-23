import { $, html, render, debounce } from "../dom.js";
import { api } from "../api.js";
import { inr, shortDate, longDate, cap } from "../format.js";

const STATUS_SETS = [
  { id: "all", label: "All", status: "all" },
  { id: "success", label: "Successful", status: "success" },
  { id: "failed", label: "Failed or reversed", status: "failed,reversed" },
];

let panel, ctx;
const f = { q: "", category: "", set: "success" };
let rows = [];
let selected = null;

export function mount(el, c) {
  panel = el; ctx = c;
  render(panel, html`
    <div class="two two--tape">
      <div>
        <div class="bar">
          <label class="field">Search vendor<input class="in" id="q" type="search" placeholder="Swiggy, canteen…"></label>
          <label class="field">Category
            <select class="in" id="cat"><option value="">All categories</option>
              ${ctx.categories.map(([k, l]) => html`<option value="${k}">${l}</option>`)}
            </select></label>
          <div class="seg" role="group" aria-label="Status">
            ${STATUS_SETS.map((s) => html`<button type="button" data-set="${s.id}" aria-pressed="${s.id === f.set}">${s.label}</button>`)}
          </div>
          <a class="btn" id="export" href="/api/export">Export CSV</a>
        </div>
        <div id="table" aria-live="polite"></div>
        <div class="total"><span class="muted" id="count"></span><b id="sum"></b></div>
      </div>
      <div id="tape"></div>
    </div>`);

  $("#q", panel).addEventListener("input", debounce((e) => { f.q = e.target.value.trim(); load(); }, 250));
  $("#cat", panel).addEventListener("change", (e) => { f.category = e.target.value; load(); });
  panel.addEventListener("click", (e) => {
    const seg = e.target.closest("[data-set]");
    if (seg) {
      f.set = seg.dataset.set;
      panel.querySelectorAll("[data-set]").forEach((b) => b.setAttribute("aria-pressed", b === seg));
      return load();
    }
    const row = e.target.closest("tr[data-id]");
    if (row) { selected = rows.find((r) => r.id === row.dataset.id) ?? null; drawTable(); drawTape(); }
  });
  drawTape();
}

export function show() { load(); }

const params = () => ({
  q: f.q, category: f.category,
  status: STATUS_SETS.find((s) => s.id === f.set).status,
});

async function load() {
  const host = $("#table", panel);
  try {
    const data = await api.get("/api/ledger", { ...params(), limit: 200 });
    rows = data.transactions;
    if (selected) selected = rows.find((r) => r.id === selected.id) ?? null;
    $("#export", panel).href = "/api/export?" + new URLSearchParams(Object.entries(params()).filter(([, v]) => v));
    $("#count", panel).textContent = `${data.total} ${data.total === 1 ? "row" : "rows"}${f.set === "success" ? ", successful only" : ""}`;
    $("#sum", panel).textContent = inr(data.totals.sum);
    drawTable();
    drawTape();
  } catch (err) {
    render(host, html`<p class="err">${err.message}</p>`);
  }
}

function drawTable() {
  const host = $("#table", panel);
  if (!rows.length) return render(host, html`<p class="empty">No transactions match these filters.</p>`);
  render(host, html`<div class="tablewrap"><table class="led">
    <thead><tr><th>Date</th><th>Vendor</th><th>Category</th><th>App</th><th class="amt">Amount</th></tr></thead>
    <tbody>${rows.map((r) => html`
      <tr data-id="${r.id}" class="${r.id === selected?.id ? "is-sel" : ""} ${r.status !== "success" ? "is-dim" : ""}">
        <td>${shortDate(r.datetime_local)}</td>
        <td><button type="button" class="rowbtn">${r.vendor_raw || r.vendor_normalized}</button>
          ${r.review_flag ? html`<span class="flag">review</span>` : ""}
          ${r.status !== "success" ? html`<small> ${r.status}</small>` : ""}</td>
        <td>${cap(r.category)}</td><td>${r.payment_app || "–"}</td>
        <td class="amt">${inr(r.amount)}</td>
      </tr>`)}
    </tbody></table></div>`);
}

function drawTape() {
  const host = $("#tape", panel);
  if (!selected) {
    return render(host, html`<p class="tape tape--empty">Select a row to see what was parsed, change its category, add a note, or flag it for review.</p>`);
  }
  const t = selected;
  const fields = [
    ["Document", t.doc_type], ["Status", t.status], ["Currency", t.currency],
    ["Payment app", t.payment_app ?? "–"], ["Reference", t.payment_ref ?? "–"],
    ["Source file", t.source_file ?? "–"], ["Content hash", t.content_hash ?? "–"],
    ["Confidence", t.confidence != null ? Math.round(t.confidence * 100) + "%" : "–"],
    ["GST", t.gst_amount != null ? inr(t.gst_amount) : "–"],
  ];
  render(host, html`
    <div class="tape">
      <h3>${t.vendor_raw || t.vendor_normalized}</h3>
      <p class="muted">${longDate(t.datetime_local)}</p>
      <div class="tape__sum"><span>Total</span><b>${inr(t.amount)}</b></div>
      <dl>${fields.map(([k, v]) => html`<dt>${k}</dt><dd>${v}</dd>`)}</dl>
      <label class="field">Category
        <select class="in" id="d-cat">${ctx.categories.map(([k, l]) => html`<option value="${k}" ${k === t.category ? "selected" : ""}>${l}</option>`)}</select></label>
      <label class="field">Notes<textarea class="in pen-in" id="d-notes" rows="2" placeholder="Add a note">${t.notes ?? ""}</textarea></label>
      <label class="check"><input type="checkbox" id="d-flag" ${t.review_flag ? "checked" : ""}> Flag for review</label>
      <p class="err" id="d-err" hidden></p>
      <div class="acts">
        <button class="btn btn--solid" type="button" id="d-save" style="min-height:2.5rem;font-size:.95rem">Save changes</button>
        <button class="btn btn--danger" type="button" id="d-del">Delete</button>
      </div>
    </div>`);
  $("#d-save", host).onclick = () => change(() => api.patch(`/api/ledger/${t.id}`, {
    category: $("#d-cat", host).value, notes: $("#d-notes", host).value || null, review_flag: $("#d-flag", host).checked ? 1 : 0,
  }));
  $("#d-del", host).onclick = () => {
    if (!confirm(`Delete this transaction (${t.vendor_raw})? This cannot be undone.`)) return;
    change(() => api.del(`/api/ledger/${t.id}`), true);
  };
}

async function change(action, clear = false) {
  try {
    await action();
    if (clear) selected = null;
    await load();
    ctx.refreshCounts();
  } catch (err) {
    const e = $("#d-err", panel);
    if (e) { e.textContent = err.message; e.hidden = false; }
  }
}
