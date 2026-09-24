import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PatientOnboardingPanel } from "@/components/management/PatientOnboardingPanel";
import type { Patient } from "@/lib/api/patients";



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

        submitting: "Creating patient…",

        createSuccess: "Patient created successfully.",

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

const revokePatientConsent = vi.fn();



vi.mock("@/lib/api/patients", () => ({

  createPatient: (...args: unknown[]) => createPatient(...args),

}));



vi.mock("@/lib/api/consents", () => ({

  fetchPatientConsents: (...args: unknown[]) => fetchPatientConsents(...args),

  grantPatientConsent: (...args: unknown[]) => grantPatientConsent(...args),

  revokePatientConsent: (...args: unknown[]) => revokePatientConsent(...args),

}));



const activeConsentRow = {

  id: "consent-1",

  patient_id: "pat-1",

  organization_id: "org-1",

  consent_type: "clinical_data_processing",

  status: "granted" as const,

  granted_at: "2024-01-01T00:00:00Z",

  revoked_at: null,

  recorded_by_user_id: "admin",

  version: 1,

  source: "clinic_admin",

  created_at: "2024-01-01T00:00:00Z",

};



function duplicateConsentError() {

  return import("@/lib/api/client").then(({ ApiClientError }) =>

    new ApiClientError("An active consent already exists for this patient and consent type", 409),

  );

}

