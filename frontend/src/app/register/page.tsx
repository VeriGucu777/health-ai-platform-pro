import type { Metadata } from "next";
import { AuthFormShell } from "@/components/auth/AuthFormShell";
import { RegisterForm } from "@/components/auth/RegisterForm";
import { getCommonContent } from "@/lib/i18n/content";

const content = getCommonContent();

export const metadata: Metadata = {
  title: content.auth.registerTitle,
  description: content.auth.registerDescription,
};

export default function RegisterPage() {
  return (
    <AuthFormShell mode="register">
      <RegisterForm />
    </AuthFormShell>
  );
}
