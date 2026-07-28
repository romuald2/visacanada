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
