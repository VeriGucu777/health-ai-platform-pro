"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { EncounterDetailPageContent } from "@/components/patients/EncounterDetailPageContent";
import { PageContainer } from "@/components/layout/PageContainer";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useLocale } from "@/lib/i18n/use-locale";

export default function PatientEncounterDetailPage() {
  const params = useParams<{ id: string; encounterId: string }>();
  const patientId = params.id;
  const encounterId = params.encounterId;
  const { accessToken, handleUnauthorized } = useAuth();
  const { content, formatDateTime } = useLocale();
  const hub = content.patientHub;
  const enc = hub.encounters;

  return (
    <PageContainer className="py-8 sm:py-10">
      <div className="mb-6">
        <Link
          href={`/patients/${patientId}`}
          className="text-sm font-medium text-brand-700 hover:text-brand-800"
        >
          ← {enc.backToPatient}
        </Link>
      </div>
      <EncounterDetailPageContent
        patientId={patientId}
        encounterId={encounterId}
        accessToken={accessToken}
        formatDateTime={formatDateTime}
        onUnauthorized={handleUnauthorized}
        labels={{
          detailTitle: enc.detailTitle,
          backToPatient: enc.backToPatient,
          statusLabels: enc.statusLabels,
          specialtyLabel: enc.specialtyLabel,
          startedAt: enc.startedAt,
          endedAt: enc.endedAt,
          complaintsHeading: enc.complaintsHeading,
          findingsHeading: enc.findingsHeading,
          responsesHeading: enc.responsesHeading,
          finalSummaryHeading: enc.finalSummaryHeading,
          complaintsEmpty: enc.complaintsEmpty,
          findingsEmpty: enc.findingsEmpty,
          responsesEmpty: enc.responsesEmpty,
          detailNotFound: enc.detailNotFound,
          detailLoadError: enc.detailLoadError,
          notFoundOrDenied: enc.notFoundOrDenied,
          genericError: enc.genericError,
          accessDenied: enc.accessDenied,
          loadingLabel: content.common.loading,
          retryLabel: content.common.retry,
          clinicianNoteLabel: enc.clinicianNoteLabel,
        }}
      />
    </PageContainer>
  );
}
