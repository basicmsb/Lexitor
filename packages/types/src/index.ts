export type AnalysisStatus = "ok" | "warn" | "fail" | "neutral" | "accepted" | "uncertain";

export interface AnalysisItem {
  id: string;
  text: string;
  status: AnalysisStatus;
  explanation?: string;
  citations?: Citation[];
}

export interface Citation {
  source: "ZJN" | "DKOM" | "VUS" | "EU";
  reference: string;
  snippet: string;
  url?: string;
}

export interface AnalysisDocument {
  id: string;
  filename: string;
  type: "troskovnik" | "don" | "zalba" | "drugo";
  uploadedAt: string;
  items: AnalysisItem[];
  status: "pending" | "running" | "complete" | "error";
}
