import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "@/lib/auth-storage";
import type {
  AnalysisDetail,
  AnalysisItemFeedbackUpdate,
  AnalysisItemPublic,
  AnalysisPublic,
  DocumentList,
  DocumentPublic,
  DocumentType,
  KnowledgeSearchResponse,
  KnowledgeSourceKind,
  MeResponse,
  ProjectInfo,
  SourcesResponse,
  StartAnalysisResponse,
  TokenPair,
  UserAddedFindingCreate,
} from "@/lib/types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

const API_BASE = API_BASE_URL;

class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

interface RequestOptions extends RequestInit {
  skipAuth?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { skipAuth, headers, body, ...rest } = options;
  const isFormData = typeof FormData !== "undefined" && body instanceof FormData;

  const finalHeaders: Record<string, string> = {
    ...((headers as Record<string, string>) ?? {}),
  };
  if (!isFormData && body !== undefined && finalHeaders["Content-Type"] === undefined) {
    finalHeaders["Content-Type"] = "application/json";
  }

  if (!skipAuth) {
    const token = getAccessToken();
    if (token) finalHeaders.Authorization = `Bearer ${token}`;
  }

  const fetchInit: RequestInit = { ...rest, body, headers: finalHeaders };

  const response = await fetch(`${API_BASE}${path}`, fetchInit);

  if (response.status === 401 && !skipAuth) {
    const rotated = await tryRefresh();
    if (rotated) {
      finalHeaders.Authorization = `Bearer ${rotated}`;
      const retry = await fetch(`${API_BASE}${path}`, { ...fetchInit, headers: finalHeaders });
      if (!retry.ok) {
        clearTokens();
        throw await toError(retry);
      }
      return (await retry.json()) as T;
    }
    clearTokens();
    throw await toError(response);
  }

  if (!response.ok) throw await toError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function toError(response: Response): Promise<ApiError> {
  let detail = response.statusText;
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") detail = body.detail;
  } catch {
    /* ignore */
  }
  return new ApiError(response.status, detail);
}

async function tryRefresh(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;
  try {
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!response.ok) return null;
    const data = (await response.json()) as TokenPair;
    setTokens(data.access_token, data.refresh_token);
    return data.access_token;
  } catch {
    return null;
  }
}

export const api = {
  async register(payload: {
    email: string;
    password: string;
    full_name?: string;
    project_name: string;
  }): Promise<TokenPair> {
    return request<TokenPair>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
      skipAuth: true,
    });
  },

  async login(email: string, password: string): Promise<TokenPair> {
    return request<TokenPair>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
      skipAuth: true,
    });
  },

  async me(): Promise<MeResponse> {
    return request<MeResponse>("/auth/me");
  },

  async uploadDocument(file: File, type: DocumentType): Promise<DocumentPublic> {
    const form = new FormData();
    form.append("file", file);
    form.append("document_type", type);
    return request<DocumentPublic>("/documents", {
      method: "POST",
      body: form,
    });
  },

  async listDocuments(): Promise<DocumentList> {
    return request<DocumentList>("/documents");
  },

  async getDocument(id: string): Promise<DocumentPublic> {
    return request<DocumentPublic>(`/documents/${id}`);
  },

  async deleteDocument(id: string): Promise<void> {
    await request<void>(`/documents/${id}`, { method: "DELETE" });
  },

  async listDocumentAnalyses(documentId: string): Promise<AnalysisPublic[]> {
    return request<AnalysisPublic[]>(`/documents/${documentId}/analyses`);
  },

  async startAnalysis(documentId: string): Promise<StartAnalysisResponse> {
    return request<StartAnalysisResponse>(`/documents/${documentId}/analyze`, {
      method: "POST",
    });
  },

  async getAnalysis(id: string): Promise<AnalysisDetail> {
    return request<AnalysisDetail>(`/analyses/${id}`);
  },

  async updateItemFeedback(
    analysisId: string,
    itemId: string,
    payload: AnalysisItemFeedbackUpdate,
  ): Promise<AnalysisItemPublic> {
    return request<AnalysisItemPublic>(
      `/analyses/${analysisId}/items/${itemId}`,
      {
        method: "PATCH",
        body: JSON.stringify(payload),
      },
    );
  },

  async addUserFinding(
    analysisId: string,
    itemId: string,
    payload: UserAddedFindingCreate,
  ): Promise<AnalysisItemPublic> {
    return request<AnalysisItemPublic>(
      `/analyses/${analysisId}/items/${itemId}/user-findings`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
  },

  async deleteUserFinding(
    analysisId: string,
    itemId: string,
    findingId: string,
  ): Promise<AnalysisItemPublic> {
    return request<AnalysisItemPublic>(
      `/analyses/${analysisId}/items/${itemId}/user-findings/${findingId}`,
      { method: "DELETE" },
    );
  },

  async exportLabels(params: { since?: string; documentId?: string } = {}): Promise<Blob> {
    const query = new URLSearchParams();
    if (params.since) query.set("since", params.since);
    if (params.documentId) query.set("document_id", params.documentId);
    const qs = query.toString();
    const path = `/admin/export-labels${qs ? `?${qs}` : ""}`;
    const token = getAccessToken();
    const response = await fetch(`${API_BASE}${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    if (!response.ok) throw await toError(response);
    return await response.blob();
  },

  async searchKnowledge(
    query: string,
    options: { limit?: number; year?: string; source?: KnowledgeSourceKind } = {},
  ): Promise<KnowledgeSearchResponse> {
    return request<KnowledgeSearchResponse>("/knowledge/search", {
      method: "POST",
      body: JSON.stringify({
        query,
        limit: options.limit ?? 10,
        year: options.year,
        source: options.source,
      }),
    });
  },

  async listSources(): Promise<SourcesResponse> {
    return request<SourcesResponse>("/knowledge/sources");
  },

  async getMyProject(): Promise<ProjectInfo> {
    return request<ProjectInfo>("/projects/me");
  },

  async uploadProjectLogo(file: File): Promise<ProjectInfo> {
    const form = new FormData();
    form.append("file", file);
    return request<ProjectInfo>("/projects/me/logo", {
      method: "POST",
      body: form,
    });
  },

  async deleteProjectLogo(): Promise<ProjectInfo> {
    return request<ProjectInfo>("/projects/me/logo", { method: "DELETE" });
  },
};

export { ApiError };
