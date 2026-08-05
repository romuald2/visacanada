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

// --- CRS Calculator ---

export interface LanguageScore {
  reading: number;
  writing: number;
  listening: number;
  speaking: number;
  test_type: string;
}

export interface CRSCalculateRequest {
  age: number;
  marital_status: string;
  education_level: string;
  canadian_education: string;
  first_language: LanguageScore;
  second_language?: LanguageScore;
  canadian_experience_years: number;
  foreign_experience_years: number;
  spouse_education: string;
  spouse_language?: LanguageScore;
  spouse_canadian_experience_years: number;
  has_provincial_nomination: boolean;
  has_arranged_employment: boolean;
  arranged_employment_noc: string;
  has_canadian_sibling: boolean;
  french_language_proficiency: string;
}

export interface CRSResult {
  total_score: number;
  breakdown: Record<string, number>;
  clb_levels: {
    first: Record<string, number>;
    second?: Record<string, number>;
  };
  recommendations: string[];
  recent_rounds: Array<{
    date: string;
    score: number;
    program: string;
  }>;
  eligible_for_ita: boolean;
}

// --- Portal (Candidate self-service) ---

export interface CandidateProfile {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  nationality: string | null;
}

export type PortalDossierStatus =
  | "nouveau"
  | "en_cours"
  | "documents_manquants"
  | "en_revision"
  | "soumis"
  | "approuve"
  | "refuse"
  | "archive";

export interface PortalDossierSummary {
  id: number;
  status: PortalDossierStatus;
  status_label: {
    fr: string;
    en: string;
  };
  progress: number;
  reference_number: string | null;
  submitted_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface PortalDossierDetail {
  id: number;
  status: PortalDossierStatus;
  status_label: {
    fr: string;
    en: string;
  };
  progress: number;
  reference_number: string | null;
  program: {
    id: number;
    name: string;
    category: string;
  } | null;
  submitted_at: string | null;
  decision_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export type DocumentStatus = "uploaded" | "approved" | "rejected" | "expired";

export interface ProvidedDocument {
  id: number;
  document_type: string;
  file_name: string;
  status: DocumentStatus;
  rejection_reason: string | null;
  uploaded_at: string | null;
}

export interface MissingDocument {
  document_type: string;
  document_name: string;
  description: string | null;
  priority: string;
}

export interface DossierDocuments {
  dossier_id: number;
  provided: ProvidedDocument[];
  missing: MissingDocument[];
  provided_count: number;
  missing_count: number;
}

export type NotificationType =
  | "deadline_reminder"
  | "document_approved"
  | "document_rejected"
  | "status_change"
  | "message"
  | "system";

export interface PortalNotification {
  id: number;
  type: NotificationType;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string | null;
}
