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
  /** Locale used for API/report requests; matches visible UI language after hydration. */
  effectiveLocale: SupportedLocale;
  content: CommonContent;
  setLocale: (locale: SupportedLocale) => void;
  isReady: boolean;
  formatDate: (value: string) => string;
  formatDateTime: (value: string) => string;
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
    if (!isReady) {
      return;
    }

    const definition = getLocaleDefinition(locale);
    document.documentElement.lang = locale;
    document.documentElement.dir = definition.direction;
  }, [isReady, locale]);

  const setLocale = useCallback((nextLocale: SupportedLocale) => {
    setLocaleState(nextLocale);
    writeStoredLocale(nextLocale);
  }, []);

  /** Keep SSR and first client paint on DEFAULT_LOCALE to avoid hydration mismatches. */
  const contentLocale = isReady ? locale : DEFAULT_LOCALE;

  const content = useMemo(
    () => getLocaleDefinition(contentLocale).messages,
    [contentLocale],
  );

  const formatDate = useCallback(
    (value: string) => {
      try {
        return new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(value));
      } catch {
        return value;
      }
    },
    [locale],
  );

  const formatDateTime = useCallback(
    (value: string) => {
      try {
        return new Intl.DateTimeFormat(locale, {
          dateStyle: "medium",
          timeStyle: "short",
        }).format(new Date(value));
      } catch {
        return value;
      }
    },
    [locale],
  );

  const value = useMemo(
    () => ({
      locale,
      effectiveLocale: contentLocale,
      content,
      setLocale,
      isReady,
      formatDate,
      formatDateTime,
    }),
    [content, contentLocale, formatDate, formatDateTime, isReady, locale, setLocale],
  );

  return (
    <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
  );
}
