"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "./AuthProvider";
import type { UserRole } from "@/lib/types";

export interface RequireAuthProps {
  children: React.ReactNode;
  /** If set, the user must hold one of these roles, else they are redirected. */
  roles?: UserRole[];
  /** Where to send unauthenticated users. */
  redirectTo?: string;
}

/**
 * Client-side route guard. Redirects to `/login` while unauthenticated, and to
 * `/dashboard` when the user is authenticated but lacks the required role.
 */
export function RequireAuth({
  children,
  roles,
  redirectTo = "/login",
}: RequireAuthProps) {
  const { user, loading } = useAuth();
  const router = useRouter();

  const roleAllowed = !roles || (user != null && roles.includes(user.role));

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace(redirectTo);
    } else if (!roleAllowed) {
      router.replace("/dashboard");
    }
  }, [loading, user, roleAllowed, redirectTo, router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground">
        Chargement…
      </div>
    );
  }

  if (!user || !roleAllowed) {
    return null;
  }

  return <>{children}</>;
}
