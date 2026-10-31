import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { api, clearTokens, getAccessToken, getRefreshToken, setTokens } from "@/lib/api";
import type { TokenPair, User } from "@/types";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (payload: {
    name: string;
    email: string;
    password: string;
    confirm_password: string;
    company_name?: string;
    company_slug?: string;
  }) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

async function loadMe(): Promise<User> {
  return api<User>("/auth/me");
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const boot = async () => {
      if (!getAccessToken() && !getRefreshToken()) {
        setLoading(false);
        return;
      }
      try {
        setUser(await loadMe());
      } catch {
        clearTokens();
        setUser(null);
      } finally {
        setLoading(false);
      }
    };
    void boot();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      async login(email, password) {
        const tokens = await api<TokenPair>("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
          skipAuth: true,
        });
        setTokens(tokens.access_token, tokens.refresh_token);
        const me = await loadMe();
        setUser(me);
        return me;
      },
      async register(payload) {
        const tokens = await api<TokenPair>("/auth/register", {
          method: "POST",
          body: JSON.stringify(payload),
          skipAuth: true,
        });
        setTokens(tokens.access_token, tokens.refresh_token);
        const me = await loadMe();
        setUser(me);
        return me;
      },
      async logout() {
        const refresh = getRefreshToken();
        try {
          if (refresh) {
            await api("/auth/logout", {
              method: "POST",
              body: JSON.stringify({ refresh_token: refresh }),
              skipAuth: true,
            });
          }
        } finally {
          clearTokens();
          setUser(null);
        }
      },
      async refreshUser() {
        setUser(await loadMe());
      },
    }),
    [user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
