import { apiClient } from "@/lib/api/index";

export type Patient = {
  id: string;
  owner_id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  phone: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type PatientListResponse = {
  items: Patient[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export async function fetchPatients(
  authToken: string,
  params?: { page?: number; page_size?: number },
): Promise<PatientListResponse> {
  const search = new URLSearchParams();
  if (params?.page) {
    search.set("page", String(params.page));
  }
  if (params?.page_size) {
    search.set("page_size", String(params.page_size));
  }

  const query = search.toString();
  const path = query ? `/patients?${query}` : "/patients";

  return apiClient.get<PatientListResponse>(path, { authToken });
}

export async function fetchPatient(authToken: string, patientId: string): Promise<Patient> {
  return apiClient.get<Patient>(`/patients/${patientId}`, { authToken });
}
