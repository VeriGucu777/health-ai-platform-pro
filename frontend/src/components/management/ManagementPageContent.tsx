"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/Button";
import {
  createPatientAssignment,
  deactivatePatientAssignment,
  fetchPatientAssignments,
  type PatientAssignment,
} from "@/lib/api/assignments";
import {
  fetchMyOrganizationMembership,
  fetchOrganizationDoctors,
  type ClinicAdminMembership,
  type OrganizationDoctorMember,
} from "@/lib/api/organizations";
import { fetchPatients, type Patient } from "@/lib/api/patients";
import { PatientOnboardingPanel } from "@/components/management/PatientOnboardingPanel";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  findDoctorByUserId,
  formatDoctorDisplayName,
  formatDoctorOptionLabel,
  formatPatientListLabel,
} from "@/lib/management/doctor-display";
import { resolveManagementErrorMessage } from "@/lib/management/error-messages";
import { useLocale } from "@/lib/i18n/use-locale";

function sectionCardClassName(): string {
  return "rounded-xl border border-border bg-white p-4 sm:p-5";
}

export function ManagementPageContent() {
  const { accessToken } = useAuth();
  const { content, formatDate, formatDateTime } = useLocale();
  const mgmt = content.management;

  const [membership, setMembership] = useState<ClinicAdminMembership | null>(null);
  const [doctors, setDoctors] = useState<OrganizationDoctorMember[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string>("");
  const [assignments, setAssignments] = useState<PatientAssignment[]>([]);
  const [selectedDoctorId, setSelectedDoctorId] = useState<string>("");
  const [isPrimary, setIsPrimary] = useState(false);

  const [bootstrapLoading, setBootstrapLoading] = useState(true);
  const [bootstrapError, setBootstrapError] = useState<string | null>(null);
  const [assignmentsLoading, setAssignmentsLoading] = useState(false);
  const [assignmentsError, setAssignmentsError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionPending, setActionPending] = useState(false);
  const [patientCreateNotice, setPatientCreateNotice] = useState<string | null>(null);

  const loadPatients = useCallback(async () => {
    if (!accessToken) {
      return null;
    }
    const patientsData = await fetchPatients(accessToken, { page: 1, page_size: 100 });
    setPatients(patientsData.items);
    return patientsData.items;
  }, [accessToken]);

  const loadBootstrap = useCallback(async () => {
    if (!accessToken) {
      return;
    }

    setBootstrapLoading(true);
    setBootstrapError(null);

    try {
      const [membershipData, doctorsData, patientsData] = await Promise.all([
        fetchMyOrganizationMembership(accessToken),
        fetchOrganizationDoctors(accessToken),
        fetchPatients(accessToken, { page: 1, page_size: 100 }),
      ]);
      setMembership(membershipData);
      setDoctors(doctorsData.items);
      setPatients(patientsData.items);
      if (doctorsData.items.length > 0) {
        setSelectedDoctorId((current) => current || doctorsData.items[0].user_id);
      }
    } catch (err) {
      const resolved = resolveManagementErrorMessage(err, content.management.errors);
      setBootstrapError(resolved.message);
      setMembership(null);
      setDoctors([]);
      setPatients([]);
    } finally {
      setBootstrapLoading(false);
    }
  }, [accessToken, content.management.errors]);

  const loadAssignments = useCallback(async () => {
    if (!accessToken || !selectedPatientId) {
      setAssignments([]);
      setAssignmentsError(null);
      return;
    }

    setAssignmentsLoading(true);
    setAssignmentsError(null);

    try {
      const response = await fetchPatientAssignments(accessToken, selectedPatientId);
      setAssignments(response.items);
    } catch (err) {
      const resolved = resolveManagementErrorMessage(err, content.management.errors);
      setAssignmentsError(resolved.message);
      setAssignments([]);
    } finally {
      setAssignmentsLoading(false);
    }
  }, [accessToken, content.management.errors, selectedPatientId]);

  useEffect(() => {
    void loadBootstrap();
  }, [loadBootstrap]);

  useEffect(() => {
    void loadAssignments();
  }, [loadAssignments]);

  const selectedPatient = useMemo(
    () => patients.find((patient) => patient.id === selectedPatientId) ?? null,
    [patients, selectedPatientId],
  );

  const handleAssign = async () => {
    if (!accessToken || !selectedPatientId || !selectedDoctorId) {
      return;
    }

    setActionPending(true);
    setActionError(null);
    setActionMessage(null);

    try {
      await createPatientAssignment(accessToken, selectedPatientId, {
        assignee_user_id: selectedDoctorId,
        is_primary: isPrimary,
      });
      setActionMessage(mgmt.createSuccess);
      await loadAssignments();
    } catch (err) {
      const resolved = resolveManagementErrorMessage(err, content.management.errors);
      setActionError(resolved.message);
    } finally {
      setActionPending(false);
    }
  };

  const handleDeactivate = async (assignment: PatientAssignment) => {
    if (!accessToken || !selectedPatientId || assignment.status !== "active") {
      return;
    }

    setActionPending(true);
    setActionError(null);
    setActionMessage(null);

    try {
      await deactivatePatientAssignment(accessToken, selectedPatientId, assignment.id);
      setActionMessage(mgmt.deactivateSuccess);
      await loadAssignments();
    } catch (err) {
      const resolved = resolveManagementErrorMessage(err, content.management.errors);
      setActionError(resolved.message);
    } finally {
      setActionPending(false);
    }
  };

  if (bootstrapLoading) {
    return <p className="text-center text-text-secondary">{content.common.loading}</p>;
  }

  if (bootstrapError) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900" role="alert">
        <p className="font-medium">{mgmt.loadError}</p>
        <p className="mt-1 break-words">{bootstrapError}</p>
        <Button type="button" size="sm" variant="secondary" className="mt-3" onClick={loadBootstrap}>
          {content.common.retry}
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6 lg:space-y-8">
      <header className="max-w-3xl">
        <h1 className="text-2xl font-bold text-text-primary sm:text-3xl">{mgmt.title}</h1>
        <p className="mt-2 text-text-secondary">{mgmt.description}</p>
      </header>

      {patientCreateNotice ? (
        <p
          className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm font-medium text-green-900"
          role="status"
          aria-live="polite"
        >
          {patientCreateNotice}
        </p>
      ) : null}

      {actionMessage ? (
        <p className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-900" role="status">
          {actionMessage}
        </p>
      ) : null}

      {actionError ? (
        <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900" role="alert">
          {actionError}
        </p>
      ) : null}

      {accessToken ? (
        <PatientOnboardingPanel
          accessToken={accessToken}
          selectedPatientId={selectedPatientId}
          onPatientCreated={async (patient) => {
            setPatientCreateNotice(mgmt.onboarding.createSuccess);
            setSelectedPatientId(patient.id);
            if (!accessToken) {
              return;
            }
            try {
              const items = await loadPatients();
              if (items && !items.some((row) => row.id === patient.id)) {
                setPatients([patient, ...items]);
              }
            } catch {
              setPatients((current) => {
                if (current.some((row) => row.id === patient.id)) {
                  return current;
                }
                return [patient, ...current];
              });
            }
            setSelectedPatientId(patient.id);
          }}
          onConsentChanged={() => {
            void loadAssignments();
          }}
        />
      ) : null}

      <div className="grid gap-6 lg:grid-cols-2">
        <section className={sectionCardClassName()} aria-labelledby="mgmt-org-heading">
          <h2 id="mgmt-org-heading" className="text-lg font-semibold text-text-primary">
            {mgmt.organizationSection}
          </h2>
          {membership ? (
            <dl className="mt-4 space-y-2 text-sm">
              <div className="flex flex-col gap-0.5 sm:flex-row sm:justify-between">
                <dt className="text-text-secondary">{mgmt.organizationName}</dt>
                <dd className="font-medium text-text-primary">{membership.organization_name}</dd>
              </div>
              <div className="flex flex-col gap-0.5 sm:flex-row sm:justify-between">
                <dt className="text-text-secondary">{mgmt.membershipRole}</dt>
                <dd className="text-text-primary">
                  {mgmt.membershipRoles[membership.membership_role] ?? membership.membership_role}
                </dd>
              </div>
              <div className="flex flex-col gap-0.5 sm:flex-row sm:justify-between">
                <dt className="text-text-secondary">{mgmt.membershipStatus}</dt>
                <dd className="text-text-primary">
                  {mgmt.membershipStatuses[membership.membership_status] ??
                    membership.membership_status}
                </dd>
              </div>
              <div className="flex flex-col gap-0.5 sm:flex-row sm:justify-between">
                <dt className="text-text-secondary">{mgmt.joinedAt}</dt>
                <dd className="text-text-primary">{formatDateTime(membership.joined_at)}</dd>
              </div>
              <details className="pt-2 text-xs text-text-secondary">
                <summary className="cursor-pointer font-medium">{mgmt.technicalDetails}</summary>
                <div className="mt-2 space-y-1 font-mono break-all">
                  <div>
                    {mgmt.organizationId}: {membership.organization_id}
                  </div>
                  <div>
                    {mgmt.membershipId}: {membership.membership_id}
                  </div>
                </div>
              </details>
            </dl>
          ) : null}
        </section>

        <section className={sectionCardClassName()} aria-labelledby="mgmt-doctors-heading">
          <h2 id="mgmt-doctors-heading" className="text-lg font-semibold text-text-primary">
            {mgmt.doctorsSection}
          </h2>
          {doctors.length === 0 ? (
            <p className="mt-4 text-sm text-text-secondary">{mgmt.emptyDoctors}</p>
          ) : (
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-border text-text-secondary">
                  <tr>
                    <th className="py-2 pr-4 font-medium">{mgmt.doctorName}</th>
                    <th className="py-2 pr-4 font-medium">{mgmt.doctorEmail}</th>
                    <th className="py-2 font-medium">{mgmt.joinedAt}</th>
                  </tr>
                </thead>
                <tbody>
                  {doctors.map((doctor) => (
                    <tr key={doctor.membership_id} className="border-b border-border last:border-b-0">
                      <td className="py-2 pr-4 text-text-primary">
                        {formatDoctorDisplayName(doctor)}
                      </td>
                      <td className="py-2 pr-4 text-text-secondary">{doctor.email}</td>
                      <td className="py-2 text-text-secondary">{formatDateTime(doctor.joined_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      <section className={sectionCardClassName()} aria-labelledby="mgmt-patients-heading">
        <h2 id="mgmt-patients-heading" className="text-lg font-semibold text-text-primary">
          {mgmt.patientsSection}
        </h2>
        {patients.length === 0 ? (
          <p className="mt-4 text-sm text-text-secondary">{content.patients.empty}</p>
        ) : (
          <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
            <label htmlFor="mgmt-patient-select" className="flex min-w-0 flex-1 flex-col gap-1 text-sm">
              <span className="font-medium text-text-secondary">{mgmt.selectPatient}</span>
              <select
                id="mgmt-patient-select"
                className="min-h-11 rounded-lg border border-border bg-white px-3 py-2 text-text-primary"
                value={selectedPatientId}
                onChange={(event) => setSelectedPatientId(event.target.value)}
              >
                <option value="">{mgmt.selectPatient}</option>
                {patients.map((patient) => (
                  <option key={patient.id} value={patient.id}>
                    {formatPatientListLabel(patient, formatDate)}
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}
      </section>

      <section className={sectionCardClassName()} aria-labelledby="mgmt-assign-heading">
        <h2 id="mgmt-assign-heading" className="text-lg font-semibold text-text-primary">
          {mgmt.assignmentsSection}
        </h2>

        {!selectedPatientId ? (
          <p className="mt-4 text-sm text-text-secondary">{mgmt.noPatientSelected}</p>
        ) : assignmentsLoading ? (
          <p className="mt-4 text-sm text-text-secondary">{content.common.loading}</p>
        ) : assignmentsError ? (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900" role="alert">
            <p>{assignmentsError}</p>
            <Button type="button" size="sm" variant="secondary" className="mt-3" onClick={loadAssignments}>
              {content.common.retry}
            </Button>
          </div>
        ) : (
          <>
            {selectedPatient ? (
              <p className="mt-2 text-sm text-text-secondary">
                {mgmt.patientLabel}: {formatPatientListLabel(selectedPatient, formatDate)}
              </p>
            ) : null}

            <div className="mt-4 flex flex-col gap-3 border-b border-border pb-4 sm:flex-row sm:flex-wrap sm:items-end">
              <label htmlFor="mgmt-doctor-select" className="flex min-w-[12rem] flex-1 flex-col gap-1 text-sm">
                <span className="font-medium text-text-secondary">{mgmt.selectDoctor}</span>
                <select
                  id="mgmt-doctor-select"
                  className="min-h-11 rounded-lg border border-border bg-white px-3 py-2"
                  value={selectedDoctorId}
                  onChange={(event) => setSelectedDoctorId(event.target.value)}
                  disabled={doctors.length === 0 || actionPending}
                >
                  <option value="">{mgmt.selectDoctor}</option>
                  {doctors.map((doctor) => (
                    <option key={doctor.user_id} value={doctor.user_id}>
                      {formatDoctorOptionLabel(doctor)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex min-h-11 items-center gap-2 text-sm text-text-primary">
                <input
                  type="checkbox"
                  checked={isPrimary}
                  onChange={(event) => setIsPrimary(event.target.checked)}
                  disabled={actionPending}
                />
                {mgmt.isPrimary}
              </label>
              <Button
                type="button"
                onClick={handleAssign}
                disabled={!selectedDoctorId || actionPending}
              >
                {mgmt.assignDoctor}
              </Button>
            </div>

            {assignments.length === 0 ? (
              <p className="mt-4 text-sm text-text-secondary">{mgmt.emptyAssignments}</p>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="border-b border-border bg-brand-50/40 text-text-secondary">
                    <tr>
                      <th className="px-2 py-2 font-medium">{mgmt.assignedDoctor}</th>
                      <th className="px-2 py-2 font-medium">{mgmt.status}</th>
                      <th className="px-2 py-2 font-medium">{mgmt.isPrimary}</th>
                      <th className="px-2 py-2 font-medium">{mgmt.assignedAt}</th>
                      <th className="px-2 py-2 font-medium">
                        <span className="sr-only">{mgmt.removeAssignment}</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {assignments.map((assignment) => {
                      const doctor = findDoctorByUserId(doctors, assignment.assignee_user_id);
                      const doctorLabel = doctor
                        ? formatDoctorDisplayName(doctor)
                        : mgmt.errors.doctorNotFound;

                      return (
                        <tr key={assignment.id} className="border-b border-border last:border-b-0">
                          <td className="px-2 py-2 text-text-primary">
                            <div>{doctorLabel}</div>
                            {doctor ? (
                              <div className="text-xs text-text-secondary">{doctor.email}</div>
                            ) : null}
                          </td>
                          <td className="px-2 py-2">
                            {mgmt.assignmentStatuses[assignment.status] ?? assignment.status}
                          </td>
                          <td className="px-2 py-2">{assignment.is_primary ? "✓" : "—"}</td>
                          <td className="px-2 py-2 text-text-secondary">
                            {formatDateTime(assignment.assigned_at)}
                          </td>
                          <td className="px-2 py-2">
                            {assignment.status === "active" ? (
                              <Button
                                type="button"
                                size="sm"
                                variant="secondary"
                                disabled={actionPending}
                                onClick={() => void handleDeactivate(assignment)}
                              >
                                {mgmt.removeAssignment}
                              </Button>
                            ) : (
                              <span className="text-text-secondary">—</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
