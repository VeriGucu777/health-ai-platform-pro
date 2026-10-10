export function isComplaintInputValid(complaintKey: string, displayText: string): boolean {
  return complaintKey.trim().length > 0 || displayText.trim().length > 0;
}

export function parseOptionalFiniteNumber(raw: string): number | null {
  const trimmed = raw.trim();
  if (!trimmed) {
    return null;
  }
  const value = Number(trimmed);
  if (!Number.isFinite(value)) {
    return null;
  }
  return value;
}

export function isFindingValueProvided(valueCode: string, valueNumericRaw: string): boolean {
  return valueCode.trim().length > 0 || parseOptionalFiniteNumber(valueNumericRaw) !== null;
}
