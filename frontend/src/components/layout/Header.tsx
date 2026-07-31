"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Navigation } from "@/components/layout/Navigation";
import { PageContainer } from "@/components/layout/PageContainer";
import { getCommonContent } from "@/lib/i18n/content";

export function Header() {
  const content = getCommonContent();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-white/95 backdrop-blur">
      <PageContainer className="flex items-center justify-between gap-4 py-4">
        <div className="flex min-w-0 items-center gap-3">
          <Link
            href="/"
            className="flex min-w-0 items-center gap-3 rounded-md focus-visible:outline-offset-4"
          >
            <span
              aria-hidden="true"
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-sm font-bold text-white"
            >
              HA
            </span>
            <span className="min-w-0">
              <span className="block truncate text-sm font-semibold text-text-primary sm:text-base">
                {content.brandName}
              </span>
              <span className="hidden truncate text-xs text-text-secondary sm:block">
                {content.brandTagline}
              </span>
            </span>
          </Link>
        </div>

        <div className="hidden items-center gap-6 md:flex">
          <Navigation />
          <div className="flex items-center gap-2">
            <Button href="/login" variant="ghost" size="sm">
              {content.nav.login}
            </Button>
            <Button href="/register" size="sm">
              {content.nav.register}
            </Button>
          </div>
        </div>

        <button
          type="button"
          className="inline-flex items-center justify-center rounded-lg border border-border px-3 py-2 text-sm font-medium text-text-primary md:hidden"
          aria-expanded={mobileOpen}
          aria-controls="mobile-navigation"
          onClick={() => setMobileOpen((open) => !open)}
        >
          {mobileOpen ? "Close menu" : "Open menu"}
        </button>
      </PageContainer>

      {mobileOpen ? (
        <div
          id="mobile-navigation"
          className="border-t border-border bg-white md:hidden"
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
