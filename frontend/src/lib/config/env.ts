const API_V1_PREFIX = "/api/v1";

function trimTrailingSlash(value: string): string {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

/**
 * Reads the public API base URL from environment configuration.
 * Components must use this helper instead of hard-coding backend URLs.
 */
export function getApiBaseUrl(): string {
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
  return `${getApiBaseUrl()}${API_V1_PREFIX}`;
}

export const apiConfig = {
  v1Prefix: API_V1_PREFIX,
} as const;
