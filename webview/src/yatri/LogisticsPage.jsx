import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";

// STUB — real logistics rate table + overcharge-report note lands in Task 6.
export default function LogisticsPage() {
  const { language } = useLang();
  return (
    <div>
      <h1>{tr(strings, "logistics", language)}</h1>
      <p>coming in Plan 3</p>
    </div>
  );
}
