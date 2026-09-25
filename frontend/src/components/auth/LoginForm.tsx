"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { FormInput } from "@/components/ui/FormInput";
import { useAuth } from "@/lib/auth";
import { ApiClientError } from "@/lib/api/client";
import { useLocale } from "@/lib/i18n/use-locale";

export function LoginForm() {
  const { content } = useLocale();
  const { login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
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
      const next = searchParams.get("next");
      if (next && next.startsWith("/")) {
        router.push(next);
      }
    } catch (submitError) {
      if (submitError instanceof ApiClientError) {
        if (
          submitError.status === 403 &&
          submitError.body?.details?.reason_code === "email_not_verified"
        ) {
          setError(content.auth.emailNotVerified);
        } else {
          setError(submitError.message);
        }
      } else if (
        submitError instanceof TypeError &&
        /failed to fetch|networkerror/i.test(submitError.message)
      ) {
        setError(
          "Cannot reach the API. If using a remote backend from localhost, enable NEXT_PUBLIC_API_USE_DEV_PROXY in .env.local and restart the dev server.",
        );
      } else {
        setError(content.auth.loginError ?? content.auth.genericError);
      }
    } finally {
      setIsSubmitting(false);
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
          <p className="break-words rounded-lg bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
            {error}
          </p>
        ) : content.auth.phaseNotice ? (
          <p className="break-words rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-900">
            {content.auth.phaseNotice}
          </p>
        ) : null}

        <Button type="submit" fullWidth disabled={isSubmitting}>
          {isSubmitting ? content.common.loading : content.auth.loginSubmit}
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
