import type { RiskAssessmentHistoryItem } from "@/lib/api/risk-history";

type HistoryItemWire = RiskAssessmentHistoryItem & {
  riskLevel?: string | null;
};

function readSnapshotField(snapshot: RiskAssessmentHistoryItem["result_snapshot"], key: string): unknown {
  if (!snapshot || typeof snapshot !== "object") {
    return undefined;
  }
  return (snapshot as Record<string, unknown>)[key];
}

/** True when a score or risk level should be shown (no placeholders). */
export function hasRiskMetricValue(value: string | number | null | undefined): boolean {
  if (value === null || value === undefined) {
    return false;
  }
  if (typeof value === "string") {
    return value.trim().length > 0;
  }
  if (typeof value === "number") {
    return !Number.isNaN(value);
  }
  return false;
}

export function resolveRiskHistoryScore(item: RiskAssessmentHistoryItem): number | null {
  const candidates: unknown[] = [item.score, readSnapshotField(item.result_snapshot, "score")];
  for (const candidate of candidates) {
    if (candidate === null || candidate === undefined || candidate === "") {
      continue;
    }
    const numeric = typeof candidate === "number" ? candidate : Number(candidate);
    if (!Number.isNaN(numeric)) {
      return numeric;
    }
  }
  return null;
}

export function resolveRiskHistoryLevel(item: RiskAssessmentHistoryItem): string | null {
  const wire = item as HistoryItemWire;
  const candidates: unknown[] = [
    item.risk_level,
    wire.riskLevel,
    readSnapshotField(item.result_snapshot, "risk_level"),
  ];
  for (const candidate of candidates) {
    if (typeof candidate !== "string") {
      continue;
    }
    const trimmed = candidate.trim();
    if (trimmed) {
      return trimmed.toLowerCase();
    }
  }
  return null;
}

export function formatRiskLevelLabel(level: string, labels: Record<string, string>): string {
  const key = level.trim().toLowerCase();
  if (labels[key]) {
    return labels[key];
  }
  if (key === "high" && labels.elevated) {
    return labels.elevated;
  }
  return level;
}

export function formatRiskScoreLabel(score: number): string {
  if (Number.isInteger(score)) {
    return String(score);
  }
  const rounded = Math.round(score * 10) / 10;
  return Number.isInteger(rounded) ? String(rounded) : String(rounded);
}
