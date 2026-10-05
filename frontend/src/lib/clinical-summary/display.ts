import type { ClinicalSummaryOverviewItem } from "@/lib/api/clinical-summary";
import type { SupportedLocale } from "@/lib/i18n/locale";

type ClinicalSummaryCopy = {
  itemLabels: Record<string, string>;
  trendMessages: Record<string, string>;
  itemMessages: Record<string, string>;
};

function applyTemplate(template: string, params: Record<string, string>): string {
  return Object.entries(params).reduce(
    (result, [key, value]) => result.replaceAll(`{${key}}`, value),
    template,
  );
}

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
  formatDate?: (value: string) => string,
): string {
  if (item.message_key && copy.itemMessages[item.message_key]) {
    const params = { ...(item.message_params ?? {}) };
    if (item.message_key === "upcoming_follow_up_date" && params.date && formatDate) {
      params.date = formatDate(params.date);
    }
    return applyTemplate(copy.itemMessages[item.message_key], params);
  }

  if (item.trend_status && copy.trendMessages[item.trend_status]) {
    const template = copy.trendMessages[item.trend_status];
    return applyTemplate(template, {
      count: String(item.source_count),
      context: localizedContextForKey(item.key, locale),
    });
  }

  return item.message;
}

function localizedContextForKey(key: string, locale: SupportedLocale): string {
  if (key === "fasting_glucose_trend") {
    return locale === "tr" ? "açlık kan şekeri" : "fasting blood glucose";
  }
  if (key === "post_meal_glucose_trend") {
    return locale === "tr" ? "yemek sonrası kan şekeri" : "post-meal blood glucose";
  }
  if (key === "blood_pressure_trend") {
    return locale === "tr" ? "sistolik tansiyon" : "systolic blood pressure";
  }
  if (key === "heart_rate_trend") {
    return locale === "tr" ? "dinlenme nabzı" : "resting heart rate";
  }
  return locale === "tr" ? "ölçüm" : "measurement";
}
