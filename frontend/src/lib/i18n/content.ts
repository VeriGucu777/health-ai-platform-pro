import {
  DEFAULT_LOCALE,
  getLocaleDefinition,
  getRegisteredLocales,
} from "@/lib/i18n/registry";
import type { SupportedLocale } from "@/lib/i18n/locale";
import type { CommonContent } from "@/lib/i18n/types";

/** Resolves localized messages for a locale, falling back to English. */
export function getCommonContent(locale: SupportedLocale = DEFAULT_LOCALE): CommonContent {
  return getLocaleDefinition(locale).messages;
}

export { DEFAULT_LOCALE, getRegisteredLocales };
