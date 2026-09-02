import type { CommonContent } from "@/lib/i18n/types";

export const commonContent: CommonContent = {
  brandName: "Health AI Platform Pro",
  brandTagline: "Clinical decision-support for modern care teams",
  nav: {
    home: "Home",
    login: "Sign in",
    register: "Create account",
    skipToContent: "Skip to main content",
    openMenu: "Open menu",
    closeMenu: "Close menu",
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
    badge: "Healthcare SaaS foundation",
    heroTitle: "Smarter clinical workflows, built for care teams",
    heroDescription:
      "Coordinate patient records, health insights, and risk assessments in one secure workspace designed for healthcare professionals.",
    primaryCta: "Get started",
    secondaryCta: "Sign in",
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
        title: "Production-ready foundation",
        description:
          "Connect to a FastAPI backend with JWT authentication, observability, and PostgreSQL persistence.",
      },
    ],
    trustTitle: "Designed with clinical safety in mind",
    trustPoints: [
      "No patient identifiers in demo content",
      "Clear medical disclaimers on decision-support outputs",
      "Secure API integration via environment configuration",
    ],
  },
  auth: {
    loginTitle: "Sign in",
    loginDescription: "Access your workspace with your Health AI Platform Pro account.",
    registerTitle: "Create account",
    registerDescription: "Register a professional account to access the platform.",
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
    phaseNotice: "",
    firstNameLabel: "First name",
    firstNamePlaceholder: "Jane",
    lastNameLabel: "Last name",
    lastNamePlaceholder: "Doe",
    passwordMismatch: "Passwords do not match.",
    genericError: "Something went wrong. Please try again.",
    logout: "Sign out",
    signedInAs: "Signed in as",
  },
};

export type { CommonContent };
