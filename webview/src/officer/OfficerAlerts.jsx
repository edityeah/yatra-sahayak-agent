import { useCallback, useEffect, useState } from "react";
import { Megaphone, Send, XCircle } from "lucide-react";
import OfficerGate, { useOfficerKey } from "./OfficerGate.jsx";
import { adminGet, adminPost, YATRA } from "./officerApi.js";

const SEV = { info: "bg-blue-50 text-blue-700 border-blue-200", warning: "bg-amber-50 text-amber-700 border-amber-200", danger: "bg-red-50 text-red-700 border-red-200" };

function Inner() {
  const key = useOfficerKey();
  const [rows, setRows] = useState(null);
  const [f, setF] = useState({ title: "", message: "", severity: "warning", yatra: "" });
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => adminGet("/api/alerts", key).then(setRows).catch(() => setRows([])), [key]);
  useEffect(() => { load(); }, [load]);

  const send = async () => {
    if (!f.title.trim() || !f.message.trim() || busy) return;
    setBusy(true);
    try { await adminPost("/api/alerts", key, { ...f, yatra: f.yatra || null }); setF({ title: "", message: "", severity: "warning", yatra: "" }); load(); }
    finally { setBusy(false); }
  };
  const deactivate = async (id) => { await adminPost(`/api/alerts/${id}/deactivate`, key, {}); load(); };
  const set = (k) => (e) => setF((s) => ({ ...s, [k]: e.target.value }));

  return (
    <main className="max-w-3xl w-full mx-auto px-4 py-4 space-y-4">
      <div className="rounded-2xl border border-bdr bg-surface shadow-card p-4 space-y-3">
        <div className="text-[14px] font-extrabold text-ink flex items-center gap-2"><Megaphone size={16} className="text-primary" /> Broadcast an alert to pilgrims</div>
        <input value={f.title} onChange={set("title")} placeholder="Title (e.g. Heavy rain warning)" className="w-full h-10 rounded-xl border border-bdr bg-surface px-3 text-[14px] outline-none focus:border-primary" />
        <textarea value={f.message} onChange={set("message")} placeholder="Message shown to pilgrims" rows={3} className="w-full rounded-xl border border-bdr bg-surface px-3 py-2 text-[14px] outline-none focus:border-primary" />
        <div className="flex gap-2">
          <select value={f.severity} onChange={set("severity")} className="h-10 rounded-xl border border-bdr bg-surface px-3 text-[13.5px]">
            <option value="info">Info</option><option value="warning">Warning</option><option value="danger">Danger</option>
          </select>
          <select value={f.yatra} onChange={set("yatra")} className="h-10 rounded-xl border border-bdr bg-surface px-3 text-[13.5px]">
            <option value="">All yatras</option><option value="pandharpur">Pandharpur Wari</option><option value="kumbh">Simhastha Kumbh</option>
          </select>
        </div>
        <button onClick={send} disabled={busy} className="w-full h-11 rounded-full bg-primary text-white font-extrabold flex items-center justify-center gap-2 disabled:opacity-60 hover:bg-primary-700 transition"><Send size={16} /> {busy ? "Sending…" : "Send alert"}</button>
      </div>

      <div className="space-y-2.5">
        <div className="text-[12px] font-bold uppercase tracking-wide text-muted">Active alerts</div>
        {rows === null ? <div className="text-muted text-[13.5px]">Loading…</div> : null}
        {rows && rows.length === 0 ? <div className="text-center py-8 text-muted text-[13.5px]">No active alerts.</div> : null}
        {(rows || []).map((a) => (
          <div key={a.id} className="rounded-2xl border border-bdr bg-surface shadow-card p-3.5 flex items-start gap-3">
            <span className={`text-[10.5px] font-bold rounded-full border px-2 py-0.5 flex-shrink-0 capitalize ${SEV[a.severity] || SEV.info}`}>{a.severity}</span>
            <div className="flex-1 min-w-0">
              <div className="text-[14px] font-extrabold text-ink">{a.title}</div>
              <p className="text-[13px] text-ink break-words">{a.message}</p>
              <div className="text-[11.5px] text-muted">{a.yatra ? (YATRA[a.yatra] || a.yatra) : "All yatras"} · {a.id}</div>
            </div>
            <button onClick={() => deactivate(a.id)} className="flex-shrink-0 inline-flex items-center gap-1 rounded-lg border border-bdr bg-surface-2 text-ink text-[12px] font-bold px-2.5 h-8 hover:border-red-400 transition"><XCircle size={13} /> End</button>
          </div>
        ))}
      </div>
    </main>
  );
}

export default function OfficerAlerts() {
  return <OfficerGate title="Alerts" subtitle="Broadcast to pilgrims" back><Inner /></OfficerGate>;
}
