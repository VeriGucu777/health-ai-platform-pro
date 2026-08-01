import { DEFAULT_LOCALE, isSupportedLocale, type SupportedLocale } from "@/lib/i18n/locale";

export const LOCALE_STORAGE_KEY = "hap-locale";

export function readStoredLocale(): SupportedLocale | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY);

    if (stored && isSupportedLocale(stored)) {
      return stored;
    }
  } catch {
    return null;
  }

  return null;
}

export function writeStoredLocale(locale: SupportedLocale): void {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(LOCALE_STORAGE_KEY, locale);
  } catch {
    // Ignore storage failures and keep in-memory locale only.
  }
}

export function resolveLocale(candidate: string | null | undefined): SupportedLocale {
  if (candidate && isSupportedLocale(candidate)) {
    return candidate;
  }

  return DEFAULT_LOCALE;
}
