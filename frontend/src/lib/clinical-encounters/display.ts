import type { EncounterStatus } from "@/lib/api/clinical-encounters";

export function formatEncounterStatusLabel(
  status: EncounterStatus,
  labels: Record<string, string>,
): string {
  return labels[status] ?? status;
}
