import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";

// STUB — real Leaflet/OSM route map (reads ?yatra=, apiGet('/api/yatra/'+
// yatra+'/routes'), markers + popups) lands in Task 5.
export default function MapPage() {
  const { language } = useLang();
  return (
    <div>
      <h1>{tr(strings, "map", language)}</h1>
      <p>coming in Plan 3</p>
    </div>
  );
}
