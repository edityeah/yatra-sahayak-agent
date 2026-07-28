import { useCallback, useState } from "react";
import { MapPin, LocateFixed, Thermometer, CloudRain, ArrowRight, Loader2 } from "lucide-react";
import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";
import PageShell from "../components/PageShell.jsx";
import { t } from "../lib/i18n.js";

// Destination per yatra (where the route ends).
const DEST = {
  pandharpur: { name: { mr: "पंढरपूर", hi: "पंढरपुर", en: "Pandharpur" }, lat: 17.679, lng: 75.333 },
  kumbh: { name: { mr: "नाशिक (रामकुंड)", hi: "नासिक (रामकुंड)", en: "Nashik (Ramkund)" }, lat: 20.007, lng: 73.792 },
};

// Preset starting cities to SIMULATE location sharing (also real geolocation).
const CITIES = [
  { mr: "मुंबई", hi: "मुंबई", en: "Mumbai", lat: 19.076, lng: 72.877 },
  { mr: "पुणे", hi: "पुणे", en: "Pune", lat: 18.516, lng: 73.856 },
  { mr: "नाशिक", hi: "नासिक", en: "Nashik", lat: 19.997, lng: 73.79 },
  { mr: "कोल्हापूर", hi: "कोल्हापुर", en: "Kolhapur", lat: 16.705, lng: 74.243 },
  { mr: "सोलापूर", hi: "सोलापुर", en: "Solapur", lat: 17.659, lng: 75.906 },
  { mr: "छत्रपती संभाजीनगर", hi: "छत्रपति संभाजीनगर", en: "Chh. Sambhajinagar", lat: 19.876, lng: 75.343 },
  { mr: "नागपूर", hi: "नागपुर", en: "Nagpur", lat: 21.146, lng: 79.088 },
];

// WMO weather code → emoji + trilingual label + rain flag.
function wx(code) {
  const c = code ?? 3;
  if (c === 0) return { e: "☀️", rain: false, l: { mr: "स्वच्छ", hi: "साफ़", en: "Clear" } };
  if (c <= 3) return { e: "⛅", rain: false, l: { mr: "ढगाळ", hi: "बादल", en: "Cloudy" } };
  if (c <= 48) return { e: "🌫️", rain: false, l: { mr: "धुके", hi: "कोहरा", en: "Fog" } };
  if (c <= 67) return { e: "🌧️", rain: true, l: { mr: "पाऊस", hi: "बारिश", en: "Rain" } };
  if (c <= 77) return { e: "❄️", rain: false, l: { mr: "बर्फ", hi: "बर्फ़", en: "Snow" } };
  if (c <= 82) return { e: "🌧️", rain: true, l: { mr: "सरी", hi: "बौछारें", en: "Showers" } };
  return { e: "⛈️", rain: true, l: { mr: "वादळी पाऊस", hi: "आंधी-तूफ़ान", en: "Thunderstorm" } };
}

