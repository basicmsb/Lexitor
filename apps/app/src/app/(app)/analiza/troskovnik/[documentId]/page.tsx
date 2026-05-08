"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AnalysisResults } from "@/components/AnalysisResults";
import { useAnalysisStream } from "@/hooks/useAnalysisStream";
import { API_BASE_URL, api } from "@/lib/api";
import { getAccessToken } from "@/lib/auth-storage";
import type { AnalysisItemPublic, DocumentPublic } from "@/lib/types";

export default function TroskovnikDetailPage() {
  const params = useParams<{ documentId: string }>();
  const router = useRouter();
  const documentId = params?.documentId;

  const [document, setDocument] = useState<DocumentPublic | null>(null);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [bootstrapError, setBootstrapError] = useState<string | null>(null);
  const [bootstrapping, setBootstrapping] = useState(true);

  const stream = useAnalysisStream(analysisId);
  const [historicalItems, setHistoricalItems] = useState<AnalysisItemPublic[]>([]);

  const bootstrap = useCallback(async () => {
    if (!documentId) return;
    setBootstrapping(true);
    setBootstrapError(null);
    try {
      const doc = await api.getDocument(documentId);
      setDocument(doc);

      const existing = await api.listDocumentAnalyses(documentId);
      if (existing.length === 0) {
        const started = await api.startAnalysis(documentId);
        setAnalysisId(started.analysis_id);
        setHistoricalItems([]);
      } else {
        const latest = existing[0];
        setAnalysisId(latest.id);
        if (latest.status === "complete" || latest.status === "error") {
          const detail = await api.getAnalysis(latest.id);
          setHistoricalItems(detail.items);
        }
      }
    } catch (err) {
      setBootstrapError(err instanceof Error ? err.message : "Greška pri pripremi analize.");
    } finally {
      setBootstrapping(false);
    }
  }, [documentId]);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  const restart = async () => {
    if (!documentId) return;
    setHistoricalItems([]);
    setAnalysisId(null);
    try {
      const started = await api.startAnalysis(documentId);
      setAnalysisId(started.analysis_id);
    } catch (err) {
      setBootstrapError(err instanceof Error ? err.message : "Pokretanje nije uspjelo.");
    }
  };

  const exportPdf = (onlyErrors: boolean) => {
    if (!analysisId) return;
    const token = getAccessToken();
    if (!token) {
      setBootstrapError("Nedostaje pristupni token. Prijavi se ponovno.");
      return;
    }
    const params = new URLSearchParams({
      token,
      only_errors: String(onlyErrors),
    });
    // Open in a new tab — browser handles the download via the
    // attachment Content-Disposition header.
    window.open(
      `${API_BASE_URL}/analyses/${analysisId}/pdf?${params}`,
      "_blank",
      "noopener,noreferrer",
    );
  };

  if (!documentId) return null;

  if (bootstrapping) {
    return <p className="text-sm text-muted">Pripremam analizu…</p>;
  }

  if (bootstrapError) {
    return (
      <div className="rounded-lg border border-[#A8392B]/30 bg-[#A8392B]/10 p-4 text-sm text-[#7C2A21]">
        {bootstrapError}
      </div>
    );
  }

  const items = stream.items.length > 0 ? stream.items : historicalItems;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <button
            type="button"
            onClick={() => router.push("/analiza/troskovnik")}
            className="text-sm text-muted hover:text-ink mb-2 transition"
          >
            ← Natrag na popis
          </button>
          <h1 className="font-display text-2xl text-ink">{document?.filename ?? "Analiza"}</h1>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative inline-flex rounded-md border border-brand-border overflow-hidden">
            <button
              type="button"
              onClick={() => exportPdf(false)}
              disabled={!analysisId || stream.status !== "complete"}
              className="px-3 py-1.5 text-sm text-navy hover:bg-surface-2 disabled:opacity-40 disabled:cursor-not-allowed transition"
              title="Izvezi cijelu analizu u PDF"
            >
              Izvezi PDF
            </button>
            <button
              type="button"
              onClick={() => exportPdf(true)}
              disabled={!analysisId || stream.status !== "complete"}
              className="px-3 py-1.5 text-sm text-navy hover:bg-surface-2 disabled:opacity-40 disabled:cursor-not-allowed transition border-l border-brand-border"
              title="Izvezi samo stavke s nalazima (FAIL/WARN/UNCERTAIN)"
            >
              Samo greške
            </button>
          </div>
          <button
            type="button"
            onClick={restart}
            className="rounded-md border border-brand-border px-3 py-1.5 text-sm text-navy hover:border-ink transition"
          >
            Pokreni ponovno
          </button>
        </div>
      </div>

      <AnalysisResults
        status={stream.status}
        progress={stream.progress}
        items={items}
        summary={stream.summary}
        error={stream.error}
        analysisId={analysisId ?? ""}
      />
    </div>
  );
}
