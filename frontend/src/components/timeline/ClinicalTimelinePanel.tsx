"use client";

import { useCallback, useEffect, useState } from "react";
import { TimelineEventCard } from "@/components/timeline/TimelineEventCard";
import { Button } from "@/components/ui/Button";
import { ApiClientError } from "@/lib/api/client";
import {
  fetchClinicalTimeline,
  type ClinicalTimelineResponse,
} from "@/lib/api/clinical-timeline";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  dateInputToUtcIsoEnd,
  dateInputToUtcIsoStart,
  sortTimelineEventsOldestFirst,
} from "@/lib/timeline/event-styles";
import { useLocale } from "@/lib/i18n/use-locale";

type ClinicalTimelinePanelProps = {
  patientId: string;
};

export function ClinicalTimelinePanel({ patientId }: ClinicalTimelinePanelProps) {
  const { accessToken } = useAuth();
  const { content } = useLocale();

  const [data, setData] = useState<ClinicalTimelineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusCode, setStatusCode] = useState<number | null>(null);

  const [dateFromInput, setDateFromInput] = useState("");
  const [dateToInput, setDateToInput] = useState("");
  const [includeRiskSnapshot, setIncludeRiskSnapshot] = useState(false);

  const [appliedDateFrom, setAppliedDateFrom] = useState<string | undefined>();
  const [appliedDateTo, setAppliedDateTo] = useState<string | undefined>();
  const [appliedRisk, setAppliedRisk] = useState(false);

  const loadTimeline = useCallback(async () => {
    if (!accessToken) {
      return;
    }

    setLoading(true);
    setError(null);
    setStatusCode(null);

    try {
      const response = await fetchClinicalTimeline(accessToken, patientId, {
        date_from: appliedDateFrom,
        date_to: appliedDateTo,
        include_risk_snapshot: appliedRisk,
      });
      setData(response);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setStatusCode(err.status);
        setError(err.message);
      } else {
        setError(content.timeline.loadError);
      }
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [
    accessToken,
    patientId,
    appliedDateFrom,
    appliedDateTo,
    appliedRisk,
    content.timeline.loadError,
  ]);

  useEffect(() => {
    void loadTimeline();
  }, [loadTimeline]);

  const applyFilters = () => {
    setAppliedDateFrom(dateFromInput ? dateInputToUtcIsoStart(dateFromInput) : undefined);
    setAppliedDateTo(dateToInput ? dateInputToUtcIsoEnd(dateToInput) : undefined);
    setAppliedRisk(includeRiskSnapshot);
  };

  const clearFilters = () => {
    setDateFromInput("");
    setDateToInput("");
    setIncludeRiskSnapshot(false);
    setAppliedDateFrom(undefined);
    setAppliedDateTo(undefined);
    setAppliedRisk(false);
  };

  const sortedEvents = data ? sortTimelineEventsOldestFirst(data.events) : [];

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-border bg-white p-4 sm:p-5">
        <h2 className="text-lg font-semibold text-text-primary">{content.timeline.filtersTitle}</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-text-primary">
              {content.timeline.dateFrom}
            </span>
            <input
              type="date"
              value={dateFromInput}
              onChange={(event) => setDateFromInput(event.target.value)}
              className="w-full rounded-lg border border-border px-3 py-2 text-sm"
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-text-primary">
              {content.timeline.dateTo}
            </span>
            <input
              type="date"
              value={dateToInput}
              onChange={(event) => setDateToInput(event.target.value)}
              className="w-full rounded-lg border border-border px-3 py-2 text-sm"
            />
          </label>
          <label className="flex items-end gap-2 text-sm sm:col-span-2 lg:col-span-1">
            <input
              type="checkbox"
              checked={includeRiskSnapshot}
              onChange={(event) => setIncludeRiskSnapshot(event.target.checked)}
              className="h-4 w-4 rounded border-border"
            />
            <span className="font-medium text-text-primary">{content.timeline.includeRiskSnapshot}</span>
          </label>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button type="button" size="sm" onClick={applyFilters}>
            {content.timeline.applyFilters}
          </Button>
          <Button type="button" size="sm" variant="secondary" onClick={clearFilters}>
            {content.timeline.clearFilters}
          </Button>
        </div>
      </section>

      {loading ? (
        <p className="text-center text-text-secondary">{content.common.loading}</p>
      ) : null}

      {!loading && error ? (
        <div
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900"
          role="alert"
        >
          <p className="font-medium">
            {statusCode === 401
              ? content.common.unauthorized
              : statusCode === 404
                ? content.common.notFound
                : content.timeline.loadError}
          </p>
          <p className="mt-1 break-words">{error}</p>
          <Button type="button" size="sm" variant="secondary" className="mt-3" onClick={loadTimeline}>
            {content.common.retry}
          </Button>
        </div>
      ) : null}

      {!loading && !error && data ? (
        <>
          <p className="text-sm text-text-secondary">{content.timeline.sortNotice}</p>
          {data.truncated ? (
            <p className="rounded-lg bg-brand-50 px-3 py-2 text-sm text-brand-900">
              {content.timeline.truncatedNotice}
            </p>
          ) : null}
          {sortedEvents.length === 0 ? (
            <p className="rounded-xl border border-dashed border-border bg-white px-4 py-8 text-center text-text-secondary">
              {content.timeline.empty}
            </p>
          ) : (
            <ul className="space-y-4" role="list">
              {sortedEvents.map((event, index) => (
                <li key={`${event.event_type}-${event.occurred_at}-${index}`}>
                  <TimelineEventCard event={event} />
                </li>
              ))}
            </ul>
          )}
          <p className="rounded-lg border border-border bg-surface px-4 py-3 text-sm text-text-secondary">
            {content.timeline.disclaimer}
          </p>
        </>
      ) : null}
    </div>
  );
}
