export type UserRole = "user" | "admin" | "owner";

export interface UserPublic {
  id: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  is_super_admin: boolean;
  project_id: string | null;
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
  set_id?: string | null;
  created_at: string;
}

export interface DocumentList {
  items: DocumentPublic[];
}

export interface DocumentSetPublic {
  id: string;
  project_id: string;
  name: string;
  document_type: DocumentType;
  documents: DocumentPublic[];
  created_at: string;
  updated_at: string;
}

export interface DocumentSetList {
  items: DocumentSetPublic[];
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
  verdict?: string | null;
  verdict_raw?: string | null;
  confidence?: number | null;
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

// ---------------------------------------------------------------------------
// DKOM Spot-check (super-admin only)

export type ClaimType =
  | "brand_lock" | "kratki_rok" | "vague_kriterij" | "diskrim_uvjeti"
  | "neprecizna_specifikacija" | "neispravna_grupacija" | "kriterij_odabira"
  | "ocjena_ponude" | "espd_dokazi" | "jamstvo" | "trosak_postupka" | "ostalo";

export type SpotcheckVerdict = "correct" | "wrong" | "uncertain" | "skip";

export interface ClaimSample {
  id: string;
  klasa: string;
  predmet: string;
  pdf_filename: string | null;
  pdf_url: string | null;
  llm_category: ClaimType;
  dkom_verdict: string;
  argument_zalitelja: string;
  obrana_narucitelja: string | null;
  dkom_obrazlozenje: string;
  violated_article_claimed: string | null;
}

export interface SpotcheckBatch {
  total_claims: number;
  sample_size: number;
  seed: number;
  items: ClaimSample[];
  already_reviewed_ids: string[];
}

export interface SpotcheckStats {
  total_feedback: number;
  by_verdict: Record<string, number>;
  accuracy: number | null;
  by_category_accuracy: Record<string, { correct: number; wrong: number; accuracy: number }>;
  miscls: { llm_said: string; correct: string; count: number }[];
}

// ---------------------------------------------------------------------------
// Žalbe modul

export type ZalbeClaimType = ClaimType | "auto";

export interface ZalbeAnalyzeRequest {
  argument: string;
  claim_type?: ZalbeClaimType;
  vijece_members?: string[];
  limit?: number;
}

export interface SimilarPrecedent {
  klasa: string;
  predmet: string;
  datum_odluke: string | null;
  narucitelj: string | null;
  vrsta_postupka: string | null;
  claim_type: string;
  dkom_verdict: string;
  argument_zalitelja: string;
  dkom_obrazlozenje: string;
  violated_article_claimed: string | null;
  outcome: string | null;
  vijece: string[];
  pdf_url: string | null;
  similarity: number;
}

export interface ZalbePrediction {
  n_similar: number;
  success_rate: number;
  detected_claim_type: string;
  type_distribution: Record<string, number>;
  panel_rate: number | null;
  panel_n_cases: number | null;
  panel_members_found: string[];
  panel_members_unknown: string[];
}

export interface ZalbeAnalyzeResponse {
  prediction: ZalbePrediction;
  similar_precedents: SimilarPrecedent[];
}
