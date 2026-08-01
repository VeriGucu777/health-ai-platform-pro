/** Default locale for the application. English is the primary language. */
export const DEFAULT_LOCALE = "en" as const;

/**
 * Supported locale codes. To add a language later (e.g. "de", "ar"):
 * 1. Add the code here
 * 2. Create src/content/<code>/common.ts
 * 3. Register it in src/lib/i18n/registry.ts
 */
export type SupportedLocale = typeof DEFAULT_LOCALE | "tr";

export const SUPPORTED_LOCALES: readonly SupportedLocale[] = [
  DEFAULT_LOCALE,
  "tr",
] as const;

export function isSupportedLocale(value: string): value is SupportedLocale {
  return (SUPPORTED_LOCALES as readonly string[]).includes(value);
}
