import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { de } from "./de";
import { en } from "./en";

export type Language = "en" | "de";

const DICTIONARIES: Record<Language, Record<string, string>> = { en, de };

const STORAGE_KEY = "af_language_v1";

type Ctx = {
  lang: Language;
  setLang: (l: Language) => void;
  t: (key: string) => string;
};

const LanguageContext = createContext<Ctx | null>(null);

function detect(): Language {
  if (typeof window === "undefined") return "en";
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === "de" || saved === "en") return saved;
  const browser = (navigator.language || "").toLowerCase();
  return browser.startsWith("de") ? "de" : "en";
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Language>(detect);

  useEffect(() => {
    document.documentElement.lang = lang;
    localStorage.setItem(STORAGE_KEY, lang);
  }, [lang]);

  const setLang = useCallback((l: Language) => setLangState(l), []);

  const t = useCallback(
    (key: string) => {
      const dict = DICTIONARIES[lang];
      const value = dict[key];
      if (value !== undefined) return value;
      // Dev-friendly fallback to English, surface missing keys in console.
      const fallback = DICTIONARIES.en[key];
      if (fallback !== undefined) {
        if (import.meta.env.DEV) console.warn(`i18n: missing key ${key} in ${lang}`);
        return fallback;
      }
      if (import.meta.env.DEV) console.warn(`i18n: unknown key ${key}`);
      return key;
    },
    [lang],
  );

  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useT() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useT must be used within LanguageProvider");
  return ctx;
}
