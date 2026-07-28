/** Minimal typed API client for the VisaCanada backend. */

import type { UpcomingResponse } from "@/lib/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface RequestOptions {
  token?: string;
  signal?: AbortSignal;
}

async function apiGet<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (opts.token) {
    headers.Authorization = `Bearer ${opts.token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers,
      signal: opts.signal,
    });
  } catch (err) {
    throw new ApiError(
      err instanceof Error ? err.message : "Erreur reseau",
      0,
    );
  }

  if (!response.ok) {
    let detail = `Erreur ${response.status}`;
    try {
      const body = await response.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      // non-JSON error body; keep the status-based message
    }
    throw new ApiError(detail, response.status);
  }

  return (await response.json()) as T;
}

/** Fetch upcoming deadlines/alerts within `days` (default 30). */
export function getUpcomingDeadlines(
  opts: RequestOptions & { days?: number } = {},
): Promise<UpcomingResponse> {
  const days = opts.days ?? 30;
  return apiGet<UpcomingResponse>(`/alerts/upcoming?days=${days}`, opts);
}
