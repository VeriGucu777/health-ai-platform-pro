import { describe, expect, it } from "vitest";
import { commonContent as en } from "@/content/en/common";
import { commonContent as tr } from "@/content/tr/common";

describe("management i18n", () => {
  it("includes TR and EN management nav and core actions", () => {
    expect(en.nav.management.length).toBeGreaterThan(0);
    expect(tr.nav.management.length).toBeGreaterThan(0);
    expect(en.management.assignDoctor).not.toBe(tr.management.assignDoctor);
    expect(en.management.removeAssignment).not.toBe(tr.management.removeAssignment);
    expect(en.management.errors.duplicateAssignment).toBeTruthy();
    expect(tr.management.errors.duplicateAssignment).toBeTruthy();
  });

  it("uses distinct create loading and success copy in TR and EN", () => {
    expect(en.management.onboarding.submitting).toBe("Creating patient…");
    expect(tr.management.onboarding.submitting).toBe("Hasta oluşturuluyor…");
    expect(en.management.onboarding.createSuccess).toBe("Patient created successfully.");
    expect(tr.management.onboarding.createSuccess).toBe("Hasta başarıyla oluşturuldu.");
  });
});
