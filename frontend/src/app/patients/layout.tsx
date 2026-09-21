"use client";

import { Suspense, type ReactNode } from "react";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { PageContainer } from "@/components/layout/PageContainer";
import { useLocale } from "@/lib/i18n/use-locale";

function PatientsLayoutFallback() {
  const { content } = useLocale();

  return (
    <PageContainer className="py-16">
      <p className="text-center text-text-secondary">{content.common.loading}</p>
    </PageContainer>
  );
}

export default function PatientsLayout({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<PatientsLayoutFallback />}>
      <RequireAuth>{children}</RequireAuth>
    </Suspense>
  );
}
