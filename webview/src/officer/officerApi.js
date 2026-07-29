// Shared helpers for the officer war-room (chat agent + activity webviews).
// Everything is gated by the ADMIN_API_KEY, held in sessionStorage — so
// pilgrim PII isn't behind the browser-shipped key.
const BASE = import.meta.env.VITE_AGENT_URL || "http://localhost:8000";
export const SS_KEY = "ysahayak.officerKey";

export const getKey = () => { try { return sessionStorage.getItem(SS_KEY) || ""; } catch { return ""; } };
export const setKey = (k) => { try { sessionStorage.setItem(SS_KEY, k); } catch { /* */ } };

export async function adminGet(path, key) {
  const r = await fetch(`${BASE}${path}`, { headers: { "X-API-Key": key } });
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
}
// Download an admin CSV export (fetch as a blob so we can send the key header,
// which a plain <a download> can't do).
export async function adminDownloadCsv(path, key, filename = "export.csv") {
  const r = await fetch(`${BASE}${path}`, { headers: { "X-API-Key": key } });
  if (!r.ok) throw new Error(String(r.status));
  const blob = await r.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; document.body.appendChild(a); a.click();
  a.remove(); URL.revokeObjectURL(url);
}

export async function adminPost(path, key, body) {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST", headers: { "Content-Type": "application/json", "X-API-Key": key },
    body: JSON.stringify(body || {}),
  });
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
}
// Officer ops chat — POST /officer/messages (SSE), parse the single delta.
export async function officerAsk(text, key) {
  const r = await fetch(`${BASE}/officer/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Admin-Key": key },
    body: JSON.stringify({ user_id: "officer-web", message: { content: [{ type: "text", text: { value: text } }] } }),
  });
  if (!r.ok) throw new Error(String(r.status));
  const txt = await r.text();
  let out = "";
  for (const frame of txt.split(/\r?\n\r?\n/)) {
    const ev = frame.split("\n").find((l) => l.startsWith("event:"))?.slice(6).trim();
    const data = frame.split("\n").find((l) => l.startsWith("data:"))?.slice(5).trim();
    if (ev === "delta" && data) {
      try { const d = JSON.parse(data); if (d.o === "append") out += d.v; } catch { /* */ }
    }
  }
  return out;
}

export const YATRA = { pandharpur: "Pandharpur Wari", kumbh: "Simhastha Kumbh" };
