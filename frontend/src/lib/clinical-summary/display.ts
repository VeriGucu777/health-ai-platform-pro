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

export function formatClinicalSummaryCompactPeriodRange(
  windowStart: string,
  windowEnd: string,
  locale: SupportedLocale,
): string {
  if (windowStart === windowEnd) {
    return formatMediumDate(windowStart, locale);
  }
  const start = new Date(`${windowStart}T12:00:00`);
  const end = new Date(`${windowEnd}T12:00:00`);
  const sameYear = start.getFullYear() === end.getFullYear();
  if (sameYear) {
    const dayMonth = new Intl.DateTimeFormat(locale, { day: "numeric", month: "short" });
    const dayMonthYear = new Intl.DateTimeFormat(locale, {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
    return `${dayMonth.format(start)}–${dayMonthYear.format(end)}`;
  }
  return `${formatMediumDate(windowStart, locale)}–${formatMediumDate(windowEnd, locale)}`;
}

function formatMediumDate(value: string, locale: SupportedLocale): string {
  try {
    return new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(
      new Date(`${value}T12:00:00`),
    );
  } catch {
    return value;
  }
}

export function formatClinicalSummaryOverviewSubtitle(
  periodStart: string | null | undefined,
  periodEnd: string | null | undefined,
  formatDate: (value: string) => string,
  fallback: string,
  periodViewSuffix: string,
): string {
  if (!periodStart || !periodEnd) {
    return fallback;
  }
  return `${formatDate(periodStart)} – ${formatDate(periodEnd)} ${periodViewSuffix}`;
}

export function formatClinicalSummaryItemLabel(
  item: ClinicalSummaryOverviewItem,
  copy: ClinicalSummaryCopy,
): string {
  return copy.itemLabels[item.key] ?? item.label;
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

function enrichMessageParams(
  item: ClinicalSummaryOverviewItem,
  params: Record<string, string>,
  locale: SupportedLocale,
  formatDate?: (value: string) => string,
): Record<string, string> {
  const enriched = { ...params };
  if (enriched.record_date && formatDate) {
    enriched.record_date = formatDate(enriched.record_date);
  }
  if (item.message_key?.startsWith("trend_hybrid_")) {
    enriched.count = String(item.source_count);
    enriched.context = localizedContextForKey(item.key, locale);
    if (enriched.window_start && enriched.window_end) {
      enriched.period_range = formatClinicalSummaryCompactPeriodRange(
        enriched.window_start,
        enriched.window_end,
        locale,
      );
    }
  }
  return enriched;
}

export function formatClinicalSummaryItemMessage(
  item: ClinicalSummaryOverviewItem,
  copy: ClinicalSummaryCopy,
  locale: SupportedLocale,
  formatDate?: (value: string) => string,
): string {
  if (item.message_key && copy.itemMessages[item.message_key]) {
    const params = enrichMessageParams(
      item,
      { ...(item.message_params ?? {}) },
      locale,
      formatDate,
    );
    if (
      (item.message_key === "upcoming_follow_up_date" ||
        item.message_key === "overdue_follow_up_date") &&
      params.date &&
      formatDate
    ) {
      params.date = formatDate(params.date);
    }
    return applyTemplate(copy.itemMessages[item.message_key], params);
  }

  if (item.trend_status && copy.trendMessages[item.trend_status]) {
    const template = copy.trendMessages[item.trend_status];
    const params: Record<string, string> = {
      count: String(item.source_count),
      context: localizedContextForKey(item.key, locale),
    };
    if (item.message_params?.window_start && item.message_params?.window_end) {
      params.period_range = formatClinicalSummaryCompactPeriodRange(
        item.message_params.window_start,
        item.message_params.window_end,
        locale,
      );
    }
    return applyTemplate(template, params);
  }

  return item.message;
}
