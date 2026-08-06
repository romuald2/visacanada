/** Minimal typed API client for the VisaCanada backend. */

import type {
  DossierPage,
  DashboardOverview,
  TokenResponse,
  UpcomingResponse,
  User,
  AnalyticsOverview,
  SuccessRateByProgram,
  ProcessingTimeData,
  RevenueData,
  WorkloadForecast,
} from "@/lib/types";

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

async function parseError(response: Response): Promise<ApiError> {
  let detail = `Erreur ${response.status}`;
  try {
    const body = await response.json();
    if (body?.detail) detail = String(body.detail);
  } catch {
    // non-JSON error body; keep the status-based message
  }
  return new ApiError(detail, response.status);
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
    throw await parseError(response);
  }

  return (await response.json()) as T;
}

async function apiPost<T>(
  path: string,
  body: unknown,
  opts: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    "Content-Type": "application/json",
  };
  if (opts.token) {
    headers.Authorization = `Bearer ${opts.token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      signal: opts.signal,
    });
  } catch (err) {
    throw new ApiError(
      err instanceof Error ? err.message : "Erreur reseau",
      0,
    );
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as T;
}

// --- Auth endpoints ---

/** Authenticate with email/password. Throws ApiError(401) on bad credentials. */
export function login(
  email: string,
  password: string,
  opts: RequestOptions = {},
): Promise<TokenResponse> {
  return apiPost<TokenResponse>("/auth/login", { email, password }, opts);
}

/** Fetch the current user for a given access token. */
export function getMe(opts: RequestOptions = {}): Promise<User> {
  return apiGet<User>("/auth/me", opts);
}

/** Exchange a refresh token for a fresh token pair. */
export function refresh(
  refreshToken: string,
  opts: RequestOptions = {},
): Promise<TokenResponse> {
  return apiPost<TokenResponse>(
    "/auth/refresh",
    { refresh_token: refreshToken },
    opts,
  );
}

/** Fetch upcoming deadlines/alerts within `days` (default 30). */
export function getUpcomingDeadlines(
  opts: RequestOptions & { days?: number } = {},
): Promise<UpcomingResponse> {
  const days = opts.days ?? 30;
  return apiGet<UpcomingResponse>(`/alerts/upcoming?days=${days}`, opts);
}

/** List dossiers (paginated). The backend scopes results by role. */
export function getDossiers(
  opts: RequestOptions & {
    page?: number;
    size?: number;
    status?: string;
    program_id?: number;
    assigned_to?: number;
  } = {},
): Promise<DossierPage> {
  const params = new URLSearchParams();
  params.set("page", String(opts.page ?? 1));
  params.set("size", String(opts.size ?? 20));
  if (opts.status) params.set("status", opts.status);
  if (opts.program_id) params.set("program_id", String(opts.program_id));
  if (opts.assigned_to) params.set("assigned_to", String(opts.assigned_to));
  return apiGet<DossierPage>(`/dossiers/?${params.toString()}`, opts);
}

/** Get dashboard overview stats (counts by status, totals, compliance avg). */
export function getDashboardOverview(
  opts: RequestOptions = {},
): Promise<DashboardOverview> {
  return apiGet<DashboardOverview>("/dashboard/overview", opts);
}

// --- Analytics endpoints ---

/** Get analytics overview (active, approved, refused, archived counts). */
export function getAnalyticsOverview(
  opts: RequestOptions = {},
): Promise<AnalyticsOverview> {
  return apiGet<AnalyticsOverview>("/analytics/overview", opts);
}

/** Get success rate by program. */
export function getSuccessRate(
  opts: RequestOptions = {},
): Promise<SuccessRateByProgram[]> {
  return apiGet<SuccessRateByProgram[]>("/analytics/success-rate", opts);
}

/** Get processing time statistics. */
export function getProcessingTime(
  opts: RequestOptions = {},
): Promise<ProcessingTimeData> {
  return apiGet<ProcessingTimeData>("/analytics/processing-time", opts);
}

/** Get revenue data by period. */
export function getRevenue(
  opts: RequestOptions & { period?: "month" | "year" } = {},
): Promise<RevenueData> {
  const period = opts.period ?? "month";
  return apiGet<RevenueData>(`/analytics/revenue?period=${period}`, opts);
}

/** Get workload forecast. */
export function getWorkloadForecast(
  opts: RequestOptions = {},
): Promise<WorkloadForecast> {
  return apiGet<WorkloadForecast>("/analytics/workload-forecast", opts);
}
