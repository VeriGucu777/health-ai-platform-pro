"use client";

import Link from "next/link";
import { PageContainer } from "@/components/layout/PageContainer";
import { useLocale } from "@/lib/i18n/use-locale";

export function Footer() {
  const { content } = useLocale();

  return (
    <footer className="border-t border-border bg-white">
      <PageContainer className="py-8 sm:py-10">
        <div className="grid gap-8 md:grid-cols-[1.5fr_1fr]">
          <div className="min-w-0 space-y-3">
            <p className="text-base font-semibold text-text-primary">
              {content.brandName}
            </p>
            <p className="max-w-xl break-words text-sm text-text-secondary">
              {content.footer.tagline}
            </p>
            <p className="max-w-xl break-words text-sm text-text-secondary">
              {content.footer.disclaimer}
            </p>
          </div>

          <nav aria-label="Footer" className="min-w-0">
            <ul className="space-y-2 text-sm" role="list">
              <li>
                <Link
                  href="#"
                  className="inline-flex min-h-11 items-center text-text-secondary transition-colors hover:text-brand-700"
                >
                  {content.footer.links.privacy}
                </Link>
              </li>
              <li>
                <Link
                  href="#"
                  className="inline-flex min-h-11 items-center text-text-secondary transition-colors hover:text-brand-700"
                >
                  {content.footer.links.terms}
                </Link>
              </li>
              <li>
                <Link
                  href="#"
                  className="inline-flex min-h-11 items-center text-text-secondary transition-colors hover:text-brand-700"
                >
                  {content.footer.links.contact}
                </Link>
              </li>
            </ul>
          </nav>
        </div>

        <p className="mt-8 break-words border-t border-border pt-6 text-sm text-text-secondary">
          © {new Date().getFullYear()} {content.footer.copyright}
        </p>
      </PageContainer>
    </footer>
  );
}
