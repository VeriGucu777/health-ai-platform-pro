"use client";

import { useCallback, useId, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ApiClientError } from "@/lib/api/client";
import {
  cancelClinicalEncounter,
  finalizeClinicalEncounter,
  type ClinicalEncounterDetail,
  type FinalizeClinicalEncounterBody,
} from "@/lib/api/clinical-encounters";
import {
  resolveEncounterMutationErrorMessage,
  type EncounterMutationErrorLabels,
} from "@/lib/clinical-encounters/mutation-errors";

export type EncounterTerminalLabels = {
  sectionHeading: string;
  finalizeEncounter: string;
  cancelEncounter: string;
  finalizePending: string;
  cancelPending: string;
  finalizeSuccess: string;
  cancelSuccess: string;
  finalizeConfirmTitle: string;
  finalizeConfirmBody: string;
  finalizeConfirmAction: string;
  finalizeConfirmCancel: string;
  cancelConfirmTitle: string;
  cancelConfirmBody: string;
  cancelConfirmAction: string;
  cancelConfirmCancel: string;
  summarySectionKeyLabel: string;
  summaryContentKeyLabel: string;
  summaryClinicianTextLabel: string;
  summaryClinicianNoteLabel: string;
  validationSectionKeyRequired: string;
  validationSummaryTextRequired: string;
  finalizeValidation: string;
  mutationErrors: EncounterMutationErrorLabels;
};

type EncounterTerminalActionsProps = {
  encounterId: string;
  accessToken: string;
  detail: ClinicalEncounterDetail;
  labels: EncounterTerminalLabels;
  onRefresh: () => Promise<void>;
  onDetailUpdated: (detail: ClinicalEncounterDetail) => void;
  onUnauthorized: () => void;
  onStatusMessage: (message: string | null) => void;
};

function inputClassName(): string {
  return "mt-1 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-text-primary shadow-sm";
}

