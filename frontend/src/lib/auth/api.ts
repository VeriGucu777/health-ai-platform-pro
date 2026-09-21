import { createApiClient } from "@/lib/api/client";
import type {
  AuthUser,
  LoginPayload,
  RegisterPayload,
  TokenPair,
} from "@/lib/auth/types";
import { getApiV1BaseUrl } from "@/lib/config/env";

const authClient = createApiClient(getApiV1BaseUrl());

export async function loginRequest(payload: LoginPayload): Promise<TokenPair> {
  return authClient.post<TokenPair>("/auth/login", { body: payload });
}

export async function registerRequest(payload: RegisterPayload): Promise<AuthUser> {
  return authClient.post<AuthUser>("/auth/register", {
    body: { ...payload, role: payload.role ?? "patient" },
  });
}

export async function refreshRequest(refreshToken: string): Promise<TokenPair> {
  return authClient.post<TokenPair>("/auth/refresh", {
    body: { refresh_token: refreshToken },
  });
}

export async function logoutRequest(refreshToken: string): Promise<void> {
  await authClient.post<{ message: string }>("/auth/logout", {
    body: { refresh_token: refreshToken },
  });
}

export async function fetchCurrentUser(accessToken: string): Promise<AuthUser> {
  return authClient.get<AuthUser>("/auth/me", { authToken: accessToken });
}

export async function fetchHealthStatus(accessToken?: string) {
  return authClient.get<{ status: string }>("/health", {
    authToken: accessToken,
  });
}
