import { useCallback, useEffect, useState } from "react";
import { Siren, CheckCircle2 } from "lucide-react";
import OfficerGate, { useOfficerKey } from "./OfficerGate.jsx";
import { adminGet, adminPost, YATRA } from "./officerApi.js";

function Inner() {
  const key = useOfficerKey();
  const [rows, setRows] = useState(null);
  const load = useCallback(() => adminGet("/api/sos?status=open", key).then(setRows).catch(() => setRows([])), [key]);
  useEffect(() => { load(); }, [load]);
  const resolve = async (id) => { await adminPost(`/api/sos/${id}/status`, key, { status: "resolved" }); load(); };
  return (
    <main className="max-w-3xl w-full mx-auto px-4 py-4 space-y-2.5">
      {rows === null ? <div className="text-muted text-[13.5px] py-3">Loading…</div> : null}
      {rows && rows.length === 0 ? <div className="text-center py-12 text-muted text-[13.5px]">No open SOS.</div> : null}
      {(rows || []).map((s) => (
        <div key={s.id} className="rounded-2xl border border-bdr bg-surface shadow-card p-3.5 flex items-start gap-3">
          <span className="w-8 h-8 rounded-full bg-red-100 text-red-600 flex items-center justify-center flex-shrink-0"><Siren size={16} /></span>
          <div className="flex-1 min-w-0">
            <div className="text-[14px] font-extrabold text-ink">{s.nature || "SOS"}</div>
            <div className="text-[11px] font-mono text-muted">{s.id}</div>
            <div className="text-[12.5px] text-ink mt-0.5">{YATRA[s.yatra] || s.yatra || "—"} · 📍 {s.location || "—"}</div>
          </div>
          <button onClick={() => resolve(s.id)} className="flex-shrink-0 inline-flex items-center gap-1 rounded-lg bg-green-600 text-white text-[12px] font-bold px-2.5 h-8 hover:bg-green-700 transition">
            <CheckCircle2 size={13} /> Resolve
          </button>
        </div>
      ))}
    </main>
  );
}

export default function OfficerSos() {
  return <OfficerGate title="SOS feed" subtitle="Open emergencies" back><Inner /></OfficerGate>;
}
