"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ClinicalTimelinePanel } from "@/components/timeline/ClinicalTimelinePanel";
import { PatientTimelineSummary } from "@/components/timeline/PatientTimelineSummary";
import { PageContainer } from "@/components/layout/PageContainer";
import { useLocale } from "@/lib/i18n/use-locale";

export default function PatientTimelinePage() {
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
        <h1 className="text-2xl font-bold text-text-primary sm:text-3xl">{content.timeline.title}</h1>
        <p className="mt-2 text-text-secondary">{content.timeline.description}</p>
        <PatientTimelineSummary patientId={patientId} />
      </header>
      <ClinicalTimelinePanel patientId={patientId} />
    </PageContainer>
  );
}
