"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AnalysisResults } from "@/components/AnalysisResults";
import { useAnalysisStream } from "@/hooks/useAnalysisStream";
import { api } from "@/lib/api";
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

  if (!documentId) return null;

  if (bootstrapping) {
    return <p className="text-sm text-slate-500">Pripremam analizu…</p>;
  }

  if (bootstrapError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
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
            className="text-sm text-slate-500 hover:text-slate-700 mb-2"
          >
            ← Natrag na popis
          </button>
          <h1 className="font-serif text-2xl font-semibold text-slate-900">
            {document?.filename ?? "Analiza"}
          </h1>
        </div>
        <button
          type="button"
          onClick={restart}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:border-slate-400"
        >
          Pokreni ponovno
        </button>
      </div>

      <AnalysisResults
        status={stream.status}
        progress={stream.progress}
        items={items}
        summary={stream.summary}
        error={stream.error}
      />
    </div>
  );
}
