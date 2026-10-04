import { describe, expect, it } from "vitest";

import { formatTimelineDetail } from "@/lib/timeline/display";

describe("formatTimelineDetail", () => {
  it("hides internal seed markers in appointment detail", () => {
    const detail = formatTimelineDetail(
      "follow_up — seed:demo-enrich-a1/appt/00",
      "en",
      "appointment_scheduled",
    );
    expect(detail).toBe("follow_up");
    expect(detail).not.toMatch(/seed:/i);
  });

  it("localizes overdue follow-up detail in Turkish", () => {
    const detail = formatTimelineDetail(
      "Follow-up date passed (2025-01-01); no completion record found in the system.",
      "tr",
      "appointment_overdue",
    );
    expect(detail).toContain("Takip tarihi geçti");
    expect(detail).toContain("tamamlanma kaydı bulunmuyor");
  });

  it("localizes appointment type without seed suffix in Turkish", () => {
    const detail = formatTimelineDetail(
      "follow_up — seed:demo-enrich-a1/appt/01",
      "tr",
      "appointment_completed",
    );
    expect(detail).toBe("Takip randevusu");
    expect(detail).not.toMatch(/seed:/i);
  });
});
