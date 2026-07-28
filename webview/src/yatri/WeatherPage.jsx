import { useCallback, useEffect, useState } from "react";
import { MapPin, LocateFixed, Thermometer, CloudRain, ArrowRight, Loader2 } from "lucide-react";
import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";
import PageShell from "../components/PageShell.jsx";
import { apiPost } from "../lib/api.js";
import { t } from "../lib/i18n.js";

const DEST_NAME = {
  pandharpur: { mr: "पंढरपूर", hi: "पंढरपुर", en: "Pandharpur" },
  kumbh: { mr: "रामकुंड, नाशिक", hi: "रामकुंड, नासिक", en: "Ramkund, Nashik" },
};
// Preset origins to simulate location sharing (also real GPS).
const CITIES = [
  { name: { mr: "मुंबई", hi: "मुंबई", en: "Mumbai" }, lat: 19.076, lng: 72.877 },
  { name: { mr: "पुणे", hi: "पुणे", en: "Pune" }, lat: 18.516, lng: 73.856 },
  { name: { mr: "नाशिक", hi: "नासिक", en: "Nashik" }, lat: 19.997, lng: 73.79 },
  { name: { mr: "कोल्हापूर", hi: "कोल्हापुर", en: "Kolhapur" }, lat: 16.705, lng: 74.243 },
  { name: { mr: "सोलापूर", hi: "सोलापुर", en: "Solapur" }, lat: 17.659, lng: 75.906 },
  { name: { mr: "छत्रपती संभाजीनगर", hi: "छत्रपति संभाजीनगर", en: "Chh. Sambhajinagar" }, lat: 19.876, lng: 75.343 },
];
const YOU = { mr: "तुमचे ठिकाण", hi: "आपका स्थान", en: "Your location" };

// WMO weather code → emoji + trilingual label + rain flag.
function wx(code) {
  const c = code ?? 3;
  if (c === 0 || c === 1) return { e: "☀️", rain: false, l: { mr: "स्वच्छ", hi: "साफ़", en: "Clear" } };
  if (c <= 3 || c === 45 || c === 48) return { e: "⛅", rain: false, l: { mr: "ढगाळ", hi: "बादल", en: "Cloudy" } };
  if (c >= 95) return { e: "⛈️", rain: true, l: { mr: "वादळी पाऊस", hi: "आंधी-तूफ़ान", en: "Thunderstorm" } };
  if ((c >= 51 && c <= 67) || (c >= 80 && c <= 86)) return { e: "🌧️", rain: true, l: { mr: "पाऊस", hi: "बारिश", en: "Rain" } };
  return { e: "🌦️", rain: false, l: { mr: "मिश्र", hi: "मिश्रित", en: "Mixed" } };
}

const L = {
  intro: { mr: "तुमच्या ठिकाणापासून {dest} पर्यंतच्या थांब्यांवरील खरे हवामान पाहा.",
           hi: "अपने स्थान से {dest} तक के पड़ावों का असली मौसम देखें।",
           en: "See real weather at the halts along your route from where you are to {dest}." },
  useLoc: { mr: "माझे ठिकाण वापरा", hi: "मेरा स्थान इस्तेमाल करें", en: "Use my location" },
  orPick: { mr: "किंवा सुरुवातीचे शहर निवडा", hi: "या शुरुआती शहर चुनें", en: "or pick a starting city" },
  rainWarn: { mr: "⚠️ मार्गावर पाऊस अपेक्षित — रेनकोट/छत्री सोबत ठेवा.",
              hi: "⚠️ मार्ग पर बारिश संभव — रेनकोट/छाता साथ रखें।",
              en: "⚠️ Rain likely on the route — carry a raincoat/umbrella." },
  denied: { mr: "स्थान मिळाले नाही. खालून शहर निवडा.", hi: "स्थान नहीं मिला। नीचे से शहर चुनें।", en: "Couldn't get location. Pick a city below." },
  source: { mr: "स्रोत: थेट हवामान (Open-Meteo)", hi: "स्रोत: लाइव मौसम (Open-Meteo)", en: "Source: live weather (Open-Meteo)" },
  destStop: { mr: "गंतव्य", hi: "गंतव्य", en: "destination" },
};