function CreateWithAutoSelect(props: {
  accessToken: string;
  onConsentChanged: () => void;
}) {
  const [selectedPatientId, setSelectedPatientId] = useState("");
  return (
    <PatientOnboardingPanel
      accessToken={props.accessToken}
      selectedPatientId={selectedPatientId}
      onPatientCreated={async (patient: Patient) => {
        setSelectedPatientId(patient.id);
      }}
      onConsentChanged={props.onConsentChanged}
    />
  );
}

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

    grantPatientConsent.mockResolvedValue(activeConsentRow);

    revokePatientConsent.mockResolvedValue({

      ...activeConsentRow,

      status: "revoked",

      revoked_at: "2024-02-01T00:00:00Z",

    });

  });



  it("disables submit and shows loading label while create is in flight", async () => {

    let resolveCreate: (value: unknown) => void = () => undefined;

    createPatient.mockImplementation(

      () =>

        new Promise((resolve) => {

          resolveCreate = resolve;

        }),

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

      expect(screen.getByRole("button", { name: "Creating patient…" })).toBeDisabled();

    });



    resolveCreate({

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



    await waitFor(() => {

      expect(screen.getByRole("button", { name: "Create patient" })).toBeEnabled();

    });

  });



  it("sends only one create request on rapid double click", async () => {

    let resolveCreate: (value: unknown) => void = () => undefined;

    createPatient.mockImplementation(

      () =>

        new Promise((resolve) => {

          resolveCreate = resolve;

        }),

    );



    render(

      <PatientOnboardingPanel

        accessToken="token"

        selectedPatientId=""

        onPatientCreated={vi.fn()}

        onConsentChanged={vi.fn()}

      />,

    );



    const button = screen.getByRole("button", { name: "Create patient" });

    fireEvent.click(button);

    fireEvent.click(button);



    await waitFor(() => {

      expect(createPatient).toHaveBeenCalledTimes(1);

    });



    resolveCreate({

      id: "new-pat",

      owner_id: "admin",

      first_name: "Demo",

      last_name: "Pilot Patient",

      date_of_birth: "1992-04-15",

      gender: "female",

      phone: null,

      notes: null,

      is_active: true,

      created_at: "",

      updated_at: "",

    });

  });



  it("shows accessible success message and notifies parent", async () => {

    const onPatientCreated = vi.fn().mockResolvedValue(undefined);



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

      expect(screen.getByRole("status")).toHaveTextContent("Patient created successfully.");

    });

    expect(onPatientCreated).toHaveBeenCalled();

  });



  it("refetches and shows active consent when create-time grant returns 409 duplicate", async () => {

    grantPatientConsent.mockRejectedValue(await duplicateConsentError());

    fetchPatientConsents.mockImplementation(async (_token: string, patientId: string) => {

      if (patientId === "new-pat") {

        return { items: [{ ...activeConsentRow, patient_id: "new-pat" }] };

      }

      return { items: [] };

    });



    render(<CreateWithAutoSelect accessToken="token" onConsentChanged={vi.fn()} />);



    fireEvent.click(screen.getByRole("button", { name: "Create patient" }));



    await waitFor(() => {

      expect(screen.getByText("Granted")).toBeInTheDocument();

      expect(screen.queryByText("Duplicate consent")).not.toBeInTheDocument();

      expect(screen.queryByText("Consent failed warning")).not.toBeInTheDocument();

      expect(screen.queryByText("Not granted")).not.toBeInTheDocument();

    });

    expect(screen.getByRole("button", { name: "Revoke" })).toBeInTheDocument();

    expect(screen.queryByRole("button", { name: "Grant" })).not.toBeInTheDocument();

  });



  it("shows warning when patient is created but consent grant fails with non-409 error", async () => {

    const { ApiClientError } = await import("@/lib/api/client");

    grantPatientConsent.mockRejectedValue(new ApiClientError("Server error", 500));



    render(

      <PatientOnboardingPanel

        accessToken="token"

        selectedPatientId=""

        onPatientCreated={vi.fn().mockResolvedValue(undefined)}

        onConsentChanged={vi.fn()}

      />,

    );



    fireEvent.click(screen.getByRole("button", { name: "Create patient" }));



    await waitFor(() => {

      expect(screen.getByText("Patient created successfully.")).toBeInTheDocument();

      expect(screen.getByText(/Consent failed warning/)).toBeInTheDocument();

    });

  });



  it("shows API error when patient create fails and re-enables submit", async () => {

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

      expect(screen.getByRole("alert")).toHaveTextContent("Forbidden");

      expect(screen.getByRole("button", { name: "Create patient" })).toBeEnabled();

    });

  });



  it("shows no-consent state with grant action when list is empty", async () => {

    fetchPatientConsents.mockResolvedValue({ items: [] });



    render(

      <PatientOnboardingPanel

        accessToken="token"

        selectedPatientId="pat-1"

        onPatientCreated={vi.fn()}

        onConsentChanged={vi.fn()}

      />,

    );



    await waitFor(() => {

      expect(screen.getByText("Not granted")).toBeInTheDocument();

      expect(screen.getByRole("button", { name: "Grant" })).toBeInTheDocument();

    });

  });



  it("shows active consent without grant when list includes granted row", async () => {

    fetchPatientConsents.mockResolvedValue({ items: [activeConsentRow] });



    render(

      <PatientOnboardingPanel

        accessToken="token"

        selectedPatientId="pat-1"

        onPatientCreated={vi.fn()}

        onConsentChanged={vi.fn()}

      />,

    );



    await waitFor(() => {

      expect(screen.getByText("Granted")).toBeInTheDocument();

      expect(screen.getByRole("button", { name: "Revoke" })).toBeInTheDocument();

      expect(screen.queryByRole("button", { name: "Grant" })).not.toBeInTheDocument();

    });

  });



  it("refetches after 409 on manual grant and shows active state without stale error", async () => {

    fetchPatientConsents

      .mockResolvedValueOnce({ items: [] })

      .mockResolvedValueOnce({ items: [activeConsentRow] });

    grantPatientConsent.mockRejectedValue(await duplicateConsentError());



    render(

      <PatientOnboardingPanel

        accessToken="token"

        selectedPatientId="pat-1"

        onPatientCreated={vi.fn()}

        onConsentChanged={vi.fn()}

      />,

    );



    await waitFor(() => {

      expect(screen.getByText("Not granted")).toBeInTheDocument();

    });



    fireEvent.click(screen.getByRole("button", { name: "Grant" }));



    await waitFor(() => {

      expect(fetchPatientConsents).toHaveBeenCalledTimes(2);

      expect(screen.getByText("Granted")).toBeInTheDocument();

      expect(screen.queryByText("Duplicate consent")).not.toBeInTheDocument();

      expect(screen.queryByText("Not granted")).not.toBeInTheDocument();

    });

  });



  it("reloads consent when selected patient changes", async () => {

    fetchPatientConsents.mockImplementation(async (_token: string, patientId: string) => {

      if (patientId === "pat-a") {

        return { items: [activeConsentRow] };

      }

      return { items: [] };

    });



    const { rerender } = render(

      <PatientOnboardingPanel

        accessToken="token"

        selectedPatientId="pat-a"

        onPatientCreated={vi.fn()}

        onConsentChanged={vi.fn()}

      />,

    );



    await waitFor(() => {

      expect(screen.getByText("Granted")).toBeInTheDocument();

    });



    rerender(

      <PatientOnboardingPanel

        accessToken="token"

        selectedPatientId="pat-b"

        onPatientCreated={vi.fn()}

        onConsentChanged={vi.fn()}

      />,

    );



    await waitFor(() => {

      expect(fetchPatientConsents).toHaveBeenLastCalledWith("token", "pat-b");

      expect(screen.getByText("Not granted")).toBeInTheDocument();

      expect(screen.queryByRole("button", { name: "Revoke" })).not.toBeInTheDocument();

    });

  });



  it("revokes active consent and refetches list", async () => {

    fetchPatientConsents

      .mockResolvedValueOnce({ items: [activeConsentRow] })

      .mockResolvedValueOnce({ items: [{ ...activeConsentRow, status: "revoked" }] });



    const onConsentChanged = vi.fn();



    render(

      <PatientOnboardingPanel

        accessToken="token"

        selectedPatientId="pat-1"

        onPatientCreated={vi.fn()}

        onConsentChanged={onConsentChanged}

      />,

    );



    await waitFor(() => {

      expect(screen.getByRole("button", { name: "Revoke" })).toBeInTheDocument();

    });



    fireEvent.click(screen.getByRole("button", { name: "Revoke" }));



    await waitFor(() => {

      expect(revokePatientConsent).toHaveBeenCalledWith("token", "pat-1", "consent-1");

      expect(onConsentChanged).toHaveBeenCalled();

      expect(screen.getByText("Not granted")).toBeInTheDocument();

      expect(screen.getByRole("button", { name: "Grant" })).toBeInTheDocument();

    });

  });



  it("shows active consent after successful create-time grant refetch", async () => {

    fetchPatientConsents.mockImplementation(async (_token: string, patientId: string) => {

      if (patientId === "new-pat") {

        return { items: [{ ...activeConsentRow, patient_id: "new-pat" }] };

      }

      return { items: [] };

    });



    render(<CreateWithAutoSelect accessToken="token" onConsentChanged={vi.fn()} />);



    fireEvent.click(screen.getByRole("button", { name: "Create patient" }));



    await waitFor(() => {

      expect(grantPatientConsent).toHaveBeenCalledWith("token", "new-pat");

      expect(fetchPatientConsents).toHaveBeenCalledWith("token", "new-pat");

      expect(screen.getByText("Granted")).toBeInTheDocument();

      expect(screen.getByRole("button", { name: "Revoke" })).toBeInTheDocument();

    });

  });

});
