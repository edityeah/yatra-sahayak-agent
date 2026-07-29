import { useLang } from "../AppShell.jsx";
import { t } from "../../lib/i18n.js";

const LOCATION = { mr: "स्थान", hi: "स्थान", en: "Location" };

// Slippy-map math: lat/lng → the OSM tile that contains the point, plus the
// point's fractional position INSIDE that tile (so the pin sits on the exact
// spot). https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames
function tileFor(lat, lng, z) {
  const n = 2 ** z;
  const latRad = (lat * Math.PI) / 180;
  const xF = ((lng + 180) / 360) * n;
  const yF = ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n;
  const xt = Math.floor(xF), yt = Math.floor(yF);
  return {
    url: `https://tile.openstreetmap.org/${z}/${xt}/${yt}.png`,
    leftPct: (xF - xt) * 100,
    topPct: (yF - yt) * 100,
  };
}

// A shared-location bubble that looks like the native SwiftChat / Google-Maps
// location card. Uses a STATIC map tile as a plain <img> with an absolutely
// positioned pin — no Leaflet, so it can never mis-init or break the layout.
export default function LocationCard({ lat, lng }) {
  const { language } = useLang();
  const okay = typeof lat === "number" && typeof lng === "number";
  const tile = okay ? tileFor(lat, lng, 15) : null;

  return (
    <div className="w-[240px] rounded-2xl overflow-hidden bg-primary shadow-card select-none">
      <div className="relative w-full h-[140px] bg-surface-2 overflow-hidden">
        {tile ? (
          <>
            <img src={tile.url} alt="" draggable={false}
              className="absolute inset-0 w-full h-full object-cover" style={{ objectFit: "fill" }} />
            <div className="absolute text-[24px] leading-none"
              style={{ left: `${tile.leftPct}%`, top: `${tile.topPct}%`, transform: "translate(-50%,-90%)" }}>
              📍
            </div>
          </>
        ) : null}
      </div>
      <div className="px-3 py-2 text-white text-[13.5px] font-bold flex items-center gap-1.5">
        <span>📍</span> {t(LOCATION, language)}
      </div>
    </div>
  );
}
