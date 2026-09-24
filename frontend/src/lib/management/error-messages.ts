import { ApiClientError } from "@/lib/api/client";

export type ManagementErrorMessages = {
  duplicateAssignment: string;
  duplicatePrimary: string;
  duplicateConsent: string;
  patientNotFound: string;
  assignmentNotFound: string;
  doctorNotFound: string;
  generic: string;
};

const DUPLICATE_ASSIGNMENT =
  "An active assignment already exists for this doctor and patient";
const DUPLICATE_PRIMARY = "An active primary assignment already exists for this patient";
const DUPLICATE_CONSENT = "An active consent already exists for this patient and consent type";
const PATIENT_NOT_FOUND = "Patient not found";
const ASSIGNMENT_NOT_FOUND = "Assignment not found";
const DOCTOR_NOT_FOUND = "Doctor not found";

export function resolveManagementErrorMessage(
  error: unknown,
  messages: ManagementErrorMessages,
): { message: string; status: number | null } {
  if (!(error instanceof ApiClientError)) {
    return { message: messages.generic, status: null };
  }

  const detail = error.message;

  if (error.status === 409) {
    if (detail.includes(DUPLICATE_PRIMARY)) {
      return { message: messages.duplicatePrimary, status: 409 };
    }
    if (detail.includes(DUPLICATE_ASSIGNMENT)) {
      return { message: messages.duplicateAssignment, status: 409 };
    }
    if (detail.includes(DUPLICATE_CONSENT)) {
      return { message: messages.duplicateConsent, status: 409 };
    }
  }

  if (error.status === 404) {
    if (detail.includes(PATIENT_NOT_FOUND)) {
      return { message: messages.patientNotFound, status: 404 };
    }
    if (detail.includes(ASSIGNMENT_NOT_FOUND)) {
      return { message: messages.assignmentNotFound, status: 404 };
    }
    if (detail.includes(DOCTOR_NOT_FOUND)) {
      return { message: messages.doctorNotFound, status: 404 };
    }
    return { message: messages.patientNotFound, status: 404 };
  }

  return { message: detail || messages.generic, status: error.status };
}

/** POST grant returned 409 because an active consent already exists (not a hard failure). */
export function isDuplicateActiveConsentConflict(
  error: unknown,
  messages: ManagementErrorMessages,
): boolean {
  const resolved = resolveManagementErrorMessage(error, messages);
  return resolved.status === 409 && resolved.message === messages.duplicateConsent;
}
