import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RequireClinicAdmin } from "@/components/auth/RequireClinicAdmin";

const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
  usePathname: () => "/management",
}));

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({
    isAuthenticated: true,
    isHydrated: true,
  }),
}));

vi.mock("@/lib/i18n/use-locale", () => ({
  useLocale: () => ({
    content: {
      common: { loading: "Loading…" },
      management: { loadError: "Load failed", forbiddenTitle: "Denied", forbiddenDescription: "No access" },
      nav: { patients: "Patients" },
    },
  }),
}));

const useCurrentUserMock = vi.fn();

vi.mock("@/lib/auth/use-current-user", () => ({
  useCurrentUser: () => useCurrentUserMock(),
}));

describe("RequireClinicAdmin", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    replaceMock.mockClear();
    useCurrentUserMock.mockReset();
  });

  it("renders children for clinic_admin", () => {
    useCurrentUserMock.mockReturnValue({
      user: { role: "clinic_admin" },
      isLoading: false,
      isReady: true,
      error: null,
    });

    render(
      <RequireClinicAdmin>
        <p>Management content</p>
      </RequireClinicAdmin>,
    );

    expect(screen.getByText("Management content")).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("redirects doctor away from management route", () => {
    useCurrentUserMock.mockReturnValue({
      user: { role: "doctor" },
      isLoading: false,
      isReady: true,
      error: null,
    });

    render(
      <RequireClinicAdmin>
        <p>Management content</p>
      </RequireClinicAdmin>,
    );

    expect(replaceMock).toHaveBeenCalledWith("/patients");
    expect(screen.queryByText("Management content")).not.toBeInTheDocument();
  });
});
