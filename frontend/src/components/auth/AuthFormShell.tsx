import type { ReactNode } from "react";
import { PageContainer } from "@/components/layout/PageContainer";

type AuthFormShellProps = {
  title: string;
  description: string;
  children: ReactNode;
};

export function AuthFormShell({ title, description, children }: AuthFormShellProps) {
  return (
    <main id="main-content" className="py-10 sm:py-16">
      <PageContainer narrow>
        <div className="mx-auto rounded-2xl border border-border bg-white p-6 shadow-sm sm:p-8">
          <header className="space-y-2 text-center sm:text-left">
            <h1 className="text-2xl font-bold text-text-primary">{title}</h1>
            <p className="text-sm text-text-secondary">{description}</p>
          </header>

          <div className="mt-8 space-y-6">{children}</div>
        </div>
      </PageContainer>
    </main>
  );
}
