import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ClinicalCopilotPanel } from "@/components/patients/ClinicalCopilotPanel";
import * as clinicalCopilotApi from "@/lib/api/clinical-copilot";

const labels = {
  title: "Clinical Copilot",
  disclaimer: "Klinik karar desteği sağlar. Tanı veya tedavi kararı vermez.",
  idleHint: "Henüz değerlendirme yapılmadı.",
  evaluateButton: "Clinical Copilot ile değerlendir",
  evaluatePending: "Değerlendiriliyor…",
  noActiveRulesMessage:
    "Bu pilot sürümünde henüz onaylanmış klinik kural aktif değildir.",
  errorMessage: "Değerlendirme tamamlanamadı.",
  readOnlyHint: "Salt okunur.",
};

const mockResult = {
  evaluation_id: "e1",
  encounter_id: "enc1",
  patient_id: "p1",
  evaluation_status: "no_applicable_rules" as const,
  read_only: false,
  missing_information: [],
  review_domain_status: [],
  documentation_reminders: [],
  provenance: {
    input_snapshot_id: "snap",
    context_schema_version: "v1",
    vocabulary_id: null,
    vocabulary_version: null,
    vocabulary_manifest_hash: null,
    rule_manifest_hash: "empty",
    engine_version: "noop",
    specialty_module_version: "none",
    policy_profile_id: "none",
    policy_profile_version: "none",
    context_profile: "hypertension_v1",
    specialty_key: "cardiology",
    evaluated_at: "2026-01-01T00:00:00Z",
    rule_provenance: [],
  },
};

describe("ClinicalCopilotPanel", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders title and disclaimer", () => {
    render(
      <ClinicalCopilotPanel
        patientId="p1"
        encounterId="enc1"
        encounterStatus="active"
        accessToken="token"
        labels={labels}
        onUnauthorized={() => undefined}
      />,
    );
    expect(screen.getByRole("heading", { name: labels.title })).toBeInTheDocument();
    expect(screen.getByText(labels.disclaimer)).toBeInTheDocument();
  });

  it("shows idle hint and runs evaluate", async () => {
    const spy = vi.spyOn(clinicalCopilotApi, "evaluateClinicalCopilot").mockResolvedValue(mockResult);
    render(
      <ClinicalCopilotPanel
        patientId="p1"
        encounterId="enc1"
        encounterStatus="active"
        accessToken="token"
        labels={labels}
        onUnauthorized={() => undefined}
      />,
    );
    expect(screen.getAllByText(labels.idleHint).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: labels.evaluateButton }));
    await waitFor(() => {
      expect(screen.getByText(labels.noActiveRulesMessage)).toBeInTheDocument();
    });
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it("prevents duplicate clicks while loading", async () => {
    let resolve!: (value: typeof mockResult) => void;
    const pending = new Promise<typeof mockResult>((r) => {
      resolve = r;
    });
    const spy = vi.spyOn(clinicalCopilotApi, "evaluateClinicalCopilot").mockReturnValue(pending);
    render(
      <ClinicalCopilotPanel
        patientId="p1"
        encounterId="enc1"
        encounterStatus="active"
        accessToken="token"
        labels={labels}
        onUnauthorized={() => undefined}
      />,
    );
    const button = screen.getByRole("button", { name: labels.evaluateButton });
    fireEvent.click(button);
    fireEvent.click(button);
    expect(spy).toHaveBeenCalledTimes(1);
    resolve(mockResult);
    await waitFor(() => {
      expect(screen.getByText(labels.noActiveRulesMessage)).toBeInTheDocument();
    });
  });

  it("shows neutral no-rules message without clinical recommendation fields", async () => {
    vi.spyOn(clinicalCopilotApi, "evaluateClinicalCopilot").mockResolvedValue(mockResult);
    render(
      <ClinicalCopilotPanel
        patientId="p1"
        encounterId="enc1"
        encounterStatus="active"
        accessToken="token"
        labels={labels}
        onUnauthorized={() => undefined}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: labels.evaluateButton }));
    await waitFor(() => {
      expect(screen.getByText(labels.noActiveRulesMessage)).toBeInTheDocument();
    });
    expect(screen.queryByText(/hypertension stage/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/ilaç/i)).not.toBeInTheDocument();
  });

  it("shows read-only hint for finalized encounter", () => {
    render(
      <ClinicalCopilotPanel
        patientId="p1"
        encounterId="enc1"
        encounterStatus="finalized"
        accessToken="token"
        labels={labels}
        onUnauthorized={() => undefined}
      />,
    );
    expect(screen.getByText(labels.readOnlyHint)).toBeInTheDocument();
  });
});
