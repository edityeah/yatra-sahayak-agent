import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Landmark, Menu } from "lucide-react";
import { useLang } from "./AppShell.jsx";
import { getContext } from "../lib/swiftchat.js";
import { t } from "../lib/i18n.js";
import { YATRA_NAMES } from "../data/yatraNames.js";
import MenuDrawer from "./chat/MenuDrawer.jsx";

// Shared shell for the inner (non-chat) pages — mirrors the chat Header
// (round primary-100 Landmark avatar, bold title, yatra subtitle,
// hamburger -> MenuDrawer) but adds a back arrow to the chat landing so the
// whole app reads as one product with the new Pravasi-Setu look.
export default function PageShell({ title, children }) {
  const { language } = useLang();
  const navigate = useNavigate();
  const ctx = getContext();
  const [menuOpen, setMenuOpen] = useState(false);

  const subtitle = t(YATRA_NAMES[ctx.yatra], language) || ctx.yatra;

  return (
    <div className="min-h-screen flex flex-col bg-surface text-ink font-sans">
      <header className="h-14 px-2 sm:px-4 flex items-center gap-1 sm:gap-2 border-b border-bdr bg-surface flex-shrink-0 sticky top-0 z-30">
        <button
          onClick={() => navigate("/")}
          className="w-10 h-10 rounded-full hover:bg-surface-2 flex items-center justify-center text-muted flex-shrink-0"
          aria-label="Back"
        >
          <ArrowLeft size={18} />
        </button>
        <div className="w-9 h-9 rounded-full bg-primary-100 text-primary flex items-center justify-center flex-shrink-0">
          <Landmark size={17} />
        </div>
        <div className="flex-1 min-w-0 leading-tight">
          <div className="text-[14.5px] font-extrabold text-ink truncate">{title}</div>
          {subtitle ? <div className="text-[11px] text-muted truncate">{subtitle}</div> : null}
        </div>
        <button
          onClick={() => setMenuOpen(true)}
          className="w-10 h-10 rounded-full hover:bg-surface-2 flex items-center justify-center text-muted flex-shrink-0"
          aria-label="Open menu"
        >
          <Menu size={18} />
        </button>
      </header>

      <main className="flex-1 min-w-0 max-w-3xl w-full mx-auto px-4 py-4">{children}</main>

      <MenuDrawer
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        onNewChat={() => navigate("/")}
      />
    </div>
  );
}
