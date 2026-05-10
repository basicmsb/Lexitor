export type UserRole = "user" | "admin" | "owner";

export interface UserPublic {
  id: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  project_id: string;
  created_at: string;
}

export interface ProjectPublic {
  id: string;
  name: string;
  slug: string;
  created_at: string;
}

export interface ProjectInfo {
  id: string;
  name: string;
  slug: string;
  logo_path: string | null;
  has_logo: boolean;
}

export interface MeResponse {
  user: UserPublic;
  project: ProjectPublic;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export type DocumentType = "troskovnik" | "don" | "zalba" | "other";

export type TroskovnikType = "ponudbeni" | "procjena" | "nepoznato";

export interface DocumentPublic {
  id: string;
  project_id: string;
  uploaded_by_id: string | null;
  filename: string;
  content_type: string;
  size_bytes: number;
  document_type: DocumentType;
  troskovnik_type: TroskovnikType;
  created_at: string;
}

export interface DocumentList {
  items: DocumentPublic[];
}

export type AnalysisStatus = "pending" | "running" | "complete" | "error";

export type AnalysisItemStatus =
  | "ok"
  | "warn"
  | "fail"
  | "neutral"
  | "accepted"
  | "uncertain";

export type CitationSource = "zjn" | "dkom" | "vus" | "eu" | "other";

export interface CitationPublic {
  id: string;
  source: CitationSource;
  reference: string;
  snippet: string;
  url: string | null;
  page?: number | null;
}

export interface HighlightSpan {
  start: number;
  end: number;
  label: string;
  kind: string;
}

export type UserVerdict = "correct" | "incorrect";

export interface UserAddedFinding {
  id: string;
  kind: string;
  status: AnalysisItemStatus;
  comment: string;
  created_at: string;
}

export interface UserAddedFindingCreate {
  kind: string;
  status: AnalysisItemStatus;
  comment: string;
}

export interface FindingCitation {
  source: string;
  reference: string;
  snippet?: string | null;
  url?: string | null;
  page?: number | null;
}

export interface FindingPublic {
  kind: string;
  status: AnalysisItemStatus;
  explanation: string | null;
  suggestion: string | null;
  is_mock: boolean;
  citations: FindingCitation[];
}

export interface AnalysisItemPublic {
  id: string;
  position: number;
  label: string | null;
  text: string;
  status: AnalysisItemStatus;
  explanation: string | null;
  suggestion: string | null;
  metadata_json?: Record<string, unknown> | null;
  highlights?: HighlightSpan[] | null;
  citations: CitationPublic[];
  findings?: FindingPublic[] | null;
  user_verdict?: UserVerdict | null;
  user_comment?: string | null;
  include_in_pdf?: boolean;
  user_added_findings?: UserAddedFinding[] | null;
  user_kind_override?: string | null;
}

export interface AnalysisItemFeedbackUpdate {
  user_verdict?: UserVerdict | null;
  user_comment?: string | null;
  include_in_pdf?: boolean;
  user_kind_override?: string | null;
  clear_verdict?: boolean;
  clear_kind_override?: boolean;
}

export interface AnalysisSummary {
  ok: number;
  warn: number;
  fail: number;
  neutral?: number;
  accepted?: number;
  uncertain?: number;
  total: number;
}

export interface AnalysisPublic {
  id: string;
  document_id: string;
  status: AnalysisStatus;
  progress_percent: number;
  error_message: string | null;
  summary: AnalysisSummary | null;
  created_at: string;
  updated_at: string;
}

export interface AnalysisDetail extends AnalysisPublic {
  items: AnalysisItemPublic[];
}

export interface StartAnalysisResponse {
  analysis_id: string;
  document_id: string;
  status: AnalysisStatus;
}

export interface KnowledgeHit {
  klasa: string;
  predmet: string;
  page: number | null;
  chunk_index: number;
  text: string;
  score: number;
  pdf_url: string | null;
  odluka_datum: string | null;
  year: string | null;
}

export interface KnowledgeSearchResponse {
  query: string;
  hits: KnowledgeHit[];
}

export type KnowledgeSourceKind = "zjn" | "dkom" | "vus" | "eu" | "other";

export interface IndexedSource {
  source: string;
  klasa: string;
  predmet: string;
  narucitelj?: string | null;
  vrsta?: string | null;
  year?: string | null;
  odluka_datum?: string | null;
  pdf_url?: string | null;
  article_number?: number | null;
}

export interface SourcesResponse {
  items: IndexedSource[];
  total: number;
}
