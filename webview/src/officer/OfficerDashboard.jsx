import { useCallback, useEffect, useRef, useState } from "react";
import {
  ShieldCheck, Users, Siren, Package, RefreshCw, Search, CheckCircle2,
  Send, LayoutDashboard, UserRound,
} from "lucide-react";

// The officer war-room dashboard — live KPIs, SOS feed, pilgrim registry, lost
// & found, and an ops chat. Gated by the ADMIN_API_KEY (entered once, kept in
// sessionStorage) so pilgrim PII isn't behind the browser-shipped key. In
// production this is the officer bot's BotExtension activity (allowlisted).
const BASE = import.meta.env.VITE_AGENT_URL || "http://localhost:8000";
const SS_KEY = "ysahayak.officerKey";
const YATRA = { pandharpur: "Pandharpur Wari", kumbh: "Simhastha Kumbh" };

async function adminGet(path, key) {
  const r = await fetch(`${BASE}${path}`, { headers: { "X-API-Key": key } });
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}
async function adminPost(path, key, body) {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST", headers: { "Content-Type": "application/json", "X-API-Key": key },
    body: JSON.stringify(body || {}),
  });
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}
async function officerAsk(text, key) {
  const r = await fetch(`${BASE}/officer/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Admin-Key": key },
    body: JSON.stringify({ user_id: "officer-web", message: { content: [{ type: "text", text: { value: text } }] } }),
  });
  if (!r.ok) throw new Error(`${r.status}`);
  const txt = await r.text();
  let out = "";
  for (const frame of txt.split(/\r?\n\r?\n/)) {
    const ev = frame.split("\n").find((l) => l.startsWith("event:"))?.slice(6).trim();
    const data = frame.split("\n").find((l) => l.startsWith("data:"))?.slice(5).trim();
    if (ev === "delta" && data) {
      try { const d = JSON.parse(data); if (d.o === "append") out += d.v; } catch (e) { /* */ }
    }
  }
  return out;
}

export default function OfficerDashboard() {
  const [key, setKey] = useState(() => { try { return sessionStorage.getItem(SS_KEY) || ""; } catch { return ""; } });
  const [keyInput, setKeyInput] = useState("");
  const [authed, setAuthed] = useState(false);
  const [authErr, setAuthErr] = useState(null);

  const [summary, setSummary] = useState(null);
  const [sos, setSos] = useState([]);
  const [regs, setRegs] = useState([]);
  const [lf, setLf] = useState([]);
  const [tab, setTab] = useState("sos");
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (k) => {
    setLoading(true); setAuthErr(null);
    try {
      const [sum, s, rg, l] = await Promise.all([
        adminGet("/api/officer/summary", k),
        adminGet("/api/sos", k),
        adminGet("/api/registrations", k),
        adminGet("/api/lostfound", k),
      ]);
      setSummary(sum); setSos(s || []); setRegs((rg && rg.registrations) || []); setLf(l || []);
      setAuthed(true);
    } catch (e) {
      if (String(e.message) === "401" || String(e.message) === "403") setAuthErr("Invalid officer key.");
      else setAuthErr(e?.message || String(e));
      setAuthed(false);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { if (key) load(key); }, [key, load]);

  const unlock = () => {
    const k = keyInput.trim();
    if (!k) return;
    try { sessionStorage.setItem(SS_KEY, k); } catch { /* */ }
    setKey(k);
  };
  const resolveSos = async (id) => { await adminPost(`/api/sos/${id}/status`, key, { status: "resolved" }); load(key); };
  const resolveLf = async (id) => { await adminPost(`/api/lostfound/${id}/status`, key, { status: "reunited" }); load(key); };

  if (!authed) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center px-4 font-sans">
        <div className="w-full max-w-sm rounded-2xl border border-bdr bg-surface shadow-card p-6 text-center">
          <div className="w-12 h-12 rounded-full bg-primary-100 text-primary flex items-center justify-center mx-auto"><ShieldCheck size={22} /></div>
          <h1 className="mt-3 text-[17px] font-extrabold text-ink">Yatra Control — War Room</h1>
          <p className="mt-1 text-[13px] text-muted">Officer access only. Enter your officer key.</p>
          <input type="password" value={keyInput} onChange={(e) => setKeyInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && unlock()} placeholder="Officer key"
            className="mt-4 w-full h-11 rounded-xl border border-bdr bg-surface px-3 text-[14px] text-ink focus:border-primary outline-none" />
          {authErr ? <p className="mt-2 text-[12.5px] text-red-600">{authErr}</p> : null}
          <button onClick={unlock} className="mt-3 w-full h-11 rounded-full bg-primary text-white font-extrabold hover:bg-primary-700 transition">Unlock</button>
        </div>
      </div>
    );
  }

  const filteredRegs = q
    ? regs.filter((r) => `${r.name} ${r.yatra_id} ${r.phone}`.toLowerCase().includes(q.toLowerCase()))
    : regs;
  const openSos = sos.filter((s) => (s.status || "open") === "open");
  const openLf = lf.filter((x) => (x.status || "open") === "open");

  return (
    <div className="min-h-screen bg-surface-2 font-sans text-ink">
      <header className="h-14 px-4 flex items-center gap-2 border-b border-bdr bg-surface sticky top-0 z-20">
        <div className="w-9 h-9 rounded-full bg-primary-100 text-primary flex items-center justify-center"><ShieldCheck size={17} /></div>
        <div className="flex-1 leading-tight">
          <div className="text-[14.5px] font-extrabold">Yatra Control — War Room</div>
          <div className="text-[11px] text-muted">Officer dashboard</div>
        </div>
        <button onClick={() => load(key)} className="w-9 h-9 rounded-full hover:bg-surface-2 flex items-center justify-center text-muted" title="Refresh">
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
        </button>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-4 space-y-4">
        {/* KPIs */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Kpi icon={<Users size={16} />} label="Pilgrims" value={summary?.pilgrims ?? "—"} sub={`${summary?.families ?? 0} families`} />
          <Kpi icon={<Siren size={16} />} label="Open SOS" value={summary?.open_sos ?? "—"} tone={summary?.open_sos ? "red" : "ok"} />
          <Kpi icon={<Package size={16} />} label="Lost & Found" value={summary?.open_lostfound ?? "—"} tone={summary?.open_lostfound ? "amber" : "ok"} />
          <Kpi icon={<LayoutDashboard size={16} />} label="By yatra"
            value={Object.entries(summary?.by_yatra || {}).map(([k, v]) => `${YATRA[k] || k}: ${v}`).join(" · ") || "—"} small />
        </div>

        {/* Tabs */}
        <div className="flex gap-2 overflow-x-auto">
          {[["sos", `SOS (${openSos.length})`], ["registry", `Registry (${regs.length})`], ["lostfound", `Lost & Found (${openLf.length})`], ["chat", "Ask"]].map(([k, label]) => (
            <button key={k} onClick={() => setTab(k)}
              className={`flex-shrink-0 h-9 px-4 rounded-full text-[13px] font-bold border transition ${tab === k ? "bg-primary text-white border-primary" : "bg-surface text-ink border-bdr"}`}>
              {label}
            </button>
          ))}
        </div>

        {tab === "sos" ? (
          <Section empty={openSos.length === 0} emptyText="No open SOS.">
            {openSos.map((s) => (
              <Row key={s.id} tone="red" icon={<Siren size={16} />} title={s.nature || "SOS"} id={s.id}
                meta={`${YATRA[s.yatra] || s.yatra || "—"} · 📍 ${s.location || "—"}`}
                action={<Resolve onClick={() => resolveSos(s.id)} label="Resolve" />} />
            ))}
          </Section>
        ) : null}

        {tab === "registry" ? (
          <>
            <div className="flex items-center gap-2 rounded-xl border border-bdr bg-surface px-3 h-10">
              <Search size={15} className="text-muted" />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name / Yatra ID / phone"
                className="flex-1 bg-transparent text-[14px] outline-none" />
            </div>
            <Section empty={filteredRegs.length === 0} emptyText="No pilgrims.">
              {filteredRegs.slice(0, 100).map((r) => (
                <Row key={r.yatra_id} icon={<UserRound size={16} />} title={`${r.name} (${r.age || "?"})`} id={r.yatra_id}
                  meta={`${YATRA[r.yatra] || r.yatra} · ${r.group_name || "—"} · ☎ ${r.emergency_contact || "—"}${r.medical_flags && r.medical_flags !== "none" ? ` · ⚕ ${r.medical_flags}` : ""}`} />
              ))}
            </Section>
          </>
        ) : null}

        {tab === "lostfound" ? (
          <Section empty={openLf.length === 0} emptyText="No open lost & found reports.">
            {openLf.map((x) => (
              <Row key={x.id} tone={x.kind === "person" ? "red" : "amber"} icon={x.kind === "person" ? <UserRound size={16} /> : <Package size={16} />}
                title={`${x.kind === "person" ? "Person" : "Item"}: ${x.name || "—"}`} id={x.id}
                meta={`${x.description || ""} · 📍 ${x.last_seen || "—"}`}
                action={<Resolve onClick={() => resolveLf(x.id)} label="Reunited" />} />
            ))}
          </Section>
        ) : null}

        {tab === "chat" ? <OfficerChat officerKey={key} /> : null}
      </main>
    </div>
  );
}

function Kpi({ icon, label, value, sub, tone, small }) {
  const color = tone === "red" ? "text-red-600" : tone === "amber" ? "text-amber-600" : "text-ink";
  return (
    <div className="rounded-2xl border border-bdr bg-surface shadow-card p-3">
      <div className="flex items-center gap-1.5 text-[11.5px] font-bold text-muted uppercase tracking-wide">{icon} {label}</div>
      <div className={`mt-1 font-extrabold ${small ? "text-[12.5px] leading-snug" : `text-[24px] ${color}`}`}>{value}</div>
      {sub ? <div className="text-[11px] text-muted">{sub}</div> : null}
    </div>
  );
}
function Section({ empty, emptyText, children }) {
  if (empty) return <div className="text-center py-12 text-muted text-[13.5px]">{emptyText}</div>;
  return <div className="space-y-2.5">{children}</div>;
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
function Resolve({ onClick, label }) {
  return (
    <button onClick={onClick} className="flex-shrink-0 inline-flex items-center gap-1 rounded-lg bg-green-600 text-white text-[12px] font-bold px-2.5 h-8 hover:bg-green-700 transition">
      <CheckCircle2 size={13} /> {label}
    </button>
  );
}

function OfficerChat({ officerKey }) {
  const [msgs, setMsgs] = useState([{ role: "bot", text: "👮 Ask me for a summary, the SOS feed, lost & found, or to find a pilgrim by name / Yatra ID." }]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);
  const send = async () => {
    const t = input.trim(); if (!t || busy) return;
    setInput(""); setMsgs((m) => [...m, { role: "user", text: t }]); setBusy(true);
    try { const reply = await officerAsk(t, officerKey); setMsgs((m) => [...m, { role: "bot", text: reply }]); }
    catch (e) { setMsgs((m) => [...m, { role: "bot", text: `Error: ${e?.message || e}` }]); }
    finally { setBusy(false); }
  };
  return (
    <div className="rounded-2xl border border-bdr bg-surface shadow-card flex flex-col h-[60vh]">
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
        {msgs.map((m, i) => (
          <div key={i} className={m.role === "user" ? "flex justify-end" : "flex"}>
            <div className={`max-w-[85%] px-3.5 py-2 rounded-2xl text-[13.5px] whitespace-pre-wrap ${m.role === "user" ? "bg-primary text-white rounded-br-md" : "bg-surface-2 text-ink rounded-tl-md"}`}>{m.role === "bot" ? m.text.replace(/\*\*/g, "").replace(/`/g, "") : m.text}</div>
          </div>
        ))}
        {busy ? <div className="text-[12.5px] text-muted italic px-1">…</div> : null}
        <div ref={endRef} />
      </div>
      <div className="border-t border-bdr p-2 flex items-center gap-2">
        <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="e.g. how many registered for Kumbh?" className="flex-1 h-10 rounded-full bg-surface-2 px-4 text-[14px] outline-none" />
        <button onClick={send} disabled={busy} className="w-10 h-10 rounded-full bg-primary text-white flex items-center justify-center disabled:opacity-60"><Send size={16} /></button>
      </div>
    </div>
  );
}
