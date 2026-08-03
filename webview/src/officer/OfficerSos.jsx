import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Siren, X, Phone, MapPin, Landmark, Clock, Truck, CheckCircle2,
  PhoneForwarded, ShieldCheck, Users, HeartPulse, User, Send, Plus, ChevronRight,
} from "lucide-react";
import OfficerGate, { useOfficerKey } from "./OfficerGate.jsx";
import { adminGet, sosDetail, sosUpdate, YATRA } from "./officerApi.js";

// Each status → how it reads + the action that advances it, and what that
// action should capture. The console is an incident log, not a status toggle:
// every transition records who acted + a note + structured detail.
const STATUS = {
  open:         { label: "Awaiting acknowledgement", tone: "red" },
  acknowledged: { label: "Acknowledged",             tone: "amber" },
  dispatched:   { label: "Unit dispatched",          tone: "blue" },
  resolved:     { label: "Resolved",                 tone: "green" },
};
const ACTION = {
  open:         { next: "acknowledged", verb: "Acknowledge", icon: PhoneForwarded, fields: [] },
  acknowledged: { next: "dispatched",   verb: "Dispatch unit", icon: Truck,
                  fields: [["unit", "Responding unit (108 / police / NDRF)"], ["contact", "Unit contact number"], ["eta", "ETA (e.g. 8 min)"]] },
  dispatched:   { next: "resolved",     verb: "Mark resolved", icon: CheckCircle2,
                  fields: [["outcome", "Outcome (e.g. shifted to hospital, safe)"]] },
};
const TONE = {
  red: "bg-red-100 text-red-700", amber: "bg-amber-100 text-amber-800",
  blue: "bg-blue-100 text-blue-700", green: "bg-green-100 text-green-700",
};
const NAME_KEY = "ysahayak.officerName";

