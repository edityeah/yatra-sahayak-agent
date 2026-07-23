import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";
import { Loading, ErrorNote } from "../components/ui.jsx";
import { apiGet } from "../lib/api.js";
import { getContext } from "../lib/swiftchat.js";
import { t } from "../lib/i18n.js";

// Route/POI marker colors by kind — matches the legend below.
const KIND_COLORS = {
  night_halt: "#4f46e5",
  ghat: "#0d9488",
  medical: "#dc2626",
  water: "#2563eb",
  toilet: "#6b7280",
};

const KIND_LABELS = {
  night_halt: { mr: "मुक्काम", hi: "पड़ाव", en: "Night halt" },
  ghat: { mr: "घाट", hi: "घाट", en: "Ghat" },
  medical: { mr: "आरोग्य केंद्र", hi: "स्वास्थ्य केंद्र", en: "Medical" },
  water: { mr: "पिण्याचे पाणी", hi: "पेयजल", en: "Drinking water" },
  toilet: { mr: "शौचालय", hi: "शौचालय", en: "Toilet" },
};

const EMPTY_TEXT = {
  mr: "या यात्रेसाठी मार्ग माहिती उपलब्ध नाही.",
  hi: "इस यात्रा के लिए मार्ग जानकारी उपलब्ध नहीं है।",
  en: "No route information is available for this yatra.",
};

// Small colored-dot icon per kind — avoids the well-known broken default
// Leaflet marker icon issue under bundlers (no external image assets).
function dotIcon(kind) {
  const c = KIND_COLORS[kind] || "#4f46e5";
  return L.divIcon({
    className: "",
    html: `<div style="width:16px;height:16px;border-radius:50%;background:${c};border:2px solid #fff;box-shadow:0 0 0 1px ${c}"></div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
}

const legendWrapStyle = {
  display: "flex",
  flexWrap: "wrap",
  gap: "0.5rem 1rem",
  marginTop: "0.75rem",
  padding: "0.6rem 0.8rem",
  background: "#fff",
  border: "1px solid #e3ddd0",
  borderRadius: "10px",
  fontSize: "0.85rem",
};

const legendItemStyle = {
  display: "inline-flex",
  alignItems: "center",
  gap: "0.4rem",
};

function legendDotStyle(color) {
  return {
    width: "12px",
    height: "12px",
    borderRadius: "50%",
    background: color,
    border: "2px solid #fff",
    boxShadow: `0 0 0 1px ${color}`,
    display: "inline-block",
    flex: "0 0 auto",
  };
}

function Legend({ language }) {
  return (
    <div style={legendWrapStyle}>
      {Object.keys(KIND_COLORS).map((kind) => (
        <span style={legendItemStyle} key={kind}>
          <span style={legendDotStyle(KIND_COLORS[kind])} />
          {t(KIND_LABELS[kind], language)}
        </span>
      ))}
    </div>
  );
}

export default function MapPage() {
  const { language } = useLang();
  const [searchParams] = useSearchParams();
  const ctx = getContext();
  const yatra = searchParams.get("yatra") || ctx.yatra;

  const [entries, setEntries] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiGet(`/api/yatra/${yatra}/routes`)
      .then((data) => {
        if (!cancelled) setEntries(data);
      })
      .catch((e) => {
        if (!cancelled) setError(e?.message || String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [yatra]);

  const points = useMemo(
    () =>
      (entries || []).filter(
        (e) => typeof e.lat === "number" && typeof e.lng === "number"
      ),
    [entries]
  );

  const bounds = useMemo(() => {
    if (points.length === 0) return null;
    return points.map((p) => [p.lat, p.lng]);
  }, [points]);

  return (
    <div>
      <h1>{tr(strings, "map", language)}</h1>

      {loading ? <Loading text={tr(strings, "loading", language)} /> : null}
      {!loading && error ? <ErrorNote>{error}</ErrorNote> : null}

      {!loading && !error && points.length === 0 ? (
        <div className="card">{EMPTY_TEXT[language] || EMPTY_TEXT.en}</div>
      ) : null}

      {!loading && !error && points.length > 0 ? (
        <>
          <div style={{ width: "100%", maxWidth: "100%", overflow: "hidden", borderRadius: "10px", border: "1px solid #e3ddd0" }}>
            <MapContainer
              key={yatra}
              bounds={bounds}
              boundsOptions={{ padding: [24, 24] }}
              scrollWheelZoom={true}
              style={{ height: "70vh", width: "100%" }}
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              />
              {points.map((entry, i) => (
                <Marker
                  key={i}
                  position={[entry.lat, entry.lng]}
                  icon={dotIcon(entry.kind)}
                >
                  <Popup>
                    <strong>{t(entry.name, language)}</strong>
                    <br />
                    {t(KIND_LABELS[entry.kind], language) || entry.kind}
                    {entry.note ? (
                      <>
                        <br />
                        {t(entry.note, language)}
                      </>
                    ) : null}
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
          </div>
          <Legend language={language} />
        </>
      ) : null}
    </div>
  );
}
