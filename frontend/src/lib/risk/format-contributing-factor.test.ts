import { describe, expect, it } from "vitest";
import { formatContributingFactorMessage } from "@/lib/risk/format-contributing-factor";
import type { RiskContributingFactor } from "@/lib/api/risk-history";

const base: RiskContributingFactor = {
  factor: "blood_pressure_monitoring",
  status: "present",
  severity: "info",
  weight: 0.2,
  message: "Default wire message.",
  source: "health_measurement",
};

describe("formatContributingFactorMessage", () => {
  it("prefers message_tr when locale is tr", () => {
    const factor: RiskContributingFactor = {
      ...base,
      message_tr: "Kan basıncı ölçümleri izlenmektedir.",
      message_en: "Blood pressure readings are monitored.",
    };
    expect(formatContributingFactorMessage(factor, "tr")).toBe(
      "Kan basıncı ölçümleri izlenmektedir.",
    );
  });

  it("prefers message_en when locale is en", () => {
    const factor: RiskContributingFactor = {
      ...base,
      message_tr: "Türkçe metin.",
      message_en: "English clinical context line.",
    };
    expect(formatContributingFactorMessage(factor, "en")).toBe("English clinical context line.");
  });

  it("falls back to message when locale-specific field is absent", () => {
    expect(formatContributingFactorMessage(base, "tr")).toBe("Default wire message.");
  });
});
