import { useEffect, useMemo, useState } from "react";
import { MapPin, ArrowRight, ArrowUpDown, Users, Clock, IndianRupee, MessageCircle, CalendarDays, Wallet } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";
import PageShell from "../components/PageShell.jsx";
import { apiGet } from "../lib/api.js";
import { t } from "../lib/i18n.js";

const L = {
  from: { mr: "कुठून", hi: "कहाँ से", en: "From" },
  to: { mr: "कुठे", hi: "कहाँ", en: "To" },
  date: { mr: "प्रवासाची तारीख", hi: "यात्रा तिथि", en: "Travel date" },
  departAt: { mr: "निघण्याची वेळ", hi: "प्रस्थान समय", en: "Depart at" },
  people: { mr: "प्रवासी", hi: "यात्री", en: "Travellers" },
  plan: { mr: "पर्याय शोधा", hi: "विकल्प खोजें", en: "Search options" },
  distance: { mr: "अंदाजे अंतर", hi: "अनुमानित दूरी", en: "Approx distance" },
  km: { mr: "किमी", hi: "किमी", en: "km" },
  perPerson: { mr: "प्रति व्यक्ती", hi: "प्रति व्यक्ति", en: "per person" },
  free: { mr: "मोफत", hi: "निःशुल्क", en: "Free" },
  pickDiff: { mr: "वेगळी ठिकाणे निवडा.", hi: "अलग स्थान चुनें।", en: "Pick two different places." },
  hrs: { mr: "तास", hi: "घं", en: "h" },
  min: { mr: "मि", hi: "मि", en: "m" },
  dep: { mr: "निघणे", hi: "प्रस्थान", en: "Dep" },
  arr: { mr: "पोहोच", hi: "आगमन", en: "Arr" },
  total: { mr: "एकूण (अंदाजे)", hi: "कुल (अनुमानित)", en: "Total (est.)" },
  cheapest: { mr: "स्वस्त", hi: "सस्ता", en: "Cheapest" },
  fastest: { mr: "जलद", hi: "तेज़", en: "Fastest" },
  all: { mr: "सर्व", hi: "सभी", en: "All" },
  results: { mr: "पर्याय", hi: "विकल्प", en: "options" },
  note: { mr: "दर सूचक आहेत — प्रवासापूर्वी दर ठरवा व पावती मागा. जास्त दर आकारल्यास तक्रार नोंदवा.",
          hi: "दर सूचक हैं — यात्रा से पहले दर तय करें व रसीद माँगें। अधिक दाम पर शिकायत दर्ज करें।",
          en: "Fares are indicative estimates — agree the fare before travel and ask for a receipt. Report overcharging." },
  reportOvercharge: { mr: "जास्त दराची तक्रार", hi: "अधिक दाम की शिकायत", en: "Report overcharging" },
};

// Category label per filter key (only present ones are shown as chips).
const CAT = {
  walk: { mr: "पायी", hi: "पैदल", en: "On foot" },
  bus: { mr: "बस", hi: "बस", en: "Bus" },
  shared: { mr: "शेअर", hi: "शेयर", en: "Shared" },
  private: { mr: "ऑटो/टॅक्सी", hi: "ऑटो/टैक्सी", en: "Auto / Taxi" },
  cart: { mr: "बैलगाडी", hi: "बैलगाड़ी", en: "Bullock cart" },
  other: { mr: "इतर", hi: "अन्य", en: "Other" },
};
// mode id → { category, emoji icon }.
const MODE_META = {
  walk: { cat: "walk", icon: "🚶" },
  bullock: { cat: "cart", icon: "🐂" },
  shared_jeep: { cat: "shared", icon: "🚐" },
  st_bus: { cat: "bus", icon: "🚌" },
  city_bus: { cat: "bus", icon: "🚌" },
  auto: { cat: "private", icon: "🛺" },
  taxi: { cat: "private", icon: "🚕" },
};
const metaFor = (id) => MODE_META[id] || { cat: "other", icon: "🚗" };

function haversineKm(a, b) {
  const R = 6371, toRad = (d) => (d * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat), dLng = toRad(b.lng - a.lng);
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(s));
}

const todayISO = () => new Date().toISOString().slice(0, 10);

