"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  ApiError,
  getMe as apiGetMe,
  login as apiLogin,
  refresh as apiRefresh,
} from "@/lib/api";
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from "@/lib/auth-storage";
import type { User } from "@/lib/types";

export interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  /** Access token valid now, refreshing once if the current one is stale. */
  getValidToken: () => Promise<string | null>;
  /** Current access token (may be stale; use getValidToken for guaranteed freshness). */
  token: string | null;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState<string | null>(null);

  // On mount: if we have a token, try to resolve the current user.
  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      const accessToken = getAccessToken();
      setToken(accessToken);
      if (!accessToken) {
        setLoading(false);
        return;
      }
      try {
        const me = await apiGetMe({ token: accessToken });
        if (!cancelled) setUser(me);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          const refreshed = await tryRefresh();
          if (!cancelled && refreshed) {
            setToken(refreshed);
            try {
              const me = await apiGetMe({ token: refreshed });
              if (!cancelled) setUser(me);
            } catch {
              if (!cancelled) {
                clearTokens();
                setToken(null);
              }
            }
          } else if (!cancelled) {
            clearTokens();
            setToken(null);
          }
        } else if (!cancelled) {
          // Network or server error: keep tokens, treat as logged out for now.
          clearTokens();
          setToken(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await apiLogin(email, password);
    setTokens(tokens);
    setToken(tokens.access_token);
    const me = await apiGetMe({ token: tokens.access_token });
    setUser(me);
  }, []);

  const logout = useCallback(() => {
    clearTokens();
    setToken(null);
    setUser(null);
  }, []);

  const getValidToken = useCallback(async () => {
    const token = getAccessToken();
    if (!token) return null;
    return token;
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, loading, login, logout, getValidToken, token }),
    [user, loading, login, logout, getValidToken, token],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** Attempt a token refresh; returns the new access token or null. */
async function tryRefresh(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;
  try {
    const tokens = await apiRefresh(refreshToken);
    setTokens(tokens);
    return tokens.access_token;
  } catch {
    clearTokens();
    return null;
  }
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth doit être utilisé dans un <AuthProvider>");
  }
  return ctx;
}
