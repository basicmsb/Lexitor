"use client";

import { useCallback, useRef, useState, type ChangeEvent, type DragEvent } from "react";

import { api } from "@/lib/api";
import type { DocumentPublic, DocumentType } from "@/lib/types";

const ACCEPT = ".pdf,.xlsx,.arhigonfile";

interface Props {
  documentType: DocumentType;
  onUploaded: (doc: DocumentPublic) => void;
}

export function UploadDropzone({ documentType, onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0) return;
      const file = files[0];
      setError(null);
      setUploading(true);
      try {
        const doc = await api.uploadDocument(file, documentType);
        onUploaded(doc);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload nije uspio.");
      } finally {
        setUploading(false);
        if (inputRef.current) inputRef.current.value = "";
      }
    },
    [documentType, onUploaded],
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
          Podržani formati: <code className="font-mono">.pdf</code>,{" "}
          <code className="font-mono">.xlsx</code>,{" "}
          <code className="font-mono">.arhigonfile</code> · maks. 50 MB
        </p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
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