function haversineKm(a, b) {
  const R = 6371, r = (d) => (d * Math.PI) / 180;
  const dLat = r(b.lat - a.lat), dLng = r(b.lng - a.lng);
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(r(a.lat)) * Math.cos(r(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(s));
}

async function fetchWx(lat, lng) {
  const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lng}&current=temperature_2m,weather_code,precipitation`;
  const r = await fetch(url);
  if (!r.ok) throw new Error(String(r.status));
  const d = await r.json();
  return { temp: d.current?.temperature_2m, code: d.current?.weather_code, precip: d.current?.precipitation };
}

const L = {
  intro: { mr: "तुमच्या ठिकाणापासून {dest} पर्यंतच्या मार्गावरील खरे हवामान पाहा.",
           hi: "अपने स्थान से {dest} तक के मार्ग का असली मौसम देखें।",
           en: "See real weather along your route from where you are to {dest}." },
  useLoc: { mr: "माझे ठिकाण वापरा", hi: "मेरा स्थान इस्तेमाल करें", en: "Use my location" },
  orPick: { mr: "किंवा सुरुवातीचे शहर निवडा", hi: "या शुरुआती शहर चुनें", en: "or pick a starting city" },
  yourLoc: { mr: "तुमचे ठिकाण", hi: "आपका स्थान", en: "Your location" },
  enroute: { mr: "मार्गावर", hi: "मार्ग पर", en: "En route" },
  totalKm: { mr: "एकूण अंतर", hi: "कुल दूरी", en: "Total distance" },
  km: { mr: "किमी", hi: "किमी", en: "km" },
  rainWarn: { mr: "⚠️ मार्गावर पाऊस अपेक्षित — रेनकोट/छत्री सोबत ठेवा.",
              hi: "⚠️ मार्ग पर बारिश संभव — रेनकोट/छाता साथ रखें।",
              en: "⚠️ Rain likely on the route — carry a raincoat/umbrella." },
  denied: { mr: "स्थान मिळाले नाही. खालून शहर निवडा.", hi: "स्थान नहीं मिला। नीचे से शहर चुनें।", en: "Couldn't get location. Pick a city below." },
  source: { mr: "स्रोत: थेट हवामान (Open-Meteo)", hi: "स्रोत: लाइव मौसम (Open-Meteo)", en: "Source: live weather (Open-Meteo)" },
};

export default function WeatherPage() {
  const { language, yatra } = useLang();
  const dest = DEST[yatra] || DEST.pandharpur;
  const [points, setPoints] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);
  const [startLabel, setStartLabel] = useState("");

  // Build 4 points from origin → destination and fetch live weather at each.
  const planRoute = useCallback(async (origin, originLabel) => {
    setLoading(true); setErr(null); setStartLabel(originLabel); setPoints(null);
    try {
      const N = 4;
      const stops = Array.from({ length: N }, (_, i) => {
        const f = i / (N - 1);
        return {
          lat: origin.lat + f * (dest.lat - origin.lat),
          lng: origin.lng + f * (dest.lng - origin.lng),
          label: i === 0 ? t(L.yourLoc, language) : i === N - 1 ? t(dest.name, language) : t(L.enroute, language),
          fromKm: Math.round(haversineKm(origin, {
            lat: origin.lat + f * (dest.lat - origin.lat), lng: origin.lng + f * (dest.lng - origin.lng),
          })),
        };
      });
      const wxs = await Promise.all(stops.map((s) => fetchWx(s.lat, s.lng)));
      setPoints(stops.map((s, i) => ({ ...s, ...wxs[i] })));
    } catch (e) {
      setErr(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }, [dest, language]);

  const useMyLocation = () => {
    if (!navigator.geolocation) { setErr(t(L.denied, language)); return; }
    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => planRoute({ lat: pos.coords.latitude, lng: pos.coords.longitude }, t(L.yourLoc, language)),
      () => { setLoading(false); setErr(t(L.denied, language)); },
      { timeout: 8000 }
    );
  };

  const totalKm = points ? points[points.length - 1].fromKm : 0;
  const anyRain = points ? points.some((p) => wx(p.code).rain) : false;

  return (
    <PageShell title={tr(strings, "routeWeather", language)}>
      <div className="rounded-2xl border border-bdr bg-surface shadow-card p-4 space-y-3">
        <p className="text-[13.5px] text-ink leading-relaxed">
          {t(L.intro, language).replace("{dest}", t(dest.name, language))}
        </p>
        <button onClick={useMyLocation} disabled={loading}
          className="w-full h-11 rounded-full bg-primary text-white font-extrabold flex items-center justify-center gap-2 disabled:opacity-60 hover:bg-primary-700 transition">
          {loading ? <Loader2 size={17} className="animate-spin" /> : <LocateFixed size={17} />} {t(L.useLoc, language)}
        </button>
        <div className="text-[12px] text-muted text-center">{t(L.orPick, language)}</div>
        <div className="flex flex-wrap gap-2">
          {CITIES.map((c, i) => (
            <button key={i} onClick={() => planRoute(c, t(c, language))} disabled={loading}
              className="inline-flex items-center gap-1 rounded-full border border-bdr bg-surface-2 text-ink text-[12.5px] font-bold px-3 h-9 hover:border-primary transition disabled:opacity-60">
              <MapPin size={13} className="text-primary" /> {t(c, language)}
            </button>
          ))}
        </div>
        {err ? <div className="text-[12.5px] text-red-600">{err}</div> : null}
      </div>

      {points ? (
        <div className="mt-3 space-y-3">
          <div className="text-[13px] text-muted text-center">
            {startLabel} <ArrowRight size={13} className="inline" /> {t(dest.name, language)}
            {" · "}{t(L.totalKm, language)}: <span className="font-bold text-ink">{totalKm} {t(L.km, language)}</span>
          </div>
          {anyRain ? (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 text-amber-800 text-[13px] px-4 py-3 font-semibold">
              {t(L.rainWarn, language)}
            </div>
          ) : null}
          <div className="space-y-2.5">
            {points.map((p, i) => {
              const w = wx(p.code);
              return (
                <div key={i} className="rounded-2xl border border-bdr bg-surface shadow-card p-4 flex items-center gap-3">
                  <div className="text-[30px] leading-none flex-shrink-0">{w.e}</div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[14.5px] font-extrabold text-ink">{p.label}</div>
                    <div className="text-[12px] text-muted">{p.fromKm} {t(L.km, language)} · {t(w.l, language)}</div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className="text-[20px] font-extrabold text-ink flex items-center gap-1">
                      <Thermometer size={16} className="text-red-500" />{p.temp != null ? Math.round(p.temp) : "—"}°C
                    </div>
                    {w.rain ? <div className="text-[11px] text-primary flex items-center justify-end gap-0.5"><CloudRain size={12} /> {t(w.l, language)}</div> : null}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="text-[11.5px] text-muted text-center">{t(L.source, language)}</div>
        </div>
      ) : null}
    </PageShell>
  );
}
