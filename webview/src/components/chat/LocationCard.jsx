import { MapContainer, TileLayer, Marker } from "react-leaflet";
import L from "leaflet";
import { useLang } from "../AppShell.jsx";
import { t } from "../../lib/i18n.js";

const LOCATION = { mr: "स्थान", hi: "स्थान", en: "Location" };

// A red map pin (divIcon avoids Leaflet's broken default-marker asset paths).
const PIN = L.divIcon({
  className: "",
  html:
    '<div style="font-size:26px;line-height:1;transform:translate(-50%,-90%)">📍</div>',
  iconSize: [0, 0],
});

// A shared-location bubble that mimics the native SwiftChat/Google-Maps
// location card: a small non-interactive map centered on the pin, with a
// "Location" caption. Rendered for user messages of kind "location".
export default function LocationCard({ lat, lng }) {
  const { language } = useLang();
  return (
    <div className="w-[248px] rounded-2xl overflow-hidden bg-primary shadow-card">
      <div className="h-[150px] w-full pointer-events-none">
        <MapContainer
          center={[lat, lng]}
          zoom={14}
          zoomControl={false}
          attributionControl={false}
          dragging={false}
          doubleClickZoom={false}
          scrollWheelZoom={false}
          touchZoom={false}
          keyboard={false}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <Marker position={[lat, lng]} icon={PIN} />
        </MapContainer>
      </div>
      <div className="px-3 py-2 text-white text-[13.5px] font-bold">{t(LOCATION, language)}</div>
    </div>
  );
}
