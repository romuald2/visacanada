"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";

/** Entry point: show landing page when not authenticated, else route to dashboard. */
export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    // If authenticated, redirect to dashboard
    if (user) {
      router.replace("/dashboard");
    }
  }, [loading, user, router]);

  // Show landing page when not authenticated
  if (!user && !loading) {
    router.replace("/landing");
    return null;
  }

  return (
    <main className="flex min-h-screen items-center justify-center text-muted-foreground">
      Chargement…
    </main>
  );
}
