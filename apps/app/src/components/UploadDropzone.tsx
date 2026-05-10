"use client";

import { useCallback, useRef, useState, type ChangeEvent, type DragEvent } from "react";

import { api } from "@/lib/api";
import type { DocumentPublic, DocumentType, TroskovnikType } from "@/lib/types";

// Različiti accept tipovi po vrsti dokumenta. Troškovnik: XLSX struktura
// + .arhigonfile XML BoQ. DON: EOJN sad servira Markdown (.md) za glavne
// sekcije + .docx za priloge — najpoželjniji format za parsing. Žalba:
// PDF i Word.
const ACCEPT_BY_TYPE: Record<string, string> = {
  troskovnik: ".pdf,.xlsx,.arhigonfile",
  don: ".md,.pdf,.docx,.doc",
  zalba: ".pdf,.docx,.doc",
  other: ".md,.pdf,.xlsx,.docx,.doc,.arhigonfile",
};

interface Props {
  documentType: DocumentType;
  onUploaded: (doc: DocumentPublic) => void;
}

export function UploadDropzone({ documentType, onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [troskovnikType, setTroskovnikType] =
    useState<TroskovnikType>("nepoznato");
  const showTypeSelector = documentType === "troskovnik";
  const accept = ACCEPT_BY_TYPE[documentType] || ACCEPT_BY_TYPE.other;

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0) return;
      const file = files[0];
      setError(null);
      setUploading(true);
      try {
        const doc = await api.uploadDocument(
          file,
          documentType,
          troskovnikType,
        );
        onUploaded(doc);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload nije uspio.");
      } finally {
        setUploading(false);
        if (inputRef.current) inputRef.current.value = "";
      }
    },
    [documentType, onUploaded, troskovnikType],
  );

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    if (uploading) return;
    void handleFiles(e.dataTransfer.files);
  };

  const onDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (!dragging) setDragging(true);
  };

  const onDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
  };

  const onChange = (e: ChangeEvent<HTMLInputElement>) => {
    void handleFiles(e.target.files);
  };

  return (
    <div className="space-y-3">
      {showTypeSelector && (
        <div className="rounded-lg border border-brand-border bg-white p-4">
          <div className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-2">
            Tip troškovnika
          </div>
          <div
            className="grid gap-2 sm:grid-cols-3"
            role="radiogroup"
            aria-label="Tip troškovnika"
          >
            {(
              [
                {
                  value: "ponudbeni" as const,
                  label: "Ponudbeni",
                  hint: "Jed. cijena prazna — ponuditelj popunjava",
                },
                {
                  value: "procjena" as const,
                  label: "Procjena",
                  hint: "Jed. cijena popunjena — projektantska procjena",
                },
                {
                  value: "nepoznato" as const,
                  label: "Nepoznato",
                  hint: "Ne primjenjuju se posebna pravila",
                },
              ]
            ).map((opt) => (
              <button
                key={opt.value}
                type="button"
                role="radio"
                aria-checked={troskovnikType === opt.value}
                onClick={() => setTroskovnikType(opt.value)}
                disabled={uploading}
                className={`text-left rounded-md border px-3 py-2 transition ${
                  troskovnikType === opt.value
                    ? "border-ink bg-ink/5"
                    : "border-brand-border hover:border-navy"
                } ${uploading ? "opacity-60 pointer-events-none" : ""}`}
              >
                <div className="text-sm font-medium text-ink">{opt.label}</div>
                <div className="text-[11px] text-muted leading-snug">{opt.hint}</div>
              </button>
            ))}
          </div>
        </div>
      )}
      <div
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onClick={() => !uploading && inputRef.current?.click()}
        className={`rounded-lg border-2 border-dashed p-12 text-center cursor-pointer transition ${
          dragging
            ? "border-signal bg-signal/5"
            : "border-brand-border bg-white hover:border-navy"
        } ${uploading ? "opacity-60 pointer-events-none" : ""}`}
      >
        <p className="font-medium text-ink">
          {uploading ? "Učitavam…" : "Povuci datoteku ovdje ili klikni za odabir"}
        </p>
        <p className="mt-2 text-sm text-muted">
          Podržani formati:{" "}
          {accept
            .split(",")
            .map((ext, idx) => (
              <span key={ext}>
                {idx > 0 && ", "}
                <code className="font-mono">{ext}</code>
              </span>
            ))}{" "}
          · maks. 50 MB
        </p>
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          className="hidden"
          onChange={onChange}
          disabled={uploading}
        />
      </div>
      {error && (
        <p className="text-sm bg-[#A8392B]/10 border border-[#A8392B]/30 text-[#7C2A21] rounded-md px-3 py-2">
          {error}
        </p>
      )}
    </div>
  );
}
