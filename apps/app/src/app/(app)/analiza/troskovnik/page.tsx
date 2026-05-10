"use client";

import { useCallback, useEffect, useState } from "react";

import { DocumentList } from "@/components/DocumentList";
import { UploadDropzone } from "@/components/UploadDropzone";
import { api } from "@/lib/api";
import type { DocumentPublic } from "@/lib/types";

export default function AnalizaTroskovnikPage() {
  const [documents, setDocuments] = useState<DocumentPublic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const list = await api.listDocuments();
      setDocuments(list.items.filter((d) => d.document_type === "troskovnik"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Greška pri dohvatu.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const onUploaded = (doc: DocumentPublic) => {
    setDocuments((prev) => [doc, ...prev]);
  };

  const onDeleted = (id: string) => {
    setDocuments((prev) => prev.filter((d) => d.id !== id));
  };

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <h1 className="font-display text-3xl text-ink mb-2">Analiza troškovnika</h1>
        <p className="text-muted">
          Učitaj PDF, XLSX ili .arhigonfile — Lexitor će analizirati svaku stavku.
        </p>
      </div>

      <UploadDropzone documentType="troskovnik" onUploaded={onUploaded} />

      <div className="mt-10">
        <h2 className="text-lg font-semibold text-ink mb-3">Nedavno učitano</h2>
        {error && (
          <p className="text-sm bg-status-fail/10 border border-status-fail/30 text-status-fail rounded-md px-3 py-2 mb-3">
            {error}
          </p>
        )}
        {loading ? (
          <p className="text-sm text-muted">Učitavam…</p>
        ) : (
          <DocumentList documents={documents} onDeleted={onDeleted} />
        )}
      </div>
    </div>
  );
}
