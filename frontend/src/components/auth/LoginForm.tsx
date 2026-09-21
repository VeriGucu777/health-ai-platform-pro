"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { FormInput } from "@/components/ui/FormInput";
import { ApiClientError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useLocale } from "@/lib/i18n/use-locale";

export function LoginForm() {
  const { content } = useLocale();
  const { login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    const formData = new FormData(event.currentTarget);
    const email = String(formData.get("email") ?? "");
    const password = String(formData.get("password") ?? "");

    try {
      await login({ email, password });
      const next = searchParams.get("next") ?? "/patients";
      router.push(next);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError(content.auth.loginError);
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <form className="space-y-5" onSubmit={handleSubmit}>
        <FormInput
          id="login-email"
          name="email"
          type="email"
          autoComplete="email"
          label={content.auth.emailLabel}
          placeholder={content.auth.emailPlaceholder}
          required
        />
        <FormInput
          id="login-password"
          name="password"
          type="password"
          autoComplete="current-password"
          label={content.auth.passwordLabel}
          placeholder={content.auth.passwordPlaceholder}
          required
        />

        {error ? (
          <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-900" role="alert">
            {error}
          </p>
        ) : (
          <p className="break-words rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-900">
            {content.auth.phaseNotice}
          </p>
        )}

        <Button type="submit" fullWidth disabled={submitting}>
          {submitting ? content.common.loading : content.auth.loginSubmit}
        </Button>
      </form>

      <p className="break-words text-center text-sm text-text-secondary">
        {content.auth.noAccount}{" "}
        <Link href="/register" className="font-medium text-brand-700 hover:text-brand-800">
          {content.nav.register}
        </Link>
      </p>
    </>
  );
}
