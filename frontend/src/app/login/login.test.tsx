import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import LoginPage from "./page";
import { ApiError } from "@/lib/api";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
}));

const login = vi.fn();
let mockUser: { role: string } | null = null;
let mockLoading = false;
vi.mock("@/components/auth/AuthProvider", () => ({
  useAuth: () => ({
    user: mockUser,
    loading: mockLoading,
    login,
    logout: vi.fn(),
    getValidToken: vi.fn(),
  }),
}));

beforeEach(() => {
  vi.clearAllMocks();
  mockUser = null;
  mockLoading = false;
});

describe("LoginPage", () => {
  it("renders the form", () => {
    render(<LoginPage />);
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Mot de passe")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /se connecter/i })).toBeInTheDocument();
  });

  it("logs in and redirects to the dashboard", async () => {
    login.mockResolvedValue(undefined);
    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "admin@cabinet.ca" },
    });
    fireEvent.change(screen.getByLabelText("Mot de passe"), {
      target: { value: "secret12" },
    });
    fireEvent.click(screen.getByRole("button", { name: /se connecter/i }));

    await waitFor(() =>
      expect(login).toHaveBeenCalledWith("admin@cabinet.ca", "secret12"),
    );
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
  });

  it("shows an error on bad credentials", async () => {
    login.mockRejectedValue(new ApiError("Email ou mot de passe incorrect", 401));
    render(<LoginPage />);
    fireEvent.click(screen.getByRole("button", { name: /se connecter/i }));

    expect(
      await screen.findByText("Email ou mot de passe incorrect"),
    ).toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });

  it("shows a rate-limit message on 429", async () => {
    login.mockRejectedValue(new ApiError("throttled", 429));
    render(<LoginPage />);
    fireEvent.click(screen.getByRole("button", { name: /se connecter/i }));

    expect(await screen.findByText(/trop de tentatives/i)).toBeInTheDocument();
  });

  it("redirects away if already authenticated", async () => {
    mockUser = { role: "admin" };
    render(<LoginPage />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
  });
});
