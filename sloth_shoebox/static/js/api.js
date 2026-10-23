// Thin fetch wrapper. Errors carry the server's `detail` message.

async function call(method, path, { params, json, body } = {}) {
  let url = path;
  if (params) {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") q.set(k, v);
    const s = q.toString();
    if (s) url += "?" + s;
  }
  const init = { method, headers: {} };
  if (json !== undefined) { init.headers["Content-Type"] = "application/json"; init.body = JSON.stringify(json); }
  if (body) init.body = body;
  let res;
  try { res = await fetch(url, init); } catch { throw new Error("Can't reach the local server. Is it still running?"); }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data.detail;
    throw new Error(typeof d === "string" ? d : Array.isArray(d) ? d.map((e) => e.msg).join("; ") : `Request failed (${res.status})`);
  }
  return data;
}

export const api = {
  get: (path, params) => call("GET", path, { params }),
  post: (path, json) => call("POST", path, { json }),
  patch: (path, json) => call("PATCH", path, { json }),
  del: (path) => call("DELETE", path),
  upload: (path, file) => { const f = new FormData(); f.append("file", file); return call("POST", path, { body: f }); },
};
