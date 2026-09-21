/** Shared message catalog shape. All locale files must implement this interface. */
export type CommonContent = {
  brandName: string;
  brandTagline: string;
  nav: {
    home: string;
    login: string;
    register: string;
    patients: string;
    management: string;
    logout: string;
    skipToContent: string;
    openMenu: string;
    closeMenu: string;
  };
  common: {
    loading: string;
    error: string;
    retry: string;
    back: string;
    notFound: string;
    unauthorized: string;
    forbidden: string;
  };
  language: {
    switcherLabel: string;
  };
  footer: {
    tagline: string;
    disclaimer: string;
    copyright: string;
    links: {
      privacy: string;
      terms: string;
      contact: string;
    };
  };
  landing: {
    badge: string;
    heroTitle: string;
    heroDescription: string;
    primaryCta: string;
    secondaryCta: string;
    secondaryCtaAuthenticated: string;
    featuresTitle: string;
    features: ReadonlyArray<{
      title: string;
      description: string;
    }>;
    trustTitle: string;
    trustPoints: readonly string[];
  };
  auth: {
    loginTitle: string;
    loginDescription: string;
    registerTitle: string;
    registerDescription: string;
    emailLabel: string;
    emailPlaceholder: string;
    passwordLabel: string;
    passwordPlaceholder: string;
    confirmPasswordLabel: string;
    confirmPasswordPlaceholder: string;
    loginSubmit: string;
    registerSubmit: string;
    noAccount: string;
    hasAccount: string;
    phaseNotice: string;
    firstNameLabel: string;
    lastNameLabel: string;
    loginError: string;
    registerError: string;
    passwordMismatch: string;
  };
  patients: {
    title: string;
    description: string;
    empty: string;
    viewTimeline: string;
    name: string;
    dateOfBirth: string;
    gender: string;
    loadError: string;
    genders: Record<string, string>;
  };
  timeline: {
    title: string;
    description: string;
    sortNotice: string;
    empty: string;
    loadError: string;
    truncatedNotice: string;
    filtersTitle: string;
    dateFrom: string;
    dateTo: string;
    applyFilters: string;
    clearFilters: string;
    includeRiskSnapshot: string;
    sourceKind: string;
    severity: string;
    disclaimer: string;
    eventTypes: Record<string, string>;
    headlines: Record<string, string>;
    sourceKinds: Record<string, string>;
    severityLevels: Record<string, string>;
    detailPhrases: Record<string, string>;
    patientSummary: {
      ageSuffix: string;
    };
  };
  management: {
    title: string;
    description: string;
    forbiddenTitle: string;
    forbiddenDescription: string;
    organizationSection: string;
    doctorsSection: string;
    patientsSection: string;
    assignmentsSection: string;
    assignDoctor: string;
    removeAssignment: string;
    selectPatient: string;
    selectDoctor: string;
    noPatientSelected: string;
    membershipId: string;
    organizationId: string;
    membershipRole: string;
    joinedAt: string;
    userId: string;
    patientLabel: string;
    isPrimary: string;
    status: string;
    assignedAt: string;
    endedAt: string;
    assignmentId: string;
    assigneeUserId: string;
    emptyDoctors: string;
    emptyAssignments: string;
    loadError: string;
    createSuccess: string;
    deactivateSuccess: string;
    membershipRoles: Record<string, string>;
    assignmentStatuses: Record<string, string>;
    errors: {
      duplicateAssignment: string;
      duplicatePrimary: string;
      patientNotFound: string;
      assignmentNotFound: string;
      doctorNotFound: string;
      generic: string;
    };
  };
};

export type LocaleDirection = "ltr" | "rtl";

/** Metadata for each registered locale. Extend this when adding languages. */
export type LocaleDefinition = {
  code: string;
  label: string;
  nativeLabel: string;
  direction: LocaleDirection;
  messages: CommonContent;
};
