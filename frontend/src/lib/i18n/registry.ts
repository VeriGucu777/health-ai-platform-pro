import { commonContent as enMessages } from "@/content/en/common";
import { commonContent as trMessages } from "@/content/tr/common";
import {
  DEFAULT_LOCALE,
  SUPPORTED_LOCALES,
  type SupportedLocale,
} from "@/lib/i18n/locale";
import type { LocaleDefinition } from "@/lib/i18n/types";

/**
 * Central language registry. To add a locale (e.g. German, Arabic):
 * 1. Extend SupportedLocale in locale.ts
 * 2. Add content/<code>/common.ts
 * 3. Register the locale in LOCALE_REGISTRY below
 */
export const LOCALE_REGISTRY: Record<SupportedLocale, LocaleDefinition> = {
  en: {
    code: "en",
    label: "English",
    nativeLabel: "English",
    direction: "ltr",
    messages: enMessages,
  },
  tr: {
    code: "tr",
    label: "Turkish",
    nativeLabel: "Türkçe",
    direction: "ltr",
    messages: trMessages,
  },
};

export const LOCALE_LIST: readonly LocaleDefinition[] = SUPPORTED_LOCALES.map(
  (code) => LOCALE_REGISTRY[code],
);

export function getLocaleDefinition(locale: SupportedLocale): LocaleDefinition {
  return LOCALE_REGISTRY[locale];
}

export function getRegisteredLocales(): readonly SupportedLocale[] {
  return SUPPORTED_LOCALES;
}

export { DEFAULT_LOCALE };
