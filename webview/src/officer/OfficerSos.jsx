import { useCallback, useEffect, useState } from "react";
import { Siren, CheckCircle2, PhoneForwarded, Truck, Landmark } from "lucide-react";
import OfficerGate, { useOfficerKey } from "./OfficerGate.jsx";
import { adminGet, adminPost, YATRA } from "./officerApi.js";

// Escalation lifecycle. Each status → how it reads + the next action.
const FLOW = {
  open:         { label: "Sent to control room", tone: "red",   next: "acknowledged", action: "Acknowledge", icon: PhoneForwarded },
  acknowledged: { label: "Acknowledged",         tone: "amber", next: "dispatched",   action: "Dispatch unit", icon: Truck },
  dispatched:   { label: "Responder dispatched", tone: "blue",  next: "resolved",     action: "Resolve", icon: CheckCircle2 },
  resolved:     { label: "Resolved",             tone: "green", next: null,           action: null, icon: CheckCircle2 },
};
const TONE = {
  red: "bg-red-100 text-red-700", amber: "bg-amber-100 text-amber-800",
  blue: "bg-blue-100 text-blue-700", green: "bg-green-100 text-green-700",
};

function Inner() {
  const key = useOfficerKey();
  const [rows, setRows] = useState(null);
  const load = useCallback(() => adminGet("/api/sos", key).then((r) => setRows(Array.isArray(r) ? r : [])).catch(() => setRows([])), [key]);
  useEffect(() => { load(); }, [load]);
  const advance = async (id, status) => { await adminPost(`/api/sos/${id}/status`, key, { status }); load(); };

  const active = (rows || []).filter((s) => (s.status || "open") !== "resolved");
  const resolved = (rows || []).filter((s) => (s.status || "open") === "resolved");

  const Card = ({ s }) => {
    const f = FLOW[s.status || "open"] || FLOW.open;
    return (
      <div className="rounded-2xl border border-bdr bg-surface shadow-card p-3.5 flex items-start gap-3">
        <span className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${TONE[f.tone]}`}><Siren size={16} /></span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[14px] font-extrabold text-ink">{s.nature || "SOS"}</span>
            <span className={`text-[10.5px] font-bold px-2 py-0.5 rounded-full ${TONE[f.tone]}`}>{f.label}</span>
          </div>
          <div className="text-[11px] font-mono text-muted">{s.id}</div>
          <div className="text-[12.5px] text-ink mt-0.5">{YATRA[s.yatra] || s.yatra || "—"} · 📍 {s.location || "—"}</div>
          <div className="text-[11.5px] text-muted mt-1 flex items-center gap-1">
            <Landmark size={12} className="text-primary flex-shrink-0" /> Escalated to: {s.routed_to || "State Emergency Control Centre · 112"}
          </div>
        </div>
        {f.next ? (
          <button onClick={() => advance(s.id, f.next)} className="flex-shrink-0 inline-flex items-center gap-1 rounded-lg bg-primary text-white text-[12px] font-bold px-2.5 h-8 hover:bg-primary-700 transition">
            <f.icon size={13} /> {f.action}
          </button>
        ) : null}
      </div>
    );
  };

  return (
    <main className="max-w-3xl w-full mx-auto px-4 py-4 space-y-2.5">
      {rows === null ? <div className="text-muted text-[13.5px] py-3">Loading…</div> : null}
      {rows && active.length === 0 ? <div className="text-center py-12 text-muted text-[13.5px]">No open SOS. 🙏</div> : null}
      {active.map((s) => <Card key={s.id} s={s} />)}
      {resolved.length ? (
        <div className="pt-3">
          <div className="text-[11px] font-bold text-muted uppercase tracking-wide mb-2">Resolved ({resolved.length})</div>
          <div className="space-y-2.5 opacity-70">{resolved.slice(0, 20).map((s) => <Card key={s.id} s={s} />)}</div>
        </div>
      ) : null}
    </main>
  );
}

export default function OfficerSos() {
  return <OfficerGate title="SOS feed" subtitle="Emergencies → control-room escalation" back><Inner /></OfficerGate>;
}
