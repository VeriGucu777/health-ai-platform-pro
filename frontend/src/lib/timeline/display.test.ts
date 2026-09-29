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
