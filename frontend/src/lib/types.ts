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

// --- Knowledge / RAG ---

export type KnowledgeSourceType = "ircc_page" | "policy" | "manual" | "faq";
export type MessageRole = "user" | "assistant";

/** Knowledge document from GET /knowledge/documents. */
export interface KnowledgeDocument {
  id: number;
  title: string;
  source_type: KnowledgeSourceType;
  source_url: string | null;
  language: string;
  chunk_count: number;
  updated_at: string | null;
}

/** Request body for POST /knowledge/documents. */
export interface IngestDocumentRequest {
  title: string;
  content: string;
  source_type?: string;
  source_url?: string | null;
  language?: string;
}

/** Response from POST /knowledge/documents. */
export interface IngestDocumentResponse {
  detail: string;
  document_id: number;
  reingested: boolean;
  chunk_count: number;
  embedding_method?: string;
}

/** Citation in a chat message. */
export interface Citation {
  document_id: number;
  title: string;
  source_url: string | null;
  score: number;
}

/** One message in a conversation. */
export interface ChatMessage {
  id: number;
  role: MessageRole;
  content: string;
  citations: Citation[];
  method: string | null;
  created_at: string | null;
}

/** Conversation summary from GET /knowledge/conversations. */
export interface ConversationSummary {
  id: number;
  title: string;
  updated_at: string | null;
}

/** Full conversation from GET /knowledge/conversations/{id}. */
export interface Conversation {
  id: number;
  title: string;
  messages: ChatMessage[];
}

/** Request body for POST /knowledge/ask. */
export interface AskRequest {
  question: string;
  conversation_id?: number | null;
  top_k?: number;
}

/** Response from POST /knowledge/ask. */
export interface AskResponse {
  conversation_id: number;
  message_id: number;
  answer: string;
  method: string;
  citations: Citation[];
}
