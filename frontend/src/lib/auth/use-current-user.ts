"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchCurrentUser, type UserProfile } from "@/lib/api/auth";
import { useAuth } from "@/lib/auth/AuthProvider";
import { isClinicAdminRole } from "@/lib/auth/roles";

export type CurrentUserState = {
  user: UserProfile | null;
  isLoading: boolean;
  isReady: boolean;
  error: string | null;
  isClinicAdmin: boolean;
  refresh: () => Promise<void>;
};

export function useCurrentUser(): CurrentUserState {
  const { accessToken, isAuthenticated, isHydrated } = useAuth();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!accessToken) {
      setUser(null);
      setIsReady(true);
      setIsLoading(false);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const profile = await fetchCurrentUser(accessToken);
      setUser(profile);
    } catch (err) {
      setUser(null);
      setError(err instanceof Error ? err.message : "Failed to load profile");
    } finally {
      setIsLoading(false);
      setIsReady(true);
    }
  }, [accessToken]);

  useEffect(() => {
    if (!isHydrated) {
      return;
    }

    if (!isAuthenticated) {
      setUser(null);
      setIsReady(true);
      setIsLoading(false);
      setError(null);
      return;
    }

    void refresh();
  }, [isAuthenticated, isHydrated, refresh]);

  return {
    user,
    isLoading: isHydrated && isAuthenticated && isLoading,
    isReady: isHydrated && (!isAuthenticated || isReady),
    error,
    isClinicAdmin: isClinicAdminRole(user?.role),
    refresh,
  };
}
