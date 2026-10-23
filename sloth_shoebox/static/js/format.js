const rupees = (n, d) =>
  (n < 0 ? "-" : "") + "₹" + Math.abs(Number(n)).toLocaleString("en-IN", { minimumFractionDigits: d, maximumFractionDigits: d });
export const inr = (n) => rupees(n, 2);
export const inr0 = (n) => rupees(n, 0);

// Stored as local wall-clock strings ("2026-10-19T21:14:00"); parse as local, never UTC.
const local = (iso) => new Date(iso.length === 10 ? iso + "T00:00:00" : iso.replace("Z", ""));
export const shortDate = (iso) => local(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
export const longDate = (iso) =>
  local(iso).toLocaleString("en-IN", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
export const stamp = (iso) =>
  new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
export const monthLabel = (ym) =>
  new Date(Number(ym.slice(0, 4)), Number(ym.slice(5, 7)) - 1, 1).toLocaleString("en-IN", { month: "long", year: "numeric" });
export const monthsBack = (ym, n) => {
  const [y, m] = ym.split("-").map(Number);
  return Array.from({ length: n }, (_, i) => {
    const d = new Date(y, m - 1 - i, 1);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  });
};
export const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
