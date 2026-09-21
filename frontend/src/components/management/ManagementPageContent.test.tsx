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
        membershipId: "Membership",
        organizationId: "Org",
        membershipRole: "Role",
        joinedAt: "Joined",
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
        assignmentStatuses: { active: "Active", inactive: "Inactive" },
        errors: {
          duplicateAssignment: "Duplicate assignment",
          duplicatePrimary: "Duplicate primary",
          patientNotFound: "Patient missing",
          assignmentNotFound: "Assignment missing",
          doctorNotFound: "Doctor missing",
          generic: "Generic error",
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
const fetchPatientAssignments = vi.fn();
const createPatientAssignment = vi.fn();
const deactivatePatientAssignment = vi.fn();

vi.mock("@/lib/api/organizations", () => ({
  fetchMyOrganizationMembership: (...args: unknown[]) => fetchMyOrganizationMembership(...args),
  fetchOrganizationDoctors: (...args: unknown[]) => fetchOrganizationDoctors(...args),
}));

vi.mock("@/lib/api/patients", () => ({
  fetchPatients: (...args: unknown[]) => fetchPatients(...args),
}));

vi.mock("@/lib/api/assignments", () => ({
  fetchPatientAssignments: (...args: unknown[]) => fetchPatientAssignments(...args),
  createPatientAssignment: (...args: unknown[]) => createPatientAssignment(...args),
  deactivatePatientAssignment: (...args: unknown[]) => deactivatePatientAssignment(...args),
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
      membership_role: "clinic_admin",
      joined_at: "2026-01-01T00:00:00Z",
    });
    fetchOrganizationDoctors.mockResolvedValue({
      items: [{ membership_id: "dm1", user_id: "doc-1", joined_at: "2026-01-01T00:00:00Z" }],
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

    fireEvent.click(screen.getByRole("button", { name: "Assign doctor" }));

    await waitFor(() => {
      expect(screen.getByText("Duplicate assignment")).toBeInTheDocument();
    });
  });
});
