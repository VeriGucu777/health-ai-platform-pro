import { fireEvent, render, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "@/lib/auth/AuthProvider";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
}));

vi.mock("@/lib/auth/api", () => ({
  loginRequest: vi.fn(),
  registerRequest: vi.fn().mockResolvedValue({
    id: "user-1",
    email: "doctor@example.com",
    first_name: "Doc",
    last_name: "Tor",
    role: "doctor",
    is_active: true,
    is_verified: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  }),
  refreshRequest: vi.fn(),
  logoutRequest: vi.fn(),
  fetchCurrentUser: vi.fn(),
}));

function RegisterProbe() {
  const { register } = useAuth();
  return (
    <button
      type="button"
      onClick={() =>
        void register({
          email: "doctor@example.com",
          password: "securepass123",
          first_name: "Doc",
          last_name: "Tor",
          role: "doctor",
        })
      }
    >
      Register
    </button>
  );
}

describe("AuthProvider register flow", () => {
  it("does not auto-login and navigates to check-email", async () => {
    const { loginRequest } = await import("@/lib/auth/api");
    render(
      <AuthProvider>
        <RegisterProbe />
      </AuthProvider>,
    );
    fireEvent.click(document.querySelector("button")!);
    await waitFor(() => {
      expect(push).toHaveBeenCalledWith(
        "/register/check-email?email=doctor%40example.com",
      );
    });
    expect(loginRequest).not.toHaveBeenCalled();
  });
});
