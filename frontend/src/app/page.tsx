import type { Metadata } from "next";
import { HomePageContent } from "@/components/pages/HomePageContent";
import { getCommonContent } from "@/lib/i18n/content";

const content = getCommonContent();

export const metadata: Metadata = {
  title: content.nav.home,
  description: content.landing.heroDescription,
};

export default function HomePage() {
  return <HomePageContent />;
}
