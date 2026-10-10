import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  addEncounterComplaint,
  addEncounterFinding,
  createClinicalEncounter,
  cancelClinicalEncounter,
  deactivateEncounterComplaint,
  fetchClinicalEncounterDetail,
  fetchPatientEncounters,
  finalizeClinicalEncounter,
  upsertEncounterQuestionResponse,
} from "@/lib/api/clinical-encounters";

const get = vi.fn();
const post = vi.fn();
const put = vi.fn();
const del = vi.fn();

vi.mock("@/lib/api/index", () => ({
  apiClient: {
    get: (...args: unknown[]) => get(...args),
    post: (...args: unknown[]) => post(...args),
    put: (...args: unknown[]) => put(...args),
    delete: (...args: unknown[]) => del(...args),
  },
}));

describe("clinical-encounters API", () => {
  beforeEach(() => {
    get.mockReset();
    post.mockReset();
    put.mockReset();
    del.mockReset();
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

  it("addEncounterComplaint sends allowed fields only", async () => {
    post.mockResolvedValue({ id: "c1" });
    await addEncounterComplaint("token", "enc-1", {
      complaint_key: "chest_pain",
      clinician_display_text: "Chest pain",
      is_primary: true,
      negated: false,
    });
    expect(post).toHaveBeenCalledWith("/encounters/enc-1/complaints", {
      authToken: "token",
      body: {
        complaint_key: "chest_pain",
        clinician_display_text: "Chest pain",
        is_primary: true,
        negated: false,
      },
    });
    const body = post.mock.calls[0][1].body as Record<string, unknown>;
    expect(body).not.toHaveProperty("clinician_user_id");
    expect(body).not.toHaveProperty("recorded_by");
  });

  it("addEncounterFinding sends finding payload", async () => {
    post.mockResolvedValue({ id: "f1" });
    await addEncounterFinding("token", "enc-1", {
      finding_type: "symptom",
      finding_key: "dyspnea",
      value_numeric: 2,
      source: "clinician_observed",
    });
    expect(post).toHaveBeenCalledWith("/encounters/enc-1/findings", {
      authToken: "token",
      body: {
        finding_type: "symptom",
        finding_key: "dyspnea",
        value_numeric: 2,
        source: "clinician_observed",
      },
    });
  });

  it("upsertEncounterQuestionResponse uses PUT and encoded key", async () => {
    put.mockResolvedValue({ id: "r1" });
    await upsertEncounterQuestionResponse("token", "enc-1", "has_fever", {
      answer_type: "boolean",
      answer_code: "yes",
    });
    expect(put).toHaveBeenCalledWith("/encounters/enc-1/question-responses/has_fever", {
      authToken: "token",
      body: { answer_type: "boolean", answer_code: "yes" },
    });
  });

  it("deactivateEncounterComplaint uses DELETE", async () => {
    del.mockResolvedValue(undefined);
    await deactivateEncounterComplaint("token", "enc-1", "complaint-1");
    expect(del).toHaveBeenCalledWith("/encounters/enc-1/complaints/complaint-1", { authToken: "token" });
  });

  it("finalizeClinicalEncounter sends expected_version and summary sections only", async () => {
    post.mockResolvedValue({ encounter: { id: "enc-1" } });
    await finalizeClinicalEncounter("token", "enc-1", {
      expected_version: 3,
      summary_sections: [{ section_key: "assessment", clinician_text: "Stable" }],
      clinician_note: "Note",
    });
    expect(post).toHaveBeenCalledWith("/encounters/enc-1/finalize", {
      authToken: "token",
      body: {
        expected_version: 3,
        summary_sections: [{ section_key: "assessment", clinician_text: "Stable" }],
        clinician_note: "Note",
      },
    });
    const body = post.mock.calls.at(-1)?.[1].body as Record<string, unknown>;
    expect(body).not.toHaveProperty("finalized_by");
    expect(body).not.toHaveProperty("status");
  });

  it("cancelClinicalEncounter sends expected_version only", async () => {
    post.mockResolvedValue({ id: "enc-1", status: "cancelled" });
    await cancelClinicalEncounter("token", "enc-1", { expected_version: 2 });
    expect(post).toHaveBeenCalledWith("/encounters/enc-1/cancel", {
      authToken: "token",
      body: { expected_version: 2 },
    });
  });
});
