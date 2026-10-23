import { $, $$ } from "./dom.js";
import { api } from "./api.js";
import * as inbox from "./tabs/inbox.js";
import * as ledger from "./tabs/ledger.js";
import * as digest from "./tabs/digest.js";
import * as splits from "./tabs/splits.js";
import * as query from "./tabs/query.js";
import { initDocs } from "./docs.js";

const boot = JSON.parse($("#boot").textContent);
const TABS = { inbox, ledger, digest, splits, query };
const mounted = new Set();

const ctx = {
  samples: boot.samples,
  categories: boot.categories,
  goTo: (id) => select(id, true),
  async refreshCounts() {
    try {
      const [l, i] = await Promise.all([api.get("/api/ledger", { limit: 1, status: "all" }), api.get("/api/inbox")]);
      $("#count-ledger").textContent = l.total_count;
      $("#count-inbox").textContent = i.total;
    } catch { /* counts are decorative */ }
  },
};

function select(id, focus = false) {
  for (const tab of $$('[role="tab"]')) {
    const on = tab.id === `tab-${id}`;
    tab.setAttribute("aria-selected", on);
    tab.tabIndex = on ? 0 : -1;
    if (on && focus) tab.focus();
  }
  for (const panel of $$('[role="tabpanel"]')) panel.hidden = panel.id !== `panel-${id}`;
  const mod = TABS[id];
  const panel = $(`#panel-${id}`);
  if (!mounted.has(id)) { mounted.add(id); mod.mount(panel, ctx); }
  mod.show?.();
}

const tablist = $('[role="tablist"]');
tablist.addEventListener("click", (e) => {
  const tab = e.target.closest('[role="tab"]');
  if (tab) select(tab.id.replace("tab-", ""));
});
tablist.addEventListener("keydown", (e) => {
  const tabs = $$('[role="tab"]');
  const i = tabs.indexOf(document.activeElement);
  if (i < 0) return;
  const next = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 }[e.key];
  if (next === undefined) return;
  e.preventDefault();
  select(tabs[(next + tabs.length) % tabs.length].id.replace("tab-", ""), true);
});

select("inbox");
ctx.refreshCounts();
initDocs();
