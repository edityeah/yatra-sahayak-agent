import { useCallback, useEffect, useState } from "react";
import { Users, Search, UserRound, Package, CheckCircle2, XCircle, Download, X, Phone, ShieldCheck, HeartPulse, MapPin, IdCard, Landmark } from "lucide-react";
import OfficerGate, { useOfficerKey } from "./OfficerGate.jsx";
import { adminGet, adminPost, adminDownloadCsv, YATRA } from "./officerApi.js";

function Inner() {
  const key = useOfficerKey();
  const [summary, setSummary] = useState(null);
  const [regs, setRegs] = useState([]);
  const [lf, setLf] = useState([]);
  const [tab, setTab] = useState("registry");
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState(null);   // pilgrim profile open in the modal

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

  const filtered = q
    ? regs.filter((r) => `${r.name} ${r.yatra_id} ${r.phone} ${r.group_name}`.toLowerCase().includes(q.toLowerCase()))
    : regs;
  const openLf = lf.filter((x) => (x.status || "open") === "open");

  return (
    <main className="max-w-4xl w-full mx-auto px-4 py-4 space-y-4">
      {/* Headcount KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Kpi icon={<Users size={16} />} label="Registered pilgrims" value={summary?.pilgrims ?? regs.length} sub={`${summary?.families ?? 0} families`} accent />
        <Kpi label="By yatra" small value={Object.entries(summary?.by_yatra || {}).map(([k, v]) => `${YATRA[k] || k}: ${v}`).join(" · ") || "—"} />
        <Kpi icon={<Package size={16} />} label="Open L&F" value={summary?.open_lostfound ?? openLf.length} />
        <Kpi label="Open grievances" value={summary?.open_grievances ?? "—"} />
      </div>

      <div className="flex items-center gap-2">
        {[["registry", `Registry (${regs.length})`], ["lostfound", `Lost & Found (${openLf.length})`]].map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)} className={`h-9 px-4 rounded-full text-[13px] font-bold border transition ${tab === k ? "bg-primary text-white border-primary" : "bg-surface text-ink border-bdr"}`}>{l}</button>
        ))}
        {tab === "registry" && regs.length ? (
          <button onClick={() => adminDownloadCsv("/api/registrations?format=csv", key, "registrations.csv").catch(() => {})}
            className="ml-auto h-9 px-3 rounded-full text-[12.5px] font-bold border border-bdr bg-surface text-ink hover:border-primary transition inline-flex items-center gap-1.5">
            <Download size={14} /> Export CSV
          </button>
        ) : null}
      </div>

      {tab === "registry" ? (
        <>
          <div className="flex items-center gap-2 rounded-xl border border-bdr bg-surface px-3 h-10">
            <Search size={15} className="text-muted" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name / Yatra ID / phone / group" className="flex-1 bg-transparent text-[14px] outline-none" />
          </div>

          {filtered.length === 0 ? <div className="text-center py-10 text-muted text-[13.5px]">No pilgrims registered yet.</div> : null}

          {/* Table on wider screens */}
          {filtered.length ? (
            <div className="hidden sm:block rounded-2xl border border-bdr bg-surface shadow-card overflow-hidden">
              <table className="w-full text-[13px]">
                <thead className="bg-surface-2 text-muted text-[11px] uppercase tracking-wide">
                  <tr><Th>Name</Th><Th>Yatra ID</Th><Th>Yatra</Th><Th>Group</Th><Th>Verified</Th><Th>Medical</Th></tr>
                </thead>
                <tbody>
                  {filtered.slice(0, 200).map((r) => (
                    <tr key={r.yatra_id} onClick={() => setSelected(r)} className="border-t border-bdr-soft hover:bg-primary-50 cursor-pointer">
                      <Td><span className="font-bold text-ink">{r.name || "—"}</span> <span className="text-muted">· {r.age || "?"}</span></Td>
                      <Td mono>{r.yatra_id}</Td>
                      <Td>{YATRA[r.yatra] || r.yatra}</Td>
                      <Td>{r.group_name || "Solo"}{r.group_size > 1 ? ` (${r.group_size})` : ""}</Td>
                      <Td><VerifyDots r={r} /></Td>
                      <Td>{r.medical_flags && r.medical_flags !== "none" ? <span className="text-amber-700">⚕ {r.medical_flags}</span> : <span className="text-muted">—</span>}</Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}

          {/* Cards on mobile */}
          <div className="sm:hidden space-y-2.5">
            {filtered.slice(0, 200).map((r) => (
              <button key={r.yatra_id} onClick={() => setSelected(r)} className="w-full text-left rounded-2xl border border-bdr bg-surface shadow-card p-3.5 flex items-start gap-3 hover:border-primary transition">
                <span className="w-8 h-8 rounded-full bg-primary-100 text-primary flex items-center justify-center flex-shrink-0"><UserRound size={16} /></span>
                <div className="flex-1 min-w-0">
                  <div className="text-[14px] font-extrabold text-ink">{r.name || "—"} <span className="text-muted font-normal">· {r.age || "?"}</span></div>
                  <div className="text-[11px] font-mono text-muted">{r.yatra_id}</div>
                  <div className="text-[12px] text-ink mt-0.5">{YATRA[r.yatra] || r.yatra} · {r.group_name || "Solo"}</div>
                  <div className="mt-1"><VerifyDots r={r} /></div>
                </div>
              </button>
            ))}
          </div>
        </>
      ) : (
        <div className="space-y-2.5">
          {openLf.length === 0 ? <div className="text-center py-10 text-muted text-[13.5px]">No open reports.</div> : null}
          {openLf.map((x) => (
            <div key={x.id} className="rounded-2xl border border-bdr bg-surface shadow-card p-3.5 flex items-start gap-3">
              <span className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${x.kind === "person" ? "bg-red-100 text-red-600" : "bg-amber-100 text-amber-700"}`}>
                {x.kind === "person" ? <UserRound size={16} /> : <Package size={16} />}
              </span>
              <div className="flex-1 min-w-0">
                <div className="text-[14px] font-extrabold text-ink">{x.kind === "person" ? "Person" : "Item"}: {x.name || "—"}</div>
                <div className="text-[11px] font-mono text-muted">{x.id}</div>
                <div className="text-[12.5px] text-ink mt-0.5 break-words">{x.description || ""} · 📍 {x.last_seen || "—"}</div>
              </div>
              <button onClick={() => resolveLf(x.id)} className="flex-shrink-0 inline-flex items-center gap-1 rounded-lg bg-green-600 text-white text-[12px] font-bold px-2.5 h-8 hover:bg-green-700 transition"><CheckCircle2 size={13} /> Reunited</button>
            </div>
          ))}
        </div>
      )}

      {selected ? <ProfileModal r={selected} onClose={() => setSelected(null)} /> : null}
    </main>
  );
}

function VerifyDots({ r }) {
  const Pill = ({ ok, label }) => (
    <span className={`inline-flex items-center gap-0.5 text-[10.5px] font-bold px-1.5 py-0.5 rounded-full ${ok ? "bg-green-100 text-green-700" : "bg-surface-2 text-muted"}`}>
      {ok ? <CheckCircle2 size={10} /> : <XCircle size={10} />} {label}
    </span>
  );
  return <span className="inline-flex gap-1"><Pill ok={r.mobile_verified} label="Mobile" /><Pill ok={r.ekyc_verified} label="e-KYC" /></span>;
}

// Full pilgrim profile — every detail captured at registration.
function ProfileModal({ r, onClose }) {
  const medical = r.medical_flags && r.medical_flags !== "none" ? r.medical_flags : null;
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      <div className="absolute inset-0 bg-ink/50 backdrop-blur-[2px]" onClick={onClose} />
      <div className="relative w-full sm:max-w-md bg-surface rounded-t-3xl sm:rounded-3xl shadow-drawer max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-surface px-5 pt-5 pb-3 border-b border-bdr-soft flex items-start gap-3">
          <span className="w-11 h-11 rounded-full bg-primary-100 text-primary flex items-center justify-center flex-shrink-0"><UserRound size={20} /></span>
          <div className="flex-1 min-w-0">
            <div className="text-[17px] font-extrabold text-ink">{r.name || "—"} <span className="text-muted font-normal text-[14px]">· {r.age || "?"} yrs</span></div>
            <div className="text-[12px] font-mono text-muted">{r.yatra_id}</div>
            <span className={`mt-1 inline-block text-[10.5px] font-bold px-2 py-0.5 rounded-full ${r.is_primary ? "bg-primary-100 text-primary" : "bg-surface-2 text-muted"}`}>{r.is_primary ? "Primary" : "Family member"}</span>
          </div>
          <button onClick={onClose} className="w-9 h-9 rounded-full hover:bg-surface-2 flex items-center justify-center text-muted"><X size={18} /></button>
        </div>

        <div className="px-5 py-4 space-y-3.5">
          <Info icon={<Landmark size={15} />} label="Yatra" value={YATRA[r.yatra] || r.yatra} />
          <Info icon={<Phone size={15} />} label="Mobile" value={r.phone || "—"} />
          <Info icon={<IdCard size={15} />} label="ID type" value={r.id_type || "—"} />
          <Info icon={<ShieldCheck size={15} />} label="Verification"
            value={<span className="inline-flex flex-wrap gap-2"><Badge ok={r.mobile_verified}>Mobile {r.mobile_verified ? "verified" : "unverified"}</Badge><Badge ok={r.ekyc_verified}>e-KYC {r.ekyc_verified ? "done" : "pending"}</Badge></span>} />
          <Info icon={<Users size={15} />} label="Group / Dindi" value={`${r.group_name || "Solo"}${r.group_size > 1 ? ` · ${r.group_size} people` : ""}`} />
          {r.group_id ? <Info icon={<Users size={15} />} label="Family batch ID" value={<span className="font-mono">{r.group_id}</span>} /> : null}
          <Info icon={<Phone size={15} className="text-red-500" />} label="Emergency contact" value={r.emergency_contact || "—"} />
          <Info icon={<HeartPulse size={15} className={medical ? "text-amber-600" : ""} />} label="Medical"
            value={medical ? <span className="text-amber-700 font-bold">{medical}</span> : <span className="text-muted">None noted</span>} />
          {r.created_at ? <Info icon={<MapPin size={15} />} label="Registered" value={String(r.created_at).replace("T", " ").slice(0, 16)} /> : null}
        </div>
      </div>
    </div>
  );
}

function Info({ icon, label, value }) {
  return (
    <div className="flex items-start gap-2.5">
      <span className="text-primary mt-0.5 flex-shrink-0">{icon}</span>
      <div className="flex-1 min-w-0">
        <div className="text-[11px] font-bold text-muted uppercase tracking-wide">{label}</div>
        <div className="text-[14px] text-ink break-words">{value}</div>
      </div>
    </div>
  );
}
function Badge({ ok, children }) {
  return <span className={`inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full ${ok ? "bg-green-100 text-green-700" : "bg-surface-2 text-muted"}`}>{ok ? <CheckCircle2 size={11} /> : <XCircle size={11} />} {children}</span>;
}
function Kpi({ icon, label, value, sub, small, accent }) {
  return (
    <div className={`rounded-2xl border shadow-card p-3 ${accent ? "border-primary/30 bg-primary-50" : "border-bdr bg-surface"}`}>
      <div className="flex items-center gap-1.5 text-[11.5px] font-bold text-muted uppercase tracking-wide">{icon} {label}</div>
      <div className={`mt-1 font-extrabold ${small ? "text-[12.5px] leading-snug text-ink" : "text-[26px] text-ink"}`}>{value}</div>
      {sub ? <div className="text-[11px] text-muted">{sub}</div> : null}
    </div>
  );
}
function Th({ children }) { return <th className="text-left font-bold px-3 py-2.5">{children}</th>; }
function Td({ children, mono }) { return <td className={`px-3 py-2.5 align-top ${mono ? "font-mono text-[11.5px] text-muted" : ""}`}>{children}</td>; }

export default function OfficerRegistry() {
  return <OfficerGate title="Registry & Lost-Found" subtitle="Headcount, profiles, board" back><Inner /></OfficerGate>;
}
