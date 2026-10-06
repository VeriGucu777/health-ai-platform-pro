import type { CommonContent } from "@/lib/i18n/types";

export const commonContent: CommonContent = {
  brandName: "Health AI Platform Pro",
  brandTagline: "Clinical decision-support for modern care teams",
  nav: {
    home: "Home",
    login: "Sign in",
    register: "Create account",
    patients: "Patients",
    management: "Clinic management",
    logout: "Sign out",
    skipToContent: "Skip to main content",
    openMenu: "Open menu",
    closeMenu: "Close menu",
  },
  common: {
    loading: "LoadingÔÇĞ",
    error: "Something went wrong.",
    retry: "Try again",
    back: "Back",
    notFound: "Not found.",
    unauthorized: "Please sign in to continue.",
    forbidden: "You do not have permission to access this page.",
  },
  language: {
    switcherLabel: "Language",
  },
  footer: {
    tagline: "Secure healthcare decision-support software.",
    disclaimer:
      "This platform provides decision-support information only. It does not replace professional medical judgment.",
    copyright: "Health AI Platform Pro. All rights reserved.",
    links: {
      privacy: "Privacy",
      terms: "Terms",
      contact: "Contact",
    },
  },
  landing: {
    badge: "Clinical decision-support platform",
    heroTitle: "Faster clinical assessment for healthcare teams",
    heroDescription:
      "Summarizes patient history, measurements, laboratory, imaging, and follow-up records in one place to support clinical assessment.",
    primaryCta: "Get started",
    secondaryCta: "Sign in",
    secondaryCtaAuthenticated: "View my patients",
    featuresTitle: "Built for responsible healthcare AI",
    features: [
      {
        title: "Structured patient data",
        description:
          "Organize appointments, medical records, and health measurements with owner-scoped access controls.",
      },
      {
        title: "Decision-support analytics",
        description:
          "Review trends and insights that support clinical judgment without presenting diagnoses.",
      },
      {
        title: "Scalable technical foundation",
        description:
          "A modular architecture on FastAPI with JWT authentication, PostgreSQL persistence, and observability for growing clinical workloads.",
      },
    ],
    trustTitle: "Designed with clinical safety in mind",
    trustPoints: [
      "No patient identifiers in demo content",
      "Clear medical disclaimers on decision-support outputs",
      "Secure API and access controls",
    ],
  },
  auth: {
    loginTitle: "Sign in",
    loginDescription: "Access your workspace with your Health AI Platform Pro account.",
    registerTitle: "Create account",
    registerDescription: "Register a professional account connected to the FastAPI backend.",
    emailLabel: "Email address",
    emailPlaceholder: "you@clinic.example",
    passwordLabel: "Password",
    passwordPlaceholder: "Enter your password",
    confirmPasswordLabel: "Confirm password",
    confirmPasswordPlaceholder: "Re-enter your password",
    loginSubmit: "Sign in",
    registerSubmit: "Create account",
    noAccount: "Need an account?",
    hasAccount: "Already have an account?",
    phaseNotice:
      "Decision-support only. Do not enter real patient identifiers in demo environments.",
    firstNameLabel: "First name",
    firstNamePlaceholder: "Jane",
    lastNameLabel: "Last name",
    lastNamePlaceholder: "Doe",
    loginError: "Sign in failed. Check your email and password.",
    registerError: "Registration failed. Try a different email or stronger password.",
    passwordMismatch: "Passwords do not match.",
    genericError: "Something went wrong. Please try again.",
    logout: "Sign out",
    signedInAs: "Signed in as",
    emailNotVerified:
      "Verify your email before signing in. Check your inbox or request a new verification message.",
    checkEmailTitle: "Check your email",
    checkEmailDescription:
      "We sent a verification link to your address. Open the link to activate your account, then sign in.",
    checkEmailResend: "Resend verification email",
    checkEmailResendSuccess:
      "If an account exists for this email, a verification message has been sent.",
    checkEmailBackToLogin: "Back to sign in",
    verifyEmailTitle: "Email verification",
    verifyEmailSuccess: "Your email is verified. You can sign in now.",
    verifyEmailInvalid: "This verification link is invalid or has expired.",
    verifyEmailMissingToken: "No verification token was provided.",
    verifyEmailWorking: "Verifying your email…",
  },
  patients: {
    title: "Patients",
    description: "Select a patient to review their clinical timeline.",
    empty: "No patients found. Create patients via the API or add demo data in your backend.",
    viewTimeline: "View timeline",
    viewPatient: "View patient",
    name: "Name",
    dateOfBirth: "Date of birth",
    gender: "Gender",
    loadError: "Could not load patients.",
    genders: {
      male: "Male",
      female: "Female",
      other: "Other",
    },
  },
  patientHub: {
    title: "Patient overview",
    description: "Review assigned patient details, risk history, and reports.",
    decisionSupportTitle: "Clinical decision support only",
    decisionSupportBody:
      "This system does not provide a medical diagnosis. Information is for clinical decision support and must not replace professional medical judgment.",
    clinicalTimeline: "Clinical timeline",
    downloadPdf: "Download PDF report",
    downloadingPdf: "Preparing PDF…",
    pdfError: "Could not download the PDF report.",
    pdfSuccess: "PDF download started.",
    riskHistoryTitle: "Risk assessment history",
    riskHistoryEmpty: "No risk assessments recorded for this patient yet.",
    riskHistoryLoadError: "Could not load risk assessment history.",
    clinicalSummaryTitle: "Clinical summary",
    clinicalSummarySubtitle: "Recent clinical picture",
    clinicalSummaryPeriodViewSuffix: "clinical picture",
    clinicalSummaryDescription:
      "A brief decision-support summary from records on file.",
    clinicalSummaryEmpty: "Not enough clinical data on file to build a summary.",
    clinicalSummaryLoadError: "Could not load the clinical summary.",
    clinicalSummaryDisclaimer:
      "This summary is for clinical decision support only; it is not a diagnosis or treatment recommendation.",
    clinicalSummaryItemLabels: {
      fasting_glucose_trend: "Fasting blood glucose",
      post_meal_glucose_trend: "Post-meal blood glucose",
      blood_pressure_trend: "Blood pressure",
      heart_rate_trend: "Heart rate",
      laboratory_summary: "Laboratory",
      imaging_summary: "Imaging",
      clinical_visit_summary: "Clinical visit note",
      neurological_follow_up_summary: "Neurological follow-up",
      medication_treatment_follow_up: "Medication and follow-up",
      upcoming_follow_up: "Upcoming follow-up",
      overdue_follow_up: "Overdue follow-up",
    },
    clinicalSummaryTrendMessages: {
      stable_in_range:
        "Between {period_range}, {count} comparable {context} measurements show a stable pattern (informational).",
      stable_on_date:
        "On {period_date}, {count} comparable {context} measurements show a stable pattern (informational).",
      increasing_in_range:
        "Between {period_range}, {count} comparable {context} measurements show an increasing pattern (informational).",
      increasing_on_date:
        "On {period_date}, {count} comparable {context} measurements show an increasing pattern (informational).",
      decreasing_in_range:
        "Between {period_range}, {count} comparable {context} measurements show a decreasing pattern (informational).",
      decreasing_on_date:
        "On {period_date}, {count} comparable {context} measurements show a decreasing pattern (informational).",
      recorded_no_direction_in_range:
        "Between {period_range}, {count} comparable {context} measurements recorded; not enough data for a directional trend.",
      recorded_no_direction_on_date:
        "On {period_date}, {count} comparable {context} measurements recorded; not enough data for a directional trend.",
      insufficient_data_in_range:
        "Between {period_range}, {count} comparable {context} measurement(s) on file; trend not assessed.",
      insufficient_data_on_date:
        "{count} comparable {context} measurement(s) recorded on {period_date}; there is insufficient data for a directional assessment.",
    },
    clinicalSummaryItemMessages: {
      trend_hybrid_stable_in_range:
        "Between {period_range}, {count} comparable {context} measurements show a stable pattern (informational).",
      trend_hybrid_stable_on_date:
        "On {period_date}, {count} comparable {context} measurements show a stable pattern (informational).",
      trend_hybrid_increasing_in_range:
        "Between {period_range}, {count} comparable {context} measurements show an increasing pattern (informational).",
      trend_hybrid_increasing_on_date:
        "On {period_date}, {count} comparable {context} measurements show an increasing pattern (informational).",
      trend_hybrid_decreasing_in_range:
        "Between {period_range}, {count} comparable {context} measurements show a decreasing pattern (informational).",
      trend_hybrid_decreasing_on_date:
        "On {period_date}, {count} comparable {context} measurements show a decreasing pattern (informational).",
      trend_hybrid_no_direction_in_range:
        "Between {period_range}, {count} comparable {context} measurements recorded; not enough data for a directional trend.",
      trend_hybrid_no_direction_on_date:
        "On {period_date}, {count} comparable {context} measurements recorded; not enough data for a directional trend.",
      trend_hybrid_insufficient_in_range:
        "Between {period_range}, {count} comparable {context} measurement(s) on file; trend not assessed.",
      trend_hybrid_insufficient_on_date:
        "{count} comparable {context} measurement(s) recorded on {period_date}; there is insufficient data for a directional assessment.",
      hba1c_summary: "Most recent HbA1c ({record_date}): {value}% on file.",
      diabetes_metabolic_lab_on_file:
        "Most recent metabolic laboratory panel ({record_date}) is documented in clinical records.",
      diabetes_medication_documented:
        "Diabetes medication and follow-up plan are documented in clinical records.",
      diabetes_follow_up_plan_documented:
        "Home glucose monitoring, quarterly HbA1c follow-up, and lifestyle counseling are documented in the follow-up plan.",
      stroke_neurological_follow_up_documented:
        "Neurological follow-up and post-stroke clinical assessment ({record_date}) are documented in clinical records.",
      brain_imaging_on_file:
        "Brain imaging report ({record_date}) is documented in clinical records.",
      stroke_secondary_prevention_documented:
        "Secondary stroke prevention and follow-up plan are documented in clinical records.",
      stroke_rehabilitation_follow_up_plan_documented:
        "Neurology follow-up, blood pressure monitoring, and rehabilitation goals are documented in the follow-up plan.",
      lipid_panel_summary:
        "Most recent lipid panel ({record_date}): LDL {ldl} mg/dL and HDL {hdl} mg/dL on file.",
      lipid_panel_with_triglycerides:
        "Most recent lipid panel ({record_date}): LDL {ldl} mg/dL, HDL {hdl} mg/dL, and triglycerides {triglycerides} mg/dL on file.",
      echocardiography_on_file:
        "Echocardiography report ({record_date}) is documented in clinical records.",
      imaging_report_on_file:
        "Imaging report ({record_date}) is documented in clinical records.",
      heart_rate_monitoring_insufficient_trend:
        "Resting heart rate measurements are on file; insufficient comparable data for a directional trend.",
      medication_treatment_summary: "{detail}",
      cardiac_care_plan_documented:
        "Blood pressure follow-up, lipid recheck within 3 months, and an activity follow-up plan are documented.",
      medication_plan_on_file: "Medication and follow-up plan documented in clinical records.",
      upcoming_follow_up_date: "Upcoming follow-up appointment: {date}.",
      overdue_follow_up_date:
        "The planned follow-up dated {date} has no completion record in the system.",
      laboratory_on_file: "Laboratory results are documented in clinical records.",
      brain_imaging_summary: "{detail}",
      clinical_visit_summary: "{detail}",
    },
    riskType: "Type",
    riskLevel: "Level",
    assessedAt: "Assessed at",
    score: "Score",
    factors: "Contributing factors",
    missingInputs: "Missing inputs",
    riskDisclaimer:
      "Risk outputs are rule-based decision-support estimates, not a diagnosis or treatment plan.",
    active: "Active",
    inactive: "Inactive",
    notFoundOrDenied: "Patient not found or you do not have access to this patient.",
    loadError: "Could not load patient details.",
    assessmentTypes: {
      diabetes: "Diabetes",
      heart_disease: "Heart disease",
      stroke: "Stroke",
    },
    riskLevels: {
      low: "Low",
      moderate: "Moderate",
      elevated: "Elevated",
      high: "High",
      very_high: "Very high",
    },
    missingInputLabels: {
      systolic_blood_pressure: "Systolic blood pressure",
      diastolic_blood_pressure: "Diastolic blood pressure",
      fasting_blood_glucose: "Fasting blood glucose",
      blood_glucose: "Blood glucose",
      height_cm: "Height",
      stroke_history: "Stroke/TIA history",
    },
    missingInputReasons: {
      systolic_blood_pressure:
        "No systolic blood pressure measurements are available in the selected date range.",
      diastolic_blood_pressure:
        "No diastolic blood pressure measurements are available in the selected date range.",
      fasting_blood_glucose:
        "No fasting blood glucose measurement is available in the selected date range.",
      blood_glucose: "No blood glucose measurement is available in the selected date range.",
      height_cm: "Height is not recorded for this patient.",
      stroke_history:
        "No structured stroke or TIA history record types (stroke_history or tia_history) are present in the selected date range.",
    },
  },
  timeline: {
    title: "Clinical timeline",
    description: "Read-only summary of recorded measurements, records, and appointments.",
    sortNotice: "Events shown oldest to newest.",
    empty: "No timeline events in the selected period.",
    loadError: "Could not load the clinical timeline.",
    truncatedNotice: "Some events were omitted because the list limit was reached.",
    filtersTitle: "Filters",
    dateFrom: "From (UTC date)",
    dateTo: "To (UTC date)",
    applyFilters: "Apply filters",
    clearFilters: "Clear filters",
    includeRiskSnapshot: "Include current risk snapshot",
    sourceKind: "Source",
    severity: "Severity",
    disclaimer:
      "This clinical timeline is an informational, read-only summary of recorded data. It is not a medical diagnosis, treatment recommendation, or substitute for professional medical judgment. Derived items are rule-based interpretations of recorded measurements and appointments. Risk snapshots reflect a single on-demand assessment at generation time, not a stored clinical history.",
    patientSummary: {
      ageSuffix: "years",
    },
    syntheticDemoBanner: "Synthetic demo data — not a real patient.",
    evaluatedDataPeriod: "Evaluated data period",
    headlines: {},
    sourceKinds: {
      medical_record: "Medical record",
      health_measurement: "Health measurement",
      appointment: "Appointment",
      derived: "Derived analysis",
      risk_assessment_current_snapshot: "Current risk assessment",
    },
    severityLevels: {
      info: "Info",
      warning: "Warning",
      critical: "Critical",
    },
    detailPhrases: {},
    eventTypes: {
      medical_record_diagnosis: "Diagnosis",
      medical_record_lab_result: "Laboratory result",
      medical_record_imaging_report: "Imaging report",
      medical_record_treatment: "Treatment",
      medical_record_medication: "Medication",
      medical_record_hospitalization: "Hospitalization",
      health_measurement: "Measurement",
      appointment_scheduled: "Appointment",
      appointment_completed: "Completed",
      appointment_cancelled: "Cancelled",
      appointment_status: "Appointment",
      appointment_overdue: "Overdue follow-up",
      measurement_trend_derived: "Trend (derived)",
      measurement_trend_insufficient_comparable: "Comparable measurements",
      risk_current_snapshot: "Risk snapshot",
    },
  },
  management: {
    title: "Clinic management",
    description:
      "Register patients in your organization, record consent, and manage doctor assignments.",
    forbiddenTitle: "Access denied",
    forbiddenDescription: "This management screen is only available to clinic_admin accounts.",
    organizationSection: "Organization membership",
    doctorsSection: "Active doctors",
    patientsSection: "Select patient",
    assignmentsSection: "Current assignments",
    assignDoctor: "Assign doctor",
    removeAssignment: "Remove assignment",
    removingAssignment: "Removing assignment…",
    selectPatient: "Choose a patient",
    selectDoctor: "Choose a doctor",
    noPatientSelected: "Select a patient from the list to view assignments.",
    organizationName: "Organization",
    membershipStatus: "Membership status",
    membershipId: "Membership ID",
    organizationId: "Organization ID",
    membershipRole: "Membership role",
    joinedAt: "Joined at",
    doctorName: "Doctor",
    doctorEmail: "Email",
    assignedDoctor: "Assigned doctor",
    technicalDetails: "Technical identifiers",
    userId: "User ID",
    patientLabel: "Patient",
    isPrimary: "Primary assignment",
    status: "Status",
    assignedAt: "Assigned at",
    endedAt: "Ended at",
    assignmentId: "Assignment ID",
    assigneeUserId: "Assignee user ID",
    emptyDoctors: "No active doctors to list in your organization.",
    emptyAssignments: "No assignments recorded for this patient.",
    loadError: "Could not load management data.",
    createSuccess: "Assignment created.",
    deactivateSuccess: "Assignment deactivated.",
    membershipRoles: {
      doctor: "Doctor",
      clinic_admin: "Clinic admin",
    },
    membershipStatuses: {
      active: "Active",
      inactive: "Inactive",
    },
    assignmentStatuses: {
      active: "Active",
      inactive: "Inactive",
    },
    errors: {
      duplicateAssignment: "An active assignment already exists for this doctor and patient.",
      duplicatePrimary: "An active primary assignment already exists for this patient.",
      duplicateConsent: "An active consent record already exists for this patient.",
      patientNotFound: "Patient not found or outside your organization.",
      assignmentNotFound: "Assignment not found.",
      doctorNotFound: "Doctor not found or outside your organization.",
      generic: "The operation could not be completed. Please try again.",
    },
    onboarding: {
      createSection: "Register patient",
      createHint:
        "Patients are linked to your organization automatically. Use synthetic demo data only.",
      consentSection: "Clinical data consent",
      consentHint:
        "Record whether clinical data processing consent was obtained (KVKK / decision-support pilot).",
      firstName: "First name",
      lastName: "Last name",
      dateOfBirth: "Date of birth",
      gender: "Gender",
      genderOptions: {
        female: "Female",
        male: "Male",
        other: "Other",
      },
      demoNotesDefault:
        "Synthetic pilot record — do not use real patient data.",
      consentGrantFailedWarning:
        "Patient was created, but clinical data processing consent could not be recorded.",
      phoneOptional: "Phone (optional)",
      notesOptional: "Notes (optional)",
      grantConsentOnCreate: "Record clinical data processing consent after registration",
      submitCreate: "Create patient",
      submitting: "Creating patient…",
      createSuccess: "Patient created successfully.",
      selectPatientForConsent: "Select a patient to view or update consent.",
      consentStatusGranted: "Active consent: granted",
      consentStatusNotGranted: "No active granted consent on file.",
      grantConsent: "Record consent",
      revokeConsent: "Revoke consent",
      noConsentHistory: "No consent records yet.",
      consentTypes: {
        clinical_data_processing: "Clinical data processing",
      },
      consentStatuses: {
        granted: "Granted",
        revoked: "Revoked",
      },
    },
  },
};

export type { CommonContent };
