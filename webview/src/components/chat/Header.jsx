import { useState } from "react";
import { Landmark, Menu, Phone, ChevronDown, Check } from "lucide-react";
import { useLang } from "../AppShell.jsx";
import { t } from "../../lib/i18n.js";
import { YATRA_NAMES } from "../../data/yatraNames.js";

const YATRAS = ["pandharpur", "kumbh"];
const SWITCH_HINT = { mr: "यात्रा बदला", hi: "यात्रा बदलें", en: "Switch yatra" };

// Sticky top header — round avatar + title, and a tappable YATRA SWITCHER as
// the subtitle (this is a multi-yatra product, so the active yatra is an
// explicit, visible, changeable choice — not a silent default). Plus a phone
// (voice) button and the hamburger that opens the ThreadsDrawer.
export default function Header({ yatra, onYatraChange, onMenu, onCall }) {
  const { language } = useLang();
  const [open, setOpen] = useState(false);

  return (
    <header className="h-14 px-3 sm:px-4 flex items-center gap-2 border-b border-bdr bg-surface flex-shrink-0 sticky top-0 z-30">
      <div className="w-9 h-9 rounded-full bg-primary-100 text-primary flex items-center justify-center flex-shrink-0">
        <Landmark size={17} />
      </div>
      <div className="flex-1 min-w-0 leading-tight">
        <div className="text-[14.5px] font-extrabold text-ink truncate">Maharashtra Yatra Sahayak</div>
        <div className="relative">
          <button
            onClick={() => setOpen((v) => !v)}
            className="flex items-center gap-1 text-[11px] text-primary font-bold hover:underline"
            title={t(SWITCH_HINT, language)}
          >
            <span className="truncate max-w-[240px]">{t(YATRA_NAMES[yatra], language) || yatra}</span>
            <ChevronDown size={12} className={`transition ${open ? "rotate-180" : ""}`} />
          </button>
          {open ? (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
              <div className="absolute left-0 top-6 z-50 w-60 bg-surface border border-bdr rounded-xl shadow-drawer py-1 animate-fade-in">
                <div className="px-3 py-1.5 text-[10.5px] font-bold uppercase tracking-wide text-muted">
                  {t(SWITCH_HINT, language)}
                </div>
                {YATRAS.map((y) => (
                  <button
                    key={y}
                    onClick={() => { onYatraChange?.(y); setOpen(false); }}
                    className={`w-full flex items-center gap-2 px-3 py-2 text-left text-[13.5px] hover:bg-surface-2 ${
                      y === yatra ? "text-primary font-bold" : "text-ink"
                    }`}
                  >
                    <span className="flex-1 truncate">{t(YATRA_NAMES[y], language)}</span>
                    {y === yatra ? <Check size={15} className="text-primary flex-shrink-0" /> : null}
                  </button>
                ))}
              </div>
            </>
          ) : null}
        </div>
      </div>
      {onCall ? (
        <button
          onClick={onCall}
          className="w-10 h-10 rounded-full hover:bg-surface-2 flex items-center justify-center text-primary"
          aria-label="Voice call"
          title="Voice call"
        >
          <Phone size={18} />
        </button>
      ) : null}
      <button
        onClick={onMenu}
        className="w-10 h-10 rounded-full hover:bg-surface-2 flex items-center justify-center text-muted"
        aria-label="Open menu"
      >
        <Menu size={18} />
      </button>
    </header>
  );
}
