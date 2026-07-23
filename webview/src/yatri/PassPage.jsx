import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";

// STUB — real QR yatra pass (reads ?id=, apiGet('/api/pass/'+id), renders
// pass card + QR code) lands in Task 4.
export default function PassPage() {
  const { language } = useLang();
  return (
    <div>
      <h1>{tr(strings, "pass", language)}</h1>
      <p>coming in Plan 3</p>
    </div>
  );
}
