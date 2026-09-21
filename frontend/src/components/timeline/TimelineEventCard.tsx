"use client";

import type { TimelineEvent } from "@/lib/api/clinical-timeline";
import {
  categoryBadgeClass,
  categoryIconLabel,
  resolveTimelineCategory,
  severityBadgeClass,
} from "@/lib/timeline/event-styles";
import {
  formatSeverityLevel,
  formatSourceKind,
  formatTimelineDetail,
  formatTimelineHeadline,
} from "@/lib/timeline/display";
import { useLocale } from "@/lib/i18n/use-locale";

type TimelineEventCardProps = {
  event: TimelineEvent;
};

export function TimelineEventCard({ event }: TimelineEventCardProps) {
  const { content, formatDateTime, locale } = useLocale();
  const category = resolveTimelineCategory(event.event_type);
  const isOverdue = event.event_type === "appointment_overdue";
  const typeLabel =
    content.timeline.eventTypes[event.event_type] ?? event.event_type;
  const severityClass = severityBadgeClass(event.severity);
  const headline = formatTimelineHeadline(event, locale, content.timeline.headlines);
  const detail = formatTimelineDetail(
    event.detail,
    locale,
    event.event_type,
    content.timeline.detailPhrases,
  );
  const severityLabel = formatSeverityLevel(event.severity, content.timeline.severityLevels);
  const sourceLabel = formatSourceKind(event.source.kind, content.timeline.sourceKinds);

  return (
    <article
      className={[
        "rounded-xl border bg-white p-4 shadow-sm sm:p-5",
        isOverdue ? "border-amber-300 bg-amber-50/40" : "border-border",
      ].join(" ")}
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <span
            aria-hidden="true"
            className={[
              "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-sm font-bold",
              categoryBadgeClass(category),
            ].join(" ")}
          >
            {categoryIconLabel(category)}
          </span>
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-wide text-text-secondary">
              {formatDateTime(event.occurred_at)}
            </p>
            <h3 className="mt-1 text-base font-semibold text-text-primary">{headline}</h3>
            {detail ? (
              <p className="mt-2 break-words text-sm text-text-secondary">{detail}</p>
            ) : null}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:max-w-xs sm:justify-end">
          <span
            className={[
              "inline-flex rounded-full px-2.5 py-1 text-xs font-medium",
              categoryBadgeClass(category),
            ].join(" ")}
          >
            {typeLabel}
          </span>
          {severityClass && severityLabel ? (
            <span
              className={[
                "inline-flex rounded-full px-2.5 py-1 text-xs font-medium",
                severityClass,
              ].join(" ")}
            >
              {content.timeline.severity}: {severityLabel}
            </span>
          ) : null}
        </div>
      </div>

      <p className="mt-3 text-xs text-text-secondary">
        {content.timeline.sourceKind}:{" "}
        <span className="font-medium text-text-primary">{sourceLabel}</span>
      </p>
    </article>
  );
}
