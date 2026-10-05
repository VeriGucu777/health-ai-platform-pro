import type { ClinicalSummaryOverviewItem } from "@/lib/api/clinical-summary";
import type { SupportedLocale } from "@/lib/i18n/locale";

type ClinicalSummaryCopy = {
  itemLabels: Record<string, string>;
  trendMessages: Record<string, string>;
};

export function formatClinicalSummaryItemLabel(
  item: ClinicalSummaryOverviewItem,
  copy: ClinicalSummaryCopy,
): string {
  return copy.itemLabels[item.key] ?? item.label;
}

export function formatClinicalSummaryItemMessage(
  item: ClinicalSummaryOverviewItem,
  copy: ClinicalSummaryCopy,
  locale: SupportedLocale,
): string {
  if (item.trend_status && copy.trendMessages[item.trend_status]) {
    const template = copy.trendMessages[item.trend_status];
    return template
      .replace("{count}", String(item.source_count))
      .replace("{context}", localizedContextForKey(item.key, locale));
  }
  return item.message;
}

function localizedContextForKey(key: string, locale: SupportedLocale): string {
  if (key === "fasting_glucose_trend") {
    return locale === "tr" ? "açlık" : "fasting";
  }
  if (key === "post_meal_glucose_trend") {
    return locale === "tr" ? "yemek sonrası" : "post-meal";
  }
  if (key === "blood_pressure_trend") {
    return locale === "tr" ? "sistolik" : "systolic";
  }
  if (key === "heart_rate_trend") {
    return locale === "tr" ? "dinlenme" : "resting";
  }
  return locale === "tr" ? "ölçüm" : "measurement";
}
