"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { ApiClientError } from "@/lib/api/client";
import {
  createClinicalEncounter,
  fetchPatientEncounters,
  type ClinicalEncounterListItem,
} from "@/lib/api/clinical-encounters";
import { formatEncounterStatusLabel } from "@/lib/clinical-encounters/display";
import { resolveEncounterClientErrorMessage } from "@/lib/clinical-encounters/error-messages";
import type { SupportedLocale } from "@/lib/i18n/locale";

export type EncountersSectionLabels = {
  sectionTitle: string;
  startNew: string;
  startPending: string;
  viewDetail: string;
  listEmpty: string;
  listLoadError: string;
  createConflict: string;
  createError: string;
  openActiveEncounter: string;
  statusLabels: Record<string, string>;
  specialtyLabel: string;
  startedAt: string;
  endedAt: string;
  notFoundOrDenied: string;
  genericError: string;
  accessDenied: string;
  loadingLabel: string;
  retryLabel: string;
};

type EncountersSectionProps = {
  patientId: string;
  accessToken: string | null;
  locale: SupportedLocale;
  labels: EncountersSectionLabels;
  onUnauthorized: () => void;
  formatDateTime: (value: string) => string;
};

export function EncountersSection({
  patientId,
  accessToken,
  locale,
  labels,
  onUnauthorized,
  formatDateTime,
}: EncountersSectionProps) {
  const router = useRouter();
  const [items, setItems] = useState<ClinicalEncounterListItem[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [createPending, setCreatePending] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [activeEncounterId, setActiveEncounterId] = useState<string | null>(null);

  const loadEncounters = useCallback(async () => {
    if (!accessToken) {
      return;
    }

    setListLoading(true);
    setListError(null);

    try {
      const response = await fetchPatientEncounters(accessToken, patientId, { limit: 50, offset: 0 });
      setItems(response.items);
      const active = response.items.find((item) => item.status === "active");
      setActiveEncounterId(active?.id ?? null);
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 401) {
        onUnauthorized();
        return;
      }
      setItems([]);
      setListError(labels.listLoadError);
    } finally {
      setListLoading(false);
    }
  }, [accessToken, labels.listLoadError, onUnauthorized, patientId]);

  useEffect(() => {
    void loadEncounters();
  }, [loadEncounters]);

  const handleStartEncounter = async () => {
    if (!accessToken || createPending) {
      return;
    }

    setCreatePending(true);
    setCreateError(null);

    try {
      const detail = await createClinicalEncounter(accessToken, patientId, {
        specialty_key: "cardiology",
        locale,
      });
      router.push(`/patients/${patientId}/encounters/${detail.encounter.id}`);
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 401) {
        onUnauthorized();
        return;
      }
      if (err instanceof ApiClientError && err.status === 409) {
        setCreateError(labels.createConflict);
        await loadEncounters();
        return;
      }
      setCreateError(
        resolveEncounterClientErrorMessage(err, {
          notFoundOrDenied: labels.notFoundOrDenied,
          activeConflict: labels.createConflict,
          generic: labels.createError,
          accessDenied: labels.accessDenied,
        }),
      );
    } finally {
      setCreatePending(false);
    }
  };

  return (
    <section aria-labelledby="encounters-heading" className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 id="encounters-heading" className="text-lg font-semibold text-text-primary">
          {labels.sectionTitle}
        </h2>
        <Button
          type="button"
          variant="secondary"
          size="md"
          disabled={createPending || listLoading}
          aria-busy={createPending}
          onClick={() => void handleStartEncounter()}
        >
          {createPending ? labels.startPending : labels.startNew}
        </Button>
      </div>

      {createError ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950" role="alert">
          <p>{createError}</p>
          {activeEncounterId ? (
            <Button
              href={`/patients/${patientId}/encounters/${activeEncounterId}`}
              variant="secondary"
              size="sm"
              className="mt-3"
            >
              {labels.openActiveEncounter}
            </Button>
          ) : null}
        </div>
      ) : null}

      {listLoading ? (
        <p className="text-text-secondary" aria-busy="true">
          {labels.loadingLabel}
        </p>
      ) : listError ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900" role="alert">
          <p>{listError}</p>
          <Button type="button" size="sm" variant="secondary" className="mt-3" onClick={() => void loadEncounters()}>
            {labels.retryLabel}
          </Button>
        </div>
      ) : items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-border bg-white px-4 py-8 text-center text-text-secondary">
          {labels.listEmpty}
        </p>
      ) : (
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item.id}>
              <article className="flex flex-col gap-3 rounded-xl border border-border bg-white p-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0 space-y-1">
                  <p className="text-sm font-medium text-text-primary">
                    {labels.specialtyLabel}: {item.specialty_key}
                  </p>
                  <p className="text-sm text-text-secondary">
                    <span className="font-medium">{formatEncounterStatusLabel(item.status, labels.statusLabels)}</span>
                    {item.started_at ? (
                      <>
                        {" · "}
                        {labels.startedAt}: {formatDateTime(item.started_at)}
                      </>
                    ) : null}
                    {item.ended_at ? (
                      <>
                        {" · "}
                        {labels.endedAt}: {formatDateTime(item.ended_at)}
                      </>
                    ) : null}
                  </p>
                </div>
                <Button href={`/patients/${patientId}/encounters/${item.id}`} size="sm" variant="secondary">
                  {labels.viewDetail}
                </Button>
              </article>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
