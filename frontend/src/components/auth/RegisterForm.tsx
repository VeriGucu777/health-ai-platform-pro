"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { FormInput } from "@/components/ui/FormInput";
import { ApiClientError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useLocale } from "@/lib/i18n/use-locale";

export function RegisterForm() {
  const { content } = useLocale();
  const { register } = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    const formData = new FormData(event.currentTarget);
    const email = String(formData.get("email") ?? "");
    const password = String(formData.get("password") ?? "");
    const confirmPassword = String(formData.get("confirmPassword") ?? "");
    const first_name = String(formData.get("firstName") ?? "");
    const last_name = String(formData.get("lastName") ?? "");

    if (password !== confirmPassword) {
      setError(content.auth.passwordMismatch);
      setSubmitting(false);
      return;
    }

    try {
      await register({ email, password, first_name, last_name, role: "doctor" });
      router.push("/patients");
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError(content.auth.registerError);
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <form className="space-y-5" onSubmit={handleSubmit}>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormInput
            id="register-first-name"
            name="firstName"
            type="text"
            autoComplete="given-name"
            label={content.auth.firstNameLabel}
            required
          />
          <FormInput
            id="register-last-name"
            name="lastName"
            type="text"
            autoComplete="family-name"
            label={content.auth.lastNameLabel}
            required
          />
        </div>
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
        />
        <FormInput
          id="register-confirm-password"
          name="confirmPassword"
          type="password"
          autoComplete="new-password"
          label={content.auth.confirmPasswordLabel}
          placeholder={content.auth.confirmPasswordPlaceholder}
          required
        />

        {error ? (
          <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-900" role="alert">
            {error}
          </p>
        ) : null}

        <Button type="submit" fullWidth disabled={submitting}>
          {submitting ? content.common.loading : content.auth.registerSubmit}
        </Button>
      </form>

      <p className="mt-2 break-words text-center text-sm text-text-secondary">
        {content.auth.hasAccount}{" "}
        <Link href="/login" className="font-medium text-brand-700 hover:text-brand-800">
          {content.nav.login}
        </Link>
      </p>
    </>
  );
}
