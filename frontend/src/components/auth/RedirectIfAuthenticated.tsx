"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { PageContainer } from "@/components/layout/PageContainer";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useLocale } from "@/lib/i18n/use-locale";

type RedirectIfAuthenticatedProps = {
  children: ReactNode;
};

/** Sends signed-in users to the patient list instead of auth forms. */
export function RedirectIfAuthenticated({ children }: RedirectIfAuthenticatedProps) {
  const { isAuthenticated, isHydrated } = useAuth();
  const router = useRouter();
  const { content } = useLocale();

  useEffect(() => {
    if (!isHydrated) {
      return;
    }

    if (isAuthenticated) {
      router.replace("/patients");
    }
  }, [isAuthenticated, isHydrated, router]);

  if (!isHydrated) {
    return (
      <PageContainer className="py-16">
        <p className="text-center text-text-secondary">{content.common.loading}</p>
      </PageContainer>
    );
  }

  if (isAuthenticated) {
    return (
      <PageContainer className="py-16">
        <p className="text-center text-text-secondary">{content.common.loading}</p>
      </PageContainer>
    );
  }

  return children;
}
