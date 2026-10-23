import { $, html, render } from "../dom.js";
import { api } from "../api.js";
import { inr } from "../format.js";

let panel;
const state = {
  people: ["Aman", "Priya", "Riya"],
  expenses: [
    { id: 1, by: "Aman", amount: "1200", among: ["Aman", "Priya", "Riya"] },
    { id: 2, by: "Priya", amount: "640", among: ["Aman", "Priya", "Riya"] },
    { id: 3, by: "Riya", amount: "480", among: ["Priya", "Riya"] },
  ],
  result: null,
  error: "",
};
let nextId = 4;

export function mount(el) {
  panel = el;
  panel.addEventListener("click", onClick);
  panel.addEventListener("input", onInput);
  panel.addEventListener("change", onInput);
  panel.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && e.target.id === "newname") { e.preventDefault(); addPerson(); }
  });
  draw();
  compute();
}

function draw() {
  const { people, expenses, result, error } = state;
  const focus = document.activeElement?.id;
  render(panel, html`
    <div class="two">
      <div>
        <h3 class="cap">People</h3>
        <div class="chips">
          ${people.map((p) => html`<span class="chip">${p}<button type="button" data-rm="${p}" aria-label="Remove ${p}">×</button></span>`)}
          <span class="addname"><input class="in" id="newname" placeholder="Add a name" aria-label="Add a person">
            <button class="btn" type="button" id="addp">Add</button></span>
        </div>
        <div class="dhead"><h3 class="cap">Expenses</h3>
          <button class="btn" type="button" id="adde" ${people.length < 2 ? "disabled" : ""}>Add expense</button></div>
        ${expenses.length === 0 ? html`<p class="empty" style="margin-top:.7rem">No expenses yet. Add one to start splitting.</p>` : ""}
        ${expenses.map((e) => html`
          <div class="exp" data-e="${e.id}">
            <div class="exp__row">
              <select class="in" data-f="by" aria-label="Paid by">${people.map((p) => html`<option ${p === e.by ? "selected" : ""}>${p}</option>`)}</select>
              <span>paid ₹</span>
              <input class="in" type="number" min="0" step="0.01" data-f="amount" value="${e.amount}" placeholder="0.00" aria-label="Amount">
              <span>split among</span>
              <button class="exp__x" type="button" data-rme="${e.id}" aria-label="Remove expense">×</button>
            </div>
            <div class="who">${people.map((p) => html`<button type="button" data-tog="${p}" aria-pressed="${e.among.includes(p)}">${p}</button>`)}</div>
          </div>`)}
        <p style="margin-top:1rem"><button class="btn btn--solid" type="button" id="go" style="min-height:2.6rem;font-size:1rem">Compute settlement</button></p>
        ${error ? html`<p class="err" style="margin-top:.7rem">${error}</p>` : ""}
      </div>
      <div>
        <h3 class="cap">Simplified debts</h3>
        <p class="muted">The largest creditor is matched with the largest debtor, which cuts every owed payment down to the fewest transfers.</p>
        ${result ? html`
          <p class="dhead" style="margin-top:1rem"><span class="muted">Total spend</span><b class="amt" style="font-size:1.8rem">${inr(result.total_spend)}</b></p>
          <h3 class="cap" style="margin-top:1rem">Settle up</h3>
          ${result.settlements.length === 0
            ? html`<p class="muted">Everyone is settled. No transfers needed.</p>`
            : html`<ul class="settle">${result.settlements.map((s) => html`<li><b>${s.from}</b> pays <b>${s.to}</b><b class="amt">${inr(s.amount)}</b></li>`)}</ul>`}
          <h3 class="cap" style="margin-top:1.4rem">Per-person balance</h3>
          <table class="pp"><thead><tr><th>Person</th><th>Paid</th><th>Share</th><th>Net</th></tr></thead><tbody>
            ${result.per_person.map((p) => html`<tr><td>${p.participant}</td><td>${inr(p.paid)}</td><td>${inr(p.share)}</td>
              <td class="${p.net > 0.005 ? "pos" : p.net < -0.005 ? "neg" : ""}">${p.net > 0 ? "+" : ""}${inr(p.net)}</td></tr>`)}
          </tbody></table>`
        : html`<p class="empty" style="margin-top:1rem">Add people and expenses, then compute.</p>`}
      </div>
    </div>`);
  if (focus) document.getElementById(focus)?.focus();
}

function addPerson() {
  const name = $("#newname", panel).value.trim();
  if (!name || state.people.includes(name)) return;
  state.people.push(name);
  draw();
  $("#newname", panel).focus();
}

function onClick(e) {
  const t = e.target;
  const rm = t.closest("[data-rm]");
  if (rm) {
    const name = rm.dataset.rm;
    state.people = state.people.filter((p) => p !== name);
    state.expenses = state.expenses.filter((x) => x.by !== name).map((x) => ({ ...x, among: x.among.filter((p) => p !== name) }));
    return draw();
  }
  if (t.closest("#addp")) return addPerson();
  if (t.closest("#adde")) {
    state.expenses.push({ id: nextId++, by: state.people[0], amount: "", among: [...state.people] });
    return draw();
  }
  const rme = t.closest("[data-rme]");
  if (rme) { state.expenses = state.expenses.filter((x) => x.id !== Number(rme.dataset.rme)); return draw(); }
  const tog = t.closest("[data-tog]");
  if (tog) {
    const ex = state.expenses.find((x) => x.id === Number(tog.closest("[data-e]").dataset.e));
    const who = tog.dataset.tog;
    ex.among = ex.among.includes(who) ? ex.among.filter((p) => p !== who) : [...ex.among, who];
    return draw();
  }
  if (t.closest("#go")) compute();
}

function onInput(e) {
  const field = e.target.dataset.f;
  if (!field) return;
  const ex = state.expenses.find((x) => x.id === Number(e.target.closest("[data-e]").dataset.e));
  ex[field] = e.target.value;
}

async function compute() {
  const valid = state.expenses
    .filter((x) => Number(x.amount) > 0 && x.among.length > 0)
    .map((x) => ({ paid_by: x.by, amount: Number(x.amount), split_among: x.among }));
  if (!valid.length) {
    state.error = "Add at least one expense with an amount and someone to split it with.";
    state.result = null;
    return draw();
  }
  try {
    state.result = await api.post("/api/splits/settle", { participants: state.people, expenses: valid });
    state.error = "";
  } catch (err) {
    state.error = err.message;
    state.result = null;
  }
  draw();
}
