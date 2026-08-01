"use client";

import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { FormInput } from "@/components/ui/FormInput";
import { useLocale } from "@/lib/i18n/use-locale";

export function LoginForm() {
  const { content } = useLocale();

  return (
    <>
      <form
        action="#"
        method="post"
        className="space-y-5"
        aria-describedby="login-phase-notice"
        onSubmit={(event) => event.preventDefault()}
      >
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

        <p
          id="login-phase-notice"
          className="break-words rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-900"
        >
          {content.auth.phaseNotice}
        </p>

        <Button type="submit" fullWidth>
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
