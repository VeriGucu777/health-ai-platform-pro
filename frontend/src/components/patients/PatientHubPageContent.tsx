"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ApiClientError } from "@/lib/api/client";
import {
  fetchHealthSummaryPdf,
  triggerBlobDownload,
} from "@/lib/api/health-report";
import { fetchPatient, type Patient } from "@/lib/api/patients";
import {
  fetchRiskAssessmentHistory,
  type RiskAssessmentHistoryItem,
} from "@/lib/api/risk-history";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  calculateAgeYears,
  formatPatientGender,
} from "@/lib/timeline/display";
import { useLocale } from "@/lib/i18n/use-locale";

type PatientHubPageContentProps = {
  patientId: string;
};

type HubLoadState = "loading" | "ready" | "not_found" | "error";

function formatRiskType(type: string, labels: Record<string, string>): string {
  return labels[type] ?? type;
}

function formatRiskLevel(level: string | null, labels: Record<string, string>): string {
  if (!level) {
    return "—";
  }
  return labels[level] ?? level;
}

function RiskHistoryCard({
  item,
  labels,
  formatDateTime,
}: {
  item: RiskAssessmentHistoryItem;
  labels: {
    assessmentTypes: Record<string, string>;
    riskLevels: Record<string, string>;
    riskType: string;
    riskLevel: string;
    assessedAt: string;
    score: string;
    factors: string;
    missingInputs: string;
    riskDisclaimer: string;
  };
  formatDateTime: (value: string) => string;
}) {
  const snapshot = item.result_snapshot;
  const factors = snapshot?.contributing_factors ?? [];
  const missing = snapshot?.missing_inputs ?? [];

  return (
    <article className="rounded-xl border border-border bg-white p-4 sm:p-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-text-secondary">
            {labels.assessedAt}: {formatDateTime(item.evaluated_at)}
          </p>
          <h3 className="mt-1 text-base font-semibold text-text-primary">
            {formatRiskType(item.assessment_type, labels.assessmentTypes)}
          </h3>
        </div>
        <div className="flex flex-wrap gap-2 text-sm">
          <span className="rounded-full bg-brand-50 px-2.5 py-1 font-medium text-brand-800">
            {labels.riskLevel}: {formatRiskLevel(item.risk_level, labels.riskLevels)}
          </span>
          {item.score !== null ? (
            <span className="rounded-full bg-surface px-2.5 py-1 text-text-secondary">
              {labels.score}: {item.score}
            </span>
          ) : null}
        </div>
      </div>

      {factors.length > 0 ? (
        <div className="mt-4">
          <p className="text-sm font-medium text-text-primary">{labels.factors}</p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-text-secondary">
            {factors.map((factor) => (
              <li key={`${factor.factor}-${factor.message}`}>{factor.message}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {missing.length > 0 ? (
        <div className="mt-4">
          <p className="text-sm font-medium text-text-primary">{labels.missingInputs}</p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-text-secondary">
            {missing.map((entry) => (
              <li key={`${entry.input}-${entry.reason}`}>
                {entry.input}: {entry.reason}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <p className="mt-4 text-xs text-text-secondary">{labels.riskDisclaimer}</p>
    </article>
  );
}

export function PatientHubPageContent({ patientId }: PatientHubPageContentProps) {
  const { accessToken, handleUnauthorized } = useAuth();
  const { content, formatDate, formatDateTime, effectiveLocale } = useLocale();
  const hub = content.patientHub;

  const [patient, setPatient] = useState<Patient | null>(null);
  const [loadState, setLoadState] = useState<HubLoadState>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);

  const [riskItems, setRiskItems] = useState<RiskAssessmentHistoryItem[]>([]);
  const [riskLoading, setRiskLoading] = useState(true);
  const [riskError, setRiskError] = useState<string | null>(null);

  const [pdfPending, setPdfPending] = useState(false);
  const [pdfMessage, setPdfMessage] = useState<string | null>(null);
  const [pdfError, setPdfError] = useState<string | null>(null);

  const loadPatient = useCallback(async () => {
    if (!accessToken) {
      return;
    }

    setLoadState("loading");
    setLoadError(null);

    try {
      const data = await fetchPatient(accessToken, patientId);
      setPatient(data);
      setLoadState("ready");
    } catch (err) {
      if (err instanceof ApiClientError) {
        if (err.status === 401) {
          handleUnauthorized();
          return;
        }
        if (err.status === 404) {
          setPatient(null);
          setLoadState("not_found");
          return;
        }
      }
      setPatient(null);
      setLoadState("error");
      setLoadError(hub.loadError);
    }
  }, [accessToken, handleUnauthorized, hub.loadError, patientId]);

  const loadRiskHistory = useCallback(async () => {
    if (!accessToken || loadState !== "ready") {
      return;
    }

    setRiskLoading(true);
    setRiskError(null);

    try {
      const response = await fetchRiskAssessmentHistory(accessToken, patientId, {
        page: 1,
        page_size: 20,
      });
      setRiskItems(response.items);
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 401) {
        handleUnauthorized();
        return;
      }
      setRiskItems([]);
      setRiskError(hub.riskHistoryLoadError);
    } finally {
      setRiskLoading(false);
    }
  }, [accessToken, handleUnauthorized, hub.riskHistoryLoadError, loadState, patientId]);

  useEffect(() => {
    void loadPatient();
  }, [loadPatient]);

  useEffect(() => {
    if (loadState === "ready") {
      void loadRiskHistory();
    }
  }, [loadRiskHistory, loadState]);

  const handleDownloadPdf = async () => {
    if (!accessToken) {
      return;
    }

    setPdfPending(true);
    setPdfError(null);
    setPdfMessage(null);

    try {
      const { blob, filename } = await fetchHealthSummaryPdf(accessToken, patientId, {
        locale: effectiveLocale,
      });
      triggerBlobDownload(blob, filename);
      setPdfMessage(hub.pdfSuccess);
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 401) {
        handleUnauthorized();
        return;
      }
      setPdfError(hub.pdfError);
    } finally {
      setPdfPending(false);
    }
  };

  if (loadState === "loading") {
    return <p className="text-center text-text-secondary">{content.common.loading}</p>;
  }

  if (loadState === "not_found") {
    return (
      <div
        className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-6 text-center text-sm text-amber-950"
        role="alert"
      >
        <p className="font-medium">{hub.notFoundOrDenied}</p>
        <Button href="/patients" variant="secondary" size="sm" className="mt-4">
          {content.common.back}
        </Button>
      </div>
    );
  }

  if (loadState === "error" || !patient) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900" role="alert">
        <p className="font-medium">{loadError ?? content.common.error}</p>
        <Button type="button" size="sm" variant="secondary" className="mt-3" onClick={loadPatient}>
          {content.common.retry}
        </Button>
      </div>
    );
  }

  const age = calculateAgeYears(patient.date_of_birth);
  const genderLabel = formatPatientGender(patient.gender, content.patients.genders);

  return (
    <div className="space-y-8">
      <header className="max-w-3xl">
        <h1 className="text-2xl font-bold text-text-primary sm:text-3xl">
          {patient.first_name} {patient.last_name}
        </h1>
        <p className="mt-2 text-text-secondary">
          {formatDate(patient.date_of_birth)} ({age} {content.timeline.patientSummary.ageSuffix}) ·{" "}
          {genderLabel} ·{" "}
          <span className="font-medium">
            {patient.is_active ? hub.active : hub.inactive}
          </span>
        </p>
      </header>

      <section
        className="rounded-xl border border-brand-200 bg-brand-50/50 p-4 sm:p-5"
        aria-labelledby="decision-support-heading"
      >
        <h2 id="decision-support-heading" className="text-sm font-semibold text-brand-900">
          {hub.decisionSupportTitle}
        </h2>
        <p className="mt-2 text-sm text-text-secondary">{hub.decisionSupportBody}</p>
      </section>

      <section className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
        <Button href={`/patients/${patientId}/timeline`} size="lg">
          {hub.clinicalTimeline}
        </Button>
        <Button
          type="button"
          variant="secondary"
          size="lg"
          disabled={pdfPending}
          onClick={() => void handleDownloadPdf()}
        >
          {pdfPending ? hub.downloadingPdf : hub.downloadPdf}
        </Button>
      </section>

      {pdfMessage ? (
        <p className="text-sm text-green-800" role="status">
          {pdfMessage}
        </p>
      ) : null}
      {pdfError ? (
        <p className="text-sm text-red-800" role="alert">
          {pdfError}
        </p>
      ) : null}

      <section aria-labelledby="risk-history-heading">
        <h2 id="risk-history-heading" className="text-lg font-semibold text-text-primary">
          {hub.riskHistoryTitle}
        </h2>

        {riskLoading ? (
          <p className="mt-4 text-text-secondary">{content.common.loading}</p>
        ) : riskError ? (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900" role="alert">
            <p>{riskError}</p>
            <Button type="button" size="sm" variant="secondary" className="mt-3" onClick={loadRiskHistory}>
              {content.common.retry}
            </Button>
          </div>
        ) : riskItems.length === 0 ? (
          <p className="mt-4 rounded-xl border border-dashed border-border bg-white px-4 py-8 text-center text-text-secondary">
            {hub.riskHistoryEmpty}
          </p>
        ) : (
          <div className="mt-4 space-y-4">
            {riskItems.map((item) => (
              <RiskHistoryCard
                key={item.id}
                item={item}
                labels={{
                  assessmentTypes: hub.assessmentTypes,
                  riskLevels: hub.riskLevels,
                  riskType: hub.riskType,
                  riskLevel: hub.riskLevel,
                  assessedAt: hub.assessedAt,
                  score: hub.score,
                  factors: hub.factors,
                  missingInputs: hub.missingInputs,
                  riskDisclaimer: hub.riskDisclaimer,
                }}
                formatDateTime={formatDateTime}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
