"use client";

import { LayoutDashboard, LogOut, FileText } from "lucide-react";
import { useAuth } from "@/components/auth/AuthProvider";
import type { UserRole } from "@/lib/types";

const ROLE_LABELS: Record<UserRole, string> = {
  admin: "Administrateur",
  consultant: "Consultant",
  candidat: "Candidat",
};

export interface AppShellProps {
  children: React.ReactNode;
  title?: string;
}

/** Authenticated app frame: sidebar + header with user identity and logout. */
export function AppShell({ children, title = "Tableau de bord" }: AppShellProps) {
  const { user, logout } = useAuth();

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="hidden w-56 flex-col border-r border-border bg-card p-4 md:flex">
        <div className="mb-6 px-2 text-lg font-semibold text-card-foreground">
          VisaCanada
        </div>
        <nav className="flex flex-col gap-1 text-sm">
          <a
            href="/dashboard"
            className="flex items-center gap-2 rounded-md px-2 py-2 text-card-foreground hover:bg-secondary"
          >
            <LayoutDashboard className="h-4 w-4" aria-hidden />
            Tableau de bord
          </a>
          <a
            href="/dashboard"
            className="flex items-center gap-2 rounded-md px-2 py-2 text-muted-foreground hover:bg-secondary"
          >
            <FileText className="h-4 w-4" aria-hidden />
            Dossiers
          </a>
        </nav>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-border bg-card px-6 py-3">
          <h1 className="text-lg font-semibold text-card-foreground">{title}</h1>
          <div className="flex items-center gap-4">
            {user ? (
              <div className="text-right">
                <p className="text-sm font-medium text-card-foreground">
                  {user.full_name}
                </p>
                <p className="text-xs text-muted-foreground">
                  {ROLE_LABELS[user.role]}
                </p>
              </div>
            ) : null}
            <button
              type="button"
              onClick={logout}
              className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm text-card-foreground hover:bg-secondary"
            >
              <LogOut className="h-4 w-4" aria-hidden />
              Déconnexion
            </button>
          </div>
        </header>

        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
