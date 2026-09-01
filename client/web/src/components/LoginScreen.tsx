"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth";
import Icon from "@/components/Icon";
import Spinner from "@/components/Spinner";

export default function LoginScreen() {
  const { login } = useAuth();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(password);
    } catch {
      setError("That password isn't right. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950 px-4">
      <div className="w-full max-w-sm">
        <div className="flex justify-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/15 text-emerald-400">
            <Icon name="camera" className="h-7 w-7" />
          </div>
        </div>
        <h1 className="mt-5 text-center text-2xl font-semibold tracking-tight">
          Welcome to Watchtower
        </h1>
        <p className="mt-2 text-center text-sm text-zinc-500">
          Enter your password to view your cameras and recordings.
        </p>

        <form onSubmit={submit} className="mt-8 space-y-4">
          <div>
            <label className="text-sm text-zinc-400">Password</label>
            <input
              type="password"
              autoFocus
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Your password"
              className="mt-1.5 w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-emerald-500"
            />
          </div>
          {error && (
            <div className="rounded-lg border border-red-900/50 bg-red-950/40 px-4 py-3 text-sm text-red-300">
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={busy || !password}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-500 px-5 py-2 text-sm font-medium text-zinc-950 transition-colors hover:bg-emerald-400 disabled:opacity-50"
          >
            {busy ? (
              <Spinner className="h-4 w-4 text-zinc-950" label="Signing in…" />
            ) : (
              "Sign in"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}