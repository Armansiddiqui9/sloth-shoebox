import { $, html, render } from "../dom.js";
import { api } from "../api.js";

const SUGGESTED = [
  "How much did I spend on food this month?",
  "What are my top 3 merchants?",
  "Which subscriptions am I paying for?",
  "How does this month compare to last month?",
  "What's my biggest expense category?",
  "Am I spending more on travel than usual?",
];

let panel;
const thread = [];
let busy = false;

export function mount(el) {
  panel = el;
  render(panel, html`
    <div class="two">
      <div>
        <h3 class="cap">Ask your ledger</h3>
        <p class="muted">Ask in plain English. If Ollama is running, a small local model reads your ledger. If not, a built-in rules engine answers the common questions. Nothing goes to the cloud either way.</p>
        <form class="ask" id="form">
          <label class="field" for="qa">Your question</label>
          <textarea class="in" id="qa" rows="3" placeholder="How much did I spend on Swiggy last week?"></textarea>
          <button class="btn btn--solid" type="submit" id="send" style="min-height:2.6rem;font-size:1rem">Ask</button>
        </form>
        <h3 class="cap" style="margin-top:1.4rem">Try one</h3>
        <div class="sugg">${SUGGESTED.map((s) => html`<button type="button" data-q="${s}">${s}</button>`)}</div>
      </div>
      <div>
        <h3 class="cap">Answers</h3>
        <div class="thread" id="thread" aria-live="polite"></div>
      </div>
    </div>`);
  $("#form", panel).addEventListener("submit", (e) => { e.preventDefault(); ask($("#qa", panel).value); });
  $("#qa", panel).addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(e.target.value); }
  });
  panel.addEventListener("click", (e) => {
    const b = e.target.closest("[data-q]");
    if (b) ask(b.dataset.q);
  });
  draw();
}

async function ask(text) {
  const q = text.trim();
  if (!q || busy) return;
  busy = true;
  $("#send", panel).disabled = true;
  $("#qa", panel).value = "";
  thread.unshift({ q, pending: true });
  draw();
  try {
    const r = await api.post("/api/query", { question: q });
    Object.assign(thread[0], { pending: false, a: r.answer, engine: r.engine, ms: r.query_ms });
  } catch (err) {
    Object.assign(thread[0], { pending: false, error: err.message });
  }
  busy = false;
  $("#send", panel).disabled = false;
  thread.splice(12);
  draw();
}

function who(engine) {
  return engine === "rules"
    ? "Answered by the built-in rules engine. Start Ollama to use a local model."
    : `Answered by ${engine.replace("ollama:", "")} on this machine.`;
}

function draw() {
  const host = $("#thread", panel);
  if (!thread.length) return render(host, html`<p class="empty">Ask a question to see the answer here.</p>`);
  render(host, html`${thread.map((t) => html`
    <div><p class="q">${t.q}</p>
      ${t.pending ? html`<p class="a muted">Reading the ledger…</p>`
        : t.error ? html`<p class="err">${t.error}</p>`
        : html`<div class="a"><span class="pen-in">${t.a}</span><small>${who(t.engine)} ${t.ms.toLocaleString("en-IN")} ms.</small></div>`}
    </div>`)}`);
}
