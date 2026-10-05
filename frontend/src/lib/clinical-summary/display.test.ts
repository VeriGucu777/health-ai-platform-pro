import { describe, expect, it } from "vitest";
import {
  formatClinicalSummaryItemLabel,
  formatClinicalSummaryItemMessage,
} from "@/lib/clinical-summary/display";
import type { ClinicalSummaryOverviewItem } from "@/lib/api/clinical-summary";

const copy = {
  itemLabels: {
    fasting_glucose_trend: "Açlık kan şekeri",
    laboratory_summary: "Laboratuvar",
  },
  trendMessages: {
    recorded_no_direction:
      "{count} karşılaştırılabilir {context} ölçümü kayıtlı; yönlü trend için yeterli veri yok.",
    decreasing: "Son {count} karşılaştırılabilir {context} ölçümünde azalış eğilimi izleniyor.",
  },
  itemMessages: {
    lipid_panel_with_triglycerides:
      "Lipid panelinde LDL {ldl} mg/dL, HDL {hdl} mg/dL ve trigliserid {triglycerides} mg/dL kayıtlı.",
    echocardiography_on_file: "Ekokardiyografi raporu klinik kayıtlarda mevcut.",
  },
};

describe("clinical summary display", () => {
  it("uses localized item label when available", () => {
    const item: ClinicalSummaryOverviewItem = {
      key: "fasting_glucose_trend",
      severity: "info",
      label: "Fasting blood glucose",
      message: "English fallback",
      message_key: null,
      message_params: {},
      trend_status: null,
      source_count: 2,
      data_window_start: null,
      data_window_end: null,
    };
    expect(formatClinicalSummaryItemLabel(item, copy)).toBe("Açlık kan şekeri");
  });

  it("prefers message_key templates over raw backend message", () => {
    const item: ClinicalSummaryOverviewItem = {
      key: "laboratory_summary",
      severity: "info",
      label: "Laboratory",
      message: "Synthetic lipid panel (demo): LDL 156 mg/dL",
      message_key: "lipid_panel_with_triglycerides",
      message_params: { ldl: "156", hdl: "42", triglycerides: "190" },
      trend_status: null,
      source_count: 1,
      data_window_start: null,
      data_window_end: null,
    };
    const text = formatClinicalSummaryItemMessage(item, copy, "tr");
    expect(text).toContain("156");
    expect(text).toContain("trigliserid 190");
    expect(text.toLowerCase()).not.toContain("synthetic");
  });

  it("localizes trend message from trend_status", () => {
    const item: ClinicalSummaryOverviewItem = {
      key: "blood_pressure_trend",
      severity: "info",
      label: "Blood pressure",
      message: "English fallback",
      message_key: null,
      message_params: {},
      trend_status: "decreasing",
      source_count: 3,
      data_window_start: null,
      data_window_end: null,
    };
    expect(formatClinicalSummaryItemMessage(item, copy, "tr")).toContain("sistolik tansiyon");
    expect(formatClinicalSummaryItemMessage(item, copy, "tr")).toContain("azalış eğilimi");
  });
});
