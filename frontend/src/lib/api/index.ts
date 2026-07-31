import { createApiClient } from "@/lib/api/client";
import { getApiV1BaseUrl } from "@/lib/config/env";

/** Centralized client for the FastAPI `/api/v1` backend. */
export const apiClient = createApiClient(getApiV1BaseUrl());

export type HealthResponse = {
  status: string;
  service?: string;
  environment?: string;
};

/** Example read-only endpoint for future connectivity checks. Not used in Phase 1A UI. */
export async function fetchHealthStatus(): Promise<HealthResponse> {
  return apiClient.get<HealthResponse>("/health");
}
