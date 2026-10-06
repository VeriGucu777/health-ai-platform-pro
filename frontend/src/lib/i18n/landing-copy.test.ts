import { describe, expect, it } from "vitest";
import { commonContent as enContent } from "@/content/en/common";
import { commonContent as trContent } from "@/content/tr/common";

describe("landing page copy", () => {
  it("uses clinician-focused TR hero without administrative workflow wording", () => {
    expect(trContent.landing.heroTitle).toBe(
      "Sağlık ekipleri için daha hızlı klinik değerlendirme",
    );
    expect(trContent.landing.heroDescription).toBe(
      "Hasta geçmişini, ölçümleri, laboratuvar, görüntüleme ve takip kayıtlarını tek ekranda özetleyerek klinik değerlendirmeyi destekler.",
    );
    expect(trContent.landing.heroTitle).not.toContain("iş akış");
    expect(trContent.landing.heroDescription).not.toContain("iş akış");
  });

  it("uses clinician-focused EN hero copy", () => {
    expect(enContent.landing.heroTitle).toBe("Faster clinical assessment for healthcare teams");
    expect(enContent.landing.heroDescription).toBe(
      "Summarizes patient history, measurements, laboratory, imaging, and follow-up records in one place to support clinical assessment.",
    );
    expect(enContent.landing.heroTitle.toLowerCase()).not.toContain("workflow");
  });

  it("preserves authenticated doctor CTA labels", () => {
    expect(trContent.landing.secondaryCtaAuthenticated).toBe("Hastalarımı görüntüle");
    expect(enContent.landing.secondaryCtaAuthenticated).toBe("View my patients");
  });

  it("keeps clinical safety trust bullets aligned with product behavior", () => {
    expect(trContent.landing.trustTitle).toBe("Klinik güvenlik öncelikli tasarım");
    expect(trContent.landing.trustPoints).toContain("Güvenli API ve erişim kontrolleri");
    expect(enContent.landing.trustPoints).toContain("Secure API and access controls");
  });
});