export default function TransportPage() {
  const { language, yatra } = useLang();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [fromI, setFromI] = useState(0);
  const [toI, setToI] = useState(1);
  const [people, setPeople] = useState(1);
  const [date, setDate] = useState(todayISO());
  const [depTime, setDepTime] = useState("06:00");
  const [planned, setPlanned] = useState(false);
  const [sort, setSort] = useState("cheapest");   // cheapest | fastest
  const [cat, setCat] = useState("all");

  useEffect(() => {
    let cancelled = false;
    apiGet(`/api/yatra/${yatra || "pandharpur"}/transport`)
      .then((d) => { if (!cancelled) { setData(d); setPlanned(false); } })
      .catch((e) => !cancelled && setError(e?.message || String(e)));
    return () => { cancelled = true; };
  }, [yatra]);

  const locations = data?.locations || [];
  const modes = data?.modes || [];
  const reset = () => setPlanned(false);

  // All options for the chosen leg (before filter/sort).
  const all = useMemo(() => {
    if (!planned || !locations[fromI] || !locations[toI] || fromI === toI) return null;
    const km = Math.max(1, Math.round(haversineKm(locations[fromI], locations[toI]) * 1.3));
    const [dh, dm] = depTime.split(":").map(Number);
    const depMins = (dh || 0) * 60 + (dm || 0);
    const rows = modes.map((m) => {
      const base = Math.max(m.min_fare, Math.round(km * m.rate_per_km));
      const cost = m.rate_per_km === 0 ? 0 : (m.per_person ? base * people : base);
      const mins = Math.round((km / m.speed_kmh) * 60);
      const arrTotal = depMins + mins;
      const meta = metaFor(m.id);
      return { m, cost, mins, meta, arrTotal };
    });
    return { km, rows };
  }, [planned, fromI, toI, people, depTime, locations, modes]);

  // Which category chips to show (present in the results).
  const cats = useMemo(() => {
    if (!all) return [];
    const present = [...new Set(all.rows.map((r) => r.meta.cat))];
    const order = ["walk", "bus", "shared", "private", "cart", "other"];
    return order.filter((c) => present.includes(c));
  }, [all]);

  const shown = useMemo(() => {
    if (!all) return [];
    let rows = cat === "all" ? all.rows : all.rows.filter((r) => r.meta.cat === cat);
    rows = [...rows].sort((a, b) => (sort === "fastest" ? a.mins - b.mins : a.cost - b.cost));
    return rows;
  }, [all, cat, sort]);

  const fmtDur = (mins) => {
    const h = Math.floor(mins / 60), mm = mins % 60;
    return (h ? `${h}${t(L.hrs, language)} ` : "") + `${mm}${t(L.min, language)}`;
  };
  const fmtClock = (totalMins) => {
    const day = Math.floor(totalMins / 1440), m = ((totalMins % 1440) + 1440) % 1440;
    const hh = String(Math.floor(m / 60)).padStart(2, "0"), mm = String(m % 60).padStart(2, "0");
    return `${hh}:${mm}${day > 0 ? ` +${day}d` : ""}`;
  };

  const swap = () => { setFromI(toI); setToI(fromI); reset(); };

  return (
    <PageShell title={tr(strings, "transport", language)}>
      {error ? <div className="rounded-2xl border border-red-200 bg-red-50 text-red-700 text-[13.5px] px-4 py-3">{error}</div> : null}

      {/* Search card */}
      <div className="rounded-2xl border border-bdr bg-surface shadow-card p-4 space-y-3">
        <Select icon={<MapPin size={15} className="text-primary" />} label={t(L.from, language)} value={fromI}
          onChange={(v) => { setFromI(v); reset(); }} locations={locations} language={language} />
        <div className="flex justify-center">
          <button onClick={swap} aria-label="Swap" className="w-8 h-8 rounded-full border border-bdr bg-surface-2 flex items-center justify-center text-primary hover:border-primary transition">
            <ArrowUpDown size={15} />
          </button>
        </div>
        <Select icon={<MapPin size={15} className="text-red-500" />} label={t(L.to, language)} value={toI}
          onChange={(v) => { setToI(v); reset(); }} locations={locations} language={language} />

        <div className="grid grid-cols-2 gap-3">
          <Field icon={<CalendarDays size={14} className="text-primary" />} label={t(L.date, language)}>
            <input type="date" value={date} min={todayISO()} onChange={(e) => { setDate(e.target.value); reset(); }}
              className="w-full h-10 rounded-xl border border-bdr bg-surface px-3 text-[14px] text-ink outline-none focus:border-primary" />
          </Field>
          <Field icon={<Clock size={14} className="text-primary" />} label={t(L.departAt, language)}>
            <input type="time" value={depTime} onChange={(e) => { setDepTime(e.target.value); reset(); }}
              className="w-full h-10 rounded-xl border border-bdr bg-surface px-3 text-[14px] text-ink outline-none focus:border-primary" />
          </Field>
        </div>

        <label className="flex items-center gap-2">
          <Users size={15} className="text-muted" />
          <span className="text-[13px] font-bold text-ink flex-1">{t(L.people, language)}</span>
          <div className="flex items-center gap-2">
            <Step onClick={() => { setPeople((p) => Math.max(1, p - 1)); reset(); }}>−</Step>
            <span className="w-8 text-center text-[15px] font-extrabold text-ink">{people}</span>
            <Step onClick={() => { setPeople((p) => Math.min(20, p + 1)); reset(); }}>+</Step>
          </div>
        </label>

        <button onClick={() => { setCat("all"); setPlanned(true); }} disabled={fromI === toI}
          className="w-full h-11 rounded-full bg-primary text-white font-extrabold disabled:opacity-50 hover:bg-primary-700 transition">
          {t(L.plan, language)}
        </button>
        {fromI === toI ? <p className="text-[12.5px] text-amber-700 text-center">{t(L.pickDiff, language)}</p> : null}
      </div>

      {all ? (
        <div className="mt-3 space-y-3">
          {/* Trip summary */}
          <div className="text-[13px] text-muted text-center">
            {t(locations[fromI].name, language)} <ArrowRight size={12} className="inline" /> {t(locations[toI].name, language)}
            {" · "}<span className="font-bold text-ink">{all.km} {t(L.km, language)}</span>
            {" · "}{date}{" · "}{shown.length} {t(L.results, language)}
          </div>

          {/* Sort + category filters */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            <div className="flex rounded-full border border-bdr overflow-hidden flex-shrink-0">
              {["cheapest", "fastest"].map((s) => (
                <button key={s} onClick={() => setSort(s)}
                  className={`h-8 px-3 text-[12.5px] font-bold ${sort === s ? "bg-primary text-white" : "bg-surface text-muted"}`}>
                  {t(s === "cheapest" ? L.cheapest : L.fastest, language)}
                </button>
              ))}
            </div>
            <div className="w-px h-6 bg-bdr flex-shrink-0" />
            <Chip active={cat === "all"} onClick={() => setCat("all")}>{t(L.all, language)}</Chip>
            {cats.map((c) => (
              <Chip key={c} active={cat === c} onClick={() => setCat(c)}>{t(CAT[c], language)}</Chip>
            ))}
          </div>

          {/* Option cards */}
          {shown.map(({ m, cost, mins, meta, arrTotal }) => (
            <div key={m.id} className="rounded-2xl border border-bdr bg-surface shadow-card p-4 flex items-start gap-3">
              <div className="text-[26px] leading-none flex-shrink-0 mt-0.5">{meta.icon}</div>
              <div className="flex-1 min-w-0">
                <div className="text-[14.5px] font-extrabold text-ink">{t(m.name, language)}</div>
                <p className="text-[12px] text-muted mt-0.5">{t(m.note, language)}</p>
                <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px] text-muted">
                  <span className="flex items-center gap-1"><Clock size={12} /> ~{fmtDur(mins)}</span>
                  <span>{t(L.dep, language)} {depTime} <ArrowRight size={10} className="inline" /> {t(L.arr, language)} {fmtClock(arrTotal)}</span>
                </div>
              </div>
              <div className="text-right flex-shrink-0">
                <div className="text-[19px] font-extrabold text-ink flex items-center justify-end">
                  {cost === 0 ? t(L.free, language) : <><IndianRupee size={15} />{cost.toLocaleString("en-IN")}</>}
                </div>
                <div className="text-[10.5px] text-muted flex items-center justify-end gap-0.5">
                  <Wallet size={10} /> {t(L.total, language)}
                </div>
                {m.per_person && cost > 0 ? <div className="text-[10.5px] text-muted">{t(L.perPerson, language)} × {people}</div> : null}
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

function Field({ icon, label, children }) {
  return (
    <label className="block">
      <span className="text-[11px] font-bold text-muted uppercase tracking-wide flex items-center gap-1">{icon} {label}</span>
      <div className="mt-1">{children}</div>
    </label>
  );
}

function Step({ onClick, children }) {
  return (
    <button onClick={onClick} className="w-8 h-8 rounded-full border border-bdr bg-surface-2 text-primary text-[17px] font-bold flex items-center justify-center hover:border-primary transition">
      {children}
    </button>
  );
}

function Chip({ active, onClick, children }) {
  return (
    <button onClick={onClick}
      className={`h-8 px-3.5 rounded-full text-[12.5px] font-bold whitespace-nowrap flex-shrink-0 border transition ${active ? "bg-primary text-white border-primary" : "bg-surface text-ink border-bdr hover:border-primary"}`}>
      {children}
    </button>
  );
}
