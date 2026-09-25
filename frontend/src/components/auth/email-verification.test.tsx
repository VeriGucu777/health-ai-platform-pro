import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { VerifyEmailPanel } from "@/components/auth/VerifyEmailPanel";
import { getCommonContent } from "@/lib/i18n/content";

const push = vi.fn();
const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace }),
  useSearchParams: () => new URLSearchParams("token=test-token-value"),
}));

vi.mock("@/lib/auth/api", () => ({
  verifyEmailRequest: vi.fn().mockResolvedValue({ message: "ok" }),
}));

vi.mock("@/lib/i18n/use-locale", () => ({
  useLocale: () => ({ content: getCommonContent(), locale: "en" }),
}));

describe("VerifyEmailPanel", () => {
  it("strips token from URL and shows success", async () => {
    const replaceState = vi.spyOn(window.history, "replaceState").mockImplementation(() => {});
    render(<VerifyEmailPanel />);
    expect(replaceState).toHaveBeenCalledWith({}, "", "/verify-email");
    expect(await screen.findByText(getCommonContent().auth.verifyEmailSuccess)).toBeTruthy();
    replaceState.mockRestore();
  });
});
