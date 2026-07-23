import { Landmark, Sparkles } from "lucide-react";
import { useLang } from "../AppShell.jsx";
import { t } from "../../lib/i18n.js";

const TAGLINE = {
  mr: "तुमच्या यात्रेला मार्गदर्शन — पावलोपावली",
  hi: "आपकी यात्रा में मार्गदर्शन — कदम-कदम पर",
  en: "Guiding your yatra, every step",
};

// Big centered avatar + "AI" chip + tagline. Matches the Pravasi Setu
// Assistant empty state — yellow ring around the avatar, small blue AI pill
// with a sparkle overlapping the top-right, bold tagline below.
export default function EmptyState() {
  const { language } = useLang();
  return (
    <div className="flex flex-col items-center pt-14 sm:pt-24 pb-8">
      <div className="relative">
        <div className="w-32 h-32 rounded-full bg-ai-ring-soft border-[6px] border-ai-ring flex items-center justify-center shadow-card">
          <div className="w-20 h-20 rounded-full bg-white flex items-center justify-center">
            <Landmark size={38} className="text-primary" strokeWidth={2.2} />
          </div>
        </div>
        <span className="absolute -top-1 right-0 inline-flex items-center gap-1 bg-primary text-white text-[11px] font-extrabold px-2 py-0.5 rounded-full shadow-card">
          <Sparkles size={11} /> AI
        </span>
      </div>
      <div className="mt-5 text-[16px] font-bold text-ink text-center max-w-md px-6">
        {t(TAGLINE, language)}
      </div>
    </div>
  );
}
