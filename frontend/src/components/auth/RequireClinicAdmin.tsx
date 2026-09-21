"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { PageContainer } from "@/components/layout/PageContainer";
import { useAuth } from "@/lib/auth/AuthProvider";
import { canAccessManagementUi } from "@/lib/auth/roles";
import { useCurrentUser } from "@/lib/auth/use-current-user";
import { useLocale } from "@/lib/i18n/use-locale";

type RequireClinicAdminProps = {
  children: ReactNode;
};

export function RequireClinicAdmin({ children }: RequireClinicAdminProps) {
  const { isAuthenticated, isHydrated } = useAuth();
  const { user, isLoading, isReady, error } = useCurrentUser();
  const router = useRouter();
  const pathname = usePathname();
  const { content } = useLocale();

  useEffect(() => {
    if (!isHydrated) {
      return;
    }

    if (!isAuthenticated) {
      const next = pathname || "/management";
      router.replace(`/login?next=${encodeURIComponent(next)}`);
    }
  }, [isAuthenticated, isHydrated, router, pathname]);

  const shouldRedirectNonAdmin =
    isReady && isAuthenticated && !isLoading && user !== null && !canAccessManagementUi(user.role);

  useEffect(() => {
    if (shouldRedirectNonAdmin) {
      router.replace("/patients");
    }
  }, [router, shouldRedirectNonAdmin]);

  if (!isHydrated || !isAuthenticated || isLoading || !isReady) {
    return (
      <PageContainer className="py-16">
        <p className="text-center text-text-secondary">{content.common.loading}</p>
      </PageContainer>
    );
  }

  if (error || !user) {
    return (
      <PageContainer className="py-16">
        <p className="text-center text-text-secondary" role="alert">
          {content.management.loadError}
        </p>
      </PageContainer>
    );
  }

  if (shouldRedirectNonAdmin) {
    return (
      <PageContainer className="py-16">
        <p className="text-center text-text-secondary">{content.common.loading}</p>
      </PageContainer>
    );
  }

  return children;
}
