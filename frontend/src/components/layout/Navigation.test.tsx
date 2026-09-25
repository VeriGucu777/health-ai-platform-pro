import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Navigation } from "@/components/layout/Navigation";

const useAuth = vi.fn();
const useLocale = vi.fn();
const useCurrentUser = vi.fn();

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => useAuth(),
}));

vi.mock("@/lib/auth/use-current-user", () => ({
  useCurrentUser: () => useCurrentUser(),
}));

vi.mock("@/lib/i18n/use-locale", () => ({
  useLocale: () => useLocale(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

describe("Navigation role visibility", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    useLocale.mockReturnValue({
      content: {
        nav: {
          home: "Home",
          patients: "Patients",
          management: "Management",
        },
      },
    });
  });

  it("shows management link only for clinic_admin", () => {
    useAuth.mockReturnValue({ isAuthenticated: true });
    useCurrentUser.mockReturnValue({ isClinicAdmin: true });

    render(<Navigation />);
    expect(screen.getByRole("link", { name: "Management" })).toBeInTheDocument();
  });

  it("hides management link for doctor", () => {
    useAuth.mockReturnValue({ isAuthenticated: true });
    useCurrentUser.mockReturnValue({ isClinicAdmin: false });

    render(<Navigation />);
    expect(screen.queryByRole("link", { name: "Management" })).not.toBeInTheDocument();
  });
});
