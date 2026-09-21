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

  return (
    <div className="mt-4 rounded-xl border border-border bg-brand-50/40 px-4 py-3 text-sm text-text-secondary">
      <p className="font-semibold text-text-primary">
        {patient.first_name} {patient.last_name}
      </p>
      <p className="mt-1">
        {formatDate(patient.date_of_birth)} ({age} {content.timeline.patientSummary.ageSuffix}) ·{" "}
        {genderLabel}
      </p>
    </div>
  );
}
