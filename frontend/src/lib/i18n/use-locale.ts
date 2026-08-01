"use client";

import { useContext } from "react";
import { LocaleContext } from "@/lib/i18n/LocaleProvider";

export function useLocale() {
  const context = useContext(LocaleContext);

  if (!context) {
    throw new Error("useLocale must be used within a LocaleProvider.");
  }

  return context;
}
