import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthFormShell } from "@/components/auth/AuthFormShell";
import { CheckEmailPanel } from "@/components/auth/CheckEmailPanel";
import { getCommonContent } from "@/lib/i18n/content";

const content = getCommonContent();

export const metadata: Metadata = {
  title: content.auth.checkEmailTitle,
  description: content.auth.checkEmailDescription,
};

export default function CheckEmailPage() {
  return (
    <AuthFormShell mode="register">
      <Suspense
        fallback={
          <p className="text-sm text-text-secondary">{content.auth.checkEmailDescription}</p>
        }
      >
        <CheckEmailPanel />
      </Suspense>
    </AuthFormShell>
  );
}
