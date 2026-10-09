import { ApiClientError } from "@/lib/api/client";

export type EncounterErrorLabels = {
  notFoundOrDenied: string;
  activeConflict: string;
  generic: string;
  accessDenied: string;
};

export function resolveEncounterClientErrorMessage(
  error: unknown,
  labels: EncounterErrorLabels,
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
    return labels.activeConflict;
  }

  return labels.generic;
}
