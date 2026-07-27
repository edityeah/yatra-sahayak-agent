import { useCallback, useEffect, useState } from "react";
import { ClipboardList, CheckCircle2, Clock } from "lucide-react";
import OfficerGate, { useOfficerKey } from "./OfficerGate.jsx";
import { adminGet, adminPost, YATRA } from "./officerApi.js";

function Inner() {
  const key = useOfficerKey();
  const [rows, setRows] = useState(null);
  const load = useCallback(() => adminGet("/api/grievances", key).then(setRows).catch(() => setRows([])), [key]);
  useEffect(() => { load(); }, [load]);
  const setStatus = async (id, status) => { await adminPost(`/api/grievances/${id}/status`, key, { status }); load(); };

  const open = (rows || []).filter((g) => (g.status || "open") !== "resolved");
  return (
    <main className="max-w-3xl w-full mx-auto px-4 py-4 space-y-2.5">
      {rows === null ? <div className="text-muted text-[13.5px] py-3">Loading…</div> : null}
      {rows && open.length === 0 ? <div className="text-center py-12 text-muted text-[13.5px]">No open grievances.</div> : null}
      {open.map((g) => (
        <div key={g.id} className="rounded-2xl border border-bdr bg-surface shadow-card p-3.5 flex items-start gap-3">
          <span className="w-8 h-8 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center flex-shrink-0"><ClipboardList size={16} /></span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[14px] font-extrabold text-ink capitalize">{g.category || "other"}</span>
              {g.status === "in_progress" ? <span className="text-[10.5px] font-bold text-blue-700 bg-blue-50 border border-blue-200 rounded-full px-2 py-0.5">In progress</span> : null}
            </div>
            <div className="text-[11px] font-mono text-muted">{g.id}</div>
            {g.description ? <p className="text-[13px] text-ink mt-0.5 break-words">{g.description}</p> : null}
            <div className="text-[12px] text-muted">{YATRA[g.yatra] || g.yatra || "—"} · 📍 {g.location || "—"}{g.reporter_phone ? ` · ☎ ${g.reporter_phone}` : ""}</div>
            <div className="mt-2 flex gap-2">
              {g.status !== "in_progress" ? (
                <button onClick={() => setStatus(g.id, "in_progress")} className="inline-flex items-center gap-1 rounded-lg border border-bdr bg-surface-2 text-ink text-[12px] font-bold px-2.5 h-8 hover:border-primary transition"><Clock size={13} /> Take up</button>
              ) : null}
              <button onClick={() => setStatus(g.id, "resolved")} className="inline-flex items-center gap-1 rounded-lg bg-green-600 text-white text-[12px] font-bold px-2.5 h-8 hover:bg-green-700 transition"><CheckCircle2 size={13} /> Resolve</button>
            </div>
          </div>
        </div>
      ))}
    </main>
  );
}

export default function OfficerGrievances() {
  return <OfficerGate title="Grievances" subtitle="Pilgrim complaints" back><Inner /></OfficerGate>;
}
