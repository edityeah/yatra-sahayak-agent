import { createContext, useContext, useMemo, useState, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { getContext } from "../lib/swiftchat.js";

// Language context shared by every page (chat + inner yatri/voice pages).
// The old nav-bar AppShell component that used to live here has been
// replaced by the new Pravasi-Setu-style PageShell/Header — see
// src/components/PageShell.jsx and src/components/chat/Header.jsx.
export const LangContext = createContext({ language: "mr", setLanguage: () => {} });

export function useLang() {
  return useContext(LangContext);
}

const LS_KEY = "ysahayak.lang";
const LS_YATRA = "ysahayak.yatra";
const YATRAS = ["pandharpur", "kumbh"];

export function LangProvider({ children }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const ctx = useMemo(() => getContext(), []);
  // Priority: explicit ?lang= → last chosen (localStorage) → context default.
  // localStorage keeps the language consistent across page loads (e.g. opening
  // the wallet link) instead of snapping back to the Marathi default.
  const [language, setLanguageState] = useState(() => {
    const fromUrl = searchParams.get("lang");
    if (fromUrl && ["mr", "hi", "en"].includes(fromUrl)) return fromUrl;
    try {
      const saved = localStorage.getItem(LS_KEY);
      if (saved && ["mr", "hi", "en"].includes(saved)) return saved;
    } catch (e) { /* ignore */ }
    return ctx.language;
  });

  const setLanguage = useCallback(
    (lang) => {
      setLanguageState(lang);
      try { localStorage.setItem(LS_KEY, lang); } catch (e) { /* ignore */ }
      const next = new URLSearchParams(searchParams);
      next.set("lang", lang);
      setSearchParams(next, { replace: true });
    },
    [searchParams, setSearchParams]
  );

  // Active yatra — user-controlled + persisted (a header switcher sets it),
  // so it's an explicit choice, not a silent Pandharpur default.
  const [yatra, setYatraState] = useState(() => {
    const fromUrl = searchParams.get("yatra");
    if (YATRAS.includes(fromUrl)) return fromUrl;
    try {
      const saved = localStorage.getItem(LS_YATRA);
      if (YATRAS.includes(saved)) return saved;
    } catch (e) { /* ignore */ }
    return ctx.yatra;
  });

  const setYatra = useCallback(
    (y) => {
      if (!YATRAS.includes(y)) return;
      setYatraState(y);
      try { localStorage.setItem(LS_YATRA, y); } catch (e) { /* ignore */ }
      const next = new URLSearchParams(searchParams);
      next.set("yatra", y);
      setSearchParams(next, { replace: true });
    },
    [searchParams, setSearchParams]
  );

  const value = useMemo(
    () => ({ language, setLanguage, yatra, setYatra, user_id: ctx.user_id }),
    [language, setLanguage, yatra, setYatra, ctx.user_id]
  );

  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}
