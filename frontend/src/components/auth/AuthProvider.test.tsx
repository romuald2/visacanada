import { render, screen, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider, useAuth } from "./AuthProvider";
import { ApiError } from "@/lib/api";
import type { User } from "@/lib/types";

// --- Mocks ---
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    login: vi.fn(),
    getMe: vi.fn(),
    refresh: vi.fn(),
  };
});

vi.mock("@/lib/auth-storage", () => ({
  getAccessToken: vi.fn(),
  getRefreshToken: vi.fn(),
  setTokens: vi.fn(),
  clearTokens: vi.fn(),
}));

import * as api from "@/lib/api";
import * as storage from "@/lib/auth-storage";

const ADMIN: User = {
  id: 1,
  email: "admin@cabinet.ca",
  full_name: "Admin Test",
  role: "admin",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function Probe() {
  const { user, loading, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="user">{user ? user.email : "none"}</span>
      <button onClick={() => login("admin@cabinet.ca", "pw")}>login</button>
      <button onClick={() => logout()}>logout</button>
    </div>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("AuthProvider bootstrap", () => {
  it("stays logged out when no token is stored", async () => {
    vi.mocked(storage.getAccessToken).mockReturnValue(null);
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("loading").textContent).toBe("false"),
    );
    expect(screen.getByTestId("user").textContent).toBe("none");
    expect(api.getMe).not.toHaveBeenCalled();
  });

  it("resolves the current user from a stored token", async () => {
    vi.mocked(storage.getAccessToken).mockReturnValue("tok");
    vi.mocked(api.getMe).mockResolvedValue(ADMIN);
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("user").textContent).toBe("admin@cabinet.ca"),
    );
  });

  it("refreshes when the stored token is expired (401)", async () => {
    vi.mocked(storage.getAccessToken).mockReturnValue("stale");
    vi.mocked(storage.getRefreshToken).mockReturnValue("refresh-tok");
    vi.mocked(api.getMe)
      .mockRejectedValueOnce(new ApiError("expiré", 401))
      .mockResolvedValueOnce(ADMIN);
    vi.mocked(api.refresh).mockResolvedValue({
      access_token: "fresh",
      refresh_token: "fresh-refresh",
      token_type: "bearer",
    });

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("user").textContent).toBe("admin@cabinet.ca"),
    );
    expect(api.refresh).toHaveBeenCalledWith("refresh-tok");
    expect(storage.setTokens).toHaveBeenCalled();
  });

  it("clears tokens when refresh also fails", async () => {
    vi.mocked(storage.getAccessToken).mockReturnValue("stale");
    vi.mocked(storage.getRefreshToken).mockReturnValue(null);
    vi.mocked(api.getMe).mockRejectedValue(new ApiError("expiré", 401));

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("loading").textContent).toBe("false"),
    );
    expect(screen.getByTestId("user").textContent).toBe("none");
    expect(storage.clearTokens).toHaveBeenCalled();
  });
});

describe("AuthProvider login/logout", () => {
  it("logs in and stores tokens", async () => {
    vi.mocked(storage.getAccessToken).mockReturnValue(null);
    vi.mocked(api.login).mockResolvedValue({
      access_token: "a",
      refresh_token: "r",
      token_type: "bearer",
    });
    vi.mocked(api.getMe).mockResolvedValue(ADMIN);

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("loading").textContent).toBe("false"),
    );

    await act(async () => {
      screen.getByText("login").click();
    });

    await waitFor(() =>
      expect(screen.getByTestId("user").textContent).toBe("admin@cabinet.ca"),
    );
    expect(storage.setTokens).toHaveBeenCalledWith({
      access_token: "a",
      refresh_token: "r",
      token_type: "bearer",
    });
  });

  it("logs out and clears tokens", async () => {
    vi.mocked(storage.getAccessToken).mockReturnValue("tok");
    vi.mocked(api.getMe).mockResolvedValue(ADMIN);

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("user").textContent).toBe("admin@cabinet.ca"),
    );

    await act(async () => {
      screen.getByText("logout").click();
    });

    expect(screen.getByTestId("user").textContent).toBe("none");
    expect(storage.clearTokens).toHaveBeenCalled();
  });
});
