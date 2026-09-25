"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { verifyEmailRequest } from "@/lib/auth/api";
import { useLocale } from "@/lib/i18n/use-locale";

type VerifyState = "working" | "success" | "invalid" | "missing";

export function VerifyEmailPanel() {
  const { content } = useLocale();
  const searchParams = useSearchParams();
  const router = useRouter();
  const started = useRef(false);
  const [state, setState] = useState<VerifyState>("working");

  useEffect(() => {
    if (started.current) {
      return;
    }
    started.current = true;
    const token = searchParams.get("token")?.trim();
    if (!token) {
      setState("missing");
      return;
    }
    if (typeof window !== "undefined") {
      window.history.replaceState({}, "", "/verify-email");
    } else {
      router.replace("/verify-email");
    }
    void verifyEmailRequest(token)
      .then(() => setState("success"))
      .catch(() => setState("invalid"));
  }, [router, searchParams]);

  const message =
    state === "success"
      ? content.auth.verifyEmailSuccess
      : state === "missing"
        ? content.auth.verifyEmailMissingToken
        : state === "invalid"
          ? content.auth.verifyEmailInvalid
          : content.auth.verifyEmailWorking;

  return (
    <div className="space-y-4">
      <p
        className="text-sm text-text-secondary"
        role={state === "working" ? "status" : undefined}
      >
        {message}
      </p>
      {state === "success" || state === "invalid" || state === "missing" ? (
        <p className="text-center text-sm">
          <Link href="/login" className="font-medium text-brand-700 hover:text-brand-800">
            {content.auth.checkEmailBackToLogin}
          </Link>
        </p>
      ) : null}
    </div>
  );
}
