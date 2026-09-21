import type { Metadata } from "next";
import { ManagementPageContent } from "@/components/management/ManagementPageContent";
import { PageContainer } from "@/components/layout/PageContainer";
import { getCommonContent } from "@/lib/i18n/content";

const content = getCommonContent();

export const metadata: Metadata = {
  title: content.management.title,
  description: content.management.description,
};

export default function ManagementPage() {
  return (
    <PageContainer className="py-8 sm:py-10">
      <ManagementPageContent />
    </PageContainer>
  );
}
