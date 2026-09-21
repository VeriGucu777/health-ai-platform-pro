"use client";

import { Button } from "@/components/ui/Button";
import { PageContainer } from "@/components/layout/PageContainer";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useLocale } from "@/lib/i18n/use-locale";

export function HomePageContent() {
  const { content } = useLocale();
  const { isAuthenticated, isHydrated } = useAuth();
  const showPatientsCta = isHydrated && isAuthenticated;

  return (
    <main id="main-content" className="min-w-0 overflow-x-hidden">
      <section className="border-b border-border bg-gradient-to-b from-brand-50 to-surface py-12 sm:py-16 lg:py-24">
        <PageContainer>
          <div className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr] lg:items-center lg:gap-10">
            <div className="min-w-0 space-y-5 sm:space-y-6">
              <p className="inline-flex max-w-full rounded-full bg-brand-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-brand-800">
                {content.landing.badge}
              </p>
              <h1 className="break-words text-3xl font-bold tracking-tight text-text-primary sm:text-4xl lg:text-5xl">
                {content.landing.heroTitle}
              </h1>
              <p className="max-w-2xl break-words text-base text-text-secondary sm:text-lg">
                {content.landing.heroDescription}
              </p>
              <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
                <Button href="/register" size="lg" fullWidth className="sm:w-auto sm:min-w-[10rem]">
                  {content.landing.primaryCta}
                </Button>
                <Button
                  href={showPatientsCta ? "/patients" : "/login"}
                  variant="secondary"
                  size="lg"
                  fullWidth
                  className="sm:w-auto sm:min-w-[10rem]"
                >
                  {showPatientsCta
                    ? content.landing.secondaryCtaAuthenticated
                    : content.landing.secondaryCta}
                </Button>
              </div>
            </div>

            <div className="min-w-0 rounded-2xl border border-border bg-white p-5 shadow-sm sm:p-8">
              <h2 className="text-lg font-semibold text-text-primary sm:text-xl">
                {content.landing.trustTitle}
              </h2>
              <ul className="mt-4 space-y-3 text-sm text-text-secondary" role="list">
                {content.landing.trustPoints.map((point) => (
                  <li key={point} className="flex gap-3 break-words">
                    <span
                      aria-hidden="true"
                      className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-brand-500"
                    />
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </PageContainer>
      </section>

      <section className="py-12 sm:py-16 lg:py-20">
        <PageContainer>
          <div className="mx-auto max-w-2xl px-1 text-center">
            <h2 className="break-words text-2xl font-bold text-text-primary sm:text-3xl">
              {content.landing.featuresTitle}
            </h2>
          </div>

          <div className="mt-8 grid gap-4 sm:mt-10 sm:gap-6 md:grid-cols-2 lg:grid-cols-3">
            {content.landing.features.map((feature) => (
              <article
                key={feature.title}
                className="min-w-0 rounded-2xl border border-border bg-white p-5 shadow-sm sm:p-6"
              >
                <h3 className="break-words text-lg font-semibold text-text-primary">
                  {feature.title}
                </h3>
                <p className="mt-3 break-words text-sm leading-6 text-text-secondary">
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
