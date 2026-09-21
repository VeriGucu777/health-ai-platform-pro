import { apiClient } from "@/lib/api/index";

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type RegisterPayload = {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  role?: "patient" | "doctor";
};

export type LoginPayload = {
  email: string;
  password: string;
};

export async function loginRequest(payload: LoginPayload): Promise<TokenResponse> {
  return apiClient.post<TokenResponse>("/auth/login", { body: payload });
}

export async function registerRequest(payload: RegisterPayload): Promise<void> {
  await apiClient.post("/auth/register", {
    body: {
      ...payload,
      role: payload.role ?? "doctor",
    },
  });
}

export type UserRole = "patient" | "doctor" | "clinic_admin" | "system_admin";

export type UserProfile = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
};

export async function fetchCurrentUser(authToken: string): Promise<UserProfile> {
  return apiClient.get<UserProfile>("/auth/me", { authToken });
}
