"use client";

import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { FormInput } from "@/components/ui/FormInput";
import { useLocale } from "@/lib/i18n/use-locale";

export function RegisterForm() {
  const { content } = useLocale();

  return (
    <>
      <form
        action="#"
        method="post"
        className="space-y-5"
        aria-describedby="register-phase-notice"
        onSubmit={(event) => event.preventDefault()}
      >
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

        <p
          id="register-phase-notice"
          className="break-words rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-900"
        >
          {content.auth.phaseNotice}
        </p>

        <Button type="submit" fullWidth>
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
