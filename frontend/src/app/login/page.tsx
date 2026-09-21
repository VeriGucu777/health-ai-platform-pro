import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthFormShell } from "@/components/auth/AuthFormShell";
import { LoginForm } from "@/components/auth/LoginForm";
import { RedirectIfAuthenticated } from "@/components/auth/RedirectIfAuthenticated";
import { getCommonContent } from "@/lib/i18n/content";

const content = getCommonContent();

export const metadata: Metadata = {
  title: content.auth.loginTitle,
  description: content.auth.loginDescription,
};

export default function LoginPage() {
  return (
    <AuthFormShell mode="login">
      <RedirectIfAuthenticated>
        <Suspense fallback={null}>
          <LoginForm />
        </Suspense>
      </RedirectIfAuthenticated>
    </AuthFormShell>
  );
}
