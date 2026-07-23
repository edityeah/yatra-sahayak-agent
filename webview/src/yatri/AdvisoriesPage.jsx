import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";

// STUB — real severity-badged advisories feed lands in Task 6.
export default function AdvisoriesPage() {
  const { language } = useLang();
  return (
    <div>
      <h1>{tr(strings, "advisories", language)}</h1>
      <p>coming in Plan 3</p>
    </div>
  );
}
