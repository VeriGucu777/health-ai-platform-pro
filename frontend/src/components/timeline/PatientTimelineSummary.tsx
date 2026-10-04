"use client";

import { useEffect, useState } from "react";
import { ApiClientError } from "@/lib/api/client";
import { fetchPatient, type Patient } from "@/lib/api/patients";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  calculateAgeYears,
  formatPatientGender,
} from "@/lib/timeline/display";
import { useLocale } from "@/lib/i18n/use-locale";
import { isSyntheticDemoPatient } from "@/lib/timeline/demo-patient";

type PatientTimelineSummaryProps = {
  patientId: string;
};

export function PatientTimelineSummary({ patientId }: PatientTimelineSummaryProps) {
  const { accessToken } = useAuth();
  const { content, formatDate } = useLocale();
  const [patient, setPatient] = useState<Patient | null>(null);

  useEffect(() => {
    if (!accessToken) {
      return;
    }

    let cancelled = false;

    void (async () => {
      try {
        const data = await fetchPatient(accessToken, patientId);
        if (!cancelled) {
          setPatient(data);
        }
      } catch (err) {
        if (!cancelled && !(err instanceof ApiClientError && err.status === 404)) {
          setPatient(null);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [accessToken, patientId]);

  if (!patient) {
    return null;
  }

  const age = calculateAgeYears(patient.date_of_birth);
  const genderLabel = formatPatientGender(patient.gender, content.patients.genders);

  const showDemoBanner = isSyntheticDemoPatient(patient.notes);

  return (
    <div className="mt-4 space-y-3">
      {showDemoBanner ? (
        <p
          className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-950"
          role="status"
        >
          {content.timeline.syntheticDemoBanner}
        </p>
      ) : null}
      <div className="rounded-xl border border-border bg-brand-50/40 px-4 py-3 text-sm text-text-secondary">
        <p className="font-semibold text-text-primary">
          {patient.first_name} {patient.last_name}
        </p>
        <p className="mt-1">
          {formatDate(patient.date_of_birth)} ({age} {content.timeline.patientSummary.ageSuffix}) ·{" "}
          {genderLabel}
        </p>
      </div>
    </div>
  );
}
