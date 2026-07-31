import type { Metadata } from "next";
import { Button } from "@/components/ui/Button";
import { PageContainer } from "@/components/layout/PageContainer";
import { getCommonContent } from "@/lib/i18n/content";

const content = getCommonContent();

export const metadata: Metadata = {
  title: content.nav.home,
  description: content.landing.heroDescription,
};

export default function HomePage() {
  return (
    <main id="main-content">
      <section className="border-b border-border bg-gradient-to-b from-brand-50 to-surface py-16 sm:py-20 lg:py-24">
        <PageContainer>
          <div className="grid gap-10 lg:grid-cols-[1.2fr_0.8fr] lg:items-center">
            <div className="space-y-6">
              <p className="inline-flex rounded-full bg-brand-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-brand-800">
                Healthcare SaaS foundation
              </p>
              <h1 className="text-4xl font-bold tracking-tight text-text-primary sm:text-5xl">
                {content.landing.heroTitle}
              </h1>
              <p className="max-w-2xl text-lg text-text-secondary">
                {content.landing.heroDescription}
              </p>
              <div className="flex flex-col gap-3 sm:flex-row">
                <Button href="/register" size="lg">
                  {content.landing.primaryCta}
                </Button>
                <Button href="/login" variant="secondary" size="lg">
                  {content.landing.secondaryCta}
                </Button>
              </div>
            </div>

            <div className="rounded-2xl border border-border bg-white p-6 shadow-sm sm:p-8">
              <h2 className="text-lg font-semibold text-text-primary">
                {content.landing.trustTitle}
              </h2>
              <ul className="mt-4 space-y-3 text-sm text-text-secondary" role="list">
                {content.landing.trustPoints.map((point) => (
                  <li key={point} className="flex gap-3">
                    <span
                      aria-hidden="true"
                      className="mt-1 h-2 w-2 shrink-0 rounded-full bg-brand-500"
                    />
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </PageContainer>
      </section>

      <section className="py-16 sm:py-20">
        <PageContainer>
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold text-text-primary">
              {content.landing.featuresTitle}
            </h2>
          </div>

          <div className="mt-10 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {content.landing.features.map((feature) => (
              <article
                key={feature.title}
                className="rounded-2xl border border-border bg-white p-6 shadow-sm"
              >
                <h3 className="text-lg font-semibold text-text-primary">
                  {feature.title}
                </h3>
                <p className="mt-3 text-sm leading-6 text-text-secondary">
                  {feature.description}
                </p>
              </article>
            ))}
          </div>
        </PageContainer>
      </section>
    </main>
  );
}
