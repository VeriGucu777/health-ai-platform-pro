"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { LanguageSwitcher } from "@/components/layout/LanguageSwitcher";
import { Navigation } from "@/components/layout/Navigation";
import { PageContainer } from "@/components/layout/PageContainer";
import { useAuth } from "@/lib/auth";
import { useLocale } from "@/lib/i18n/use-locale";

export function Header() {
  const { content } = useLocale();
  const { user, isAuthenticated, isLoading, logout } = useAuth();
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

  const authActions = isLoading ? null : isAuthenticated && user ? (
    <div className="flex min-w-0 items-center gap-2">
      <span className="hidden max-w-[12rem] truncate text-sm text-text-secondary md:inline">
        {content.auth.signedInAs} {user.first_name}
      </span>
      <Button variant="ghost" size="sm" onClick={() => void logout()}>
        {content.auth.logout}
      </Button>
    </div>
  ) : (
    <div className="flex shrink-0 items-center gap-2">
      <Button href="/login" variant="ghost" size="sm">
        {content.nav.login}
      </Button>
      <Button href="/register" size="sm">
        {content.nav.register}
      </Button>
    </div>
  );

  const mobileAuthActions = isLoading ? null : isAuthenticated && user ? (
    <div className="space-y-2">
      <p className="break-words text-sm text-text-secondary">
        {content.auth.signedInAs} {user.first_name} {user.last_name}
      </p>
      <Button variant="secondary" fullWidth onClick={() => void logout()}>
        {content.auth.logout}
      </Button>
    </div>
  ) : (
    <div className="flex flex-col gap-2">
      <Button href="/login" variant="secondary" fullWidth>
        {content.nav.login}
      </Button>
      <Button href="/register" fullWidth>
        {content.nav.register}
      </Button>
    </div>
  );

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
          {authActions}
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
        <div id="mobile-navigation" className="border-t border-border bg-white lg:hidden">
          <PageContainer className="space-y-4 py-4">
            <Navigation orientation="vertical" onNavigate={() => setMobileOpen(false)} />
            {mobileAuthActions}
          </PageContainer>
        </div>
      ) : null}
    </header>
  );
}
