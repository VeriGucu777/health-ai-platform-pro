import { describe, expect, it } from "vitest";

import { validateBuildNodeEnv } from "./validate-build-env.mjs";

describe("validateBuildNodeEnv", () => {
  it("allows undefined NODE_ENV", () => {
    expect(validateBuildNodeEnv(undefined)).toEqual({ ok: true });
  });

  it("allows empty NODE_ENV", () => {
    expect(validateBuildNodeEnv("")).toEqual({ ok: true });
  });

  it("allows whitespace-only NODE_ENV", () => {
    expect(validateBuildNodeEnv("   ")).toEqual({ ok: true });
  });

  it("allows production", () => {
    expect(validateBuildNodeEnv("production")).toEqual({ ok: true });
  });

  it("rejects development", () => {
    const result = validateBuildNodeEnv("development");
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.message).toContain("development");
      expect(result.message).toContain("unset or 'production'");
    }
  });

  it("rejects test", () => {
    const result = validateBuildNodeEnv("test");
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.message).toContain("test");
    }
  });

  it("rejects custom unexpected value", () => {
    const result = validateBuildNodeEnv("staging");
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.message).toContain("staging");
    }
  });
});
