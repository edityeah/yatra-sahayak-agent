import { useEffect, useMemo, useState } from "react";
import { MapPin, ArrowRight, Users, Clock, IndianRupee, MessageCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";
import PageShell from "../components/PageShell.jsx";
import { apiGet } from "../lib/api.js";
import { t } from "../lib/i18n.js";

const L = {
  from: { mr: "कुठून", hi: "कहाँ से", en: "From" },
  to: { mr: "कुठे", hi: "कहाँ", en: "To" },
  people: { mr: "प्रवासी", hi: "यात्री", en: "Travellers" },
  plan: { mr: "पर्याय पाहा", hi: "विकल्प देखें", en: "See options" },
  distance: { mr: "अंदाजे अंतर", hi: "अनुमानित दूरी", en: "Approx distance" },
  km: { mr: "किमी", hi: "किमी", en: "km" },
  perPerson: { mr: "प्रति व्यक्ती", hi: "प्रति व्यक्ति", en: "per person" },
  free: { mr: "मोफत", hi: "निःशुल्क", en: "Free" },
  pickDiff: { mr: "वेगळी ठिकाणे निवडा.", hi: "अलग स्थान चुनें।", en: "Pick two different places." },
  hrs: { mr: "तास", hi: "घंटे", en: "h" },
  min: { mr: "मि", hi: "मि", en: "m" },
  note: { mr: "दर सूचक आहेत — प्रवासापूर्वी दर ठरवा व पावती मागा. जास्त दर आकारल्यास तक्रार नोंदवा.",
          hi: "दर सूचक हैं — यात्रा से पहले दर तय करें व रसीद माँगें। अधिक दाम पर शिकायत दर्ज करें।",
          en: "Rates are indicative — agree the fare before travel and ask for a receipt. Report overcharging." },
  reportOvercharge: { mr: "जास्त दराची तक्रार", hi: "अधिक दाम की शिकायत", en: "Report overcharging" },
};

function haversineKm(a, b) {
  const R = 6371, toRad = (d) => (d * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat), dLng = toRad(b.lng - a.lng);
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(s));
}