function timeAgo(iso) {
  if (!iso) return "";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "";
  const s = Math.max(0, Math.round((Date.now() - t) / 1000));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.round(s / 60)}m ago`;
  if (s < 86400) return `${Math.round(s / 3600)}h ago`;
  return new Date(iso).toLocaleString();
}

function Pill({ status }) {
  const s = STATUS[status] || STATUS.open;
  return <span className={`text-[10.5px] font-bold px-2 py-0.5 rounded-full ${TONE[s.tone]}`}>{s.label}</span>;
}

function Field({ icon: Icon, label, children, mono }) {
  if (!children) return null;
  return (
    <div className="flex items-start gap-2">
      <Icon size={14} className="text-muted mt-0.5 flex-shrink-0" />
      <div className="min-w-0">
        <div className="text-[10.5px] font-semibold uppercase tracking-wide text-muted">{label}</div>
        <div className={`text-[13px] text-ink ${mono ? "font-mono" : ""}`}>{children}</div>
      </div>
    </div>
  );
}

// The reporter panel — who raised the SOS, pulled from their registration.
function ReporterCard({ sos }) {
  const r = sos.reporter;
  if (!r) {
    return (
      <div className="rounded-xl border border-bdr bg-slate-50 p-3">
        <div className="flex items-center gap-2 text-[13px] font-bold text-ink"><User size={15} /> Reporter</div>
        <div className="text-[12.5px] text-muted mt-1">Not a registered pilgrim — anonymous / voice SOS.</div>
        <div className="mt-2 space-y-2">
          <Field icon={User} label="Name given">{sos.reporter_name}</Field>
          {sos.reporter_phone ? (
            <Field icon={Phone} label="Phone"><a className="text-primary underline" href={`tel:${sos.reporter_phone}`}>{sos.reporter_phone}</a></Field>
          ) : null}
          <Field icon={User} label="Device / user id" mono>{sos.user_id}</Field>
        </div>
      </div>
    );
  }
  return (
    <div className="rounded-xl border border-bdr bg-surface p-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[13.5px] font-extrabold text-ink"><User size={16} /> {r.name || "—"}{r.age ? <span className="text-muted font-medium">· {r.age} yrs</span> : null}</div>
        <div className="flex items-center gap-1">
          {r.mobile_verified ? <span className="inline-flex items-center gap-1 text-[10px] font-bold text-green-700 bg-green-100 px-1.5 py-0.5 rounded-full"><ShieldCheck size={11} /> Mobile</span> : null}
          {r.ekyc_verified ? <span className="inline-flex items-center gap-1 text-[10px] font-bold text-green-700 bg-green-100 px-1.5 py-0.5 rounded-full"><ShieldCheck size={11} /> e-KYC</span> : null}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-2.5 mt-3">
        <Field icon={Phone} label="Phone"><a className="text-primary underline" href={`tel:${r.phone}`}>{r.phone || "—"}</a></Field>
        <Field icon={Phone} label="Emergency contact">{r.emergency_contact ? <a className="text-primary underline" href={`tel:${r.emergency_contact}`}>{r.emergency_contact}</a> : "—"}</Field>
        <Field icon={ShieldCheck} label="Pass ID" mono>{r.yatra_id}</Field>
        <Field icon={Users} label="Group">{r.group_name || "—"}{r.group_size > 1 ? ` · ${r.group_size} people` : ""}</Field>
      </div>
      {r.medical_flags ? (
        <div className="mt-3 flex items-start gap-2 rounded-lg bg-red-50 border border-red-200 px-2.5 py-2">
          <HeartPulse size={15} className="text-red-600 mt-0.5 flex-shrink-0" />
          <div><div className="text-[10.5px] font-bold uppercase tracking-wide text-red-700">Medical flags</div>
            <div className="text-[12.5px] text-red-800">{r.medical_flags}</div></div>
        </div>
      ) : null}
    </div>
  );
}

// One action form. Collects the officer name + a note + the fields this
// transition needs, then logs it to the backend.
function ActionForm({ sos, officer, setOfficer, onLog }) {
  const cfg = ACTION[sos.status || "open"];
  const [note, setNote] = useState("");
  const [meta, setMeta] = useState({});
  const [busy, setBusy] = useState(false);
  useEffect(() => { setNote(""); setMeta({}); }, [sos.status, sos.id]);

  const submit = async (status) => {
    if (busy) return;
    if (!officer.trim()) return;
    setBusy(true);
    try { await onLog({ status, actor: officer.trim(), note: note.trim() || null, meta }); }
    finally { setBusy(false); }
  };

  return (
    <div className="rounded-xl border border-bdr bg-surface p-3 space-y-2.5">
      <label className="block">
        <span className="text-[10.5px] font-semibold uppercase tracking-wide text-muted">Acting officer</span>
        <input value={officer} onChange={(e) => setOfficer(e.target.value)} placeholder="Your name / call sign"
          className="mt-1 w-full rounded-lg border border-bdr px-2.5 h-9 text-[13px] outline-none focus:border-primary" />
      </label>

      {cfg?.fields?.map(([k, ph]) => (
        <input key={k} value={meta[k] || ""} onChange={(e) => setMeta((m) => ({ ...m, [k]: e.target.value }))}
          placeholder={ph}
          className="w-full rounded-lg border border-bdr px-2.5 h-9 text-[13px] outline-none focus:border-primary" />
      ))}

      <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2}
        placeholder={cfg ? `Note for the log (what you saw / did)…` : "Add a note to the log…"}
        className="w-full rounded-lg border border-bdr px-2.5 py-2 text-[13px] outline-none focus:border-primary resize-none" />

      <div className="flex flex-wrap gap-2">
        {cfg ? (
          <button disabled={busy || !officer.trim()} onClick={() => submit(cfg.next)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary text-white text-[13px] font-bold px-3 h-9 hover:bg-primary-700 disabled:opacity-50 transition">
            <cfg.icon size={15} /> {cfg.verb}
          </button>
        ) : (
          <span className="inline-flex items-center gap-1.5 text-[13px] font-bold text-green-700"><CheckCircle2 size={16} /> Incident resolved</span>
        )}
        <button disabled={busy || !officer.trim() || !note.trim()} onClick={() => submit(null)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-bdr text-ink text-[13px] font-bold px-3 h-9 hover:bg-slate-50 disabled:opacity-50 transition">
          <Plus size={15} /> Add note
        </button>
      </div>
    </div>
  );
}

function Timeline({ items }) {
  if (!items?.length) return null;
  return (
    <ol className="relative ml-1 border-l-2 border-bdr pl-4 space-y-3">
      {items.map((u) => {
        const s = STATUS[u.status];
        return (
          <li key={u.id} className="relative">
            <span className={`absolute -left-[22px] top-0.5 w-3 h-3 rounded-full ring-2 ring-surface ${s ? TONE[s.tone].split(" ")[0] : "bg-slate-300"}`} />
            <div className="flex items-center gap-2 flex-wrap">
              {s ? <Pill status={u.status} /> : <span className="text-[11px] font-bold text-muted">Note</span>}
              <span className="text-[12px] font-semibold text-ink">{u.actor}</span>
              <span className="text-[11px] text-muted flex items-center gap-1"><Clock size={11} />{timeAgo(u.created_at)}</span>
            </div>
            {u.note ? <div className="text-[12.5px] text-ink mt-0.5">{u.note}</div> : null}
            {u.meta && Object.keys(u.meta).length ? (
              <div className="flex flex-wrap gap-1.5 mt-1">
                {Object.entries(u.meta).filter(([, v]) => v).map(([k, v]) => (
                  <span key={k} className="text-[10.5px] bg-slate-100 text-ink rounded px-1.5 py-0.5"><b className="text-muted font-semibold">{k}:</b> {v}</span>
                ))}
              </div>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}

function DetailModal({ id, keyStr, officer, setOfficer, onClose, onChanged }) {
  const [sos, setSos] = useState(null);
  const [err, setErr] = useState(false);
  const load = useCallback(() => {
    setErr(false);
    sosDetail(id, keyStr).then(setSos).catch(() => setErr(true));
  }, [id, keyStr]);
  useEffect(() => { load(); }, [load]);

  const log = async (body) => {
    await sosUpdate(id, keyStr, body);
    await load();       // refresh timeline + status in the modal
    onChanged();        // refresh the underlying list
  };

  return (
    <div className="fixed inset-0 z-40 flex items-start justify-center bg-black/40 p-3 sm:p-6 overflow-y-auto" onClick={onClose}>
      <div className="w-full max-w-lg bg-surface rounded-2xl shadow-xl my-2" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-3 p-4 border-b border-bdr sticky top-0 bg-surface rounded-t-2xl">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[15px] font-extrabold text-ink">{sos?.nature || "SOS"}</span>
              {sos ? <Pill status={sos.status} /> : null}
            </div>
            <div className="text-[11px] font-mono text-muted mt-0.5">{id}</div>
          </div>
          <button onClick={onClose} className="text-muted hover:text-ink p-1 -mr-1"><X size={20} /></button>
        </div>

        {err ? <div className="p-6 text-center text-muted text-[13px]">Couldn’t load this incident. <button onClick={load} className="text-primary underline">Retry</button></div> : null}
        {!sos && !err ? <div className="p-8 text-center text-muted text-[13px]">Loading incident…</div> : null}

        {sos ? (
          <div className="p-4 space-y-4">
            <ReporterCard sos={sos} />

            <div className="rounded-xl border border-bdr bg-surface p-3 grid grid-cols-2 gap-x-4 gap-y-2.5">
              <Field icon={Siren} label="Yatra">{YATRA[sos.yatra] || sos.yatra || "—"}</Field>
              <Field icon={MapPin} label="Location">
                {typeof sos.lat === "number" && typeof sos.lng === "number" ? (
                  <a className="text-primary underline" target="_blank" rel="noopener"
                    href={`https://www.google.com/maps?q=${sos.lat},${sos.lng}`}>
                    📍 {sos.lat.toFixed(5)}, {sos.lng.toFixed(5)} — open map
                  </a>
                ) : (sos.location || "Not shared")}
              </Field>
              <Field icon={Landmark} label="Escalated to">{sos.routed_to}</Field>
              <Field icon={Clock} label="Raised">{sos.created_at ? timeAgo(sos.created_at) : "—"}</Field>
            </div>

            <div>
              <div className="text-[11px] font-bold text-muted uppercase tracking-wide mb-2">Next action</div>
              <ActionForm sos={sos} officer={officer} setOfficer={setOfficer} onLog={log} />
            </div>

            <div>
              <div className="text-[11px] font-bold text-muted uppercase tracking-wide mb-2.5">Incident timeline</div>
              <Timeline items={sos.timeline} />
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function Inner() {
  const key = useOfficerKey();
  const [rows, setRows] = useState(null);
  const [openId, setOpenId] = useState(null);
  const [officer, setOfficer] = useState(() => { try { return localStorage.getItem(NAME_KEY) || ""; } catch { return ""; } });
  const setOfficerP = (v) => { setOfficer(v); try { localStorage.setItem(NAME_KEY, v); } catch { /* */ } };

  const load = useCallback(() => adminGet("/api/sos", key)
    .then((r) => setRows(Array.isArray(r) ? r : []))
    .catch(() => setRows([])), [key]);
  useEffect(() => { load(); }, [load]);

  const active = useMemo(() => (rows || []).filter((s) => (s.status || "open") !== "resolved"), [rows]);
  const resolved = useMemo(() => (rows || []).filter((s) => (s.status || "open") === "resolved"), [rows]);

  const Card = ({ s }) => {
    const tone = STATUS[s.status || "open"]?.tone || "red";
    return (
      <button onClick={() => setOpenId(s.id)}
        className="w-full text-left rounded-2xl border border-bdr bg-surface shadow-card p-3.5 flex items-start gap-3 hover:border-primary/50 hover:shadow-md transition">
        <span className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${TONE[tone]}`}><Siren size={16} /></span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[14px] font-extrabold text-ink">{s.nature || "SOS"}</span>
            <Pill status={s.status || "open"} />
          </div>
          <div className="text-[11px] font-mono text-muted">{s.id}</div>
          <div className="text-[12.5px] text-ink mt-0.5">
            {(s.reporter_name || s.user_id) ? <span className="font-semibold">{s.reporter_name || s.user_id} · </span> : null}
            {YATRA[s.yatra] || s.yatra || "—"} · 📍 {s.location || "location not shared"}
          </div>
          <div className="text-[11.5px] text-muted mt-1 flex items-center gap-1">
            <Landmark size={12} className="text-primary flex-shrink-0" /> {s.routed_to || "State Emergency Control Centre · 112"}
          </div>
        </div>
        <span className="flex-shrink-0 inline-flex items-center gap-0.5 text-[12px] font-bold text-primary self-center">Open <ChevronRight size={14} /></span>
      </button>
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

      {openId ? (
        <DetailModal id={openId} keyStr={key} officer={officer} setOfficer={setOfficerP}
          onClose={() => setOpenId(null)} onChanged={load} />
      ) : null}
    </main>
  );
}

export default function OfficerSos() {
  return <OfficerGate title="SOS feed" subtitle="Emergencies → control-room escalation" back><Inner /></OfficerGate>;
}
