import type { OrganizationDoctorMember } from "@/lib/api/organizations";

export function formatDoctorDisplayName(doctor: OrganizationDoctorMember): string {
  const name = `${doctor.first_name} ${doctor.last_name}`.trim();
  return name.length > 0 ? name : doctor.email;
}

export function formatDoctorOptionLabel(doctor: OrganizationDoctorMember): string {
  const name = formatDoctorDisplayName(doctor);
  return `${name} (${doctor.email})`;
}

export function findDoctorByUserId(
  doctors: OrganizationDoctorMember[],
  userId: string,
): OrganizationDoctorMember | undefined {
  return doctors.find((doctor) => doctor.user_id === userId);
}

export function formatPatientListLabel(patient: {
  first_name: string;
  last_name: string;
}): string {
  return `${patient.first_name} ${patient.last_name}`.trim();
}
