"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import {
  fetchCurrentUser,
  loginRequest,
  logoutRequest,
  refreshRequest,
  registerRequest,
} from "@/lib/auth/api";
import {
  clearStoredSession,
  getStoredRefreshToken,
  loadStoredSession,
  saveStoredSession,
} from "@/lib/auth/storage";
import type { AuthSession, AuthUser, LoginPayload, RegisterPayload } from "@/lib/auth/types";
import { ApiClientError } from "@/lib/api/client";

type AuthContextValue = {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
  getAccessToken: () => string | null;
  handleUnauthorized: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const persistSession = useCallback((next: AuthSession | null) => {
    if (next) {
      saveStoredSession(next);
    } else {
      clearStoredSession();
    }
    setSession(next);
  }, []);

  const handleUnauthorized = useCallback(() => {
    persistSession(null);
    router.push("/login");
  }, [persistSession, router]);

  const bootstrap = useCallback(async () => {
    const stored = loadStoredSession();
    if (!stored) {
      setIsLoading(false);
      return;
    }

    try {
      const user = await fetchCurrentUser(stored.accessToken);
      persistSession({ ...stored, user });
    } catch (error) {
      const refreshToken = stored.refreshToken ?? getStoredRefreshToken();
      if (error instanceof ApiClientError && error.status === 401 && refreshToken) {
        try {
          const tokens = await refreshRequest(refreshToken);
          const user = await fetchCurrentUser(tokens.access_token);
          persistSession({
            accessToken: tokens.access_token,
            refreshToken: tokens.refresh_token,
            user,
          });
          setIsLoading(false);
          return;
        } catch {
          persistSession(null);
        }
      } else {
        persistSession(null);
      }
    } finally {
      setIsLoading(false);
    }
  }, [persistSession]);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  const login = useCallback(
    async (payload: LoginPayload) => {
      const tokens = await loginRequest(payload);
      const user = await fetchCurrentUser(tokens.access_token);
      persistSession({
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        user,
      });
      router.push("/");
    },
    [persistSession, router],
  );

  const register = useCallback(
    async (payload: RegisterPayload) => {
      await registerRequest(payload);
      await login({ email: payload.email, password: payload.password });
    },
    [login],
  );

  const logout = useCallback(async () => {
    const refreshToken = session?.refreshToken ?? getStoredRefreshToken();
    if (refreshToken) {
      try {
        await logoutRequest(refreshToken);
      } catch {
        // Clear local session even when the backend call fails.
      }
    }
    persistSession(null);
    router.push("/login");
  }, [persistSession, router, session?.refreshToken]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user: session?.user ?? null,
      isAuthenticated: Boolean(session?.accessToken && session?.user),
      isLoading,
      login,
      register,
      logout,
      getAccessToken: () => session?.accessToken ?? null,
      handleUnauthorized,
    }),
    [handleUnauthorized, isLoading, login, logout, register, session],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
