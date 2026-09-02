import type { AuthSession } from "@/lib/auth/types";

const ACCESS_TOKEN_KEY = "health_ai_access_token";
const REFRESH_TOKEN_KEY = "health_ai_refresh_token";
const USER_KEY = "health_ai_user";

function canUseSessionStorage(): boolean {
  return typeof window !== "undefined" && typeof window.sessionStorage !== "undefined";
}

export function loadStoredSession(): AuthSession | null {
  if (!canUseSessionStorage()) {
    return null;
  }

  const accessToken = window.sessionStorage.getItem(ACCESS_TOKEN_KEY);
  const refreshToken = window.sessionStorage.getItem(REFRESH_TOKEN_KEY);
  const userRaw = window.sessionStorage.getItem(USER_KEY);

  if (!accessToken || !refreshToken) {
    return null;
  }

  let user = null;
  if (userRaw) {
    try {
      user = JSON.parse(userRaw) as AuthSession["user"];
    } catch {
      user = null;
    }
  }

  return { accessToken, refreshToken, user };
}

export function saveStoredSession(session: AuthSession): void {
  if (!canUseSessionStorage()) {
    return;
  }

  window.sessionStorage.setItem(ACCESS_TOKEN_KEY, session.accessToken);
  window.sessionStorage.setItem(REFRESH_TOKEN_KEY, session.refreshToken);
  if (session.user) {
    window.sessionStorage.setItem(USER_KEY, JSON.stringify(session.user));
  } else {
    window.sessionStorage.removeItem(USER_KEY);
  }
}

export function clearStoredSession(): void {
  if (!canUseSessionStorage()) {
    return;
  }

  window.sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  window.sessionStorage.removeItem(REFRESH_TOKEN_KEY);
  window.sessionStorage.removeItem(USER_KEY);
}

export function getStoredAccessToken(): string | null {
  if (!canUseSessionStorage()) {
    return null;
  }
  return window.sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getStoredRefreshToken(): string | null {
  if (!canUseSessionStorage()) {
    return null;
  }
  return window.sessionStorage.getItem(REFRESH_TOKEN_KEY);
}
