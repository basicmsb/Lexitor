"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { DocumentList } from "@/components/DocumentList";
import { DocumentSetUpload } from "@/components/DocumentSetUpload";
import { api } from "@/lib/api";
import type {
  DocumentPublic,
  DocumentSetPublic,
} from "@/lib/types";

export default function AnalizaDonPage() {
  const [sets, setSets] = useState<DocumentSetPublic[]>([]);
  const [loose, setLoose] = useState<DocumentPublic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSets, setExpandedSets] = useState<Set<string>>(new Set());

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [setList, docList] = await Promise.all([
        api.listDocumentSets(),
        api.listDocuments(),
      ]);
      const donSets = setList.items.filter((s) => s.document_type === "don");
      setSets(donSets);
      // Loose = DON dokumenti BEZ set_id (pojedinačni upload, legacy)
      setLoose(
        docList.items.filter(
          (d) => d.document_type === "don" && !d.set_id,
        ),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Greška pri dohvatu.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const onCreated = (set: DocumentSetPublic) => {
    setSets((prev) => [set, ...prev]);
    setExpandedSets((prev) => new Set(prev).add(set.id));
  };

  const onLooseDeleted = (id: string) => {
    setLoose((prev) => prev.filter((d) => d.id !== id));
  };

  const toggleSet = (id: string) => {
    setExpandedSets((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const onDeleteSet = async (id: string) => {
    if (!confirm("Obrisati cijelu nabavu i sve fajlove u njoj?")) return;
    try {
      await api.deleteDocumentSet(id);
      setSets((prev) => prev.filter((s) => s.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Brisanje nije uspjelo.");
    }
  };

  return (
    <div className="max-w-5xl">
      <div className="mb-8">
        <h1 className="font-display text-3xl text-ink mb-2">Analiza DON-a</h1>
        <p className="text-muted">
          Učitaj sve fajlove jedne nabave odjednom (Upute za ponuditelje,
          Kriteriji, Općg podaci, prilozi) — Lexitor analizira protiv ZJN-a,
          pravilnika i DKOM presedana.
        </p>
      </div>

      <DocumentSetUpload onCreated={onCreated} />

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
          <div className="space-y-3">
            {sets.map((s) => {
              const expanded = expandedSets.has(s.id);
              return (
                <article
                  key={s.id}
                  className="rounded-lg border border-brand-border bg-surface-2"
                >
                  <header className="flex items-center gap-3 px-4 py-3">
                    <button
                      type="button"
                      onClick={() => toggleSet(s.id)}
                      className="text-muted hover:text-ink text-sm shrink-0"
                      aria-expanded={expanded}
                      title={expanded ? "Sakrij fajlove" : "Prikaži fajlove"}
                    >
                      {expanded ? "▾" : "▸"}
                    </button>
                    <Link
                      href={`/analiza/don/sets/${s.id}`}
                      className="flex-1 min-w-0"
                    >
                      <div className="font-display text-base text-ink truncate">
                        {s.name}
                      </div>
                      <div className="text-[11px] text-muted">
                        {s.documents.length}{" "}
                        {s.documents.length === 1 ? "fajl" : "fajlova"} ·{" "}
                        {new Date(s.created_at).toLocaleDateString("hr-HR")}
                      </div>
                    </Link>
                    <button
                      type="button"
                      onClick={() => void onDeleteSet(s.id)}
                      className="text-[11px] text-muted hover:text-status-fail transition shrink-0 px-2"
                      title="Obriši nabavu"
                    >
                      ✗
                    </button>
                  </header>
                  {expanded && s.documents.length > 0 && (
                    <ul className="border-t border-brand-border divide-y divide-brand-border">
                      {s.documents.map((doc) => (
                        <li key={doc.id} className="px-4 py-2.5">
                          <Link
                            href={`/analiza/don/${doc.id}`}
                            className="flex items-center justify-between gap-3 text-sm text-navy hover:text-ink"
                          >
                            <span className="truncate">{doc.filename}</span>
                            <span className="text-[11px] text-muted shrink-0">
                              {(doc.size_bytes / 1024).toFixed(1)} KB
                            </span>
                          </Link>
                        </li>
                      ))}
                    </ul>
                  )}
                </article>
              );
            })}
            {loose.length > 0 && (
              <div>
                <h3 className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-2 mt-6">
                  Pojedinačni fajlovi (bez nabave)
                </h3>
                <DocumentList documents={loose} onDeleted={onLooseDeleted} />
              </div>
            )}
            {sets.length === 0 && loose.length === 0 && (
              <p className="text-sm text-muted italic">
                Nemaš učitanih DON dokumenata. Koristi gornji obrazac za prvi
                upload.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
