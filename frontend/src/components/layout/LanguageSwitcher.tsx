"use client";

import { LOCALE_LIST } from "@/lib/i18n/registry";
import type { SupportedLocale } from "@/lib/i18n/locale";
import { useLocale } from "@/lib/i18n/use-locale";

export function LanguageSwitcher() {
  const { locale, setLocale, content } = useLocale();

  return (
    <div
      role="group"
      aria-label={content.language.switcherLabel}
      className="inline-flex rounded-lg border border-border bg-white p-1"
    >
      {LOCALE_LIST.map((entry) => {
        const isActive = locale === entry.code;

        return (
          <button
            key={entry.code}
            type="button"
            aria-pressed={isActive}
            aria-label={entry.label}
            onClick={() => setLocale(entry.code as SupportedLocale)}
            className={[
              "min-h-11 min-w-[3.25rem] flex-1 rounded-md px-3 py-2 text-sm font-semibold transition-colors",
              "focus-visible:outline-offset-2",
              isActive
                ? "bg-brand-600 text-white shadow-sm"
                : "text-text-secondary hover:bg-brand-50 hover:text-brand-800",
            ].join(" ")}
          >
            {entry.nativeLabel}
          </button>
        );
      })}
    </div>
  );
}
