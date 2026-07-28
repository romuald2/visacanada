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
