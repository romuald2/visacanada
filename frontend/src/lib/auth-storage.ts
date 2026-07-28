/** Token persistence for the auth session.
 *
 * Uses localStorage (internal-tool context, not exposed to hostile clients).
 * Every access is guarded for SSR since Next.js renders on the server first.
 */

import type { TokenResponse } from "@/lib/types";

const ACCESS_KEY = "vc.access_token";
const REFRESH_KEY = "vc.refresh_token";

function available(): boolean {
  return typeof window !== "undefined" && !!window.localStorage;
}

export function getAccessToken(): string | null {
  if (!available()) return null;
  return window.localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  if (!available()) return null;
  return window.localStorage.getItem(REFRESH_KEY);
}

export function setTokens(tokens: Pick<TokenResponse, "access_token" | "refresh_token">): void {
  if (!available()) return;
  window.localStorage.setItem(ACCESS_KEY, tokens.access_token);
  window.localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}

export function clearTokens(): void {
  if (!available()) return;
  window.localStorage.removeItem(ACCESS_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
}
