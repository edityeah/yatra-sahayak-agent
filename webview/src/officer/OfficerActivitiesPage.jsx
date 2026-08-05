import { useNavigate } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { useLang } from "../components/AppShell.jsx";
import { t } from "../lib/i18n.js";
import OfficerGate from "./OfficerGate.jsx";
import { OFFICER_ACTIVITIES } from "./officerActivities.js";

const TINTS = ["bg-rose-100", "bg-sky-100", "bg-amber-100", "bg-emerald-100", "bg-violet-100"];

// Full-page grid of officer modules — opened from the [+] menu's "Quick
// Activities" row. Each card routes to its module.
function Inner() {
  const { language } = useLang();
  const navigate = useNavigate();
  return (
    <main className="flex-1 max-w-3xl w-full mx-auto px-4 py-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {OFFICER_ACTIVITIES.map((a, i) => (
          <button
            key={a.id}
            onClick={() => navigate(a.action.href)}
            className={`relative text-left rounded-2xl p-4 min-h-[112px] flex flex-col justify-between ${TINTS[i % TINTS.length]} hover:brightness-95 transition shadow-card`}
          >
            <div className="absolute top-3 right-3 w-7 h-7 rounded-full bg-white/70 flex items-center justify-center text-ink/60">
              <ChevronRight size={15} />
            </div>
            <div className="text-[26px]">{a.icon}</div>
            <div>
              <div className="text-[14.5px] font-extrabold text-ink pr-8">{t(a.label, language)}</div>
              <div className="text-[12px] text-ink/70 mt-0.5">{t(a.tagline, language)}</div>
            </div>
          </button>
        ))}
      </div>
    </main>
  );
}

export default function OfficerActivitiesPage() {
  return <OfficerGate title="Modules" subtitle="Control-room activities" back><Inner /></OfficerGate>;
}
