import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { RequireAuth } from "./RequireAuth";
import type { UserRole } from "@/lib/types";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
}));

let mockUser: { role: UserRole } | null = null;
let mockLoading = false;
vi.mock("./AuthProvider", () => ({
  useAuth: () => ({
    user: mockUser,
    loading: mockLoading,
    login: vi.fn(),
    logout: vi.fn(),
    getValidToken: vi.fn(),
  }),
}));

beforeEach(() => {
  vi.clearAllMocks();
  mockUser = null;
  mockLoading = false;
});

describe("RequireAuth", () => {
  it("shows a loading state while auth resolves", () => {
    mockLoading = true;
    render(
      <RequireAuth>
        <div>secret</div>
      </RequireAuth>,
    );
    expect(screen.getByText(/chargement/i)).toBeInTheDocument();
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
  });

  it("redirects to login when unauthenticated", async () => {
    render(
      <RequireAuth>
        <div>secret</div>
      </RequireAuth>,
    );
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
  });

  it("renders children when authenticated", () => {
    mockUser = { role: "consultant" };
    render(
      <RequireAuth>
        <div>secret</div>
      </RequireAuth>,
    );
    expect(screen.getByText("secret")).toBeInTheDocument();
  });

  it("redirects to dashboard when role is not allowed", async () => {
    mockUser = { role: "consultant" };
    render(
      <RequireAuth roles={["admin"]}>
        <div>admin only</div>
      </RequireAuth>,
    );
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
    expect(screen.queryByText("admin only")).not.toBeInTheDocument();
  });

  it("renders children when role is allowed", () => {
    mockUser = { role: "admin" };
    render(
      <RequireAuth roles={["admin"]}>
        <div>admin only</div>
      </RequireAuth>,
    );
    expect(screen.getByText("admin only")).toBeInTheDocument();
  });
});
