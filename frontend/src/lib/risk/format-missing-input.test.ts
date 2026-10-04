import { describe, expect, it } from "vitest";

import { commonContent as trContent } from "@/content/tr/common";
import { commonContent as enContent } from "@/content/en/common";
import { formatRiskMissingInputLine } from "@/lib/risk/format-missing-input";

const EN_REASON =
  "No systolic blood pressure measurements are available in the selected date range.";

describe("formatRiskMissingInputLine", () => {
  it("localizes known input in Turkish without English backend reason", () => {
    const line = formatRiskMissingInputLine(
      {
        input: "systolic_blood_pressure",
        reason: EN_REASON,
        impact: "",
      },
      "tr",
      {
        missingInputLabels: trContent.patientHub.missingInputLabels,
        missingInputReasons: trContent.patientHub.missingInputReasons,
      },
    );

    expect(line).toContain("Sistolik tansiyon");
    expect(line).toContain("sistolik tansiyon ölçümü bulunmuyor");
    expect(line).not.toMatch(/No systolic blood pressure/i);
    expect(line).not.toContain("systolic_blood_pressure");
  });

  it("uses localized English label and reason for known keys", () => {
    const line = formatRiskMissingInputLine(
      {
        input: "height_cm",
        reason: "Height is not recorded for this patient.",
        impact: "",
      },
      "en",
      {
        missingInputLabels: enContent.patientHub.missingInputLabels,
        missingInputReasons: enContent.patientHub.missingInputReasons,
      },
    );

    expect(line).toBe("Height: Height is not recorded for this patient.");
  });

  it("falls back to backend reason for unknown input keys", () => {
    const fallback = "Custom backend explanation for an unknown field.";
    const line = formatRiskMissingInputLine(
      {
        input: "custom_unknown_metric",
        reason: fallback,
        impact: "",
      },
      "tr",
      {
        missingInputLabels: trContent.patientHub.missingInputLabels,
        missingInputReasons: trContent.patientHub.missingInputReasons,
      },
    );

    expect(line).toBe(fallback);
    expect(line).not.toContain("custom_unknown_metric");
  });
});
