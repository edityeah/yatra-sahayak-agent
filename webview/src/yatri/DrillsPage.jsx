import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";

// STUB — real expandable drill module cards land in Task 6.
export default function DrillsPage() {
  const { language } = useLang();
  return (
    <div>
      <h1>{tr(strings, "drills", language)}</h1>
      <p>coming in Plan 3</p>
    </div>
  );
}
