import { $$ } from "./dom.js";

// Mark the contents link for the heading nearest the top of the viewport.
export function initDocs() {
  const links = new Map($$(".docs__toc a").map((a) => [a.getAttribute("href").slice(1), a]));
  const headings = [...links.keys()].map((id) => document.getElementById(id)).filter(Boolean);
  if (!headings.length || !("IntersectionObserver" in window)) return;
  const seen = new Set();
  const paint = () => {
    const first = headings.find((h) => seen.has(h.id));
    if (!first) return;
    for (const [id, a] of links) {
      if (id === first.id) a.setAttribute("aria-current", "true");
      else a.removeAttribute("aria-current");
    }
  };
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) (e.isIntersecting ? seen.add(e.target.id) : seen.delete(e.target.id));
    paint();
  }, { rootMargin: "-80px 0px -70% 0px" });
  headings.forEach((h) => io.observe(h));
}
