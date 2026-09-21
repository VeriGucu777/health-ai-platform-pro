"use client";

import { PatientsListPanel } from "@/components/patients/PatientsListPanel";
import { useLocale } from "@/lib/i18n/use-locale";

export function PatientsPageContent() {
  const { content } = useLocale();

  return (
    <>
      <header className="mb-8 max-w-3xl">
        <h1 className="text-2xl font-bold text-text-primary sm:text-3xl">{content.patients.title}</h1>
        <p className="mt-2 text-text-secondary">{content.patients.description}</p>
      </header>
      <PatientsListPanel />
    </>
  );
}
