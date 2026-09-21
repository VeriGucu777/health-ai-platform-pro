import type { Metadata } from "next";
import { PatientsPageContent } from "@/components/patients/PatientsPageContent";
import { PageContainer } from "@/components/layout/PageContainer";
import { getCommonContent } from "@/lib/i18n/content";

const content = getCommonContent();

export const metadata: Metadata = {
  title: content.patients.title,
  description: content.patients.description,
};

export default function PatientsPage() {
  return (
    <PageContainer className="py-8 sm:py-10">
      <PatientsPageContent />
    </PageContainer>
  );
}
