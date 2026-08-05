/** Shared types mirroring the backend alerts/deadlines API. */

export type AlertSeverity = "critical" | "warning" | "info";

export type AlertType =
  | "passport_expiring"
  | "medical_expiring"
  | "language_expiring"
  | "express_entry_round"
  | "policy_change"
  | "submission_deadline"
  | "ita_response"
  | "biometrics"
  | "ppr"
  | "medical_request"
  | "permit_expiring";

/** One item from GET /alerts/upcoming. */
export interface UpcomingAlert {
  id: number;
  dossier_id: number;
  alert_type: AlertType;
  severity: AlertSeverity;
  title: string;
  message: string;
  days_left: number | null;
  is_notified: boolean;
  created_at: string | null;
}

/** Response envelope from GET /alerts/upcoming. */
export interface UpcomingResponse {
  count: number;
  window_days: number;
  items: UpcomingAlert[];
}

// --- Auth ---

export type UserRole = "admin" | "consultant" | "candidat";

/** Authenticated user, from GET /auth/me. */
export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** Token pair from POST /auth/login and /auth/refresh. */
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// --- Dossiers ---

export type DossierStatus =
  | "nouveau"
  | "en_cours"
  | "documents_manquants"
  | "en_revision"
  | "soumis"
  | "approuve"
  | "refuse"
  | "archive";

/** One dossier from GET /dossiers/ (staff view). */
export interface Dossier {
  id: number;
  candidate_id: number;
  program_id: number;
  assigned_to: number | null;
  status: DossierStatus;
  compliance_score: number | null;
  reference_number: string | null;
  notes: string | null;
  submitted_at: string | null;
  decision_at: string | null;
  created_at: string;
  updated_at: string;
}

/** Paginated envelope from GET /dossiers/. */
export interface DossierPage {
  items: Dossier[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// --- Dashboard ---

/** Response from GET /dashboard/overview. */
export interface DashboardOverview {
  total_dossiers: number;
  total_candidates: number;
  average_compliance_score: number | null;
  by_status: Record<string, number>;
}

// --- Analytics ---

export interface AnalyticsOverview {
  active: number;
  approved: number;
  refused: number;
  archived: number;
}

export interface SuccessRateByProgram {
  program_id: number;
  program_name: string;
  total: number;
  approved: number;
  refused: number;
  approval_rate: number;
}

export interface ProcessingTimeData {
  overall_avg: number;
  by_program: Array<{
    program_id: number;
    program_name: string;
    avg_days: number;
    count: number;
  }>;
}

export interface RevenueData {
  total: number;
  period: string;
  series: Array<{
    period: string;
    amount: number;
  }>;
}

export interface WorkloadForecast {
  expected_decisions_30d: number;
  expected_decisions_90d: number;
  by_program: Array<{
    program_id: number;
    program_name: string;
    count: number;
  }>;
}
