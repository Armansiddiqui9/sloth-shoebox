import { $, $$, html, render, raw } from "../dom.js";
import { api } from "../api.js";
import { inr, stamp } from "../format.js";

const STEPS = ["Dedupe", "Parse", "Validate", "Commit"];
const STATUS = { committed: "Committed", review: "Needs review", quarantined: "Quarantined" };
const KIND = { upi_screenshot: "UPI screenshot", receipt_photo: "Receipt photo", pdf_bill: "PDF bill" };
const MSG = {
  0: "Hashing the artifact and checking for duplicates.",
  1: "Sending it to the local vision model.",
  2: "Checking the result against the schema.",
};

let panel, ctx;
let runs = [];
let seq = 0;

export function mount(el, c) {
  panel = el; ctx = c;
  render(panel, html`
    <div class="two">
      <div>
        <h3 class="cap">Sample artifacts</h3>
        <p class="muted">The kinds of files the app watches for. Pick one to send it through the pipeline, or drop your own file below.</p>
        <div class="thumbs">
          ${ctx.samples.map((s) => html`
            <button class="thumb" type="button" draggable="true" data-sample="${s.id}">
              <img src="${s.url}" alt="" loading="lazy">
              <b>${s.label}</b><span>${KIND[s.kind]}</span>
            </button>`)}
        </div>
        <button class="drop" type="button" id="drop">
          <b>Drop a screenshot or receipt here</b>
          <span class="muted">or choose a file. It never leaves this machine.</span>
        </button>
        <input type="file" id="pick" accept="image/*,.pdf" hidden>
      </div>
      <div>
        <h3 class="cap">Pipeline</h3>
        <p class="muted">Dedupe, parse, validate, then commit, review or quarantine.</p>
        <div class="runs" id="runs" aria-live="polite"></div>
        <h3 class="cap" style="margin-top:1.8rem">Earlier in the inbox</h3>
        <div id="recent"></div>
      </div>
    </div>`);

  panel.addEventListener("click", (e) => {
    const thumb = e.target.closest("[data-sample]");
    if (thumb) return ingestSample(thumb.dataset.sample);
    if (e.target.closest("#drop")) return $("#pick", panel).click();
    const go = e.target.closest("[data-go-ledger]");
    if (go) ctx.goTo("ledger");
  });
  panel.addEventListener("dragstart", (e) => {
    const thumb = e.target.closest("[data-sample]");
    if (thumb) { e.dataTransfer.setData("text/plain", thumb.dataset.sample); e.dataTransfer.effectAllowed = "copy"; }
  });
  const drop = $("#drop", panel);
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("is-over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("is-over"));
  drop.addEventListener("drop", (e) => {
    e.preventDefault();
    drop.classList.remove("is-over");
    const files = [...e.dataTransfer.files];
    if (files.length) return files.forEach(ingestFile);
    const id = e.dataTransfer.getData("text/plain");
    if (ctx.samples.some((s) => s.id === id)) ingestSample(id);
  });
  $("#pick", panel).addEventListener("change", (e) => {
    [...e.target.files].forEach(ingestFile);
    e.target.value = "";
  });
  drawRuns();
  loadRecent();
}

export function show() { loadRecent(); }

function ingestSample(id) {
  const label = ctx.samples.find((s) => s.id === id)?.label ?? id;
  track(label, () => api.post("/api/ingest", { sample_id: id }));
}
function ingestFile(file) { track(file.name, () => api.upload("/api/ingest/upload", file)); }

async function track(label, send) {
  const run = { id: ++seq, label, step: 0, final: null };
  runs = [run, ...runs].slice(0, 4);
  drawRuns();
  // The request is synchronous; the stage track is paced so each step can be seen.
  const timer = setInterval(() => { if (run.step < 2) { run.step += 1; drawRuns(); } }, 380);
  const started = Date.now();
  try {
    const data = await send();
    await new Promise((r) => setTimeout(r, Math.max(0, 1100 - (Date.now() - started))));
    run.final = data.artifact.stage;
    run.tx = data.transaction;
    run.reason = data.quarantined?.reason;
  } catch (err) {
    run.final = "quarantined";
    run.reason = err.message;
  } finally {
    clearInterval(timer);
  }
  drawRuns();
  loadRecent();
  ctx.refreshCounts();
}

function drawRuns() {
  const host = $("#runs", panel);
  if (!runs.length) {
    render(host, html`<p class="empty">Pick an artifact to watch the pipeline run.</p>`);
    return;
  }
  render(host, html`${runs.map((r) => {
    const done = r.final !== null;
    const reached = (i) => (done ? r.final !== "quarantined" || i < 3 : i <= r.step);
    return html`
      <div class="run ${done ? "run--" + r.final : ""}">
        <div class="run__top"><span>${r.label}</span>
          ${done ? html`<span class="pill pill--${r.final}">${STATUS[r.final]}</span>` : html`<span class="pill">Running</span>`}
        </div>
        <div class="track" aria-hidden="true">
          ${STEPS.map((_, i) => html`<i class="${reached(i) ? "on" : ""} ${!done && i === r.step ? "now" : ""}"></i>`)}
        </div>
        <div class="track-labels" aria-hidden="true">${STEPS.map((s) => html`<span>${s}</span>`)}</div>
        <div class="run__body">${body(r, done)}</div>
      </div>`;
  })}`);
}

function body(r, done) {
  if (!done) return MSG[r.step];
  if (r.final === "quarantined") return html`<b>Quarantined.</b> ${r.reason || "Schema validation failed after re-ask."}`;
  const t = r.tx;
  const pct = Math.round((t.confidence ?? 0) * 100);
  return html`
    <b>${t.vendor_raw}</b>, ${t.category}. <span class="run__amt">${inr(t.amount)}</span><br>
    ${r.final === "review"
      ? html`Confidence is ${pct}%, so the row is committed but flagged for a one-tap confirm.`
      : html`Confidence ${pct}%.`}
    <button type="button" class="linkbtn" data-go-ledger>See it in the ledger</button>`;
}

async function loadRecent() {
  const host = $("#recent", panel);
  if (!host) return;
  try {
    const { artifacts } = await api.get("/api/inbox");
    render(host, artifacts.length
      ? html`<table class="mini"><tbody>${artifacts.slice(0, 6).map((a) => html`
          <tr><td>${a.file_name}</td><td><span class="pill pill--${a.stage}">${STATUS[a.stage] ?? a.stage}</span></td><td>${stamp(a.created_at)}</td></tr>`)}
        </tbody></table>`
      : html`<p class="empty">Nothing processed yet.</p>`);
  } catch (err) {
    render(host, html`<p class="err">${err.message}</p>`);
  }
}
