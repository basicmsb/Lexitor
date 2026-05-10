"use client";

import { useCallback, useRef, useState, type ChangeEvent, type DragEvent } from "react";

import { api } from "@/lib/api";
import type { DocumentSetPublic } from "@/lib/types";

const ACCEPT = ".md,.txt,.pdf,.docx,.doc";

interface Props {
  onCreated: (set: DocumentSetPublic) => void;
}

/** Multi-file upload za DON: korisnik upiše ime nabave (npr.
 *  "JN-25/2026 Krupa i Crnopac"), pa drag-drop sve fajlove odjednom.
 *  Kreira DocumentSet + N Documents s istim set_id. */
export function DocumentSetUpload({ onCreated }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [name, setName] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<{ current: number; total: number }>({
    current: 0,
    total: 0,
  });
  const [error, setError] = useState<string | null>(null);

  const addFiles = useCallback((list: FileList | null) => {
    if (!list || list.length === 0) return;
    const arr = Array.from(list);
    setFiles((prev) => [...prev, ...arr]);
    setError(null);
  }, []);

  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const onSubmit = async () => {
    if (!name.trim()) {
      setError("Unesi naziv nabave (npr. evidencijski broj ili predmet).");
      return;
    }
    if (files.length === 0) {
      setError("Dodaj barem jedan fajl.");
      return;
    }
    setUploading(true);
    setError(null);
    try {
      const set = await api.createDocumentSet(name.trim(), "don");
      setProgress({ current: 0, total: files.length });
      for (let i = 0; i < files.length; i++) {
        await api.uploadDocument(files[i], "don", "nepoznato", set.id);
        setProgress({ current: i + 1, total: files.length });
      }
      const refreshed = await api.getDocumentSet(set.id);
      onCreated(refreshed);
      // Reset form
      setName("");
      setFiles([]);
      setProgress({ current: 0, total: 0 });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload nije uspio.");
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    if (uploading) return;
    addFiles(e.dataTransfer.files);
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
    addFiles(e.target.files);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="space-y-3">
      <div className="rounded-lg border border-brand-border bg-surface-2 p-5 space-y-4">
        <div>
          <label className="block text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-1">
            Naziv nabave
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={uploading}
            placeholder="npr. JN-25/2026 — Nabava urbane opreme Krupa i Crnopac"
            className="w-full rounded-md border border-brand-border bg-surface-2 px-3 py-2 text-sm text-navy placeholder:text-muted/70 focus:outline-none focus:border-ink"
          />
          <p className="text-[11px] text-muted mt-1">
            Slobodan tekst — može sadržavati evidencijski broj (formati variraju
            po naručitelju), predmet nabave, ili kombinaciju.
          </p>
        </div>

        <div
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onClick={() => !uploading && inputRef.current?.click()}
          className={`rounded-lg border-2 border-dashed p-8 text-center cursor-pointer transition ${
            dragging
              ? "border-signal bg-signal/5"
              : "border-brand-border bg-surface-2/40 hover:border-navy"
          } ${uploading ? "opacity-60 pointer-events-none" : ""}`}
        >
          <p className="font-medium text-ink">
            {uploading
              ? `Učitavam ${progress.current}/${progress.total}…`
              : "Povuci fajlove ovdje ili klikni za odabir (više njih odjednom)"}
          </p>
          <p className="mt-2 text-sm text-muted">
            Podržani formati:{" "}
            {ACCEPT.split(",").map((ext, idx) => (
              <span key={ext}>
                {idx > 0 && ", "}
                <code className="font-mono">{ext}</code>
              </span>
            ))}
          </p>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            multiple
            className="hidden"
            onChange={onChange}
            disabled={uploading}
          />
        </div>

        {files.length > 0 && (
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-2">
              Spremno za upload ({files.length})
            </div>
            <ul className="space-y-1.5">
              {files.map((f, idx) => (
                <li
                  key={`${f.name}-${idx}`}
                  className="flex items-center justify-between gap-2 px-3 py-2 rounded border border-brand-border bg-surface-2/40 text-sm"
                >
                  <span className="text-navy truncate">{f.name}</span>
                  <span className="text-[11px] text-muted shrink-0">
                    {(f.size / 1024).toFixed(1)} KB
                  </span>
                  <button
                    type="button"
                    onClick={() => removeFile(idx)}
                    disabled={uploading}
                    className="text-[11px] text-muted hover:text-status-fail transition"
                  >
                    ✗
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onSubmit}
            disabled={uploading || files.length === 0 || !name.trim()}
            className="rounded-md bg-ink px-4 py-2 text-sm text-surface hover:bg-navy transition disabled:opacity-50"
          >
            {uploading ? "Učitavam…" : `Učitaj nabavu (${files.length})`}
          </button>
          {error && (
            <p className="text-sm text-status-fail">{error}</p>
          )}
        </div>
      </div>
    </div>
  );
}
