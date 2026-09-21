"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useCurrentUser } from "@/lib/auth/use-current-user";
import { useLocale } from "@/lib/i18n/use-locale";

type NavigationProps = {
  orientation?: "horizontal" | "vertical";
  onNavigate?: () => void;
  onLogout?: () => void;
};

export function Navigation({
  orientation = "horizontal",
  onNavigate,
  onLogout,
}: NavigationProps) {
  const pathname = usePathname();
  const { content } = useLocale();
  const { isAuthenticated } = useAuth();
  const { isClinicAdmin } = useCurrentUser();

  const items = isAuthenticated
    ? [
        { href: "/", label: content.nav.home },
        { href: "/patients", label: content.nav.patients },
        ...(isClinicAdmin ? [{ href: "/management", label: content.nav.management }] : []),
      ]
    : [
        { href: "/", label: content.nav.home },
        { href: "/login", label: content.nav.login },
        { href: "/register", label: content.nav.register },
      ];

  const listClasses =
    orientation === "horizontal"
      ? "flex flex-wrap items-center gap-1 sm:gap-2"
      : "flex flex-col gap-1";

  const linkClasses = (href: string) => {
    const isActive = pathname === href || (href !== "/" && pathname.startsWith(`${href}/`));

    return [
      "inline-flex min-h-11 items-center rounded-md px-3 py-2 text-sm font-medium transition-colors",
      isActive
        ? "bg-brand-50 text-brand-800"
        : "text-text-secondary hover:bg-brand-50 hover:text-brand-800",
    ].join(" ");
  };

  const logoutClasses =
    "inline-flex min-h-11 w-full items-center rounded-md px-3 py-2 text-left text-sm font-medium text-text-secondary transition-colors hover:bg-brand-50 hover:text-brand-800 sm:w-auto";

  return (
    <nav aria-label="Primary" className="min-w-0 shrink">
      <ul className={listClasses} role="list">
        {items.map((item) => (
          <li key={item.href}>
            <Link
              href={item.href}
              className={linkClasses(item.href)}
              aria-current={pathname === item.href ? "page" : undefined}
              onClick={onNavigate}
            >
              {item.label}
            </Link>
          </li>
        ))}
        {isAuthenticated && onLogout ? (
          <li>
            <button type="button" className={logoutClasses} onClick={onLogout}>
              {content.nav.logout}
            </button>
          </li>
        ) : null}
      </ul>
    </nav>
  );
}
