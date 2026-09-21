"use client";

import type { ReactNode } from "react";
import { PageContainer } from "@/components/layout/PageContainer";
import { useLocale } from "@/lib/i18n/use-locale";

type AuthFormShellProps = {
  mode: "login" | "register";
  children: ReactNode;
};

export function AuthFormShell({ mode, children }: AuthFormShellProps) {
  const { content } = useLocale();
  const title =
    mode === "login" ? content.auth.loginTitle : content.auth.registerTitle;
  const description =
    mode === "login"
      ? content.auth.loginDescription
      : content.auth.registerDescription;

  return (
    <main
      id="main-content"
      className="min-w-0 flex-1 overflow-x-hidden py-8 pb-10 sm:py-10 sm:pb-12 lg:py-12 lg:pb-14"
    >
      <PageContainer narrow>
        <div className="mx-auto w-full min-w-0 rounded-2xl border border-border bg-white p-4 shadow-sm sm:p-6 lg:p-8">
          <header className="space-y-2 text-center sm:text-left">
            <h1 className="break-words text-2xl font-bold text-text-primary sm:text-3xl">
              {title}
            </h1>
            <p className="break-words text-sm text-text-secondary sm:text-base">
              {description}
            </p>
          </header>

          <div className="mt-6 space-y-6 sm:mt-8">{children}</div>
        </div>
      </PageContainer>
    </main>
  );
}
