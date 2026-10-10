"use client";

import { useCallback, useId, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ApiClientError } from "@/lib/api/client";
import {
  addEncounterComplaint,
  addEncounterFinding,
  deactivateEncounterComplaint,
  type ClinicalEncounterDetail,
  type ClinicalInputSource,
  type EncounterComplaintCreateBody,
  type EncounterFindingCreateBody,
  type EncounterQuestionResponseUpsertBody,
  type FindingType,
  type QuestionAnswerType,
  upsertEncounterQuestionResponse,
} from "@/lib/api/clinical-encounters";
import {
  resolveEncounterMutationErrorMessage,
  type EncounterMutationErrorLabels,
} from "@/lib/clinical-encounters/mutation-errors";
import {
  isComplaintInputValid,
  parseOptionalFiniteNumber,
} from "@/lib/clinical-encounters/validation";

export type EncounterWorkspaceLabels = {
  recordsHeading: string;
  complaintsHeading: string;
  findingsHeading: string;
  responsesHeading: string;
  complaintsEmpty: string;
  findingsEmpty: string;
  responsesEmpty: string;
  readOnlyFinalized: string;
  readOnlyCancelled: string;
  readOnlyDraft: string;
  primaryBadge: string;
  negatedBadge: string;
  recordedAt: string;
  complaintKeyLabel: string;
  complaintKeyHint: string;
  complaintTextLabel: string;
  complaintPrimaryLabel: string;
  complaintNegatedLabel: string;
  addComplaint: string;
  addComplaintPending: string;
  complaintSuccess: string;
  removeComplaint: string;
  removeComplaintConfirm: string;
  removeComplaintPending: string;
  removeComplaintSuccess: string;
  primaryComplaintHint: string;
  findingTypeLabel: string;
  findingKeyLabel: string;
  findingKeyHint: string;
  findingValueCodeLabel: string;
  findingValueNumericLabel: string;
  findingUnitLabel: string;
  findingNegatedLabel: string;
  findingSourceLabel: string;
  addFinding: string;
  addFindingPending: string;
  findingSuccess: string;
  questionKeyLabel: string;
  questionKeyHint: string;
  answerTypeLabel: string;
  answerCodeLabel: string;
  answerNumericLabel: string;
  clinicianNoteLabel: string;
  booleanYes: string;
  booleanNo: string;
  booleanUnknown: string;
  saveResponse: string;
  saveResponsePending: string;
  responseSuccess: string;
  validationComplaintRequired: string;
  validationFindingKeyRequired: string;
  validationNumericInvalid: string;
  validationQuestionKeyRequired: string;
  validationAnswerRequired: string;
  validationNoteRequired: string;
  findingTypes: Record<string, string>;
  findingSources: Record<string, string>;
  answerTypes: Record<string, string>;
  mutationErrors: EncounterMutationErrorLabels;
};

type Props = {
  encounterId: string;
  accessToken: string;
  detail: ClinicalEncounterDetail;
  labels: EncounterWorkspaceLabels;
  formatDateTime: (value: string) => string;
  onRefresh: () => Promise<void>;
  onUnauthorized: () => void;
  onStatusMessage: (message: string | null) => void;
};

const FINDING_TYPES: FindingType[] = [
  "symptom",
  "physical_exam",
  "history_item",
  "risk_factor",
  "negative_finding",
  "other",
];

const FINDING_SOURCES: ClinicalInputSource[] = [
  "patient_reported",
  "clinician_observed",
  "historical_record",
  "device",
  "other",
];

const ANSWER_TYPES: QuestionAnswerType[] = ["boolean", "single_choice", "number", "text"];

function inputClassName(): string {
  return "mt-1 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-text-primary shadow-sm";
}

