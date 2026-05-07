"use client";

import Link from "next/link";

import type { DocumentPublic } from "@/lib/types";

interface Props {
  documents: DocumentPublic[];
  emptyHint?: string;
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

export function DocumentList({ documents, emptyHint = "Još nema učitanih dokumenata." }: Props) {
  if (documents.length === 0) {
    return <p className="text-sm text-muted italic">{emptyHint}</p>;
  }

  return (
    <ul className="divide-y divide-brand-border rounded-lg border border-brand-border bg-white">
      {documents.map((doc) => (
        <li key={doc.id}>
          <Link
            href={`/analiza/${doc.document_type === "don" ? "don" : "troskovnik"}/${doc.id}`}
            className="flex items-center justify-between gap-4 px-4 py-3 hover:bg-surface-2 transition"
          >
            <div className="min-w-0">
              <p className="text-sm font-medium text-ink truncate">{doc.filename}</p>
              <p className="text-xs text-muted mt-0.5">
                {TYPE_LABEL[doc.document_type] ?? doc.document_type} ·{" "}
                {formatBytes(doc.size_bytes)} · {formatDate(doc.created_at)}
              </p>
            </div>
            <span className="text-xs text-signal shrink-0">Otvori →</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