export default function WeatherPage() {
  const { language, yatra, origin, setOrigin } = useLang();
  const yk = yatra || "pandharpur";
  const [points, setPoints] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  const plan = useCallback(async (o) => {
    setLoading(true); setErr(null); setPoints(null);
    try {
      const res = await apiPost("/api/route-weather", {
        yatra: yk, origin: { lat: o.lat, lng: o.lng }, origin_name: o.name,
      });
      setPoints(res.points || []);
      setOrigin(o);   // remember for next time
    } catch (e) {
      setErr(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }, [yk, setOrigin]);

  // Auto-load if we already know where the pilgrim is.
  useEffect(() => { if (origin && !points) plan(origin); /* eslint-disable-next-line */ }, []);

  const useMyLocation = () => {
    if (!navigator.geolocation) { setErr(t(L.denied, language)); return; }
    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => plan({ lat: pos.coords.latitude, lng: pos.coords.longitude, name: YOU }),
      () => { setLoading(false); setErr(t(L.denied, language)); },
      { timeout: 8000 }
    );
  };

  const anyRain = points ? points.some((p) => p.rain || wx(p.code).rain) : false;

  return (
    <PageShell title={tr(strings, "routeWeather", language)}>
      <div className="rounded-2xl border border-bdr bg-surface shadow-card p-4 space-y-3">
        <p className="text-[13.5px] text-ink leading-relaxed">
          {t(L.intro, language).replace("{dest}", t(DEST_NAME[yk] || DEST_NAME.pandharpur, language))}
        </p>
        <button onClick={useMyLocation} disabled={loading}
          className="w-full h-11 rounded-full bg-primary text-white font-extrabold flex items-center justify-center gap-2 disabled:opacity-60 hover:bg-primary-700 transition">
          {loading ? <Loader2 size={17} className="animate-spin" /> : <LocateFixed size={17} />} {t(L.useLoc, language)}
        </button>
        <div className="text-[12px] text-muted text-center">{t(L.orPick, language)}</div>
        <div className="flex flex-wrap gap-2">
          {CITIES.map((c, i) => (
            <button key={i} onClick={() => plan(c)} disabled={loading}
              className="inline-flex items-center gap-1 rounded-full border border-bdr bg-surface-2 text-ink text-[12.5px] font-bold px-3 h-9 hover:border-primary transition disabled:opacity-60">
              <MapPin size={13} className="text-primary" /> {t(c.name, language)}
            </button>
          ))}
        </div>
        {err ? <div className="text-[12.5px] text-red-600">{err}</div> : null}
      </div>

      {points ? (
        <div className="mt-3 space-y-3">
          <div className="text-[13px] text-muted text-center">
            {t(points[0].name, language)} <ArrowRight size={13} className="inline" /> {t(points[points.length - 1].name, language)}
          </div>
          {anyRain ? (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 text-amber-800 text-[13px] px-4 py-3 font-semibold">
              {t(L.rainWarn, language)}
            </div>
          ) : null}
          <div className="space-y-2.5">
            {points.map((p, i) => {
              const w = wx(p.code);
              const isDest = i === points.length - 1;
              return (
                <div key={i} className="rounded-2xl border border-bdr bg-surface shadow-card p-4 flex items-center gap-3">
                  <div className="text-[30px] leading-none flex-shrink-0">{w.e}</div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[14.5px] font-extrabold text-ink">
                      {p.you ? "📍 " : ""}{t(p.name, language)}
                      {isDest ? <span className="ml-1 text-[11px] font-bold text-primary">· {t(L.destStop, language)}</span> : null}
                    </div>
                    <div className="text-[12px] text-muted">{t(p.summary, language) || t(w.l, language)}</div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className="text-[20px] font-extrabold text-ink flex items-center gap-1">
                      <Thermometer size={16} className="text-red-500" />{p.temp_c != null ? Math.round(p.temp_c) : "—"}°C
                    </div>
                    {p.rain || w.rain ? <div className="text-[11px] text-primary flex items-center justify-end gap-0.5"><CloudRain size={12} /> {t(w.l, language)}</div> : null}
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
