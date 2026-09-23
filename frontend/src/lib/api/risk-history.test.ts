import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiClientError } from "@/lib/api/client";

const getMock = vi.fn();

vi.mock("@/lib/api/index", () => ({
  apiClient: {
    get: (...args: unknown[]) => getMock(...args),
  },
}));

describe("fetchRiskAssessmentHistory", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("returns risk history on success", async () => {
    getMock.mockResolvedValue({
      items: [
        {
          id: "hist-1",
          patient_id: "p1",
          assessment_type: "diabetes",
          risk_level: "low",
          score: 12,
          evaluated_at: "2026-01-01T00:00:00Z",
          result_snapshot: { contributing_factors: [], missing_inputs: [] },
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
      pages: 1,
    });

    const { fetchRiskAssessmentHistory } = await import("@/lib/api/risk-history");
    const result = await fetchRiskAssessmentHistory("token", "p1");

    expect(result.items).toHaveLength(1);
    expect(getMock).toHaveBeenCalledWith(
      "/patients/p1/risk-assessments/history?page=1&page_size=20",
      { authToken: "token" },
    );
  });

  it("returns empty history list", async () => {
    getMock.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      pages: 0,
    });

    const { fetchRiskAssessmentHistory } = await import("@/lib/api/risk-history");
    const result = await fetchRiskAssessmentHistory("token", "p1");

    expect(result.items).toEqual([]);
  });

  it("propagates 401 errors", async () => {
    getMock.mockRejectedValue(new ApiClientError("Unauthorized", 401));

    const { fetchRiskAssessmentHistory } = await import("@/lib/api/risk-history");
    await expect(fetchRiskAssessmentHistory("token", "p1")).rejects.toMatchObject({ status: 401 });
  });

  it("propagates 404 errors", async () => {
    getMock.mockRejectedValue(new ApiClientError("Not found", 404));

    const { fetchRiskAssessmentHistory } = await import("@/lib/api/risk-history");
    await expect(fetchRiskAssessmentHistory("token", "p1")).rejects.toMatchObject({ status: 404 });
  });

  it("propagates generic errors", async () => {
    getMock.mockRejectedValue(new Error("network"));

    const { fetchRiskAssessmentHistory } = await import("@/lib/api/risk-history");
    await expect(fetchRiskAssessmentHistory("token", "p1")).rejects.toThrow("network");
  });
});
