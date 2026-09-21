"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { PageContainer } from "@/components/layout/PageContainer";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useLocale } from "@/lib/i18n/use-locale";

type RequireAuthProps = {
  children: ReactNode;
};

export function RequireAuth({ children }: RequireAuthProps) {
  const { isAuthenticated, isHydrated } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const { content } = useLocale();

  useEffect(() => {
    if (!isHydrated) {
      return;
    }

    if (!isAuthenticated) {
      const next = pathname || "/patients";
      router.replace(`/login?next=${encodeURIComponent(next)}`);
    }
  }, [isAuthenticated, isHydrated, router, pathname]);

  if (!isHydrated) {
    return (
      <PageContainer className="py-16">
        <p className="text-center text-text-secondary">{content.common.loading}</p>
      </PageContainer>
    );
  }

  if (!isAuthenticated) {
    return (
      <PageContainer className="py-16">
        <p className="text-center text-text-secondary">{content.common.loading}</p>
      </PageContainer>
    );
  }

  return children;
}