function handleMutationFailure(
  err: unknown,
  mutationErrors: EncounterMutationErrorLabels,
  onUnauthorized: () => void,
  onRefresh: () => Promise<void>,
  onStatusMessage: (message: string | null) => void,
): void {
  if (err instanceof ApiClientError && err.status === 401) {
    onUnauthorized();
    return;
  }
  if (err instanceof ApiClientError && err.status === 409) {
    void onRefresh();
    onStatusMessage(mutationErrors.conflictStale);
    return;
  }
  onStatusMessage(resolveEncounterMutationErrorMessage(err, mutationErrors));
}

export function EncounterDetailWriteWorkspace({
  encounterId,
  accessToken,
  detail,
  labels,
  formatDateTime,
  onRefresh,
  onUnauthorized,
  onStatusMessage,
}: Props) {
  const isWritable = detail.encounter.status === "active";
  const mutationErrors = labels.mutationErrors;

  const [complaintKey, setComplaintKey] = useState("");
  const [complaintText, setComplaintText] = useState("");
  const [complaintPrimary, setComplaintPrimary] = useState(false);
  const [complaintNegated, setComplaintNegated] = useState(false);
  const [complaintPending, setComplaintPending] = useState(false);
  const [complaintFieldError, setComplaintFieldError] = useState<string | null>(null);
  const [deactivatePendingId, setDeactivatePendingId] = useState<string | null>(null);

  const [findingType, setFindingType] = useState<FindingType>("symptom");
  const [findingKey, setFindingKey] = useState("");
  const [findingValueCode, setFindingValueCode] = useState("");
  const [findingValueNumeric, setFindingValueNumeric] = useState("");
  const [findingUnit, setFindingUnit] = useState("");
  const [findingNegated, setFindingNegated] = useState(false);
  const [findingSource, setFindingSource] = useState<ClinicalInputSource>("clinician_observed");
  const [findingPending, setFindingPending] = useState(false);
  const [findingFieldError, setFindingFieldError] = useState<string | null>(null);

  const [questionKey, setQuestionKey] = useState("");
  const [answerType, setAnswerType] = useState<QuestionAnswerType>("boolean");
  const [booleanCode, setBooleanCode] = useState<"yes" | "no" | "unknown">("yes");
  const [singleChoiceCode, setSingleChoiceCode] = useState("");
  const [answerNumericRaw, setAnswerNumericRaw] = useState("");
  const [clinicianNote, setClinicianNote] = useState("");
  const [responsePending, setResponsePending] = useState(false);
  const [responseFieldError, setResponseFieldError] = useState<string | null>(null);

  const complaintFormId = useId();
  const findingFormId = useId();
  const responseFormId = useId();

  const submitComplaint = useCallback(async () => {
    if (!isWritable || complaintPending) {
      return;
    }
    if (!isComplaintInputValid(complaintKey, complaintText)) {
      setComplaintFieldError(labels.validationComplaintRequired);
      return;
    }
    setComplaintFieldError(null);
    setComplaintPending(true);
    onStatusMessage(null);

    const body: EncounterComplaintCreateBody = {
      is_primary: complaintPrimary,
      negated: complaintNegated,
    };
    const keyTrim = complaintKey.trim();
    const textTrim = complaintText.trim();
    if (keyTrim) {
      body.complaint_key = keyTrim;
    }
    if (textTrim) {
      body.clinician_display_text = textTrim;
    }

    try {
      await addEncounterComplaint(accessToken, encounterId, body);
      await onRefresh();
      setComplaintKey("");
      setComplaintText("");
      setComplaintPrimary(false);
      setComplaintNegated(false);
      onStatusMessage(labels.complaintSuccess);
    } catch (err) {
      handleMutationFailure(err, mutationErrors, onUnauthorized, onRefresh, onStatusMessage);
    } finally {
      setComplaintPending(false);
    }
  }, [
    accessToken,
    complaintKey,
    complaintNegated,
    complaintPending,
    complaintPrimary,
    complaintText,
    encounterId,
    isWritable,
    labels.complaintSuccess,
    labels.validationComplaintRequired,
    mutationErrors,
    onRefresh,
    onStatusMessage,
    onUnauthorized,
  ]);

  const deactivateComplaint = useCallback(
    async (complaintId: string) => {
      if (!isWritable || deactivatePendingId) {
        return;
      }
      if (!window.confirm(labels.removeComplaintConfirm)) {
        return;
      }
      setDeactivatePendingId(complaintId);
      onStatusMessage(null);
      try {
        await deactivateEncounterComplaint(accessToken, encounterId, complaintId);
        await onRefresh();
        onStatusMessage(labels.removeComplaintSuccess);
      } catch (err) {
        handleMutationFailure(err, mutationErrors, onUnauthorized, onRefresh, onStatusMessage);
      } finally {
        setDeactivatePendingId(null);
      }
    },
    [
      accessToken,
      deactivatePendingId,
      encounterId,
      isWritable,
      labels.removeComplaintConfirm,
      labels.removeComplaintSuccess,
      mutationErrors,
      onRefresh,
      onStatusMessage,
      onUnauthorized,
    ],
  );

  const submitFinding = useCallback(async () => {
    if (!isWritable || findingPending) {
      return;
    }
    if (!findingKey.trim()) {
      setFindingFieldError(labels.validationFindingKeyRequired);
      return;
    }
    const numeric = parseOptionalFiniteNumber(findingValueNumeric);
    if (findingValueNumeric.trim() && numeric === null) {
      setFindingFieldError(labels.validationNumericInvalid);
      return;
    }
    setFindingFieldError(null);
    setFindingPending(true);
    onStatusMessage(null);

    const body: EncounterFindingCreateBody = {
      finding_type: findingType,
      finding_key: findingKey.trim(),
      negated: findingNegated,
      source: findingSource,
    };
    const codeTrim = findingValueCode.trim();
    if (codeTrim) {
      body.value_code = codeTrim;
    }
    if (numeric !== null) {
      body.value_numeric = numeric;
    }
    const unitTrim = findingUnit.trim();
    if (unitTrim) {
      body.unit = unitTrim;
    }

    try {
      await addEncounterFinding(accessToken, encounterId, body);
      await onRefresh();
      setFindingKey("");
      setFindingValueCode("");
      setFindingValueNumeric("");
      setFindingUnit("");
      setFindingNegated(false);
      onStatusMessage(labels.findingSuccess);
    } catch (err) {
      handleMutationFailure(err, mutationErrors, onUnauthorized, onRefresh, onStatusMessage);
    } finally {
      setFindingPending(false);
    }
  }, [
    accessToken,
    encounterId,
    findingKey,
    findingNegated,
    findingPending,
    findingSource,
    findingType,
    findingUnit,
    findingValueCode,
    findingValueNumeric,
    isWritable,
    labels.findingSuccess,
    labels.validationFindingKeyRequired,
    labels.validationNumericInvalid,
    mutationErrors,
    onRefresh,
    onStatusMessage,
    onUnauthorized,
  ]);

  const submitResponse = useCallback(async () => {
    if (!isWritable || responsePending) {
      return;
    }
    const qk = questionKey.trim();
    if (!qk) {
      setResponseFieldError(labels.validationQuestionKeyRequired);
      return;
    }

    const body: EncounterQuestionResponseUpsertBody = { answer_type: answerType };

    if (answerType === "boolean") {
      body.answer_code = booleanCode;
    } else if (answerType === "single_choice") {
      const code = singleChoiceCode.trim();
      if (!code) {
        setResponseFieldError(labels.validationAnswerRequired);
        return;
      }
      body.answer_code = code;
    } else if (answerType === "number") {
      const numeric = parseOptionalFiniteNumber(answerNumericRaw);
      if (numeric === null) {
        setResponseFieldError(labels.validationNumericInvalid);
        return;
      }
      body.answer_numeric = numeric;
    } else if (answerType === "text") {
      const note = clinicianNote.trim();
      if (!note) {
        setResponseFieldError(labels.validationNoteRequired);
        return;
      }
      body.clinician_note = note;
    }

    setResponseFieldError(null);
    setResponsePending(true);
    onStatusMessage(null);

    try {
      await upsertEncounterQuestionResponse(accessToken, encounterId, qk, body);
      await onRefresh();
      setQuestionKey("");
      setSingleChoiceCode("");
      setAnswerNumericRaw("");
      setClinicianNote("");
      onStatusMessage(labels.responseSuccess);
    } catch (err) {
      handleMutationFailure(err, mutationErrors, onUnauthorized, onRefresh, onStatusMessage);
    } finally {
      setResponsePending(false);
    }
  }, [
    accessToken,
    answerNumericRaw,
    answerType,
    booleanCode,
    clinicianNote,
    encounterId,
    isWritable,
    labels.responseSuccess,
    labels.validationAnswerRequired,
    labels.validationNoteRequired,
    labels.validationNumericInvalid,
    labels.validationQuestionKeyRequired,
    mutationErrors,
    onRefresh,
    onStatusMessage,
    onUnauthorized,
    questionKey,
    responsePending,
    singleChoiceCode,
  ]);

  const readOnlyBanner =
    detail.encounter.status === "finalized"
      ? labels.readOnlyFinalized
      : detail.encounter.status === "cancelled"
        ? labels.readOnlyCancelled
        : detail.encounter.status !== "active"
          ? labels.readOnlyDraft
          : null;

  return (
    <div className="space-y-10">
      <h2 className="text-lg font-semibold text-text-primary">{labels.recordsHeading}</h2>

      {readOnlyBanner ? (
        <p
          className="rounded-lg border border-border bg-slate-50 px-4 py-3 text-sm text-text-secondary"
          role="status"
        >
          {readOnlyBanner}
        </p>
      ) : null}

      <section aria-labelledby="enc-complaints-heading" className="space-y-4">
        <h3 id="enc-complaints-heading" className="text-base font-semibold text-text-primary">
          {labels.complaintsHeading}
        </h3>
        {detail.complaints.length === 0 ? (
          <p className="text-sm text-text-secondary">{labels.complaintsEmpty}</p>
        ) : (
          <ul className="space-y-2">
            {detail.complaints.map((item) => (
              <li
                key={item.id}
                className="flex flex-col gap-2 rounded-lg border border-border bg-white px-4 py-3 text-sm sm:flex-row sm:items-start sm:justify-between"
              >
                <div className="min-w-0 text-text-secondary">
                  <p className="font-medium text-text-primary">
                    {item.clinician_display_text ?? item.complaint_key ?? "—"}
                  </p>
                  {item.complaint_key && item.clinician_display_text ? (
                    <p className="mt-1 text-xs text-text-secondary">{item.complaint_key}</p>
                  ) : null}
                  <p className="mt-1 text-xs">
                    {labels.recordedAt}: {formatDateTime(item.recorded_at)}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {item.is_primary ? (
                      <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-800">
                        {labels.primaryBadge}
                      </span>
                    ) : null}
                    {item.negated ? (
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-text-secondary">
                        {labels.negatedBadge}
                      </span>
                    ) : null}
                  </div>
                </div>
                {isWritable ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    disabled={deactivatePendingId === item.id}
                    aria-busy={deactivatePendingId === item.id}
                    onClick={() => void deactivateComplaint(item.id)}
                  >
                    {deactivatePendingId === item.id ? labels.removeComplaintPending : labels.removeComplaint}
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        )}

        {isWritable ? (
          <form
            id={complaintFormId}
            className="max-w-xl space-y-4 rounded-xl border border-border bg-slate-50/80 p-4"
            onSubmit={(event) => {
              event.preventDefault();
              void submitComplaint();
            }}
          >
            <p className="text-xs text-text-secondary">{labels.primaryComplaintHint}</p>
            <div>
              <label htmlFor={`${complaintFormId}-key`} className="text-sm font-medium text-text-primary">
                {labels.complaintKeyLabel}
              </label>
              <p id={`${complaintFormId}-key-hint`} className="text-xs text-text-secondary">
                {labels.complaintKeyHint}
              </p>
              <input
                id={`${complaintFormId}-key`}
                className={inputClassName()}
                maxLength={128}
                value={complaintKey}
                onChange={(e) => setComplaintKey(e.target.value)}
                aria-describedby={`${complaintFormId}-key-hint`}
              />
            </div>
            <div>
              <label htmlFor={`${complaintFormId}-text`} className="text-sm font-medium text-text-primary">
                {labels.complaintTextLabel}
              </label>
              <textarea
                id={`${complaintFormId}-text`}
                className={inputClassName()}
                maxLength={4000}
                rows={3}
                value={complaintText}
                onChange={(e) => setComplaintText(e.target.value)}
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-text-secondary">
              <input
                type="checkbox"
                checked={complaintPrimary}
                onChange={(e) => setComplaintPrimary(e.target.checked)}
              />
              {labels.complaintPrimaryLabel}
            </label>
            <label className="flex items-center gap-2 text-sm text-text-secondary">
              <input
                type="checkbox"
                checked={complaintNegated}
                onChange={(e) => setComplaintNegated(e.target.checked)}
              />
              {labels.complaintNegatedLabel}
            </label>
            {complaintFieldError ? (
              <p className="text-sm text-red-800" role="alert">
                {complaintFieldError}
              </p>
            ) : null}
            <Button type="submit" size="sm" disabled={complaintPending} aria-busy={complaintPending}>
              {complaintPending ? labels.addComplaintPending : labels.addComplaint}
            </Button>
          </form>
        ) : null}
      </section>

      <section aria-labelledby="enc-findings-heading" className="space-y-4">
        <h3 id="enc-findings-heading" className="text-base font-semibold text-text-primary">
          {labels.findingsHeading}
        </h3>
        {detail.findings.length === 0 ? (
          <p className="text-sm text-text-secondary">{labels.findingsEmpty}</p>
        ) : (
          <ul className="space-y-2">
            {detail.findings.map((item) => (
              <li key={item.id} className="rounded-lg border border-border bg-white px-4 py-3 text-sm text-text-secondary">
                <p className="font-medium text-text-primary">
                  {labels.findingTypes[item.finding_type] ?? item.finding_type}: {item.finding_key}
                </p>
                {item.value_code ? <p>{item.value_code}</p> : null}
                {item.value_numeric != null ? (
                  <p>
                    {item.value_numeric}
                    {item.unit ? ` ${item.unit}` : ""}
                  </p>
                ) : null}
                <p className="mt-1 text-xs">
                  {labels.findingSources[item.source] ?? item.source} · {labels.recordedAt}:{" "}
                  {formatDateTime(item.recorded_at)}
                </p>
                {item.negated ? (
                  <span className="mt-2 inline-block rounded-full bg-slate-100 px-2 py-0.5 text-xs">
                    {labels.negatedBadge}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        )}

        {isWritable ? (
          <form
            id={findingFormId}
            className="max-w-xl space-y-4 rounded-xl border border-border bg-slate-50/80 p-4"
            onSubmit={(event) => {
              event.preventDefault();
              void submitFinding();
            }}
          >
            <div>
              <label htmlFor={`${findingFormId}-type`} className="text-sm font-medium text-text-primary">
                {labels.findingTypeLabel}
              </label>
              <select
                id={`${findingFormId}-type`}
                className={inputClassName()}
                value={findingType}
                onChange={(e) => setFindingType(e.target.value as FindingType)}
              >
                {FINDING_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {labels.findingTypes[type] ?? type}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor={`${findingFormId}-key`} className="text-sm font-medium text-text-primary">
                {labels.findingKeyLabel}
              </label>
              <p id={`${findingFormId}-key-hint`} className="text-xs text-text-secondary">
                {labels.findingKeyHint}
              </p>
              <input
                id={`${findingFormId}-key`}
                className={inputClassName()}
                maxLength={128}
                value={findingKey}
                onChange={(e) => setFindingKey(e.target.value)}
                aria-describedby={`${findingFormId}-key-hint`}
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor={`${findingFormId}-code`} className="text-sm font-medium text-text-primary">
                  {labels.findingValueCodeLabel}
                </label>
                <input
                  id={`${findingFormId}-code`}
                  className={inputClassName()}
                  maxLength={128}
                  value={findingValueCode}
                  onChange={(e) => setFindingValueCode(e.target.value)}
                />
              </div>
              <div>
                <label htmlFor={`${findingFormId}-num`} className="text-sm font-medium text-text-primary">
                  {labels.findingValueNumericLabel}
                </label>
                <input
                  id={`${findingFormId}-num`}
                  className={inputClassName()}
                  inputMode="decimal"
                  value={findingValueNumeric}
                  onChange={(e) => setFindingValueNumeric(e.target.value)}
                />
              </div>
            </div>
            <div>
              <label htmlFor={`${findingFormId}-unit`} className="text-sm font-medium text-text-primary">
                {labels.findingUnitLabel}
              </label>
              <input
                id={`${findingFormId}-unit`}
                className={inputClassName()}
                maxLength={32}
                value={findingUnit}
                onChange={(e) => setFindingUnit(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor={`${findingFormId}-source`} className="text-sm font-medium text-text-primary">
                {labels.findingSourceLabel}
              </label>
              <select
                id={`${findingFormId}-source`}
                className={inputClassName()}
                value={findingSource}
                onChange={(e) => setFindingSource(e.target.value as ClinicalInputSource)}
              >
                {FINDING_SOURCES.map((source) => (
                  <option key={source} value={source}>
                    {labels.findingSources[source] ?? source}
                  </option>
                ))}
              </select>
            </div>
            <label className="flex items-center gap-2 text-sm text-text-secondary">
              <input
                type="checkbox"
                checked={findingNegated}
                onChange={(e) => setFindingNegated(e.target.checked)}
              />
              {labels.findingNegatedLabel}
            </label>
            {findingFieldError ? (
              <p className="text-sm text-red-800" role="alert">
                {findingFieldError}
              </p>
            ) : null}
            <Button type="submit" size="sm" disabled={findingPending} aria-busy={findingPending}>
              {findingPending ? labels.addFindingPending : labels.addFinding}
            </Button>
          </form>
        ) : null}
      </section>

      <section aria-labelledby="enc-responses-heading" className="space-y-4">
        <h3 id="enc-responses-heading" className="text-base font-semibold text-text-primary">
          {labels.responsesHeading}
        </h3>
        {detail.question_responses.length === 0 ? (
          <p className="text-sm text-text-secondary">{labels.responsesEmpty}</p>
        ) : (
          <ul className="space-y-2">
            {detail.question_responses.map((item) => (
              <li key={item.id} className="rounded-lg border border-border bg-white px-4 py-3 text-sm text-text-secondary">
                <span className="font-medium text-text-primary">{item.question_key}</span>
                <span className="text-text-secondary">
                  {" "}
                  · {labels.answerTypes[item.answer_type] ?? item.answer_type}
                </span>
                {item.answer_code ? `: ${item.answer_code}` : ""}
                {item.answer_numeric != null ? `: ${item.answer_numeric}` : ""}
                {item.clinician_note ? (
                  <p className="mt-2 whitespace-pre-wrap text-text-secondary">{item.clinician_note}</p>
                ) : null}
              </li>
            ))}
          </ul>
        )}

        {isWritable ? (
          <form
            id={responseFormId}
            className="max-w-xl space-y-4 rounded-xl border border-border bg-slate-50/80 p-4"
            onSubmit={(event) => {
              event.preventDefault();
              void submitResponse();
            }}
          >
            <div>
              <label htmlFor={`${responseFormId}-qk`} className="text-sm font-medium text-text-primary">
                {labels.questionKeyLabel}
              </label>
              <p id={`${responseFormId}-qk-hint`} className="text-xs text-text-secondary">
                {labels.questionKeyHint}
              </p>
              <input
                id={`${responseFormId}-qk`}
                className={inputClassName()}
                maxLength={128}
                value={questionKey}
                onChange={(e) => setQuestionKey(e.target.value)}
                aria-describedby={`${responseFormId}-qk-hint`}
              />
            </div>
            <div>
              <label htmlFor={`${responseFormId}-at`} className="text-sm font-medium text-text-primary">
                {labels.answerTypeLabel}
              </label>
              <select
                id={`${responseFormId}-at`}
                className={inputClassName()}
                value={answerType}
                onChange={(e) => setAnswerType(e.target.value as QuestionAnswerType)}
              >
                {ANSWER_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {labels.answerTypes[type] ?? type}
                  </option>
                ))}
              </select>
            </div>
            {answerType === "boolean" ? (
              <fieldset>
                <legend className="text-sm font-medium text-text-primary">{labels.answerCodeLabel}</legend>
                <div className="mt-2 flex flex-wrap gap-4 text-sm">
                  {(
                    [
                      ["yes", labels.booleanYes],
                      ["no", labels.booleanNo],
                      ["unknown", labels.booleanUnknown],
                    ] as const
                  ).map(([value, label]) => (
                    <label key={value} className="flex items-center gap-2">
                      <input
                        type="radio"
                        name={`${responseFormId}-bool`}
                        checked={booleanCode === value}
                        onChange={() => setBooleanCode(value)}
                      />
                      {label}
                    </label>
                  ))}
                </div>
              </fieldset>
            ) : null}
            {answerType === "single_choice" ? (
              <div>
                <label htmlFor={`${responseFormId}-sc`} className="text-sm font-medium text-text-primary">
                  {labels.answerCodeLabel}
                </label>
                <input
                  id={`${responseFormId}-sc`}
                  className={inputClassName()}
                  maxLength={128}
                  value={singleChoiceCode}
                  onChange={(e) => setSingleChoiceCode(e.target.value)}
                />
              </div>
            ) : null}
            {answerType === "number" ? (
              <div>
                <label htmlFor={`${responseFormId}-num`} className="text-sm font-medium text-text-primary">
                  {labels.answerNumericLabel}
                </label>
                <input
                  id={`${responseFormId}-num`}
                  className={inputClassName()}
                  inputMode="decimal"
                  value={answerNumericRaw}
                  onChange={(e) => setAnswerNumericRaw(e.target.value)}
                />
              </div>
            ) : null}
            {answerType === "text" ? (
              <div>
                <label htmlFor={`${responseFormId}-note`} className="text-sm font-medium text-text-primary">
                  {labels.clinicianNoteLabel}
                </label>
                <textarea
                  id={`${responseFormId}-note`}
                  className={inputClassName()}
                  maxLength={4000}
                  rows={3}
                  value={clinicianNote}
                  onChange={(e) => setClinicianNote(e.target.value)}
                />
              </div>
            ) : null}
            {responseFieldError ? (
              <p className="text-sm text-red-800" role="alert">
                {responseFieldError}
              </p>
            ) : null}
            <Button type="submit" size="sm" disabled={responsePending} aria-busy={responsePending}>
              {responsePending ? labels.saveResponsePending : labels.saveResponse}
            </Button>
          </form>
        ) : null}
      </section>
    </div>
  );
}
