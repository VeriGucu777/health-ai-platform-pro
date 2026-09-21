import { apiClient } from "@/lib/api/index";

export type AssignmentStatus = "active" | "inactive";

export type PatientAssignment = {
  id: string;
  organization_id: string;
  patient_id: string;
  assignee_user_id: string;
  is_primary: boolean;
  status: AssignmentStatus;
  assigned_at: string;
  ended_at: string | null;
  assigned_by_user_id: string | null;
};

export type PatientAssignmentListResponse = {
  items: PatientAssignment[];
};

export type PatientAssignmentCreatePayload = {
  assignee_user_id: string;
  is_primary?: boolean;
};

export async function fetchPatientAssignments(
  authToken: string,
  patientId: string,
): Promise<PatientAssignmentListResponse> {
  return apiClient.get<PatientAssignmentListResponse>(`/patients/${patientId}/assignments`, {
    authToken,
  });
}

export async function createPatientAssignment(
  authToken: string,
  patientId: string,
  payload: PatientAssignmentCreatePayload,
): Promise<PatientAssignment> {
  return apiClient.post<PatientAssignment>(`/patients/${patientId}/assignments`, {
    authToken,
    body: payload,
  });
}

export async function deactivatePatientAssignment(
  authToken: string,
  patientId: string,
  assignmentId: string,
): Promise<PatientAssignment> {
  return apiClient.patch<PatientAssignment>(
    `/patients/${patientId}/assignments/${assignmentId}`,
    { authToken },
  );
}
