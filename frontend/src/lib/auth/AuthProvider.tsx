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
import { loginRequest, registerRequest, type LoginPayload, type RegisterPayload } from "@/lib/api/auth";
import {
  clearStoredTokens,
  getAccessToken,
  getStoredTokens,
  setStoredTokens,
} from "@/lib/auth/token-storage";

type AuthContextValue = {
  accessToken: string | null;
  isAuthenticated: boolean;
  isHydrated: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    setAccessToken(getAccessToken());
    setIsHydrated(true);
  }, []);

  const login = useCallback(async (payload: LoginPayload) => {
    const tokens = await loginRequest(payload);
    setStoredTokens({
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
    });
    setAccessToken(tokens.access_token);
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    await registerRequest(payload);
    await login({ email: payload.email, password: payload.password });
  }, [login]);

  const logout = useCallback(() => {
    clearStoredTokens();
    setAccessToken(null);
  }, []);

  const value = useMemo(
    () => ({
      accessToken,
      isAuthenticated: Boolean(accessToken),
      isHydrated,
      login,
      register,
      logout,
    }),
    [accessToken, isHydrated, login, register, logout],
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

export function useOptionalAuth(): AuthContextValue | undefined {
  return useContext(AuthContext);
}

/** Returns stored tokens after hydration; useful for bootstrapping. */
export function readInitialAuthState(): boolean {
  return getStoredTokens() !== null;
}
