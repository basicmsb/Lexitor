"use client";

import Link from "next/link";
import { useState } from "react";

import { api } from "@/lib/api";
import type { DocumentPublic } from "@/lib/types";

interface Props {
  documents: DocumentPublic[];
  emptyHint?: string;
  onDeleted?: (id: string) => void;
}

const TYPE_LABEL: Record<string, string> = {
  troskovnik: "Troškovnik",
  don: "DON",
  zalba: "Žalba",
  other: "Ostalo",
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("hr-HR", { dateStyle: "medium", timeStyle: "short" });
}

export function DocumentList({
  documents,
  emptyHint = "Još nema učitanih dokumenata.",
  onDeleted,
}: Props) {
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (documents.length === 0) {
    return <p className="text-sm text-muted italic">{emptyHint}</p>;
  }

  async function handleDelete(doc: DocumentPublic) {
    if (busyId) return;
    const ok = window.confirm(
      `Obrisati „${doc.filename}”? Sve analize tog dokumenta bit će uklonjene.`,
    );
    if (!ok) return;
    setError(null);
    setBusyId(doc.id);
    try {
      await api.deleteDocument(doc.id);
      onDeleted?.(doc.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Brisanje nije uspjelo.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-2">
      {error && (
        <p className="text-sm bg-[#A8392B]/10 border border-[#A8392B]/30 text-[#7C2A21] rounded-md px-3 py-2">
          {error}
        </p>
      )}
      <ul className="divide-y divide-brand-border rounded-lg border border-brand-border bg-white">
        {documents.map((doc) => {
          const href = `/analiza/${doc.document_type === "don" ? "don" : "troskovnik"}/${doc.id}`;
          const isBusy = busyId === doc.id;
          return (
            <li
              key={doc.id}
              className="flex items-center gap-4 pr-2 hover:bg-surface-2 transition"
            >
              <Link href={href} className="flex-1 min-w-0 px-4 py-3">
                <p className="text-sm font-medium text-ink truncate">{doc.filename}</p>
                <p className="text-xs text-muted mt-0.5">
                  {TYPE_LABEL[doc.document_type] ?? doc.document_type} ·{" "}
                  {formatBytes(doc.size_bytes)} · {formatDate(doc.created_at)}
                </p>
              </Link>
              <Link
                href={href}
                className="hidden sm:inline text-xs text-signal shrink-0 px-2"
              >
                Otvori →
              </Link>
              <button
                type="button"
                onClick={() => void handleDelete(doc)}
                disabled={isBusy}
                aria-label={`Obriši ${doc.filename}`}
                title="Obriši dokument"
                className="shrink-0 rounded-md p-2 text-muted hover:text-[#A8392B] hover:bg-[#A8392B]/10 transition disabled:opacity-50"
              >
                {isBusy ? (
                  <span className="text-xs">…</span>
                ) : (
                  <svg
                    aria-hidden
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M3 6h18" />
                    <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                    <line x1="10" y1="11" x2="10" y2="17" />
                    <line x1="14" y1="11" x2="14" y2="17" />
                  </svg>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
