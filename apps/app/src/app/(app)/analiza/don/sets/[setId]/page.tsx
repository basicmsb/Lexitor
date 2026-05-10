"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { DonAnalysisView } from "@/components/don/DonAnalysisView";
import { api } from "@/lib/api";
import type { DocumentSetPublic } from "@/lib/types";

export default function DonSetDetailPage() {
  const params = useParams<{ setId: string }>();
  const router = useRouter();
  const setId = params?.setId;

  const [set, setSet] = useState<DocumentSetPublic | null>(null);
  const [activeDocId, setActiveDocId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!setId) return;
    setLoading(true);
    try {
      const s = await api.getDocumentSet(setId);
      setSet(s);
      if (s.documents.length > 0 && !activeDocId) {
        setActiveDocId(s.documents[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Greška pri dohvatu.");
    } finally {
      setLoading(false);
    }
  }, [setId, activeDocId]);

  useEffect(() => {
    void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setId]);

  if (!setId) return null;
  if (loading) return <p className="text-sm text-muted">Učitavam…</p>;
  if (error)
    return (
      <p className="text-sm bg-status-fail/10 border border-status-fail/30 text-status-fail rounded-md px-3 py-2">
        {error}
      </p>
    );
  if (!set) return null;

  return (
    <div className="flex flex-col gap-3 h-[calc(100vh-100px)] min-h-0">
      <div>
        <button
          type="button"
          onClick={() => router.push("/analiza/don")}
          className="text-sm text-muted hover:text-ink mb-1 transition"
        >
          ← Natrag na popis
        </button>
        <h1 className="font-display text-2xl text-ink">{set.name}</h1>
        <p className="text-[11px] text-muted">
          {set.documents.length} {set.documents.length === 1 ? "fajl" : "fajlova"} ·
          učitano {new Date(set.created_at).toLocaleDateString("hr-HR")}
        </p>
      </div>

      {/* Tabs po fajlu */}
      <div className="border-b border-brand-border">
        <ul
          role="tablist"
          className="flex gap-1 overflow-x-auto pb-px scrollbar-thin"
        >
          {set.documents.map((doc) => {
            const isActive = doc.id === activeDocId;
            return (
              <li key={doc.id}>
                <button
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  onClick={() => setActiveDocId(doc.id)}
                  className={`whitespace-nowrap px-4 py-2 text-sm transition border-b-2 -mb-px ${
                    isActive
                      ? "border-ink text-ink font-medium"
                      : "border-transparent text-muted hover:text-navy"
                  }`}
                >
                  {doc.filename}
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      {/* Active document analiza */}
      {activeDocId ? (
        <DonAnalysisView
          key={activeDocId}
          documentId={activeDocId}
          showHeader={false}
          containerHeightClass="flex-1"
        />
      ) : (
        <p className="text-sm text-muted italic">
          Nema fajlova u ovoj nabavi.
        </p>
      )}
    </div>
  );
}
