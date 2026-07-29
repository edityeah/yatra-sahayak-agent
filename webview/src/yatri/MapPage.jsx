import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import { Navigation, MessageCircle, CalendarDays, Route as RouteIcon } from "lucide-react";
import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";
import PageShell from "../components/PageShell.jsx";
import { apiGet } from "../lib/api.js";
import { t } from "../lib/i18n.js";
import { YATRA_NAMES } from "../data/yatraNames.js";

// POI kinds → color + trilingual label (matches the filter chips + legend).
const KIND = {
  night_halt: { color: "#2563EB", label: { mr: "मुक्काम", hi: "पड़ाव", en: "Night halt" } },
  ghat: { color: "#0d9488", label: { mr: "घाट", hi: "घाट", en: "Ghat" } },
  medical: { color: "#dc2626", label: { mr: "आरोग्य", hi: "स्वास्थ्य", en: "Medical" } },
  water: { color: "#0891b2", label: { mr: "पिण्याचे पाणी", hi: "पेयजल", en: "Drinking water" } },
  toilet: { color: "#6b7280", label: { mr: "शौचालय", hi: "शौचालय", en: "Toilet" } },
  stay: { color: "#7c3aed", label: { mr: "निवास", hi: "आवास", en: "Stay" } },
  hotel: { color: "#d97706", label: { mr: "हॉटेल", hi: "होटल", en: "Hotels" } },
};
const POI_KINDS = Object.keys(KIND);

const ALL = { mr: "सर्व", hi: "सभी", en: "All" };
const EVENTS = { mr: "कार्यक्रम", hi: "कार्यक्रम", en: "Events" };
const EVENTS_TITLE = { mr: "कार्यक्रम व वेळापत्रक", hi: "कार्यक्रम व समय-सारणी", en: "Events & schedule" };
const ITIN = { mr: "प्रवास वेळापत्रक", hi: "यात्रा कार्यक्रम", en: "Itinerary" };
const ITIN_TITLE = { mr: "दिवसनिहाय प्रवास वेळापत्रक", hi: "दिन-प्रतिदिन यात्रा कार्यक्रम", en: "Day-by-day itinerary" };
const DAY = { mr: "दिवस", hi: "दिन", en: "Day" };
const KM = { mr: "किमी", hi: "किमी", en: "km" };
const NAVIGATE = { mr: "दिशा", hi: "दिशा", en: "Navigate" };
const ASK = { mr: "चॅटमध्ये विचारा", hi: "चैट में पूछें", en: "Ask in chat" };
const EMPTY_TEXT = {
  mr: "या यात्रेसाठी माहिती उपलब्ध नाही.",
  hi: "इस यात्रा के लिए जानकारी उपलब्ध नहीं है।",
  en: "No information is available for this yatra.",
};
const LOAD_FAILED = {
  mr: "माहिती लोड करता आली नाही. सर्व्हर सुरू होत असावा — पुन्हा प्रयत्न करा.",
  hi: "जानकारी लोड नहीं हो सकी। सर्वर शुरू हो रहा होगा — फिर से कोशिश करें।",
  en: "Couldn't load the route info — the server may be waking up. Try again.",
};
const RETRY = { mr: "पुन्हा प्रयत्न करा", hi: "फिर से कोशिश करें", en: "Retry" };
// Quick prompts that hop back to the chat (the webview → SwiftChat bridge).
const PROMPTS = [
  { mr: "आजचा टप्पा नियोजित करा", hi: "आज का चरण प्लान करें", en: "Plan today's stage" },
  { mr: "जवळचे आरोग्य केंद्र?", hi: "नज़दीकी स्वास्थ्य केंद्र?", en: "Nearest medical help?" },
  { mr: "आज रात्री कुठे राहू?", hi: "आज रात कहाँ रुकें?", en: "Where can I stay tonight?" },
];