export default function TransportPage() {
  const { language, yatra } = useLang();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [fromI, setFromI] = useState(0);
  const [toI, setToI] = useState(1);
  const [people, setPeople] = useState(1);
  const [planned, setPlanned] = useState(false);

  useEffect(() => {
    let cancelled = false;
    apiGet(`/api/yatra/${yatra || "pandharpur"}/transport`)
      .then((d) => { if (!cancelled) { setData(d); setPlanned(false); } })
      .catch((e) => !cancelled && setError(e?.message || String(e)));
    return () => { cancelled = true; };
  }, [yatra]);

  const locations = data?.locations || [];
  const modes = data?.modes || [];

  const results = useMemo(() => {
    if (!planned || !locations[fromI] || !locations[toI] || fromI === toI) return null;
    const km = Math.max(1, Math.round(haversineKm(locations[fromI], locations[toI]) * 1.3));
    const rows = modes.map((m) => {
      const base = Math.max(m.min_fare, Math.round(km * m.rate_per_km));
      const cost = m.rate_per_km === 0 ? 0 : (m.per_person ? base * people : base);
      const mins = Math.round((km / m.speed_kmh) * 60);
      return { m, cost, mins };
    }).sort((a, b) => a.cost - b.cost);
    return { km, rows };
  }, [planned, fromI, toI, people, locations, modes]);

  const fmtTime = (mins) => {
    const h = Math.floor(mins / 60), mm = mins % 60;
    return (h ? `${h}${t(L.hrs, language)} ` : "") + `${mm}${t(L.min, language)}`;
  };

  return (
    <PageShell title={tr(strings, "transport", language)}>
      {error ? <div className="rounded-2xl border border-red-200 bg-red-50 text-red-700 text-[13.5px] px-4 py-3">{error}</div> : null}

      <div className="rounded-2xl border border-bdr bg-surface shadow-card p-4 space-y-3">
        <Select icon={<MapPin size={15} className="text-primary" />} label={t(L.from, language)} value={fromI}
          onChange={(v) => { setFromI(v); setPlanned(false); }} locations={locations} language={language} />
        <div className="flex justify-center text-muted"><ArrowRight size={16} /></div>
        <Select icon={<MapPin size={15} className="text-red-500" />} label={t(L.to, language)} value={toI}
          onChange={(v) => { setToI(v); setPlanned(false); }} locations={locations} language={language} />
        <label className="flex items-center gap-2">
          <Users size={15} className="text-muted" />
          <span className="text-[13px] font-bold text-ink flex-1">{t(L.people, language)}</span>
          <input type="number" min={1} max={20} value={people} onChange={(e) => { setPeople(Math.max(1, +e.target.value || 1)); setPlanned(false); }}
            className="w-20 h-9 rounded-xl border border-bdr bg-surface px-3 text-[14px] text-center outline-none focus:border-primary" />
        </label>
        <button onClick={() => setPlanned(true)} disabled={fromI === toI}
          className="w-full h-11 rounded-full bg-primary text-white font-extrabold disabled:opacity-50 hover:bg-primary-700 transition">
          {t(L.plan, language)}
        </button>
        {fromI === toI ? <p className="text-[12.5px] text-amber-700 text-center">{t(L.pickDiff, language)}</p> : null}
      </div>

      {results ? (
        <div className="mt-3 space-y-3">
          <div className="text-[13px] text-muted text-center">
            {t(L.distance, language)}: <span className="font-bold text-ink">{results.km} {t(L.km, language)}</span>
            {" · "}{t(locations[fromI].name, language)} → {t(locations[toI].name, language)}
          </div>
          {results.rows.map(({ m, cost, mins }) => (
            <div key={m.id} className="rounded-2xl border border-bdr bg-surface shadow-card p-4 flex items-start gap-3">
              <div className="flex-1 min-w-0">
                <div className="text-[14.5px] font-extrabold text-ink">{t(m.name, language)}</div>
                <p className="text-[12.5px] text-muted mt-0.5">{t(m.note, language)}</p>
                <div className="mt-1.5 flex items-center gap-1 text-[12.5px] text-muted"><Clock size={13} /> ~{fmtTime(mins)}</div>
              </div>
              <div className="text-right flex-shrink-0">
                <div className="text-[18px] font-extrabold text-ink flex items-center justify-end">
                  {cost === 0 ? t(L.free, language) : <><IndianRupee size={15} />{cost.toLocaleString("en-IN")}</>}
                </div>
                {m.per_person && cost > 0 ? <div className="text-[11px] text-muted">{t(L.perPerson, language)} × {people}</div> : null}
              </div>
            </div>
          ))}
          <div className="rounded-2xl border border-amber-200 bg-amber-50 text-amber-800 text-[12.5px] px-4 py-3 leading-relaxed">
            {t(L.note, language)}
          </div>
          <button onClick={() => navigate("/yatri/grievance")}
            className="w-full h-10 rounded-full border border-bdr bg-surface text-ink text-[13px] font-bold flex items-center justify-center gap-1.5 hover:border-primary transition">
            <MessageCircle size={14} /> {t(L.reportOvercharge, language)}
          </button>
        </div>
      ) : null}
    </PageShell>
  );
}

function Select({ icon, label, value, onChange, locations, language }) {
  return (
    <label className="block">
      <span className="text-[12px] font-bold text-muted uppercase tracking-wide flex items-center gap-1.5">{icon} {label}</span>
      <select value={value} onChange={(e) => onChange(+e.target.value)}
        className="mt-1 w-full h-11 rounded-xl border border-bdr bg-surface px-3 text-[14px] text-ink outline-none focus:border-primary">
        {locations.map((l, i) => <option key={i} value={i}>{t(l.name, language)}</option>)}
      </select>
    </label>
  );
}
