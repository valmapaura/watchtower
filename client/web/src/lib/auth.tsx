"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api } from "@/lib/api";

interface AuthContextValue {
  /** Whether the user is authenticated (or auth is disabled). */
  authenticated: boolean;
  /** Whether we've finished checking auth status on load. */
  loading: boolean;
  login: (password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .authStatus()
      .then((res) => {
        if (!cancelled) setAuthenticated(res.authenticated);
      })
      .catch(() => {
        // Backend unreachable — assume not authenticated.
        if (!cancelled) setAuthenticated(false);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = async (password: string) => {
    await api.login(password);
    setAuthenticated(true);
  };

  const logout = async () => {
    try {
      await api.logout();
    } finally {
      setAuthenticated(false);
    }
  };

  return (
    <AuthContext.Provider value={{ authenticated, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}