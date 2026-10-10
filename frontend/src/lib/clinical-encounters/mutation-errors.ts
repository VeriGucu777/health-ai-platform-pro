import { ApiClientError } from "@/lib/api/client";

export type EncounterMutationErrorLabels = {
  notFoundOrDenied: string;
  validation: string;
  conflictStale: string;
  terminalEdit: string;
  server: string;
  accessDenied: string;
  generic: string;
};

export function resolveEncounterMutationErrorMessage(
  error: unknown,
  labels: EncounterMutationErrorLabels,
): string {
  if (!(error instanceof ApiClientError)) {
    return labels.generic;
  }

  if (error.status === 404) {
    return labels.notFoundOrDenied;
  }

  if (error.status === 403) {
    return labels.accessDenied;
  }

  if (error.status === 409) {
    return labels.conflictStale;
  }

  if (error.status === 400 || error.status === 422) {
    return labels.validation;
  }

  if (error.status >= 500) {
    return labels.server;
  }

  return labels.generic;
}
