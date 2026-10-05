"use client";

import type { ClinicalSummaryOverviewItem } from "@/lib/api/clinical-summary";
import {
  formatClinicalSummaryItemLabel,
  formatClinicalSummaryItemMessage,
} from "@/lib/clinical-summary/display";
import type { SupportedLocale } from "@/lib/i18n/locale";

type ClinicalSummaryCardProps = {
  locale: SupportedLocale;
  title: string;
  subtitle: string;
  description: string;
  emptyMessage: string;
  disclaimer: string;
  itemLabels: Record<string, string>;
  trendMessages: Record<string, string>;
  itemMessages: Record<string, string>;
  items: ClinicalSummaryOverviewItem[];
  loading: boolean;
  loadError: string | null;
  onRetry: () => void;
  retryLabel: string;
  loadingLabel: string;
  formatDate: (value: string) => string;
};

export function ClinicalSummaryCard({
  locale,
  title,
  subtitle,
  description,
  emptyMessage,
  disclaimer,
  itemLabels,
  trendMessages,
  itemMessages,
  items,
  loading,
  loadError,
  onRetry,
  retryLabel,
  loadingLabel,
  formatDate,
}: ClinicalSummaryCardProps) {
  const copy = { itemLabels, trendMessages, itemMessages };

  return (
    <section
      className="rounded-xl border border-border bg-white p-4 sm:p-5"
      aria-labelledby="clinical-summary-heading"
    >
      <h2 id="clinical-summary-heading" className="text-lg font-semibold text-text-primary">
        {title}
      </h2>
      <p className="mt-1 text-sm font-medium text-text-secondary">{subtitle}</p>
      {description ? (
        <p className="mt-2 text-sm text-text-secondary">{description}</p>
      ) : null}

      {loading ? <p className="mt-4 text-sm text-text-secondary">{loadingLabel}</p> : null}

      {loadError ? (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900">
          <p>{loadError}</p>
          <button
            type="button"
            className="mt-2 text-sm font-semibold text-brand-700 underline"
            onClick={onRetry}
          >
            {retryLabel}
          </button>
        </div>
      ) : null}

      {!loading && !loadError ? (
        items.length === 0 ? (
          <p className="mt-4 text-sm text-text-secondary">{emptyMessage}</p>
        ) : (
          <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-text-primary" role="list">
            {items.slice(0, 6).map((item) => (
              <li key={item.key}>
                <span className="font-medium text-text-primary">
                  {formatClinicalSummaryItemLabel(item, copy)}:
                </span>{" "}
                <span className="text-text-secondary">
                  {formatClinicalSummaryItemMessage(item, copy, locale, formatDate)}
                </span>
              </li>
            ))}
          </ul>
        )
      ) : null}

      <p className="mt-4 text-xs text-text-secondary">{disclaimer}</p>
    </section>
  );
}
