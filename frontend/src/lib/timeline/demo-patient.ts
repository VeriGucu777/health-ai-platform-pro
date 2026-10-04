/** True when patient notes mark idempotent synthetic demo seed data. */
export function isSyntheticDemoPatient(notes: string | null | undefined): boolean {
  if (!notes) {
    return false;
  }
  return notes.trim().toLowerCase().startsWith("seed:demo");
}
