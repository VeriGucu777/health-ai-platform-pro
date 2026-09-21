import { createApiClient, type ApiClient } from "@/lib/api/client";
import { getApiV1BaseUrl } from "@/lib/config/env";

let cachedClient: ApiClient | undefined;

/** Lazily created so static/SSR prerender does not require env at import time. */
export function getApiClient(): ApiClient {
  if (!cachedClient) {
    cachedClient = createApiClient(getApiV1BaseUrl());
  }

  return cachedClient;
}

/** Centralized client for the FastAPI `/api/v1` backend. */
export const apiClient: ApiClient = {
  get: (path, options) => getApiClient().get(path, options),
  post: (path, options) => getApiClient().post(path, options),
  put: (path, options) => getApiClient().put(path, options),
  patch: (path, options) => getApiClient().patch(path, options),
  delete: (path, options) => getApiClient().delete(path, options),
};

export type HealthResponse = {
  status: string;
  service?: string;
  environment?: string;
};

/** Example read-only endpoint for future connectivity checks. Not used in Phase 1A UI. */
export async function fetchHealthStatus(): Promise<HealthResponse> {
  return apiClient.get<HealthResponse>("/health");
}
