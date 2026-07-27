import { Landmark, Menu, Phone } from "lucide-react";

// Sticky top header — round primary-100 avatar with a Landmark glyph, bold
// title, a subtitle (the active yatra, once selected — the yatra is chosen in
// the chat itself, not a header control), a phone (voice) button, and a
// hamburger that opens the ThreadsDrawer.
export default function Header({ subtitle, onMenu, onCall }) {
  return (
    <header className="h-14 px-3 sm:px-4 flex items-center gap-2 border-b border-bdr bg-surface flex-shrink-0 sticky top-0 z-30">
      <div className="w-9 h-9 rounded-full bg-primary-100 text-primary flex items-center justify-center flex-shrink-0">
        <Landmark size={17} />
      </div>
      <div className="flex-1 min-w-0 leading-tight">
        <div className="text-[14.5px] font-extrabold text-ink truncate">Maharashtra Yatra Sahayak</div>
        {subtitle ? <div className="text-[11px] text-muted truncate">{subtitle}</div> : null}
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
