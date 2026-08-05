import { useCallback, useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import { Users, AlertTriangle, Siren, RefreshCw, Sparkles } from "lucide-react";
import OfficerGate, { useOfficerKey } from "./OfficerGate.jsx";
import { getHeatmap, simulateArrivals, YATRA } from "./officerApi.js";

// Occupancy status → colour. Green ok · amber busy · red over-capacity.
const TONE = {
  ok: { hex: "#16a34a", pill: "bg-green-100 text-green-700", label: "OK" },
  busy: { hex: "#d97706", pill: "bg-amber-100 text-amber-800", label: "Busy" },
  over: { hex: "#dc2626", pill: "bg-red-100 text-red-700", label: "Over capacity" },
};
const REFRESH_MS = 15000;

function Kpi({ icon: Icon, label, value, tone }) {
  return (
    <div className="rounded-xl border border-bdr bg-surface p-3 flex items-center gap-2.5">
      <span className={`w-8 h-8 rounded-full flex items-center justify-center ${tone || "bg-primary-50 text-primary"}`}><Icon size={16} /></span>
      <div><div className="text-[17px] font-extrabold text-ink leading-none">{value}</div>
        <div className="text-[11px] text-muted mt-0.5">{label}</div></div>
    </div>
  );
}

function Inner() {
  const key = useOfficerKey();
  const [yatra, setYatra] = useState("pandharpur");
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => getHeatmap(key, yatra).then(setData).catch(() => setData(null)), [key, yatra]);
  useEffect(() => {
    load();
    const t = setInterval(load, REFRESH_MS);   // live — refresh every 15s
    return () => clearInterval(t);
  }, [load]);

  const simulate = async () => {
    setBusy(true);
    try { await simulateArrivals(key, yatra); await load(); }
    finally { setBusy(false); }
  };

  const cps = data?.checkpoints || [];
  const bounds = useMemo(() => (cps.length ? cps.map((c) => [c.lat, c.lng]) : null), [cps]);
  const t = data?.totals || {};

  return (
    <main className="max-w-4xl w-full mx-auto px-4 py-4 space-y-3">
      {/* Yatra toggle + refresh + simulate */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex gap-1.5">
          {Object.entries(YATRA).map(([k, v]) => (
            <button key={k} onClick={() => setYatra(k)}
              className={`text-[12.5px] font-bold px-3 h-8 rounded-full border transition ${yatra === k ? "bg-primary text-white border-primary" : "bg-surface text-ink border-bdr"}`}>{v}</button>
          ))}
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="inline-flex items-center gap-1.5 rounded-full border border-bdr text-ink text-[12px] font-bold px-3 h-8 hover:bg-slate-50"><RefreshCw size={13} /> Refresh</button>
          <button onClick={simulate} disabled={busy} className="inline-flex items-center gap-1.5 rounded-full bg-primary text-white text-[12px] font-bold px-3 h-8 hover:bg-primary-700 disabled:opacity-50"><Sparkles size={13} /> {busy ? "Simulating…" : "Simulate arrivals"}</button>
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <Kpi icon={Users} label={`scans · last ${data?.window_min || 30} min`} value={t.scans ?? "—"} />
        <Kpi icon={AlertTriangle} label="zones over capacity" value={t.over ?? "—"} tone={t.over ? "bg-red-100 text-red-700" : undefined} />
        <Kpi icon={Siren} label="open SOS" value={t.open_sos ?? "—"} tone={t.open_sos ? "bg-red-100 text-red-700" : undefined} />
        <Kpi icon={Users} label="lost & found" value={t.open_lostfound ?? "—"} />
      </div>

      {/* Over-capacity alert banner */}
      {data?.alerts?.length ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3">
          <div className="flex items-center gap-2 text-[13px] font-extrabold text-red-700"><AlertTriangle size={16} /> Crowd threshold exceeded</div>
          <div className="text-[12.5px] text-red-800 mt-1">{data.alerts.map((a) => `${a.name.en} (${a.count}/${a.capacity})`).join(" · ")}</div>
        </div>
      ) : null}

      {/* Density map */}
      {bounds ? (
        <div className="w-full overflow-hidden rounded-2xl border border-bdr shadow-card">
          <MapContainer key={yatra} bounds={bounds} boundsOptions={{ padding: [30, 30] }} scrollWheelZoom style={{ height: "44vh", width: "100%" }}>
            <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution='&copy; OpenStreetMap' />
            {cps.map((c) => (
              <CircleMarker key={c.id} center={[c.lat, c.lng]}
                radius={8 + Math.min(c.load, 1.5) * 16}
                pathOptions={{ color: TONE[c.status].hex, fillColor: TONE[c.status].hex, fillOpacity: 0.45, weight: 2 }}>
                <Popup>
                  <strong>{c.name.en}</strong><br />
                  {c.count} in last {data.window_min} min · {Math.round(c.load * 100)}% of capacity<br />
                  {TONE[c.status].label}{c.incidents ? ` · ${c.incidents} SOS nearby` : ""}
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>
      ) : null}

      {/* Zone list (busiest first) */}
      <div className="space-y-2">
        {cps.map((c) => (
          <div key={c.id} className="rounded-xl border border-bdr bg-surface p-3">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: TONE[c.status].hex }} />
                <span className="text-[13.5px] font-bold text-ink truncate">{c.name.en}</span>
                {c.incidents ? <span className="inline-flex items-center gap-1 text-[10.5px] font-bold text-red-700 bg-red-100 px-1.5 py-0.5 rounded-full"><Siren size={10} /> {c.incidents}</span> : null}
              </div>
              <span className={`text-[10.5px] font-bold px-2 py-0.5 rounded-full flex-shrink-0 ${TONE[c.status].pill}`}>{TONE[c.status].label}</span>
            </div>
            <div className="mt-2 flex items-center gap-3">
              <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
                <div className="h-full rounded-full" style={{ width: `${Math.min(c.load, 1) * 100}%`, background: TONE[c.status].hex }} />
              </div>
              <span className="text-[12px] font-mono text-muted flex-shrink-0">{c.count}/{c.capacity}</span>
            </div>
          </div>
        ))}
        {data && !cps.length ? <div className="text-center py-10 text-muted text-[13.5px]">No checkpoints for this yatra.</div> : null}
        {!data ? <div className="text-center py-10 text-muted text-[13.5px]">Loading crowd map…</div> : null}
      </div>

      <p className="text-[11px] text-muted px-1 pt-1">Occupancy is counted from pass scans at gates — a headcount per checkpoint, with no tracking of anyone between checkpoints.</p>
    </main>
  );
}

export default function OfficerHeatmap() {
  return <OfficerGate title="Crowd map" subtitle="Live occupancy from pass scans" back><Inner /></OfficerGate>;
}
