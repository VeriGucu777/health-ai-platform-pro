"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { FormInput } from "@/components/ui/FormInput";
import { useAuth } from "@/lib/auth";
import { ApiClientError } from "@/lib/api/client";
import { useLocale } from "@/lib/i18n/use-locale";

export function LoginForm() {
  const { content } = useLocale();
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    const formData = new FormData(event.currentTarget);
    const email = String(formData.get("email") ?? "").trim();
    const password = String(formData.get("password") ?? "");

    try {
      await login({ email, password });
    } catch (submitError) {
      if (submitError instanceof ApiClientError) {
        setError(submitError.message);
      } else {
        setError(content.auth.genericError);
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <>
      <form action="#" method="post" className="space-y-5" onSubmit={handleSubmit}>
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
          <p className="break-words rounded-lg bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
            {error}
          </p>
        ) : null}

        <Button type="submit" fullWidth disabled={isSubmitting}>
          {content.auth.loginSubmit}
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
