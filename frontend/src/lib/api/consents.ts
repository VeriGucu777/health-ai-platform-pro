import { apiClient } from "@/lib/api/index";

export type PatientConsent = {
  id: string;
  patient_id: string;
  organization_id: string;
  consent_type: string;
  status: "granted" | "revoked";
  granted_at: string;
  revoked_at: string | null;
  recorded_by_user_id: string;
  version: number;
  source: string;
  created_at: string;
};

export type PatientConsentListResponse = {
  items: PatientConsent[];
};

export type PatientConsentGrantPayload = {
  consent_type?: "clinical_data_processing";
};

export async function fetchPatientConsents(
  authToken: string,
  patientId: string,
): Promise<PatientConsentListResponse> {
  return apiClient.get<PatientConsentListResponse>(`/patients/${patientId}/consents`, {
    authToken,
  });
}

export async function grantPatientConsent(
  authToken: string,
  patientId: string,
  payload: PatientConsentGrantPayload = { consent_type: "clinical_data_processing" },
): Promise<PatientConsent> {
  return apiClient.post<PatientConsent>(`/patients/${patientId}/consents`, {
    authToken,
    body: payload,
  });
}

export async function revokePatientConsent(
  authToken: string,
  patientId: string,
  consentId: string,
): Promise<PatientConsent> {
  return apiClient.patch<PatientConsent>(
    `/patients/${patientId}/consents/${consentId}`,
    { authToken },
  );
}
