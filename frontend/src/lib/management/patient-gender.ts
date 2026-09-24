/** Canonical patient gender values sent to the API (backend-agnostic strings). */

export const PATIENT_GENDER_VALUES = ["female", "male", "other"] as const;

export type PatientGenderValue = (typeof PATIENT_GENDER_VALUES)[number];

export type GenderOptionLabels = Record<PatientGenderValue, string>;

export function isPatientGenderValue(value: string): value is PatientGenderValue {
  return (PATIENT_GENDER_VALUES as readonly string[]).includes(value);
}

export function buildGenderOptions(labels: GenderOptionLabels): Array<{
  value: PatientGenderValue;
  label: string;
}> {
  return PATIENT_GENDER_VALUES.map((value) => ({
    value,
    label: labels[value],
  }));
}
