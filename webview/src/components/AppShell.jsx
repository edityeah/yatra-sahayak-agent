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

export function LangProvider({ children }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const ctx = useMemo(() => getContext(), []);
  const [language, setLanguageState] = useState(searchParams.get("lang") || ctx.language);

  const setLanguage = useCallback(
    (lang) => {
      setLanguageState(lang);
      const next = new URLSearchParams(searchParams);
      next.set("lang", lang);
      setSearchParams(next, { replace: true });
    },
    [searchParams, setSearchParams]
  );

  const value = useMemo(
    () => ({ language, setLanguage, yatra: ctx.yatra, user_id: ctx.user_id }),
    [language, setLanguage, ctx.yatra, ctx.user_id]
  );

  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}
