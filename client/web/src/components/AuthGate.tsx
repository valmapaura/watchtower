"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import LoginScreen from "@/components/LoginScreen";
import SetupWizard from "@/components/SetupWizard";

/** Shows login when not authenticated; first-run setup when no cameras exist. */
export default function AuthGate({ children }: { children: React.ReactNode }) {
  const { authenticated, loading } = useAuth();
  const [checkingSetup, setCheckingSetup] = useState(true);
  const [needsSetup, setNeedsSetup] = useState(false);

  useEffect(() => {
    if (!authenticated) return;
    let cancelled = false;
    api
      .getSettings()
      .then((s) => {
        if (!cancelled) setNeedsSetup(s.cameras.length === 0);
      })
      .catch(() => {
        if (!cancelled) setNeedsSetup(false);
      })
      .finally(() => {
        if (!cancelled) setCheckingSetup(false);
      });
    return () => {
      cancelled = true;
    };
  }, [authenticated]);

  if (loading || (authenticated && checkingSetup)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-zinc-700 border-t-emerald-500" />
      </div>
    );
  }

  if (!authenticated) {
    return <LoginScreen />;
  }

  if (needsSetup) {
    return <SetupWizard onDone={() => setNeedsSetup(false)} />;
  }

  return <>{children}</>;
}