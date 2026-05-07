"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api } from "@/lib/api";
import { clearTokens, getAccessToken, setTokens } from "@/lib/auth-storage";
import type { MeResponse } from "@/lib/types";

interface AuthContextValue {
  status: "loading" | "anon" | "authed";
  me: MeResponse | null;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: {
    email: string;
    password: string;
    full_name?: string;
    project_name: string;
  }) => Promise<void>;
  logout: () => void;
  refreshMe: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [status, setStatus] = useState<"loading" | "anon" | "authed">("loading");
  const [me, setMe] = useState<MeResponse | null>(null);

  const refreshMe = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setStatus("anon");
      setMe(null);
      return;
    }
    try {
      const data = await api.me();
      setMe(data);
      setStatus("authed");
    } catch {
      clearTokens();
      setStatus("anon");
      setMe(null);
    }
  }, []);

  useEffect(() => {
    void refreshMe();
  }, [refreshMe]);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await api.login(email, password);
      setTokens(tokens.access_token, tokens.refresh_token);
      await refreshMe();
      router.push("/dashboard");
    },
    [refreshMe, router],
  );

  const register = useCallback(
    async (payload: {
      email: string;
      password: string;
      full_name?: string;
      project_name: string;
    }) => {
      const tokens = await api.register(payload);
      setTokens(tokens.access_token, tokens.refresh_token);
      await refreshMe();
      router.push("/dashboard");
    },
    [refreshMe, router],
  );

  const logout = useCallback(() => {
    clearTokens();
    setMe(null);
    setStatus("anon");
    router.push("/login");
  }, [router]);

  const value = useMemo<AuthContextValue>(
    () => ({ status, me, login, register, logout, refreshMe }),
    [status, me, login, register, logout, refreshMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
