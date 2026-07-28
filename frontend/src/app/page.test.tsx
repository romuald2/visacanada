import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Home from "./page";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
}));

let mockUser: { role: string } | null = null;
let mockLoading = false;
vi.mock("@/components/auth/AuthProvider", () => ({
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

describe("Home (entry redirect)", () => {
  it("waits while auth is loading", () => {
    mockLoading = true;
    render(<Home />);
    expect(replace).not.toHaveBeenCalled();
    expect(screen.getByText(/chargement/i)).toBeInTheDocument();
  });

  it("redirects to login when unauthenticated", async () => {
    render(<Home />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
  });

  it("redirects to dashboard when authenticated", async () => {
    mockUser = { role: "consultant" };
    render(<Home />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
  });
});
