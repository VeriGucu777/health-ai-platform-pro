"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import {
  fetchPatientConsents,
  grantPatientConsent,
  revokePatientConsent,
  type PatientConsent,
} from "@/lib/api/consents";
import { createPatient, type Patient, type PatientCreatePayload } from "@/lib/api/patients";
import { resolveManagementErrorMessage } from "@/lib/management/error-messages";
import {
  buildGenderOptions,
  isPatientGenderValue,
  type PatientGenderValue,
} from "@/lib/management/patient-gender";
import { useLocale } from "@/lib/i18n/use-locale";

type PatientOnboardingPanelProps = {
  accessToken: string;
  selectedPatientId: string;
  onPatientCreated: (patient: Patient) => void | Promise<void>;
  onConsentChanged: () => void;
};

function sectionCardClassName(): string {
  return "rounded-xl border border-border bg-white p-4 sm:p-5";
}

function buildDefaultForm(onboarding: {
  demoNotesDefault: string;
}): PatientCreatePayload {
  return {
    first_name: "Demo",
    last_name: "Pilot Patient",
    date_of_birth: "1992-04-15",
    gender: "female",
    phone: null,
    notes: onboarding.demoNotesDefault,
  };
}

export function PatientOnboardingPanel({
  accessToken,
  selectedPatientId,
  onPatientCreated,
  onConsentChanged,
}: PatientOnboardingPanelProps) {
  const { content, formatDateTime } = useLocale();
  const onboarding = content.management.onboarding;

  const defaultForm = useMemo(
    () => buildDefaultForm(onboarding),
    [onboarding.demoNotesDefault],
  );

  const genderOptions = useMemo(
    () =>
      buildGenderOptions({
        female: onboarding.genderOptions.female,
        male: onboarding.genderOptions.male,
        other: onboarding.genderOptions.other,
      }),
    [onboarding.genderOptions.female, onboarding.genderOptions.male, onboarding.genderOptions.other],
  );

  const [form, setForm] = useState<PatientCreatePayload>(() => ({ ...defaultForm }));
  const [grantConsentOnCreate, setGrantConsentOnCreate] = useState(true);
  const [submitPending, setSubmitPending] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);
  const [submitWarning, setSubmitWarning] = useState<string | null>(null);

  const [consents, setConsents] = useState<PatientConsent[]>([]);
  const [consentsLoading, setConsentsLoading] = useState(false);
  const [consentsError, setConsentsError] = useState<string | null>(null);
  const [consentActionPending, setConsentActionPending] = useState(false);
  const createInFlightRef = useRef(false);
  const createSuccessRef = useRef<HTMLParagraphElement>(null);

  useEffect(() => {
    setForm((current) => ({
      ...current,
      notes: current.notes === defaultForm.notes || !current.notes?.trim()
        ? defaultForm.notes
        : current.notes,
    }));
  }, [defaultForm.notes]);

  const loadConsents = useCallback(async () => {
    if (!accessToken || !selectedPatientId) {
      setConsents([]);
      setConsentsError(null);
      return;
    }

    setConsentsLoading(true);
    setConsentsError(null);

    try {
      const response = await fetchPatientConsents(accessToken, selectedPatientId);
      setConsents(response.items);
    } catch (err) {
      const resolved = resolveManagementErrorMessage(err, content.management.errors);
      setConsentsError(resolved.message);
      setConsents([]);
    } finally {
      setConsentsLoading(false);
    }
  }, [accessToken, content.management.errors, selectedPatientId]);

  useEffect(() => {
    void loadConsents();
  }, [loadConsents]);

  const activeGranted = consents.find(
    (row) => row.status === "granted" && row.consent_type === "clinical_data_processing",
  );

  const genderValue: PatientGenderValue = isPatientGenderValue(form.gender)
    ? form.gender
    : "female";

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (submitPending || createInFlightRef.current) {
      return;
    }

    createInFlightRef.current = true;
    setSubmitPending(true);
    setSubmitError(null);
    setSubmitSuccess(null);
    setSubmitWarning(null);

    try {
      const patient = await createPatient(accessToken, {
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        date_of_birth: form.date_of_birth,
        gender: genderValue,
        phone: form.phone?.trim() || null,
        notes: form.notes?.trim() || null,
        is_active: true,
      });

      setSubmitSuccess(onboarding.createSuccess);
      await onPatientCreated(patient);

      if (grantConsentOnCreate) {
        try {
          await grantPatientConsent(accessToken, patient.id);
          onConsentChanged();
        } catch (consentErr) {
          const resolved = resolveManagementErrorMessage(
            consentErr,
            content.management.errors,
          );
          setSubmitWarning(onboarding.consentGrantFailedWarning);
          if (resolved.status !== 409) {
            setSubmitWarning(`${onboarding.consentGrantFailedWarning} ${resolved.message}`);
          }
        }
      }

      setForm({ ...defaultForm });
      requestAnimationFrame(() => {
        createSuccessRef.current?.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
      });
    } catch (err) {
      const resolved = resolveManagementErrorMessage(err, content.management.errors);
      setSubmitError(resolved.message);
    } finally {
      createInFlightRef.current = false;
      setSubmitPending(false);
    }
  };

  const handleGrantConsent = async () => {
    if (!selectedPatientId) {
      return;
    }
    setConsentActionPending(true);
    setConsentsError(null);
    try {
      await grantPatientConsent(accessToken, selectedPatientId);
      await loadConsents();
      onConsentChanged();
    } catch (err) {
      const resolved = resolveManagementErrorMessage(err, content.management.errors);
      setConsentsError(resolved.message);
    } finally {
      setConsentActionPending(false);
    }
  };

  const handleRevokeConsent = async (consentId: string) => {
    if (!selectedPatientId) {
      return;
    }
    setConsentActionPending(true);
    setConsentsError(null);
    try {
      await revokePatientConsent(accessToken, selectedPatientId, consentId);
      await loadConsents();
      onConsentChanged();
    } catch (err) {
      const resolved = resolveManagementErrorMessage(err, content.management.errors);
      setConsentsError(resolved.message);
    } finally {
      setConsentActionPending(false);
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <section className={sectionCardClassName()} aria-labelledby="mgmt-onboard-create-heading">
        <h2 id="mgmt-onboard-create-heading" className="text-lg font-semibold text-text-primary">
          {onboarding.createSection}
        </h2>
        <p className="mt-1 text-sm text-text-secondary">{onboarding.createHint}</p>

        <div aria-live="polite" aria-atomic="true" className="mt-3 empty:hidden">
          {submitSuccess ? (
            <p
              ref={createSuccessRef}
              className="rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-900"
              role="status"
            >
              {submitSuccess}
            </p>
          ) : null}
        </div>
        {submitWarning ? (
          <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950" role="status">
            {submitWarning}
          </p>
        ) : null}
        {submitError ? (
          <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900" role="alert">
            {submitError}
          </p>
        ) : null}

        <form className="mt-4 space-y-3" onSubmit={(event) => void handleSubmit(event)}>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium text-text-secondary">{onboarding.firstName}</span>
              <input
                required
                maxLength={100}
                className="min-h-11 rounded-lg border border-border px-3 py-2"
                value={form.first_name}
                onChange={(event) => setForm((prev) => ({ ...prev, first_name: event.target.value }))}
                disabled={submitPending}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium text-text-secondary">{onboarding.lastName}</span>
              <input
                required
                maxLength={100}
                className="min-h-11 rounded-lg border border-border px-3 py-2"
                value={form.last_name}
                onChange={(event) => setForm((prev) => ({ ...prev, last_name: event.target.value }))}
                disabled={submitPending}
              />
            </label>
          </div>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-text-secondary">{onboarding.dateOfBirth}</span>
            <input
              required
              type="date"
              className="min-h-11 rounded-lg border border-border px-3 py-2"
              value={form.date_of_birth}
              onChange={(event) => setForm((prev) => ({ ...prev, date_of_birth: event.target.value }))}
              disabled={submitPending}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-text-secondary">{onboarding.gender}</span>
            <select
              required
              className="min-h-11 rounded-lg border border-border bg-white px-3 py-2 text-text-primary"
              value={genderValue}
              onChange={(event) => {
                const next = event.target.value;
                if (isPatientGenderValue(next)) {
                  setForm((prev) => ({ ...prev, gender: next }));
                }
              }}
              disabled={submitPending}
            >
              {genderOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-text-secondary">{onboarding.phoneOptional}</span>
            <input
              maxLength={32}
              className="min-h-11 rounded-lg border border-border px-3 py-2"
              value={form.phone ?? ""}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, phone: event.target.value || null }))
              }
              disabled={submitPending}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-text-secondary">{onboarding.notesOptional}</span>
            <textarea
              rows={2}
              className="rounded-lg border border-border px-3 py-2"
              value={form.notes ?? ""}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, notes: event.target.value || null }))
              }
              disabled={submitPending}
            />
          </label>
          <label className="flex items-start gap-2 text-sm text-text-primary">
            <input
              type="checkbox"
              checked={grantConsentOnCreate}
              onChange={(event) => setGrantConsentOnCreate(event.target.checked)}
              disabled={submitPending}
              className="mt-1"
            />
            <span>{onboarding.grantConsentOnCreate}</span>
          </label>
          <Button type="submit" disabled={submitPending} aria-busy={submitPending}>
            {submitPending ? onboarding.submitting : onboarding.submitCreate}
          </Button>
        </form>
      </section>

      <section className={sectionCardClassName()} aria-labelledby="mgmt-onboard-consent-heading">
        <h2 id="mgmt-onboard-consent-heading" className="text-lg font-semibold text-text-primary">
          {onboarding.consentSection}
        </h2>
        <p className="mt-1 text-sm text-text-secondary">{onboarding.consentHint}</p>

        {!selectedPatientId ? (
          <p className="mt-4 text-sm text-text-secondary">{onboarding.selectPatientForConsent}</p>
        ) : consentsLoading ? (
          <p className="mt-4 text-sm text-text-secondary">{content.common.loading}</p>
        ) : (
          <>
            {consentsError ? (
              <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900" role="alert">
                {consentsError}
              </p>
            ) : null}

            <p className="mt-4 text-sm text-text-primary">
              {activeGranted
                ? onboarding.consentStatusGranted
                : onboarding.consentStatusNotGranted}
            </p>

            <div className="mt-3 flex flex-wrap gap-2">
              {!activeGranted ? (
                <Button
                  type="button"
                  size="sm"
                  disabled={consentActionPending}
                  onClick={() => void handleGrantConsent()}
                >
                  {onboarding.grantConsent}
                </Button>
              ) : (
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  disabled={consentActionPending}
                  onClick={() => void handleRevokeConsent(activeGranted.id)}
                >
                  {onboarding.revokeConsent}
                </Button>
              )}
            </div>

            {consents.length > 0 ? (
              <ul className="mt-4 space-y-2 text-sm">
                {consents.map((row) => (
                  <li
                    key={row.id}
                    className="rounded-lg border border-border px-3 py-2 text-text-secondary"
                  >
                    <span className="font-medium text-text-primary">
                      {onboarding.consentTypes[row.consent_type] ?? row.consent_type}
                    </span>
                    {" · "}
                    {onboarding.consentStatuses[row.status] ?? row.status}
                    {" · v"}
                    {row.version}
                    {" · "}
                    {formatDateTime(row.granted_at)}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 text-sm text-text-secondary">{onboarding.noConsentHistory}</p>
            )}
          </>
        )}
      </section>
    </div>
  );
}
