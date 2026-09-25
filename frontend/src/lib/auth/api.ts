import { createApiClient, type ApiClient } from "@/lib/api/client";
import type {
  AuthUser,
  LoginPayload,
  RegisterPayload,
  TokenPair,
} from "@/lib/auth/types";
import { getApiV1BaseUrl } from "@/lib/config/env";

let authClient: ApiClient | undefined;

function getAuthClient(): ApiClient {
  if (!authClient) {
    authClient = createApiClient(getApiV1BaseUrl());
  }
  return authClient;
}

export async function loginRequest(payload: LoginPayload): Promise<TokenPair> {
  return getAuthClient().post<TokenPair>("/auth/login", { body: payload });
}

export async function registerRequest(payload: RegisterPayload): Promise<AuthUser> {
  return getAuthClient().post<AuthUser>("/auth/register", {
    body: { ...payload, role: payload.role ?? "patient" },
  });
}

export async function refreshRequest(refreshToken: string): Promise<TokenPair> {
  return getAuthClient().post<TokenPair>("/auth/refresh", {
    body: { refresh_token: refreshToken },
  });
}

export async function logoutRequest(refreshToken: string): Promise<void> {
  await getAuthClient().post<{ message: string }>("/auth/logout", {
    body: { refresh_token: refreshToken },
  });
}

export async function fetchCurrentUser(accessToken: string): Promise<AuthUser> {
  return getAuthClient().get<AuthUser>("/auth/me", { authToken: accessToken });
}

export async function verifyEmailRequest(token: string): Promise<{ message: string }> {
  return getAuthClient().post<{ message: string }>("/auth/verify-email", {
    body: { token },
  });
}

export async function resendVerificationRequest(
  email: string,
  locale?: "tr" | "en",
): Promise<{ message: string }> {
  return getAuthClient().post<{ message: string }>("/auth/resend-verification", {
    body: { email, ...(locale ? { locale } : {}) },
  });
}

export async function fetchHealthStatus(accessToken?: string) {
  return getAuthClient().get<{ status: string }>("/health", {
    authToken: accessToken,
  });
}
