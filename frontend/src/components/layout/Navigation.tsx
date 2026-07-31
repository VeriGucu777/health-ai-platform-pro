"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { getCommonContent } from "@/lib/i18n/content";

type NavigationProps = {
  orientation?: "horizontal" | "vertical";
  onNavigate?: () => void;
};

export function Navigation({
  orientation = "horizontal",
  onNavigate,
}: NavigationProps) {
  const pathname = usePathname();
  const content = getCommonContent();

  const items = [
    { href: "/", label: content.nav.home },
    { href: "/login", label: content.nav.login },
    { href: "/register", label: content.nav.register },
  ];

  const listClasses =
    orientation === "horizontal"
      ? "flex flex-wrap items-center gap-1 sm:gap-2"
      : "flex flex-col gap-1";

  const linkClasses = (href: string) => {
    const isActive = pathname === href;

    return [
      "rounded-md px-3 py-2 text-sm font-medium transition-colors",
      isActive
        ? "bg-brand-50 text-brand-800"
        : "text-text-secondary hover:bg-brand-50 hover:text-brand-800",
    ].join(" ");
  };

  return (
    <nav aria-label="Primary">
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
      </ul>
    </nav>
  );
}
