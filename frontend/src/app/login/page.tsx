import type { Metadata } from "next";
import { AuthFormShell } from "@/components/auth/AuthFormShell";
import { LoginForm } from "@/components/auth/LoginForm";
import { getCommonContent } from "@/lib/i18n/content";

const content = getCommonContent();

export const metadata: Metadata = {
  title: content.auth.loginTitle,
  description: content.auth.loginDescription,
};

export default function LoginPage() {
  return (
    <AuthFormShell mode="login">
      <LoginForm />
    </AuthFormShell>
  );
}
