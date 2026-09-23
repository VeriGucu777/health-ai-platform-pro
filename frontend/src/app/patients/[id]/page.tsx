"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { PatientHubPageContent } from "@/components/patients/PatientHubPageContent";
import { PageContainer } from "@/components/layout/PageContainer";
import { useLocale } from "@/lib/i18n/use-locale";

export default function PatientHubPage() {
  const params = useParams<{ id: string }>();
  const patientId = params.id;
  const { content } = useLocale();

  return (
    <PageContainer className="py-8 sm:py-10">
      <div className="mb-6">
        <Link
          href="/patients"
          className="text-sm font-medium text-brand-700 hover:text-brand-800"
        >
          ← {content.common.back}
        </Link>
      </div>
      <header className="mb-8 max-w-3xl">
        <h1 className="text-2xl font-bold text-text-primary sm:text-3xl">{content.patientHub.title}</h1>
        <p className="mt-2 text-text-secondary">{content.patientHub.description}</p>
      </header>
      <PatientHubPageContent patientId={patientId} />
    </PageContainer>
  );
}
