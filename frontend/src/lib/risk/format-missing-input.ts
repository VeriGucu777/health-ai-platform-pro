import type { SupportedLocale } from "@/lib/i18n/locale";
import type { RiskMissingInput } from "@/lib/api/risk-history";

export type RiskMissingInputI18n = {
  missingInputLabels: Record<string, string>;
  missingInputReasons: Record<string, string>;
};

/** Localized missing-input line for risk history cards (API reason unchanged on wire). */
export function formatRiskMissingInputLine(
  entry: RiskMissingInput,
  _locale: SupportedLocale,
  i18n: RiskMissingInputI18n,
): string {
  const key = entry.input.trim();
  const label = i18n.missingInputLabels[key];
  const localizedReason = i18n.missingInputReasons[key];

  if (label && localizedReason) {
    return `${label}: ${localizedReason}`;
  }

  return entry.reason;
}
