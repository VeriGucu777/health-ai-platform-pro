"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { ApiClientError } from "@/lib/api/client";
import {
  fetchClinicalEncounterDetail,
  type ClinicalEncounterDetail,
} from "@/lib/api/clinical-encounters";
import { formatEncounterStatusLabel } from "@/lib/clinical-encounters/display";
import { resolveEncounterClientErrorMessage } from "@/lib/clinical-encounters/error-messages";

export type EncounterDetailLabels = {
  detailTitle: string;
  backToPatient: string;
  statusLabels: Record<string, string>;
  specialtyLabel: string;
  startedAt: string;
  endedAt: string;
  complaintsHeading: string;
  findingsHeading: string;
  responsesHeading: string;
  finalSummaryHeading: string;
  complaintsEmpty: string;
  findingsEmpty: string;
  responsesEmpty: string;
  detailNotFound: string;
  detailLoadError: string;
  notFoundOrDenied: string;
  genericError: string;
  accessDenied: string;
  loadingLabel: string;
  retryLabel: string;
  clinicianNoteLabel: string;
};

type EncounterDetailPageContentProps = {
  patientId: string;
  encounterId: string;
  accessToken: string | null;
  labels: EncounterDetailLabels;
  formatDateTime: (value: string) => string;
  onUnauthorized: () => void;
};

type DetailLoadState = "loading" | "ready" | "not_found" | "error";

export function EncounterDetailPageContent({
  patientId,
  encounterId,
  accessToken,
  labels,
  formatDateTime,
  onUnauthorized,
}: EncounterDetailPageContentProps) {
  const [detail, setDetail] = useState<ClinicalEncounterDetail | null>(null);
  const [loadState, setLoadState] = useState<DetailLoadState>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadDetail = useCallback(async () => {
    if (!accessToken) {
      return;
    }

    setLoadState("loading");
    setLoadError(null);

    try {
      const data = await fetchClinicalEncounterDetail(accessToken, encounterId);
      setDetail(data);
      setLoadState("ready");
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 401) {
        onUnauthorized();
        return;
      }
      if (err instanceof ApiClientError && err.status === 404) {
        setDetail(null);
        setLoadState("not_found");
        return;
      }
      setDetail(null);
      setLoadState("error");
      setLoadError(
        resolveEncounterClientErrorMessage(err, {
          notFoundOrDenied: labels.detailNotFound,
          activeConflict: labels.genericError,
          generic: labels.detailLoadError,
          accessDenied: labels.accessDenied,
        }),
      );
    }
  }, [
    accessToken,
    encounterId,
    labels.accessDenied,
    labels.detailLoadError,
    labels.detailNotFound,
    labels.genericError,
    onUnauthorized,
  ]);

  useEffect(() => {
    void loadDetail();
  }, [loadDetail]);

  if (loadState === "loading") {
    return <p className="text-text-secondary" aria-busy="true">{labels.loadingLabel}</p>;
  }

  if (loadState === "not_found") {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-6 text-center text-sm text-amber-950" role="alert">
        <p className="font-medium">{labels.detailNotFound}</p>
        <Link
          href={`/patients/${patientId}`}
          className="mt-4 inline-block text-sm font-medium text-brand-700 hover:text-brand-800"
        >
          {labels.backToPatient}
        </Link>
      </div>
    );
  }

  if (loadState === "error" || !detail) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900" role="alert">
        <p className="font-medium">{loadError ?? labels.detailLoadError}</p>
        <Button type="button" size="sm" variant="secondary" className="mt-3" onClick={() => void loadDetail()}>
          {labels.retryLabel}
        </Button>
      </div>
    );
  }

  const enc = detail.encounter;

  return (
    <div className="space-y-8">
      <header className="max-w-3xl space-y-2">
        <h1 className="text-2xl font-bold text-text-primary sm:text-3xl">{labels.detailTitle}</h1>
        <p className="text-text-secondary">
          {labels.specialtyLabel}: {enc.specialty_key} ·{" "}
          <span className="font-medium">{formatEncounterStatusLabel(enc.status, labels.statusLabels)}</span>
        </p>
        {enc.started_at ? (
          <p className="text-sm text-text-secondary">
            {labels.startedAt}: {formatDateTime(enc.started_at)}
          </p>
        ) : null}
        {enc.ended_at ? (
          <p className="text-sm text-text-secondary">
            {labels.endedAt}: {formatDateTime(enc.ended_at)}
          </p>
        ) : null}
      </header>

      <section aria-labelledby="enc-complaints-heading">
        <h2 id="enc-complaints-heading" className="text-lg font-semibold text-text-primary">
          {labels.complaintsHeading}
        </h2>
        {detail.complaints.length === 0 ? (
          <p className="mt-3 text-sm text-text-secondary">{labels.complaintsEmpty}</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {detail.complaints.map((item) => (
              <li key={item.id} className="rounded-lg border border-border bg-white px-4 py-3 text-sm text-text-secondary">
                {item.clinician_display_text ?? item.complaint_key ?? "—"}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="enc-findings-heading">
        <h2 id="enc-findings-heading" className="text-lg font-semibold text-text-primary">
          {labels.findingsHeading}
        </h2>
        {detail.findings.length === 0 ? (
          <p className="mt-3 text-sm text-text-secondary">{labels.findingsEmpty}</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {detail.findings.map((item) => (
              <li key={item.id} className="rounded-lg border border-border bg-white px-4 py-3 text-sm text-text-secondary">
                {item.finding_key}
                {item.value_code ? ` · ${item.value_code}` : ""}
                {item.value_numeric != null ? ` · ${item.value_numeric}` : ""}
                {item.unit ? ` ${item.unit}` : ""}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="enc-responses-heading">
        <h2 id="enc-responses-heading" className="text-lg font-semibold text-text-primary">
          {labels.responsesHeading}
        </h2>
        {detail.question_responses.length === 0 ? (
          <p className="mt-3 text-sm text-text-secondary">{labels.responsesEmpty}</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {detail.question_responses.map((item) => (
              <li key={item.id} className="rounded-lg border border-border bg-white px-4 py-3 text-sm text-text-secondary">
                <span className="font-medium text-text-primary">{item.question_key}</span>
                {item.answer_code ? `: ${item.answer_code}` : ""}
                {item.answer_numeric != null ? `: ${item.answer_numeric}` : ""}
                {item.clinician_note ? (
                  <p className="mt-1 text-text-secondary">{item.clinician_note}</p>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>

      {detail.final_summary ? (
        <section aria-labelledby="enc-final-summary-heading">
          <h2 id="enc-final-summary-heading" className="text-lg font-semibold text-text-primary">
            {labels.finalSummaryHeading}
          </h2>
          <div className="mt-3 space-y-4 rounded-xl border border-border bg-white p-4">
            {detail.final_summary.summary_sections.map((section) => (
              <article key={section.section_key}>
                <h3 className="text-sm font-semibold text-text-primary">{section.section_key}</h3>
                {section.content_key ? (
                  <p className="mt-1 text-xs text-text-secondary">{section.content_key}</p>
                ) : null}
                {section.clinician_text ? (
                  <p className="mt-2 whitespace-pre-wrap text-sm text-text-secondary">{section.clinician_text}</p>
                ) : null}
              </article>
            ))}
            {detail.final_summary.clinician_note ? (
              <p className="text-sm text-text-secondary">
                <span className="font-medium text-text-primary">{labels.clinicianNoteLabel}: </span>
                {detail.final_summary.clinician_note}
              </p>
            ) : null}
          </div>
        </section>
      ) : null}
    </div>
  );
}
