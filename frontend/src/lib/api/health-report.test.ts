import { afterEach, describe, expect, it, vi } from "vitest";
describe("fetchHealthSummaryPdf", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.resetModules();
  });

  it("returns pdf blob on success", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      blob: () => Promise.resolve(new Blob(["pdf"], { type: "application/pdf" })),
      headers: new Headers({
        "Content-Disposition": 'attachment; filename="report.pdf"',
      }),
    }));

    vi.doMock("@/lib/config/env", () => ({
      getApiV1BaseUrl: () => "http://127.0.0.1:8001/api/v1",
    }));

    const { fetchHealthSummaryPdf } = await import("@/lib/api/health-report");
    const result = await fetchHealthSummaryPdf("token", "patient-1");

    expect(result.filename).toBe("report.pdf");
    expect(result.blob.type).toBe("application/pdf");
    expect(fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8001/api/v1/patients/patient-1/reports/health-summary.pdf",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer token",
          "Accept-Language": "en-US,en;q=0.9",
        }),
      }),
    );
  });

  it("does not send unsupported locale values in the query string", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      blob: () => Promise.resolve(new Blob(["pdf"], { type: "application/pdf" })),
      headers: new Headers(),
    }));

    vi.doMock("@/lib/config/env", () => ({
      getApiV1BaseUrl: () => "http://127.0.0.1:8001/api/v1",
    }));

    const { fetchHealthSummaryPdf } = await import("@/lib/api/health-report");
    await fetchHealthSummaryPdf("token", "patient-1", { locale: "de" });

    expect(fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8001/api/v1/patients/patient-1/reports/health-summary.pdf",
      expect.any(Object),
    );
  });

  it("includes locale query param when provided", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      blob: () => Promise.resolve(new Blob(["pdf"], { type: "application/pdf" })),
      headers: new Headers(),
    }));

    vi.doMock("@/lib/config/env", () => ({
      getApiV1BaseUrl: () => "http://127.0.0.1:8001/api/v1",
    }));

    const { fetchHealthSummaryPdf } = await import("@/lib/api/health-report");
    await fetchHealthSummaryPdf("token", "patient-1", { locale: "tr" });

    expect(fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8001/api/v1/patients/patient-1/reports/health-summary.pdf?locale=tr",
      expect.objectContaining({
        headers: expect.objectContaining({
          "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
        }),
      }),
    );
  });

  it("surfaces network failures to the caller", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    vi.doMock("@/lib/config/env", () => ({
      getApiV1BaseUrl: () => "/api/v1",
    }));

    const { fetchHealthSummaryPdf } = await import("@/lib/api/health-report");
    await expect(fetchHealthSummaryPdf("token", "patient-1")).rejects.toThrow("Failed to fetch");
  });

  it("throws ApiClientError on pdf failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      headers: new Headers({ "content-type": "application/json" }),
      json: () => Promise.resolve({ message: "Patient not found" }),
    }));

    vi.doMock("@/lib/config/env", () => ({
      getApiV1BaseUrl: () => "/api/v1",
    }));

    const { fetchHealthSummaryPdf } = await import("@/lib/api/health-report");
    await expect(fetchHealthSummaryPdf("token", "missing")).rejects.toMatchObject({
      status: 404,
      message: "Patient not found",
    });
  });
});
