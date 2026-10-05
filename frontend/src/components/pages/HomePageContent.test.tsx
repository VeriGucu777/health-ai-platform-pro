import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HomePageContent } from "@/components/pages/HomePageContent";

const authState = {
  isAuthenticated: false,
  isHydrated: true,
};

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => authState,
}));

const localeState = {
  locale: "en" as "en" | "tr",
  content: {
    landing: {
      badge: "Badge",
      heroTitle: "Hero",
      heroDescription: "Desc",
      primaryCta: "Get started",
      secondaryCta: "Sign in",
      secondaryCtaAuthenticated: "View my patients",
      trustTitle: "Trust",
      trustPoints: ["Point"],
      featuresTitle: "Features",
      features: [{ title: "F", description: "D" }],
    },
  },
};

vi.mock("@/lib/i18n/use-locale", () => ({
  useLocale: () => localeState,
}));

describe("HomePageContent", () => {
  beforeEach(() => {
    authState.isAuthenticated = false;
    authState.isHydrated = true;
    localeState.content.landing.secondaryCtaAuthenticated = "View my patients";
  });

  afterEach(() => {
    cleanup();
  });

  it("shows single patients CTA when authenticated", () => {
    authState.isAuthenticated = true;
    authState.isHydrated = true;
    localeState.content.landing.secondaryCtaAuthenticated = "View my patients";

    render(<HomePageContent />);

    const link = screen.getByRole("link", { name: "View my patients" });
    expect(link).toHaveAttribute("href", "/patients");
    expect(screen.queryByRole("link", { name: "Get started" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Sign in" })).not.toBeInTheDocument();
  });

  it("shows register and sign-in CTAs when guest", () => {
    authState.isAuthenticated = false;
    render(<HomePageContent />);

    expect(screen.getByRole("link", { name: "Get started" })).toHaveAttribute("href", "/register");
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login");
    expect(screen.queryByRole("link", { name: "View my patients" })).not.toBeInTheDocument();
  });

  it("uses Turkish authenticated CTA label when configured", () => {
    authState.isAuthenticated = true;
    localeState.content.landing.secondaryCtaAuthenticated = "Hastalarımı görüntüle";

    render(<HomePageContent />);

    expect(screen.getByRole("link", { name: "Hastalarımı görüntüle" })).toHaveAttribute(
      "href",
      "/patients",
    );
  });
});