export function EncounterTerminalActions({
  encounterId,
  accessToken,
  detail,
  labels,
  onRefresh,
  onDetailUpdated,
  onUnauthorized,
  onStatusMessage,
}: EncounterTerminalActionsProps) {
  const isActive = detail.encounter.status === "active";
  const formId = useId();

  const [showFinalizeConfirm, setShowFinalizeConfirm] = useState(false);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const [pending, setPending] = useState<"finalize" | "cancel" | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const [sectionKey, setSectionKey] = useState("assessment");
  const [contentKey, setContentKey] = useState("");
  const [clinicianText, setClinicianText] = useState("");
  const [clinicianNote, setClinicianNote] = useState("");

  const handleTerminalError = useCallback(
    async (err: unknown, validationMessage: string) => {
      if (err instanceof ApiClientError && err.status === 401) {
        onUnauthorized();
        return;
      }
      if (err instanceof ApiClientError && err.status === 409) {
        await onRefresh();
        onStatusMessage(labels.mutationErrors.conflictStale);
        setShowFinalizeConfirm(false);
        setShowCancelConfirm(false);
        return;
      }
      if (err instanceof ApiClientError && (err.status === 400 || err.status === 422)) {
        onStatusMessage(validationMessage);
        return;
      }
      onStatusMessage(resolveEncounterMutationErrorMessage(err, labels.mutationErrors));
    },
    [labels.mutationErrors, onRefresh, onStatusMessage, onUnauthorized],
  );

  const submitFinalize = useCallback(async () => {
    if (!isActive || pending) {
      return;
    }
    const key = sectionKey.trim();
    const text = clinicianText.trim();
    if (!key) {
      setFormError(labels.validationSectionKeyRequired);
      return;
    }
    if (!text) {
      setFormError(labels.validationSummaryTextRequired);
      return;
    }
    setFormError(null);
    setPending("finalize");
    onStatusMessage(null);

    const body: FinalizeClinicalEncounterBody = {
      expected_version: detail.encounter.version,
      summary_sections: [
        {
          section_key: key,
          ...(contentKey.trim() ? { content_key: contentKey.trim() } : {}),
          clinician_text: text,
        },
      ],
    };
    const noteTrim = clinicianNote.trim();
    if (noteTrim) {
      body.clinician_note = noteTrim;
    }

    try {
      const updated = await finalizeClinicalEncounter(accessToken, encounterId, body);
      onDetailUpdated(updated);
      setShowFinalizeConfirm(false);
      setSectionKey("assessment");
      setContentKey("");
      setClinicianText("");
      setClinicianNote("");
      onStatusMessage(labels.finalizeSuccess);
    } catch (err) {
      await handleTerminalError(err, labels.finalizeValidation);
    } finally {
      setPending(null);
    }
  }, [
    accessToken,
    clinicianNote,
    clinicianText,
    contentKey,
    detail.encounter.version,
    encounterId,
    handleTerminalError,
    isActive,
    labels.finalizeSuccess,
    labels.finalizeValidation,
    labels.validationSectionKeyRequired,
    labels.validationSummaryTextRequired,
    onDetailUpdated,
    onStatusMessage,
    pending,
    sectionKey,
  ]);

  const submitCancel = useCallback(async () => {
    if (!isActive || pending) {
      return;
    }
    setPending("cancel");
    onStatusMessage(null);

    try {
      await cancelClinicalEncounter(accessToken, encounterId, {
        expected_version: detail.encounter.version,
      });
      await onRefresh();
      setShowCancelConfirm(false);
      onStatusMessage(labels.cancelSuccess);
    } catch (err) {
      await handleTerminalError(err, labels.mutationErrors.validation);
    } finally {
      setPending(null);
    }
  }, [
    accessToken,
    detail.encounter.version,
    encounterId,
    handleTerminalError,
    isActive,
    labels.cancelSuccess,
    labels.mutationErrors.validation,
    onRefresh,
    onStatusMessage,
    pending,
  ]);

  if (!isActive) {
    return null;
  }

  const actionsLocked = pending !== null;

  return (
    <section aria-labelledby="enc-terminal-heading" className="space-y-4">
      <h2 id="enc-terminal-heading" className="text-lg font-semibold text-text-primary">
        {labels.sectionHeading}
      </h2>

      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
        <Button
          type="button"
          size="md"
          disabled={actionsLocked}
          aria-busy={pending === "finalize"}
          onClick={() => {
            setShowCancelConfirm(false);
            setShowFinalizeConfirm(true);
            setFormError(null);
          }}
        >
          {labels.finalizeEncounter}
        </Button>
        <Button
          type="button"
          size="md"
          variant="secondary"
          className="border-red-300 text-red-900 hover:bg-red-50"
          disabled={actionsLocked}
          aria-busy={pending === "cancel"}
          onClick={() => {
            setShowFinalizeConfirm(false);
            setShowCancelConfirm(true);
            setFormError(null);
          }}
        >
          {labels.cancelEncounter}
        </Button>
      </div>

      {showFinalizeConfirm ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby={`${formId}-finalize-title`}
          className="max-w-xl space-y-4 rounded-xl border border-border bg-white p-4 shadow-sm"
        >
          <h3 id={`${formId}-finalize-title`} className="text-base font-semibold text-text-primary">
            {labels.finalizeConfirmTitle}
          </h3>
          <p className="text-sm text-text-secondary">{labels.finalizeConfirmBody}</p>
          <form
            className="space-y-3"
            onSubmit={(event) => {
              event.preventDefault();
              void submitFinalize();
            }}
          >
            <div>
              <label htmlFor={`${formId}-section-key`} className="text-sm font-medium text-text-primary">
                {labels.summarySectionKeyLabel}
              </label>
              <input
                id={`${formId}-section-key`}
                className={inputClassName()}
                maxLength={64}
                value={sectionKey}
                onChange={(e) => setSectionKey(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor={`${formId}-content-key`} className="text-sm font-medium text-text-primary">
                {labels.summaryContentKeyLabel}
              </label>
              <input
                id={`${formId}-content-key`}
                className={inputClassName()}
                maxLength={128}
                value={contentKey}
                onChange={(e) => setContentKey(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor={`${formId}-clinician-text`} className="text-sm font-medium text-text-primary">
                {labels.summaryClinicianTextLabel}
              </label>
              <textarea
                id={`${formId}-clinician-text`}
                className={inputClassName()}
                maxLength={4000}
                rows={4}
                value={clinicianText}
                onChange={(e) => setClinicianText(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor={`${formId}-clinician-note`} className="text-sm font-medium text-text-primary">
                {labels.summaryClinicianNoteLabel}
              </label>
              <textarea
                id={`${formId}-clinician-note`}
                className={inputClassName()}
                maxLength={4000}
                rows={2}
                value={clinicianNote}
                onChange={(e) => setClinicianNote(e.target.value)}
              />
            </div>
            {formError ? (
              <p className="text-sm text-red-800" role="alert">
                {formError}
              </p>
            ) : null}
            <div className="flex flex-col gap-2 sm:flex-row">
              <Button type="submit" size="sm" disabled={actionsLocked} aria-busy={pending === "finalize"}>
                {pending === "finalize" ? labels.finalizePending : labels.finalizeConfirmAction}
              </Button>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                disabled={actionsLocked}
                onClick={() => setShowFinalizeConfirm(false)}
              >
                {labels.finalizeConfirmCancel}
              </Button>
            </div>
          </form>
        </div>
      ) : null}

      {showCancelConfirm ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby={`${formId}-cancel-title`}
          className="max-w-xl space-y-4 rounded-xl border border-red-200 bg-red-50/50 p-4"
        >
          <h3 id={`${formId}-cancel-title`} className="text-base font-semibold text-text-primary">
            {labels.cancelConfirmTitle}
          </h3>
          <p className="text-sm text-text-secondary">{labels.cancelConfirmBody}</p>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button
              type="button"
              size="sm"
              className="border-red-300 bg-red-700 text-white hover:bg-red-800"
              disabled={actionsLocked}
              aria-busy={pending === "cancel"}
              onClick={() => void submitCancel()}
            >
              {pending === "cancel" ? labels.cancelPending : labels.cancelConfirmAction}
            </Button>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              disabled={actionsLocked}
              onClick={() => setShowCancelConfirm(false)}
            >
              {labels.cancelConfirmCancel}
            </Button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
