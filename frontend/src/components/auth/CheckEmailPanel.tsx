"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { resendVerificationRequest } from "@/lib/auth/api";
import { useLocale } from "@/lib/i18n/use-locale";

export function CheckEmailPanel() {
  const { content, locale } = useLocale();
  const searchParams = useSearchParams();
  const email = (searchParams.get("email") ?? "").trim();
  const [notice, setNotice] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleResend() {
    if (!email) {
      return;
    }
    setPending(true);
    setNotice(null);
    try {
      const response = await resendVerificationRequest(email, locale);
      setNotice(response.message || content.auth.checkEmailResendSuccess);
    } catch {
      setNotice(content.auth.checkEmailResendSuccess);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-text-secondary">{content.auth.checkEmailDescription}</p>
      {email ? (
        <p className="break-all text-sm font-medium text-text-primary">{email}</p>
      ) : null}
      {notice ? (
        <p className="rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-900" role="status">
          {notice}
        </p>
      ) : null}
      <Button type="button" fullWidth disabled={!email || pending} onClick={() => void handleResend()}>
        {pending ? content.common.loading : content.auth.checkEmailResend}
      </Button>
      <p className="text-center text-sm">
        <Link href="/login" className="font-medium text-brand-700 hover:text-brand-800">
          {content.auth.checkEmailBackToLogin}
        </Link>
      </p>
    </div>
  );
}