function dotIcon(kind) {
  const c = KIND[kind]?.color || "#2563EB";
  return L.divIcon({
    className: "",
    html: `<div style="width:16px;height:16px;border-radius:50%;background:${c};border:2px solid #fff;box-shadow:0 0 0 1px ${c}"></div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
}

export default function MapPage() {
  const { language, yatra } = useLang();
  const navigate = useNavigate();
  const [entries, setEntries] = useState(null);
  const [events, setEvents] = useState([]);
  const [itinerary, setItinerary] = useState([]);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const yatraName = YATRA_NAMES[yatra] ? t(YATRA_NAMES[yatra], language) : yatra;

  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    // routes is the primary dataset — if it FAILS (vs returns empty), surface a
    // retryable error, don't silently show "no information". events/itinerary
    // stay best-effort. apiGet already retries to ride out a cold start.
    apiGet(`/api/yatra/${yatra}/routes`)
      .then(async (routes) => {
        if (cancelled) return;
        setEntries(routes || []);
        const [evs, itin] = await Promise.all([
          apiGet(`/api/yatra/${yatra}/events`).catch(() => []),
          apiGet(`/api/yatra/${yatra}/itinerary`).catch(() => []),
        ]);
        if (cancelled) return;
        setEvents(evs || []);
        setItinerary(itin || []);
      })
      .catch((e) => !cancelled && setError(e?.message || String(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [yatra, reloadKey]);

  // POI kinds actually present for this yatra (drives which chips show).
  const presentKinds = useMemo(
    () => POI_KINDS.filter((k) => (entries || []).some((e) => e.kind === k)),
    [entries]
  );

  const pois = useMemo(
    () => (entries || []).filter((e) => typeof e.lat === "number" && typeof e.lng === "number"),
    [entries]
  );
  const nonPoiFilter = filter === "events" || filter === "itinerary";
  const shownPois = useMemo(
    () => (filter === "all" || nonPoiFilter ? pois : pois.filter((e) => e.kind === filter)),
    [pois, filter, nonPoiFilter]
  );
  const bounds = useMemo(() => (pois.length ? pois.map((p) => [p.lat, p.lng]) : null), [pois]);

  const askInChat = (question) => navigate(`/?q=${encodeURIComponent(question)}`);
  const openDirections = (lat, lng) =>
    window.open(`https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`, "_blank", "noopener");

  const listPois = nonPoiFilter ? [] : shownPois;

  return (
    <PageShell title={tr(strings, "map", language)}>
      {loading ? <div className="text-[13.5px] text-muted px-1 py-3">{tr(strings, "loading", language)}</div> : null}
      {!loading && error ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 text-amber-800 text-[13.5px] px-4 py-3 flex items-center justify-between gap-3">
          <span>{t(LOAD_FAILED, language)}</span>
          <button onClick={() => setReloadKey((k) => k + 1)}
            className="flex-shrink-0 h-9 px-4 rounded-full bg-primary text-white text-[13px] font-bold hover:bg-primary-700 transition">
            {t(RETRY, language)}
          </button>
        </div>
      ) : null}

      {!loading && !error && pois.length === 0 && events.length === 0 ? (
        <div className="rounded-2xl border border-bdr bg-surface shadow-card p-4 text-[13.5px] text-ink">
          {EMPTY_TEXT[language] || EMPTY_TEXT.en}
        </div>
      ) : null}

      {!loading && !error && (pois.length > 0 || events.length > 0) ? (
        <div className="space-y-3">
          {/* Category filter chips */}
          <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
            <Chip active={filter === "all"} onClick={() => setFilter("all")} label={t(ALL, language)} />
            {presentKinds.map((k) => (
              <Chip key={k} active={filter === k} onClick={() => setFilter(k)}
                label={t(KIND[k].label, language)} color={KIND[k].color} />
            ))}
            {itinerary.length ? (
              <Chip active={filter === "itinerary"} onClick={() => setFilter("itinerary")} label={t(ITIN, language)} />
            ) : null}
            {events.length ? (
              <Chip active={filter === "events"} onClick={() => setFilter("events")} label={t(EVENTS, language)} />
            ) : null}
          </div>

          {/* Map */}
          {shownPois.length > 0 ? (
            <div className="w-full overflow-hidden rounded-2xl border border-bdr shadow-card">
              <MapContainer key={`${yatra}-${filter}`} bounds={bounds} boundsOptions={{ padding: [24, 24] }}
                scrollWheelZoom={true} style={{ height: "48vh", width: "100%" }}>
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' />
                {shownPois.map((e, i) => (
                  <Marker key={i} position={[e.lat, e.lng]} icon={dotIcon(e.kind)}>
                    <Popup>
                      <strong>{t(e.name, language)}</strong><br />
                      {t(KIND[e.kind]?.label, language) || e.kind}
                      {e.note ? <><br />{t(e.note, language)}</> : null}
                    </Popup>
                  </Marker>
                ))}
              </MapContainer>
            </div>
          ) : null}

          {/* Ask-in-chat prompt chips (hop back to the bot) */}
          <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
            {PROMPTS.map((p, i) => (
              <button key={i} onClick={() => askInChat(`${t(p, language)} (${yatraName})`)}
                className="flex-shrink-0 inline-flex items-center gap-1.5 rounded-full border border-primary/30 bg-primary-50 text-primary text-[12.5px] font-bold px-3 py-1.5 hover:bg-primary-100 transition">
                <MessageCircle size={13} /> {t(p, language)}
              </button>
            ))}
          </div>

          {/* Directory list (POIs) */}
          {listPois.map((e, i) => (
            <div key={i} className="rounded-2xl border border-bdr bg-surface shadow-card p-4">
              <div className="flex items-start gap-2">
                <span className="mt-1 w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: KIND[e.kind]?.color }} />
                <div className="flex-1 min-w-0">
                  <div className="text-[14.5px] font-extrabold text-ink">{t(e.name, language)}</div>
                  <div className="text-[11.5px] font-bold text-muted uppercase tracking-wide">{t(KIND[e.kind]?.label, language)}</div>
                  {e.note ? <p className="mt-1 text-[13px] text-ink leading-relaxed">{t(e.note, language)}</p> : null}
                  <div className="mt-2.5 flex flex-wrap gap-2">
                    <button onClick={() => openDirections(e.lat, e.lng)}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-bdr bg-surface-2 text-ink text-[12px] font-bold px-2.5 h-8 hover:border-primary transition">
                      <Navigation size={13} /> {t(NAVIGATE, language)}
                    </button>
                    <button onClick={() => askInChat(`${t(e.name, language)} (${yatraName}) — ${t(KIND[e.kind]?.label, language)}?`)}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-primary text-white text-[12px] font-bold px-2.5 h-8 hover:bg-primary-700 transition">
                      <MessageCircle size={13} /> {t(ASK, language)}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}

          {/* Day-by-day itinerary */}
          {filter === "itinerary" && itinerary.length ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-[14px] font-extrabold text-ink pt-1">
                <RouteIcon size={16} className="text-primary" /> {t(ITIN_TITLE, language)}
              </div>
              {itinerary.map((st, i) => (
                <div key={i} className="rounded-2xl border border-bdr bg-surface shadow-card p-4 flex gap-3">
                  <div className="flex-shrink-0 w-11 h-11 rounded-xl bg-primary-50 text-primary flex flex-col items-center justify-center leading-none">
                    <span className="text-[9px] font-bold uppercase">{t(DAY, language)}</span>
                    <span className="text-[16px] font-extrabold">{st.day}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[14.5px] font-extrabold text-ink">{t(st.title, language)}</span>
                      {st.distance_km ? (
                        <span className="text-[11px] font-bold text-primary bg-primary-50 rounded-full px-2 py-0.5">
                          {st.distance_km} {t(KM, language)}
                        </span>
                      ) : null}
                    </div>
                    {st.note ? <p className="mt-1 text-[13px] text-ink leading-relaxed">{t(st.note, language)}</p> : null}
                    <button onClick={() => askInChat(`${t(st.title, language)} (${yatraName}) — ${t(ITIN, language)}?`)}
                      className="mt-2 inline-flex items-center gap-1.5 rounded-lg border border-bdr bg-surface-2 text-ink text-[12px] font-bold px-2.5 h-8 hover:border-primary transition">
                      <MessageCircle size={13} /> {t(ASK, language)}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : null}

          {/* Events / schedule */}
          {filter === "events" && events.length ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-[14px] font-extrabold text-ink pt-1">
                <CalendarDays size={16} className="text-primary" /> {t(EVENTS_TITLE, language)}
              </div>
              {events.map((ev, i) => (
                <div key={i} className="rounded-2xl border border-bdr bg-surface shadow-card p-4">
                  <div className="text-[14.5px] font-extrabold text-ink">{t(ev.name, language)}</div>
                  <div className="mt-0.5 text-[12.5px] font-bold text-primary">
                    {t(ev.when, language)}{ev.place ? ` · ${t(ev.place, language)}` : ""}
                  </div>
                  {ev.note ? <p className="mt-1 text-[13px] text-ink leading-relaxed">{t(ev.note, language)}</p> : null}
                  <button onClick={() => askInChat(`${t(ev.name, language)} (${yatraName}) — ${t(EVENTS, language)}?`)}
                    className="mt-2.5 inline-flex items-center gap-1.5 rounded-lg bg-primary text-white text-[12px] font-bold px-2.5 h-8 hover:bg-primary-700 transition">
                    <MessageCircle size={13} /> {t(ASK, language)}
                  </button>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </PageShell>
  );
}

function Chip({ active, onClick, label, color }) {
  return (
    <button onClick={onClick}
      className={`flex-shrink-0 inline-flex items-center gap-1.5 rounded-full text-[12.5px] font-bold px-3 py-1.5 border transition ${
        active ? "bg-primary text-white border-primary" : "bg-surface text-ink border-bdr hover:border-primary"
      }`}>
      {color ? <span className="w-2.5 h-2.5 rounded-full" style={{ background: active ? "#fff" : color }} /> : null}
      {label}
    </button>
  );
}
