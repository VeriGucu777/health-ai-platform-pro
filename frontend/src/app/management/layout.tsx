"use client";

import { Suspense, type ReactNode } from "react";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { RequireClinicAdmin } from "@/components/auth/RequireClinicAdmin";
import { PageContainer } from "@/components/layout/PageContainer";
import { useLocale } from "@/lib/i18n/use-locale";

function ManagementLayoutFallback() {
  const { content } = useLocale();

  return (
    <PageContainer className="py-16">
      <p className="text-center text-text-secondary">{content.common.loading}</p>
    </PageContainer>
  );
}

export default function ManagementLayout({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<ManagementLayoutFallback />}>
      <RequireAuth>
        <RequireClinicAdmin>{children}</RequireClinicAdmin>
      </RequireAuth>
    </Suspense>
  );
}
