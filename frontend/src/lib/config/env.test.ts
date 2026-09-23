import { afterEach, describe, expect, it, vi } from "vitest";

describe("getApiV1BaseUrl", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("uses same-origin /api/v1 in the browser when dev proxy is enabled", async () => {
    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("NEXT_PUBLIC_API_USE_DEV_PROXY", "true");
    vi.stubEnv("API_PROXY_TARGET", "https://api.example.com");
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.com");
    vi.stubGlobal("window", {} as Window);

    const { getApiV1BaseUrl } = await import("@/lib/config/env");
    expect(getApiV1BaseUrl()).toBe("/api/v1");
  });

  it("uses configured public base URL when dev proxy is disabled", async () => {
    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("NEXT_PUBLIC_API_USE_DEV_PROXY", "false");
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://127.0.0.1:8001");

    const { getApiV1BaseUrl } = await import("@/lib/config/env");
    expect(getApiV1BaseUrl()).toBe("http://127.0.0.1:8001/api/v1");
  });
});
