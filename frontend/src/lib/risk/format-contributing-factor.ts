import type { SupportedLocale } from "@/lib/i18n/locale";
import type { RiskContributingFactor } from "@/lib/api/risk-history";

/** Localized contributing-factor line for risk history cards (API message is fallback). */
export function formatContributingFactorMessage(
  factor: RiskContributingFactor,
  locale: SupportedLocale,
): string {
  if (locale === "tr") {
    const tr = factor.message_tr?.trim();
    if (tr) {
      return tr;
    }
  }
  if (locale === "en") {
    const en = factor.message_en?.trim();
    if (en) {
      return en;
    }
  }
  return factor.message;
}
