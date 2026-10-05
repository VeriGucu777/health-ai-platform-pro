import { describe, expect, it } from "vitest";
import type { RiskAssessmentHistoryItem } from "@/lib/api/risk-history";
import {
  formatRiskLevelLabel,
  formatRiskScoreLabel,
  hasRiskMetricValue,
  resolveRiskHistoryLevel,
  resolveRiskHistoryScore,
} from "@/lib/risk/history-display";

const baseItem = (): RiskAssessmentHistoryItem => ({
  id: "h1",
  patient_id: "p1",
  organization_id: null,
  assessment_type: "heart_disease",
  assessment_status: "completed",
  risk_level: null,
  score: null,
  probability: null,
  model_kind: "rule_based",
  model_version: "heart_rule_based_v1",
  evaluated_by_user_id: "u1",
  evaluated_at: "2026-01-01T00:00:00Z",
  result_snapshot: null,
  created_at: "2026-01-01T00:00:00Z",
});

describe("history-display", () => {
  it("resolves score and moderate level from top-level fields", () => {
    const item = {
      ...baseItem(),
      score: 58,
      risk_level: "moderate",
    };
    expect(resolveRiskHistoryScore(item)).toBe(58);
    expect(resolveRiskHistoryLevel(item)).toBe("moderate");
    expect(formatRiskScoreLabel(58)).toBe("58");
    expect(formatRiskLevelLabel("moderate", { moderate: "Orta" })).toBe("Orta");
  });

  it("hides metrics when score and level are null", () => {
    const item = baseItem();
    expect(resolveRiskHistoryScore(item)).toBeNull();
    expect(resolveRiskHistoryLevel(item)).toBeNull();
    expect(hasRiskMetricValue(null)).toBe(false);
  });

  it("maps EN risk levels including high and very_high", () => {
    const labels = {
      low: "Low",
      moderate: "Moderate",
      high: "High",
      very_high: "Very high",
      elevated: "Elevated",
    };
    expect(formatRiskLevelLabel("high", labels)).toBe("High");
    expect(formatRiskLevelLabel("very_high", labels)).toBe("Very high");
  });

  it("falls back to snapshot score and level when top-level is empty", () => {
    const item = {
      ...baseItem(),
      result_snapshot: { score: 58, risk_level: "moderate", contributing_factors: [] },
    };
    expect(resolveRiskHistoryScore(item)).toBe(58);
    expect(resolveRiskHistoryLevel(item)).toBe("moderate");
  });
});
