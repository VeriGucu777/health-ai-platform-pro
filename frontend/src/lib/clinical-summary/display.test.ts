import { describe, expect, it } from "vitest";
import {
  formatClinicalSummaryItemLabel,
  formatClinicalSummaryItemMessage,
} from "@/lib/clinical-summary/display";
import type { ClinicalSummaryOverviewItem } from "@/lib/api/clinical-summary";

const copy = {
  itemLabels: {
    fasting_glucose_trend: "Açlık kan şekeri",
  },
  trendMessages: {
    recorded_no_direction:
      "{count} karşılaştırılabilir {context} ölçümü kayıtlı; yönlü trend için yeterli veri yok.",
  },
};

describe("clinical summary display", () => {
  it("uses localized item label when available", () => {
    const item: ClinicalSummaryOverviewItem = {
      key: "fasting_glucose_trend",
      severity: "info",
      label: "Fasting blood glucose",
      message: "English fallback",
      trend_status: null,
      source_count: 2,
      data_window_start: null,
      data_window_end: null,
    };
    expect(formatClinicalSummaryItemLabel(item, copy)).toBe("Açlık kan şekeri");
  });

  it("localizes trend message from trend_status", () => {
    const item: ClinicalSummaryOverviewItem = {
      key: "fasting_glucose_trend",
      severity: "info",
      label: "Fasting blood glucose",
      message: "English fallback",
      trend_status: "recorded_no_direction",
      source_count: 2,
      data_window_start: null,
      data_window_end: null,
    };
    expect(formatClinicalSummaryItemMessage(item, copy, "tr")).toContain("açlık");
    expect(formatClinicalSummaryItemMessage(item, copy, "tr")).not.toContain("English fallback");
  });
});
