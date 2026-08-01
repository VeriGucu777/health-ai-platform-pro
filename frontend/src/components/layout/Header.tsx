"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { LanguageSwitcher } from "@/components/layout/LanguageSwitcher";
import { Navigation } from "@/components/layout/Navigation";
import { PageContainer } from "@/components/layout/PageContainer";
import { useLocale } from "@/lib/i18n/use-locale";

export function Header() {
  const { content } = useLocale();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (!mobileOpen) {
      return;
    }

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMobileOpen(false);
      }
    };

    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("keydown", handleEscape);
    };
  }, [mobileOpen]);

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-white/95 backdrop-blur">
      <PageContainer className="flex min-w-0 items-center justify-between gap-3 py-3 sm:gap-4 sm:py-4">
        <div className="flex min-w-0 flex-1 items-center gap-2 sm:gap-3">
          <Link
            href="/"
            className="flex min-w-0 items-center gap-2 rounded-md focus-visible:outline-offset-4 sm:gap-3"
          >
            <span
              aria-hidden="true"
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-sm font-bold text-white sm:h-11 sm:w-11"
            >
              HA
            </span>
            <span className="min-w-0">
              <span className="block truncate text-sm font-semibold text-text-primary sm:text-base">
                {content.brandName}
              </span>
              <span className="hidden truncate text-xs text-text-secondary md:block">
                {content.brandTagline}
              </span>
            </span>
          </Link>
        </div>

        <div className="hidden min-w-0 items-center gap-4 lg:flex lg:gap-6">
          <Navigation />
          <LanguageSwitcher />
          <div className="flex shrink-0 items-center gap-2">
            <Button href="/login" variant="ghost" size="sm">
              {content.nav.login}
            </Button>
            <Button href="/register" size="sm">
              {content.nav.register}
            </Button>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2 lg:hidden">
          <LanguageSwitcher />
          <button
            type="button"
            className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg border border-border px-3 py-2 text-sm font-medium text-text-primary"
            aria-expanded={mobileOpen}
            aria-controls="mobile-navigation"
            aria-label={mobileOpen ? content.nav.closeMenu : content.nav.openMenu}
            onClick={() => setMobileOpen((open) => !open)}
          >
            <span aria-hidden="true">{mobileOpen ? "✕" : "☰"}</span>
          </button>
        </div>
      </PageContainer>

      {mobileOpen ? (
        <div
          id="mobile-navigation"
          className="border-t border-border bg-white lg:hidden"
        >
          <PageContainer className="space-y-4 py-4">
            <Navigation orientation="vertical" onNavigate={() => setMobileOpen(false)} />
            <div className="flex flex-col gap-2">
              <Button href="/login" variant="secondary" fullWidth>
                {content.nav.login}
              </Button>
              <Button href="/register" fullWidth>
                {content.nav.register}
              </Button>
            </div>
          </PageContainer>
        </div>
      ) : null}
    </header>
  );
}
