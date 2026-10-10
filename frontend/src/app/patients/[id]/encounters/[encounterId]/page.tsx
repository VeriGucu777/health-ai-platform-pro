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
  const ws = enc.workspace;

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
          finalSummaryHeading: enc.finalSummaryHeading,
          detailNotFound: enc.detailNotFound,
          detailLoadError: enc.detailLoadError,
          notFoundOrDenied: enc.notFoundOrDenied,
          genericError: enc.genericError,
          accessDenied: enc.accessDenied,
          loadingLabel: content.common.loading,
          retryLabel: content.common.retry,
          clinicianNoteLabel: enc.clinicianNoteLabel,
          workspace: {
            recordsHeading: ws.recordsHeading,
            complaintsHeading: enc.complaintsHeading,
            findingsHeading: enc.findingsHeading,
            responsesHeading: enc.responsesHeading,
            complaintsEmpty: enc.complaintsEmpty,
            findingsEmpty: enc.findingsEmpty,
            responsesEmpty: enc.responsesEmpty,
            readOnlyFinalized: ws.readOnlyFinalized,
            readOnlyCancelled: ws.readOnlyCancelled,
            readOnlyDraft: ws.readOnlyDraft,
            primaryBadge: ws.primaryBadge,
            negatedBadge: ws.negatedBadge,
            recordedAt: ws.recordedAt,
            complaintKeyLabel: ws.complaintKeyLabel,
            complaintKeyHint: ws.complaintKeyHint,
            complaintTextLabel: ws.complaintTextLabel,
            complaintPrimaryLabel: ws.complaintPrimaryLabel,
            complaintNegatedLabel: ws.complaintNegatedLabel,
            addComplaint: ws.addComplaint,
            addComplaintPending: ws.addComplaintPending,
            complaintSuccess: ws.complaintSuccess,
            removeComplaint: ws.removeComplaint,
            removeComplaintConfirm: ws.removeComplaintConfirm,
            removeComplaintPending: ws.removeComplaintPending,
            removeComplaintSuccess: ws.removeComplaintSuccess,
            primaryComplaintHint: ws.primaryComplaintHint,
            findingTypeLabel: ws.findingTypeLabel,
            findingKeyLabel: ws.findingKeyLabel,
            findingKeyHint: ws.findingKeyHint,
            findingValueCodeLabel: ws.findingValueCodeLabel,
            findingValueNumericLabel: ws.findingValueNumericLabel,
            findingUnitLabel: ws.findingUnitLabel,
            findingNegatedLabel: ws.findingNegatedLabel,
            findingSourceLabel: ws.findingSourceLabel,
            addFinding: ws.addFinding,
            addFindingPending: ws.addFindingPending,
            findingSuccess: ws.findingSuccess,
            questionKeyLabel: ws.questionKeyLabel,
            questionKeyHint: ws.questionKeyHint,
            answerTypeLabel: ws.answerTypeLabel,
            answerCodeLabel: ws.answerCodeLabel,
            answerNumericLabel: ws.answerNumericLabel,
            booleanYes: ws.booleanYes,
            booleanNo: ws.booleanNo,
            booleanUnknown: ws.booleanUnknown,
            clinicianNoteLabel: ws.clinicianNoteLabel,
            saveResponse: ws.saveResponse,
            saveResponsePending: ws.saveResponsePending,
            responseSuccess: ws.responseSuccess,
            validationComplaintRequired: ws.validationComplaintRequired,
            validationFindingKeyRequired: ws.validationFindingKeyRequired,
            validationNumericInvalid: ws.validationNumericInvalid,
            validationQuestionKeyRequired: ws.validationQuestionKeyRequired,
            validationAnswerRequired: ws.validationAnswerRequired,
            validationNoteRequired: ws.validationNoteRequired,
            findingTypes: ws.findingTypes,
            findingSources: ws.findingSources,
            answerTypes: ws.answerTypes,
            mutationErrors: {
              notFoundOrDenied: enc.notFoundOrDenied,
              validation: ws.mutationValidation,
              conflictStale: ws.mutationConflictStale,
              terminalEdit: ws.mutationTerminalEdit,
              server: ws.mutationServer,
              accessDenied: enc.accessDenied,
              generic: enc.genericError,
            },
          },
        }}
      />
    </PageContainer>
  );
}
