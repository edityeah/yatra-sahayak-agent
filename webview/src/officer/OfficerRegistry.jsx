import { useCallback, useEffect, useState } from "react";
import { Users, Search, UserRound, Package, CheckCircle2 } from "lucide-react";
import OfficerGate, { useOfficerKey } from "./OfficerGate.jsx";
import { adminGet, adminPost, YATRA } from "./officerApi.js";

function Inner() {
  const key = useOfficerKey();
  const [summary, setSummary] = useState(null);
  const [regs, setRegs] = useState([]);
  const [lf, setLf] = useState([]);
  const [tab, setTab] = useState("registry");
  const [q, setQ] = useState("");

  const load = useCallback(async () => {
    const [s, rg, l] = await Promise.all([
      adminGet("/api/officer/summary", key).catch(() => null),
      adminGet("/api/registrations", key).catch(() => ({ registrations: [] })),
      adminGet("/api/lostfound", key).catch(() => []),
    ]);
    setSummary(s); setRegs((rg && rg.registrations) || []); setLf(l || []);
  }, [key]);
  useEffect(() => { load(); }, [load]);
  const resolveLf = async (id) => { await adminPost(`/api/lostfound/${id}/status`, key, { status: "reunited" }); load(); };

  const filtered = q ? regs.filter((r) => `${r.name} ${r.yatra_id} ${r.phone}`.toLowerCase().includes(q.toLowerCase())) : regs;
  const openLf = lf.filter((x) => (x.status || "open") === "open");

  return (
    <main className="max-w-3xl w-full mx-auto px-4 py-4 space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Kpi icon={<Users size={16} />} label="Pilgrims" value={summary?.pilgrims ?? "—"} sub={`${summary?.families ?? 0} families`} />
        <Kpi icon={<Package size={16} />} label="Open L&F" value={summary?.open_lostfound ?? "—"} />
        <Kpi label="By yatra" small value={Object.entries(summary?.by_yatra || {}).map(([k, v]) => `${YATRA[k] || k}: ${v}`).join(" · ") || "—"} />
        <Kpi label="Open grievances" value={summary?.open_grievances ?? "—"} />
      </div>

      <div className="flex gap-2">
        {[["registry", `Registry (${regs.length})`], ["lostfound", `Lost & Found (${openLf.length})`]].map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)} className={`h-9 px-4 rounded-full text-[13px] font-bold border transition ${tab === k ? "bg-primary text-white border-primary" : "bg-surface text-ink border-bdr"}`}>{l}</button>
        ))}
      </div>

      {tab === "registry" ? (
        <>
          <div className="flex items-center gap-2 rounded-xl border border-bdr bg-surface px-3 h-10">
            <Search size={15} className="text-muted" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name / Yatra ID / phone" className="flex-1 bg-transparent text-[14px] outline-none" />
          </div>
          <div className="space-y-2.5">
            {filtered.length === 0 ? <div className="text-center py-10 text-muted text-[13.5px]">No pilgrims.</div> : null}
            {filtered.slice(0, 100).map((r) => (
              <Row key={r.yatra_id} icon={<UserRound size={16} />} title={`${r.name} (${r.age || "?"})`} id={r.yatra_id}
                meta={`${YATRA[r.yatra] || r.yatra} · ${r.group_name || "—"} · ☎ ${r.emergency_contact || "—"}${r.medical_flags && r.medical_flags !== "none" ? ` · ⚕ ${r.medical_flags}` : ""}`} />
            ))}
          </div>
        </>
      ) : (
        <div className="space-y-2.5">
          {openLf.length === 0 ? <div className="text-center py-10 text-muted text-[13.5px]">No open reports.</div> : null}
          {openLf.map((x) => (
            <Row key={x.id} tone={x.kind === "person" ? "red" : "amber"} icon={x.kind === "person" ? <UserRound size={16} /> : <Package size={16} />}
              title={`${x.kind === "person" ? "Person" : "Item"}: ${x.name || "—"}`} id={x.id} meta={`${x.description || ""} · 📍 ${x.last_seen || "—"}`}
              action={<button onClick={() => resolveLf(x.id)} className="flex-shrink-0 inline-flex items-center gap-1 rounded-lg bg-green-600 text-white text-[12px] font-bold px-2.5 h-8 hover:bg-green-700 transition"><CheckCircle2 size={13} /> Reunited</button>} />
          ))}
        </div>
      )}
    </main>
  );
}

function Kpi({ icon, label, value, sub, small }) {
  return (
    <div className="rounded-2xl border border-bdr bg-surface shadow-card p-3">
      <div className="flex items-center gap-1.5 text-[11.5px] font-bold text-muted uppercase tracking-wide">{icon} {label}</div>
      <div className={`mt-1 font-extrabold ${small ? "text-[12.5px] leading-snug" : "text-[24px] text-ink"}`}>{value}</div>
      {sub ? <div className="text-[11px] text-muted">{sub}</div> : null}
    </div>
  );
}
function Row({ icon, title, id, meta, tone, action }) {
  const bg = tone === "red" ? "bg-red-100 text-red-600" : tone === "amber" ? "bg-amber-100 text-amber-700" : "bg-primary-100 text-primary";
  return (
    <div className="rounded-2xl border border-bdr bg-surface shadow-card p-3.5 flex items-start gap-3">
      <span className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${bg}`}>{icon}</span>
      <div className="flex-1 min-w-0">
        <div className="text-[14px] font-extrabold text-ink">{title}</div>
        <div className="text-[11px] font-mono text-muted">{id}</div>
        {meta ? <div className="text-[12.5px] text-ink mt-0.5 break-words">{meta}</div> : null}
      </div>
      {action}
    </div>
  );
}

export default function OfficerRegistry() {
  return <OfficerGate title="Registry & Lost-Found" subtitle="Headcount, search, board" back><Inner /></OfficerGate>;
}
