import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ManagementPageContent } from "@/components/management/ManagementPageContent";

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({ accessToken: "token" }),
}));

const localeFixture = {
  content: {
      common: { loading: "Loading…", retry: "Retry" },
      patients: { empty: "No patients" },
      management: {
        title: "Doctor assignments",
        description: "Manage assignments",
        organizationSection: "Organization",
        doctorsSection: "Doctors",
        patientsSection: "Patients",
        assignmentsSection: "Assignments",
        assignDoctor: "Assign doctor",
        removeAssignment: "Remove assignment",
        selectPatient: "Choose patient",
        selectDoctor: "Choose doctor",
        noPatientSelected: "Select a patient",
        organizationName: "Organization",
        membershipStatus: "Status",
        membershipId: "Membership",
        organizationId: "Org",
        membershipRole: "Role",
        joinedAt: "Joined",
        doctorName: "Doctor",
        doctorEmail: "Email",
        assignedDoctor: "Assigned doctor",
        technicalDetails: "Technical",
        userId: "User",
        patientLabel: "Patient",
        isPrimary: "Primary",
        status: "Status",
        assignedAt: "Assigned",
        assignmentId: "Assignment",
        assigneeUserId: "Assignee",
        emptyDoctors: "No doctors",
        emptyAssignments: "No assignments",
        loadError: "Load error",
        createSuccess: "Created",
        deactivateSuccess: "Deactivated",
        membershipRoles: { doctor: "Doctor", clinic_admin: "Admin" },
        membershipStatuses: { active: "Active", inactive: "Inactive" },
        assignmentStatuses: { active: "Active", inactive: "Inactive" },
        errors: {
          duplicateAssignment: "Duplicate assignment",
          duplicatePrimary: "Duplicate primary",
          duplicateConsent: "Duplicate consent",
          patientNotFound: "Patient missing",
          assignmentNotFound: "Assignment missing",
          doctorNotFound: "Doctor missing",
          generic: "Generic error",
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
          demoNotesDefault: "Notes default",
          consentGrantFailedWarning: "Consent warn",
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

const fetchMyOrganizationMembership = vi.fn();
const fetchOrganizationDoctors = vi.fn();
const fetchPatients = vi.fn();
const createPatient = vi.fn();
const fetchPatientAssignments = vi.fn();
const createPatientAssignment = vi.fn();
const deactivatePatientAssignment = vi.fn();

vi.mock("@/lib/api/organizations", () => ({
  fetchMyOrganizationMembership: (...args: unknown[]) => fetchMyOrganizationMembership(...args),
  fetchOrganizationDoctors: (...args: unknown[]) => fetchOrganizationDoctors(...args),
}));

vi.mock("@/lib/api/patients", () => ({
  fetchPatients: (...args: unknown[]) => fetchPatients(...args),
  createPatient: (...args: unknown[]) => createPatient(...args),
}));

vi.mock("@/lib/api/assignments", () => ({
  fetchPatientAssignments: (...args: unknown[]) => fetchPatientAssignments(...args),
  createPatientAssignment: (...args: unknown[]) => createPatientAssignment(...args),
  deactivatePatientAssignment: (...args: unknown[]) => deactivatePatientAssignment(...args),
}));

const fetchPatientConsents = vi.fn();
const grantPatientConsent = vi.fn();
const revokePatientConsent = vi.fn();

vi.mock("@/lib/api/consents", () => ({
  fetchPatientConsents: (...args: unknown[]) => fetchPatientConsents(...args),
  grantPatientConsent: (...args: unknown[]) => grantPatientConsent(...args),
  revokePatientConsent: (...args: unknown[]) => revokePatientConsent(...args),
}));

describe("ManagementPageContent", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    vi.clearAllMocks();
    fetchMyOrganizationMembership.mockResolvedValue({
      membership_id: "m1",
      organization_id: "o1",
      organization_name: "Demo Clinic",
      membership_role: "clinic_admin",
      membership_status: "active",
      joined_at: "2026-01-01T00:00:00Z",
    });
    fetchOrganizationDoctors.mockResolvedValue({
      items: [
        {
          membership_id: "dm1",
          user_id: "doc-1",
          email: "doc@example.com",
          first_name: "Jane",
          last_name: "Doctor",
          joined_at: "2026-01-01T00:00:00Z",
        },
      ],
    });
    fetchPatients.mockResolvedValue({
      items: [
        {
          id: "pat-1",
          owner_id: "x",
          first_name: "Ada",
          last_name: "Lovelace",
          date_of_birth: "1990-01-01",
          gender: "female",
          phone: null,
          notes: null,
          is_active: true,
          created_at: "",
          updated_at: "",
        },
      ],
      total: 1,
      page: 1,
      page_size: 100,
      pages: 1,
    });
    fetchPatientAssignments.mockResolvedValue({ items: [] });
    fetchPatientConsents.mockResolvedValue({ items: [] });
    grantPatientConsent.mockResolvedValue({
      id: "c1",
      patient_id: "pat-1",
      organization_id: "o1",
      consent_type: "clinical_data_processing",
      status: "granted",
      granted_at: "2026-01-01T00:00:00Z",
      revoked_at: null,
      recorded_by_user_id: "admin",
      version: 1,
      source: "test",
      created_at: "2026-01-01T00:00:00Z",
    });
    revokePatientConsent.mockResolvedValue({});
    createPatientAssignment.mockResolvedValue({
      id: "a-new",
      organization_id: "o1",
      patient_id: "pat-1",
      assignee_user_id: "doc-1",
      is_primary: false,
      status: "active",
      assigned_at: "2026-01-02T00:00:00Z",
      ended_at: null,
      assigned_by_user_id: null,
    });
    deactivatePatientAssignment.mockResolvedValue({});
  });

  it("shows doctor names instead of raw user ids in the doctor select", async () => {
    render(<ManagementPageContent />);

    await waitFor(() => {
      expect(screen.getByText("Doctor assignments")).toBeInTheDocument();
    });

    expect(screen.getByText("Jane Doctor")).toBeInTheDocument();
    expect(screen.getByText("Demo Clinic")).toBeInTheDocument();
  });

  it("creates assignment from UI", async () => {
    render(<ManagementPageContent />);

    await waitFor(() => {
      expect(screen.getByText("Doctor assignments")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Choose patient"), {
      target: { value: "pat-1" },
    });

    await waitFor(() => {
      expect(fetchPatientAssignments).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByLabelText("Choose doctor")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Choose doctor"), {
      target: { value: "doc-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Assign doctor" }));

    await waitFor(() => {
      expect(createPatientAssignment).toHaveBeenCalledWith("token", "pat-1", {
        assignee_user_id: "doc-1",
        is_primary: false,
      });
    });
  });

  it("deactivates active assignment from UI", async () => {
    fetchPatientAssignments.mockResolvedValue({
      items: [
        {
          id: "a1",
          organization_id: "o1",
          patient_id: "pat-1",
          assignee_user_id: "doc-1",
          is_primary: true,
          status: "active",
          assigned_at: "2026-01-02T00:00:00Z",
          ended_at: null,
          assigned_by_user_id: null,
        },
      ],
    });

    render(<ManagementPageContent />);

    await waitFor(() => {
      expect(screen.getByText("Doctor assignments")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Choose patient"), {
      target: { value: "pat-1" },
    });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Remove assignment" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Remove assignment" }));

    await waitFor(() => {
      expect(deactivatePatientAssignment).toHaveBeenCalledWith("token", "pat-1", "a1");
    });
  });

  it("shows localized duplicate assignment message on 409", async () => {
    const { ApiClientError } = await import("@/lib/api/client");
    createPatientAssignment.mockRejectedValue(
      new ApiClientError(
        "An active assignment already exists for this doctor and patient",
        409,
      ),
    );

    render(<ManagementPageContent />);

    await waitFor(() => {
      expect(screen.getByText("Doctor assignments")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Choose patient"), {
      target: { value: "pat-1" },
    });

    await waitFor(() => {
      expect(fetchPatientAssignments).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Assign doctor" })).toBeEnabled();
    });

    fireEvent.change(screen.getByLabelText("Choose doctor"), {
      target: { value: "doc-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Assign doctor" }));

    await waitFor(() => {
      expect(screen.getByText("Duplicate assignment")).toBeInTheDocument();
    });
  });

  it("refetches patients, selects new patient, and shows page-level create success", async () => {
    const newPatient = {
      id: "pat-new",
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
    };
    createPatient.mockResolvedValue(newPatient);
    fetchPatients
      .mockResolvedValueOnce({
        items: [
          {
            id: "pat-1",
            owner_id: "x",
            first_name: "Ada",
            last_name: "Lovelace",
            date_of_birth: "1990-01-01",
            gender: "female",
            phone: null,
            notes: null,
            is_active: true,
            created_at: "",
            updated_at: "",
          },
        ],
        total: 1,
        page: 1,
        page_size: 100,
        pages: 1,
      })
      .mockResolvedValueOnce({
        items: [newPatient, {
          id: "pat-1",
          owner_id: "x",
          first_name: "Ada",
          last_name: "Lovelace",
          date_of_birth: "1990-01-01",
          gender: "female",
          phone: null,
          notes: null,
          is_active: true,
          created_at: "",
          updated_at: "",
        }],
        total: 2,
        page: 1,
        page_size: 100,
        pages: 1,
      });

    render(<ManagementPageContent />);

    await waitFor(() => {
      expect(screen.getByText("Doctor assignments")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Create patient" }));

    await waitFor(() => {
      expect(createPatient).toHaveBeenCalledTimes(1);
      expect(fetchPatients.mock.calls.length).toBeGreaterThanOrEqual(2);
      expect(screen.getAllByText("Patient created successfully.").length).toBeGreaterThan(0);
    });

    const patientSelect = screen.getByLabelText("Choose patient") as HTMLSelectElement;
    expect(patientSelect.value).toBe("pat-new");
  });
});
