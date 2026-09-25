import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LoginForm } from "@/components/auth/LoginForm";
import { ApiClientError } from "@/lib/api/client";
import { getCommonContent } from "@/lib/i18n/content";
import type { SupportedLocale } from "@/lib/i18n/locale";

const loginMock = vi.fn();
const pushMock = vi.fn();
let mockLocale: SupportedLocale = "en";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ login: loginMock }),
}));

vi.mock("@/lib/i18n/use-locale", () => ({
  useLocale: () => ({
    content: getCommonContent(mockLocale),
    locale: mockLocale,
  }),
}));

describe("LoginForm", () => {
  afterEach(() => {
    cleanup();
    loginMock.mockReset();
    pushMock.mockClear();
    mockLocale = "en";
  });

  async function submitLogin() {
    const content = getCommonContent(mockLocale);
    fireEvent.change(screen.getByLabelText(content.auth.emailLabel), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText(content.auth.passwordLabel), {
      target: { value: "securepass123" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: content.auth.loginSubmit }),
    );
  }

  it.each<[SupportedLocale]>([["en"], ["tr"]])(
    "shows dedicated email_not_verified message (%s)",
    async (locale) => {
      mockLocale = locale;
      const content = getCommonContent(locale);
      loginMock.mockRejectedValueOnce(
        new ApiClientError("Email address is not verified", 403, {
          success: false,
          message: "Email address is not verified",
          details: { reason_code: "email_not_verified" },
        }),
      );

      render(<LoginForm />);
      await submitLogin();

      const alert = await screen.findByRole("alert");
      expect(alert.textContent).toBe(content.auth.emailNotVerified);
      expect(content.auth.emailNotVerified.toLowerCase()).toMatch(/verif|doğrul/);
      expect(content.auth.emailNotVerified.toLowerCase()).toMatch(/inbox|gelen|mesaj|message/);
    },
  );

  it("shows API message for invalid credentials (401), not email_not_verified copy", async () => {
    const invalidMessage = "Invalid email or password";
    loginMock.mockRejectedValueOnce(
      new ApiClientError(invalidMessage, 401, {
        success: false,
        message: invalidMessage,
      }),
    );

    render(<LoginForm />);
    await submitLogin();

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe(invalidMessage);
    expect(alert.textContent).not.toBe(getCommonContent("en").auth.emailNotVerified);
  });

  it("shows API message for generic 403 without email_not_verified reason", async () => {
    const forbiddenMessage = "Insufficient permissions";
    loginMock.mockRejectedValueOnce(
      new ApiClientError(forbiddenMessage, 403, {
        success: false,
        message: forbiddenMessage,
        details: { reason_code: "denied_role" },
      }),
    );

    render(<LoginForm />);
    await submitLogin();

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe(forbiddenMessage);
  });

  it("falls back to generic login error for non-ApiClientError failures", async () => {
    loginMock.mockRejectedValueOnce(new Error("unexpected"));

    render(<LoginForm />);
    await submitLogin();

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe(getCommonContent("en").auth.loginError);
  });
});
