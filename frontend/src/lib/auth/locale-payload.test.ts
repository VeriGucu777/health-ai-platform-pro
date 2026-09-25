import { describe, expect, it, vi, beforeEach } from "vitest";
import { resendVerificationRequest } from "@/lib/auth/api";

const post = vi.fn().mockResolvedValue({ message: "ok" });

vi.mock("@/lib/api/client", () => ({
  createApiClient: () => ({ post }),
}));

vi.mock("@/lib/config/env", () => ({
  getApiV1BaseUrl: () => "http://127.0.0.1:8001/api/v1",
}));

describe("verification locale payload", () => {
  beforeEach(() => {
    post.mockClear();
  });

  it("resend includes active locale when provided", async () => {
    await resendVerificationRequest("user@example.com", "tr");
    expect(post).toHaveBeenCalledWith("/auth/resend-verification", {
      body: { email: "user@example.com", locale: "tr" },
    });
  });

  it("resend omits locale when not provided", async () => {
    await resendVerificationRequest("user@example.com");
    expect(post).toHaveBeenCalledWith("/auth/resend-verification", {
      body: { email: "user@example.com" },
    });
  });
});
