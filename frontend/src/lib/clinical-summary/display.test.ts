import { describe, expect, it } from "vitest";
import {
  formatClinicalSummaryCompactPeriodRange,
  formatClinicalSummaryItemLabel,
  formatClinicalSummaryItemMessage,
  formatClinicalSummaryOverviewSubtitle,
} from "@/lib/clinical-summary/display";
import type { ClinicalSummaryOverviewItem } from "@/lib/api/clinical-summary";

const copy = {
  itemLabels: {
    fasting_glucose_trend: "Açlık kan şekeri",
    laboratory_summary: "Laboratuvar",
  },
  trendMessages: {
    recorded_no_direction:
      "{period_range} arasında {count} karşılaştırılabilir {context} ölçümü kayıtlı; yönlü değerlendirme için yeterli veri bulunmuyor.",
    decreasing:
      "{period_range} arasında kayıtlı {count} karşılaştırılabilir {context} ölçümünde azalış eğilimi izleniyor.",
  },
  itemMessages: {
    trend_hybrid_decreasing:
      "{period_range} arasında kayıtlı {count} karşılaştırılabilir {context} ölçümünde azalış eğilimi izleniyor (bilgilendirme).",
    trend_hybrid_no_direction:
      "{period_range} arasında {count} karşılaştırılabilir {context} ölçümü kayıtlı; yönlü değerlendirme için yeterli veri bulunmuyor.",
    lipid_panel_with_triglycerides:
      "En güncel lipid paneli ({record_date}): LDL {ldl} mg/dL, HDL {hdl} mg/dL ve trigliserid {triglycerides} mg/dL kayıtlı.",
    echocardiography_on_file: "Ekokardiyografi raporu ({record_date}) kayıtlarda mevcut.",
    cardiac_care_plan_documented:
      "Kan basıncı takibi, 3 ay içinde lipid kontrolü ve aktiviteye ilişkin takip planı kayıtlarda yer almaktadır.",
    upcoming_follow_up_date: "Yaklaşan kontrol randevusu: {date}.",
    overdue_follow_up_date:
      "{date} tarihli planlanmış kontrol için sistemde tamamlanma kaydı bulunmuyor.",
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
      message_params: {
        ldl: "156",
        hdl: "42",
        triglycerides: "190",
        record_date: "2026-05-12",
      },
      trend_status: null,
      source_count: 1,
      data_window_start: null,
      data_window_end: null,
    };
    const text = formatClinicalSummaryItemMessage(item, copy, "tr", (value) => `FMT:${value}`);
    expect(text).toContain("156");
    expect(text).toContain("trigliserid 190");
    expect(text).toContain("FMT:2026-05-12");
    expect(text.toLowerCase()).not.toContain("synthetic");
  });

  it("uses cardiac care plan template instead of raw English treatment text", () => {
    const item: ClinicalSummaryOverviewItem = {
      key: "medication_treatment_follow_up",
      severity: "info",
      label: "Medication and follow-up",
      message: "Blood pressure targets, lipid recheck in 3 months, and activity guidance",
      message_key: "cardiac_care_plan_documented",
      message_params: {},
      trend_status: null,
      source_count: 1,
      data_window_start: null,
      data_window_end: null,
    };
    const text = formatClinicalSummaryItemMessage(item, copy, "tr");
    expect(text).toContain("Kan basıncı takibi");
    expect(text).not.toContain("Blood pressure targets");
  });

  it("formats overdue follow-up date with locale formatter", () => {
    const item: ClinicalSummaryOverviewItem = {
      key: "overdue_follow_up",
      severity: "info",
      label: "Overdue follow-up",
      message: "The planned follow-up dated 2026-08-10 has no completion record in the system.",
      message_key: "overdue_follow_up_date",
      message_params: { date: "2026-08-10" },
      trend_status: null,
      source_count: 1,
      data_window_start: null,
      data_window_end: null,
    };
    const text = formatClinicalSummaryItemMessage(item, copy, "tr", (value) => `FMT:${value}`);
    expect(text).toContain("FMT:2026-08-10");
    expect(text).toContain("tamamlanma kaydı bulunmuyor");
  });

  it("formats upcoming appointment date with locale formatter", () => {
    const item: ClinicalSummaryOverviewItem = {
      key: "upcoming_follow_up",
      severity: "info",
      label: "Upcoming follow-up",
      message: "Next scheduled follow-up on 2026-10-15 (UTC date).",
      message_key: "upcoming_follow_up_date",
      message_params: { date: "2026-10-15" },
      trend_status: null,
      source_count: 1,
      data_window_start: null,
      data_window_end: null,
    };
    const text = formatClinicalSummaryItemMessage(item, copy, "tr", (value) => `FMT:${value}`);
    expect(text).toBe("Yaklaşan kontrol randevusu: FMT:2026-10-15.");
  });

  it("localizes hybrid trend message with item data window", () => {
    const item: ClinicalSummaryOverviewItem = {
      key: "blood_pressure_trend",
      severity: "info",
      label: "Blood pressure",
      message: "English fallback",
      message_key: "trend_hybrid_decreasing",
      message_params: { window_start: "2026-06-15", window_end: "2026-08-22" },
      trend_status: "decreasing",
      source_count: 3,
      data_window_start: null,
      data_window_end: null,
    };
    const text = formatClinicalSummaryItemMessage(item, copy, "tr");
    expect(text).toContain("sistolik tansiyon");
    expect(text).toContain("azalış eğilimi");
    expect(text).toContain("3");
  });

  it("builds overview subtitle from API period with locale dates", () => {
    const subtitle = formatClinicalSummaryOverviewSubtitle(
      "2026-06-15",
      "2026-10-05",
      (value) => `DATE(${value})`,
      "Fallback text",
      "klinik görünümü",
    );
    expect(subtitle).toBe("DATE(2026-06-15) – DATE(2026-10-05) klinik görünümü");
  });

  it("uses fallback subtitle when period is missing", () => {
    expect(
      formatClinicalSummaryOverviewSubtitle(null, null, (v) => v, "Fallback text", "suffix"),
    ).toBe("Fallback text");
  });

  it("formats compact period range for same-year windows", () => {
    const range = formatClinicalSummaryCompactPeriodRange("2026-06-15", "2026-08-22", "tr");
    expect(range).toMatch(/15/);
    expect(range).toMatch(/22/);
    expect(range).toMatch(/2026/);
  });
});
