const API_V1_PREFIX = "/api/v1";

function trimTrailingSlash(value: string): string {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

/** Dev-only: browser calls same-origin /api/v1; Next rewrites to API_PROXY_TARGET (no CORS). */
export function isDevApiProxyEnabled(): boolean {
  return (
    process.env.NODE_ENV === "development" &&
    process.env.NEXT_PUBLIC_API_USE_DEV_PROXY === "true"
  );
}

function devProxyBackendOrigin(): string | null {
  const target = process.env.API_PROXY_TARGET?.trim();
  if (!target) {
    return null;
  }
  return trimTrailingSlash(target);
}

/**
 * Reads the public API base URL from environment configuration.
 * Components must use this helper instead of hard-coding backend URLs.
 */
export function getApiBaseUrl(): string {
  if (isDevApiProxyEnabled()) {
    if (typeof window !== "undefined") {
      return "";
    }
    const origin = devProxyBackendOrigin();
    if (origin) {
      return origin;
    }
  }

  const configured = process.env.NEXT_PUBLIC_API_BASE_URL;

  if (!configured) {
    if (process.env.NODE_ENV === "production") {
      throw new Error(
        "NEXT_PUBLIC_API_BASE_URL is required in production builds.",
      );
    }

    return "http://127.0.0.1:8001";
  }

  return trimTrailingSlash(configured);
}

export function getApiV1BaseUrl(): string {
  if (isDevApiProxyEnabled() && typeof window !== "undefined") {
    return API_V1_PREFIX;
  }
  return `${getApiBaseUrl()}${API_V1_PREFIX}`;
}

export const apiConfig = {
  v1Prefix: API_V1_PREFIX,
} as const;
