"use client";

import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { DEFAULT_LOCALE, type SupportedLocale } from "@/lib/i18n/locale";
import { getLocaleDefinition } from "@/lib/i18n/registry";
import { readStoredLocale, writeStoredLocale } from "@/lib/i18n/storage";
import type { CommonContent } from "@/lib/i18n/types";

type LocaleContextValue = {
  locale: SupportedLocale;
  content: CommonContent;
  setLocale: (locale: SupportedLocale) => void;
  isReady: boolean;
};

export const LocaleContext = createContext<LocaleContextValue | null>(null);

type LocaleProviderProps = {
  children: ReactNode;
};

export function LocaleProvider({ children }: LocaleProviderProps) {
  const [locale, setLocaleState] = useState<SupportedLocale>(DEFAULT_LOCALE);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const stored = readStoredLocale();

    if (stored) {
      setLocaleState(stored);
    }

    setIsReady(true);
  }, []);

  useEffect(() => {
    const definition = getLocaleDefinition(locale);
    document.documentElement.lang = locale;
    document.documentElement.dir = definition.direction;
  }, [locale]);

  const setLocale = useCallback((nextLocale: SupportedLocale) => {
    setLocaleState(nextLocale);
    writeStoredLocale(nextLocale);
  }, []);

  const content = useMemo(
    () => getLocaleDefinition(locale).messages,
    [locale],
  );

  const value = useMemo(
    () => ({
      locale,
      content,
      setLocale,
      isReady,
    }),
    [content, isReady, locale, setLocale],
  );

  return (
    <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
  );
}
