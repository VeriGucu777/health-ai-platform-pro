export type HealthResponse = {
  status: string;
  service?: string;
  environment?: string;
};

export { fetchHealthStatus } from "@/lib/auth/api";
