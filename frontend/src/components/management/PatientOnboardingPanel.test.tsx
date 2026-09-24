import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PatientOnboardingPanel } from "@/components/management/PatientOnboardingPanel";

const localeFixture = {
  content: {
    common: { loading: "Loading…" },
    management: {
      errors: {
        duplicateConsent: "Duplicate consent",
        generic: "Generic error",
        duplicateAssignment: "",
        duplicatePrimary: "",
        patientNotFound: "",
        assignmentNotFound: "",
        doctorNotFound: "",
      },
      onboarding: {
        createSection: "Register",
        createHint: "Hint",
        consentSection: "Consent",
        consentHint: "Consent hint",
        firstName: "First",
        lastName: "Last",
        dateOfBirth: "DOB",
        gender: "Gender",
        genderOptions: { female: "Female", male: "Male", other: "Other" },
        demoNotesDefault: "Synthetic notes",
        consentGrantFailedWarning: "Consent failed warning",
        phoneOptional: "Phone",
        notesOptional: "Notes",
        grantConsentOnCreate: "Grant on create",
        submitCreate: "Create patient",
        submitting: "Saving",
        createSuccess: "Patient created",
        selectPatientForConsent: "Select patient",
        consentStatusGranted: "Granted",
        consentStatusNotGranted: "Not granted",
        grantConsent: "Grant",
        revokeConsent: "Revoke",
        noConsentHistory: "No history",
        consentTypes: { clinical_data_processing: "Clinical" },
        consentStatuses: { granted: "Granted", revoked: "Revoked" },
      },
    },
  },
  formatDateTime: (value: string) => value,
};

vi.mock("@/lib/i18n/use-locale", () => ({
  useLocale: () => localeFixture,
}));

const createPatient = vi.fn();
const grantPatientConsent = vi.fn();
const fetchPatientConsents = vi.fn();

vi.mock("@/lib/api/patients", () => ({
  createPatient: (...args: unknown[]) => createPatient(...args),
}));

vi.mock("@/lib/api/consents", () => ({
  fetchPatientConsents: (...args: unknown[]) => fetchPatientConsents(...args),
  grantPatientConsent: (...args: unknown[]) => grantPatientConsent(...args),
  revokePatientConsent: vi.fn(),
}));

describe("PatientOnboardingPanel", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    vi.clearAllMocks();
    fetchPatientConsents.mockResolvedValue({ items: [] });
    createPatient.mockResolvedValue({
      id: "new-pat",
      owner_id: "admin",
      first_name: "Demo",
      last_name: "Pilot Patient",
      date_of_birth: "1992-04-15",
      gender: "female",
      phone: null,
      notes: "Synthetic notes",
      is_active: true,
      created_at: "",
      updated_at: "",
    });
    grantPatientConsent.mockResolvedValue({});
  });

  it("submits canonical gender and shows success", async () => {
    const onPatientCreated = vi.fn();

    render(
      <PatientOnboardingPanel
        accessToken="token"
        selectedPatientId=""
        onPatientCreated={onPatientCreated}
        onConsentChanged={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Create patient" }));

    await waitFor(() => {
      expect(createPatient).toHaveBeenCalledWith(
        "token",
        expect.objectContaining({ gender: "female" }),
      );
    });

    expect(screen.getByText("Patient created")).toBeInTheDocument();
    expect(onPatientCreated).toHaveBeenCalled();
  });

  it("shows warning when patient is created but consent grant fails", async () => {
    const { ApiClientError } = await import("@/lib/api/client");
    grantPatientConsent.mockRejectedValue(
      new ApiClientError("An active consent already exists for this patient and consent type", 409),
    );

    render(
      <PatientOnboardingPanel
        accessToken="token"
        selectedPatientId=""
        onPatientCreated={vi.fn()}
        onConsentChanged={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Create patient" }));

    await waitFor(() => {
      expect(screen.getByText("Patient created")).toBeInTheDocument();
      expect(screen.getByText("Consent failed warning")).toBeInTheDocument();
    });
  });

  it("shows API error when patient create fails", async () => {
    const { ApiClientError } = await import("@/lib/api/client");
    createPatient.mockRejectedValue(new ApiClientError("Forbidden", 403));

    render(
      <PatientOnboardingPanel
        accessToken="token"
        selectedPatientId=""
        onPatientCreated={vi.fn()}
        onConsentChanged={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Create patient" }));

    await waitFor(() => {
      expect(screen.getByText("Forbidden")).toBeInTheDocument();
    });
  });
});
