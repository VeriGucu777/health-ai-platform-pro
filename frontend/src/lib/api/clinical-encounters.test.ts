import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createClinicalEncounter,
  fetchClinicalEncounterDetail,
  fetchPatientEncounters,
} from "@/lib/api/clinical-encounters";

const get = vi.fn();
const post = vi.fn();

vi.mock("@/lib/api/index", () => ({
  apiClient: {
    get: (...args: unknown[]) => get(...args),
    post: (...args: unknown[]) => post(...args),
  },
}));

describe("clinical-encounters API", () => {
  beforeEach(() => {
    get.mockReset();
    post.mockReset();
  });

  it("fetchPatientEncounters calls list endpoint", async () => {
    get.mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 });
    await fetchPatientEncounters("token", "patient-1", { limit: 50, offset: 0 });
    expect(get).toHaveBeenCalledWith("/patients/patient-1/encounters?limit=50&offset=0", {
      authToken: "token",
    });
  });

  it("createClinicalEncounter sends only specialty_key and locale", async () => {
    post.mockResolvedValue({ encounter: { id: "enc-1" } });
    await createClinicalEncounter("token", "patient-1", {
      specialty_key: "cardiology",
      locale: "tr",
    });
    expect(post).toHaveBeenCalledWith("/patients/patient-1/encounters", {
      authToken: "token",
      body: { specialty_key: "cardiology", locale: "tr" },
    });
    const body = post.mock.calls[0][1].body as Record<string, unknown>;
    expect(body).not.toHaveProperty("clinician_user_id");
    expect(body).not.toHaveProperty("organization_id");
    expect(body).not.toHaveProperty("status");
  });

  it("fetchClinicalEncounterDetail calls detail endpoint", async () => {
    get.mockResolvedValue({ encounter: { id: "enc-1" }, complaints: [], findings: [], question_responses: [] });
    await fetchClinicalEncounterDetail("token", "enc-1");
    expect(get).toHaveBeenCalledWith("/encounters/enc-1", { authToken: "token" });
  });
});
