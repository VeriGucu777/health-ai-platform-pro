/** Default locale for Phase 1A. Turkish support will extend this structure later. */
export const DEFAULT_LOCALE = "en" as const;

export type SupportedLocale = typeof DEFAULT_LOCALE | "tr";

export const SUPPORTED_LOCALES: readonly SupportedLocale[] = [
  DEFAULT_LOCALE,
  "tr",
] as const;

export function isSupportedLocale(value: string): value is SupportedLocale {
  return (SUPPORTED_LOCALES as readonly string[]).includes(value);
}
