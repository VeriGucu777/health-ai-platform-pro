/** Shared message catalog shape. All locale files must implement this interface. */
export type CommonContent = {
  brandName: string;
  brandTagline: string;
  nav: {
    home: string;
    login: string;
    register: string;
    skipToContent: string;
    openMenu: string;
    closeMenu: string;
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
