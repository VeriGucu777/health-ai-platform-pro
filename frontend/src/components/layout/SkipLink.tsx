"use client";

import { useLocale } from "@/lib/i18n/use-locale";

export function SkipLink() {
  const { content } = useLocale();

  return (
    <a href="#main-content" className="skip-link" suppressHydrationWarning>
      {content.nav.skipToContent}
    </a>
  );
}
