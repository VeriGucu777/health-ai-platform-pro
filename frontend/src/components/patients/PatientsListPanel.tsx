"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ApiClientError } from "@/lib/api/client";
import { fetchPatients, type Patient } from "@/lib/api/patients";
import { useAuth } from "@/lib/auth/AuthProvider";
import { formatPatientGender } from "@/lib/timeline/display";
import { useLocale } from "@/lib/i18n/use-locale";

export function PatientsListPanel() {
  const { accessToken } = useAuth();
  const { content, formatDate } = useLocale();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusCode, setStatusCode] = useState<number | null>(null);

  const loadPatients = useCallback(async () => {
    if (!accessToken) {
      return;
    }

    setLoading(true);
    setError(null);
    setStatusCode(null);

    try {
      const response = await fetchPatients(accessToken, { page: 1, page_size: 100 });
      setPatients(response.items);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setStatusCode(err.status);
        setError(err.message);
      } else {
        setError(content.patients.loadError);
      }
      setPatients([]);
    } finally {
      setLoading(false);
    }
  }, [accessToken, content.patients.loadError]);

  useEffect(() => {
    void loadPatients();
  }, [loadPatients]);

  if (loading) {
    return <p className="text-center text-text-secondary">{content.common.loading}</p>;
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900" role="alert">
        <p className="font-medium">
          {statusCode === 401 ? content.common.unauthorized : content.patients.loadError}
        </p>
        <p className="mt-1 break-words">{error}</p>
        <Button type="button" size="sm" variant="secondary" className="mt-3" onClick={loadPatients}>
          {content.common.retry}
        </Button>
      </div>
    );
  }

  if (patients.length === 0) {
    return (
      <p className="rounded-xl border border-dashed border-border bg-white px-4 py-8 text-center text-text-secondary">
        {content.patients.empty}
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-white">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-border bg-brand-50/60 text-text-secondary">
          <tr>
            <th className="px-4 py-3 font-medium">{content.patients.name}</th>
            <th className="px-4 py-3 font-medium">{content.patients.dateOfBirth}</th>
            <th className="px-4 py-3 font-medium">{content.patients.gender}</th>
            <th className="px-4 py-3 font-medium">
              <span className="sr-only">{content.patients.viewTimeline}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {patients.map((patient) => (
            <tr key={patient.id} className="border-b border-border last:border-b-0">
              <td className="px-4 py-3 font-medium text-text-primary">
                {patient.first_name} {patient.last_name}
              </td>
              <td className="px-4 py-3 text-text-secondary">{formatDate(patient.date_of_birth)}</td>
              <td className="px-4 py-3 text-text-secondary">
                {formatPatientGender(patient.gender, content.patients.genders)}
              </td>
              <td className="px-4 py-3">
                <Link
                  href={`/patients/${patient.id}/timeline`}
                  className="inline-flex min-h-10 items-center rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
                >
                  {content.patients.viewTimeline}
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
