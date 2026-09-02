"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { FormInput } from "@/components/ui/FormInput";
import { useAuth } from "@/lib/auth";
import { ApiClientError } from "@/lib/api/client";
import { useLocale } from "@/lib/i18n/use-locale";

export function RegisterForm() {
  const { content } = useLocale();
  const { register } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    const formData = new FormData(event.currentTarget);
    const email = String(formData.get("email") ?? "").trim();
    const password = String(formData.get("password") ?? "");
    const confirmPassword = String(formData.get("confirmPassword") ?? "");
    const first_name = String(formData.get("first_name") ?? "").trim();
    const last_name = String(formData.get("last_name") ?? "").trim();

    if (password !== confirmPassword) {
      setError(content.auth.passwordMismatch);
      setIsSubmitting(false);
      return;
    }

    try {
      await register({ email, password, first_name, last_name });
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
          id="register-first-name"
          name="first_name"
          type="text"
          autoComplete="given-name"
          label={content.auth.firstNameLabel}
          placeholder={content.auth.firstNamePlaceholder}
          required
        />
        <FormInput
          id="register-last-name"
          name="last_name"
          type="text"
          autoComplete="family-name"
          label={content.auth.lastNameLabel}
          placeholder={content.auth.lastNamePlaceholder}
          required
        />
        <FormInput
          id="register-email"
          name="email"
          type="email"
          autoComplete="email"
          label={content.auth.emailLabel}
          placeholder={content.auth.emailPlaceholder}
          required
        />
        <FormInput
          id="register-password"
          name="password"
          type="password"
          autoComplete="new-password"
          label={content.auth.passwordLabel}
          placeholder={content.auth.passwordPlaceholder}
          required
          minLength={8}
        />
        <FormInput
          id="register-confirm-password"
          name="confirmPassword"
          type="password"
          autoComplete="new-password"
          label={content.auth.confirmPasswordLabel}
          placeholder={content.auth.confirmPasswordPlaceholder}
          required
          minLength={8}
        />

        {error ? (
          <p className="break-words rounded-lg bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
            {error}
          </p>
        ) : null}

        <Button type="submit" fullWidth disabled={isSubmitting}>
          {content.auth.registerSubmit}
        </Button>
      </form>

      <p className="break-words text-center text-sm text-text-secondary">
        {content.auth.hasAccount}{" "}
        <Link href="/login" className="font-medium text-brand-700 hover:text-brand-800">
          {content.nav.login}
        </Link>
      </p>
    </>
  );
}
