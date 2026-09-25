import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthFormShell } from "@/components/auth/AuthFormShell";
import { VerifyEmailPanel } from "@/components/auth/VerifyEmailPanel";
import { getCommonContent } from "@/lib/i18n/content";

const content = getCommonContent();

export const metadata: Metadata = {
  title: content.auth.verifyEmailTitle,
};

export default function VerifyEmailPage() {
  return (
    <AuthFormShell mode="login">
      <h2 className="text-lg font-semibold text-text-primary">{content.auth.verifyEmailTitle}</h2>
      <Suspense fallback={<p className="text-sm text-text-secondary">{content.auth.verifyEmailWorking}</p>}>
        <VerifyEmailPanel />
      </Suspense>
    </AuthFormShell>
  );
}
