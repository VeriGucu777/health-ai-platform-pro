import Link from "next/link";
import { PageContainer } from "@/components/layout/PageContainer";
import { getCommonContent } from "@/lib/i18n/content";

export function Footer() {
  const content = getCommonContent();

  return (
    <footer className="border-t border-border bg-white">
      <PageContainer className="py-10">
        <div className="grid gap-8 md:grid-cols-[1.5fr_1fr]">
          <div className="space-y-3">
            <p className="text-base font-semibold text-text-primary">
              {content.brandName}
            </p>
            <p className="max-w-xl text-sm text-text-secondary">
              {content.footer.tagline}
            </p>
            <p className="max-w-xl text-sm text-text-secondary">
              {content.footer.disclaimer}
            </p>
          </div>

          <nav aria-label="Footer">
            <ul className="space-y-2 text-sm" role="list">
              <li>
                <Link
                  href="#"
                  className="text-text-secondary transition-colors hover:text-brand-700"
                >
                  {content.footer.links.privacy}
                </Link>
              </li>
              <li>
                <Link
                  href="#"
                  className="text-text-secondary transition-colors hover:text-brand-700"
                >
                  {content.footer.links.terms}
                </Link>
              </li>
              <li>
                <Link
                  href="#"
                  className="text-text-secondary transition-colors hover:text-brand-700"
                >
                  {content.footer.links.contact}
                </Link>
              </li>
            </ul>
          </nav>
        </div>

        <p className="mt-8 border-t border-border pt-6 text-sm text-text-secondary">
          © {new Date().getFullYear()} {content.footer.copyright}
        </p>
      </PageContainer>
    </footer>
  );
}
