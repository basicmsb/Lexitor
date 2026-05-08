"use client";

import { useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";
import type { ProjectInfo } from "@/lib/types";

export default function PostavkePage() {
  const [project, setProject] = useState<ProjectInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [logoCacheBuster, setLogoCacheBuster] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [exportBusy, setExportBusy] = useState(false);
  const [exportErr, setExportErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const p = await api.getMyProject();
        if (!cancelled) setProject(p);
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : "Učitavanje projekta nije uspjelo.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const onUpload = async (file: File) => {
    setBusy(true);
    setErr(null);
    try {
      const updated = await api.uploadProjectLogo(file);
      setProject(updated);
      setLogoCacheBuster((n) => n + 1);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Upload nije uspio.");
    } finally {
      setBusy(false);
    }
  };

  const onExportLabels = async () => {
    setExportBusy(true);
    setExportErr(null);
    try {
      const blob = await api.exportLabels();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const stamp = new Date().toISOString().slice(0, 10);
      a.download = `lexitor-labels-${stamp}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setExportErr(e instanceof Error ? e.message : "Export nije uspio.");
    } finally {
      setExportBusy(false);
    }
  };

  const onDelete = async () => {
    if (!confirm("Obrisati logo tvrtke?")) return;
    setBusy(true);
    setErr(null);
    try {
      const updated = await api.deleteProjectLogo();
      setProject(updated);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Brisanje nije uspjelo.");
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <p className="text-sm text-muted">Učitavam…</p>;
  if (err && !project)
    return (
      <div className="rounded-lg border border-[#A8392B]/30 bg-[#A8392B]/10 p-4 text-sm text-[#7C2A21]">
        {err}
      </div>
    );

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <div>
        <h1 className="font-display text-2xl text-ink mb-1">Postavke</h1>
        <p className="text-sm text-muted">Tvrtka i logo za PDF izvještaje.</p>
      </div>

      <section className="rounded-lg border border-brand-border bg-white p-6">
        <h2 className="font-display text-lg text-ink mb-1">Tvrtka</h2>
        <p className="text-sm text-muted mb-4">
          {project?.name ?? "—"}
        </p>

        <h3 className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-2">
          Logo tvrtke
        </h3>
        <p className="text-sm text-navy mb-3">
          Pojavljuje se u zaglavlju PDF izvještaja, pored Lexitor wordmarka.
          PNG, JPG, GIF ili WEBP, do 2 MB.
        </p>

        <div className="flex items-center gap-4 flex-wrap">
          <div className="w-40 h-20 rounded border border-brand-border bg-surface-2 flex items-center justify-center overflow-hidden">
            {project?.has_logo ? (
              // Local file path is exposed only as a server reference; we
              // can't load it directly from the browser. Show a confirmed
              // placeholder so the user sees status.
              <span
                className="text-xs text-muted"
                key={logoCacheBuster}
                aria-label="Logo postavljen"
              >
                ✓ Logo postavljen
              </span>
            ) : (
              <span className="text-xs text-muted italic">bez logotipa</span>
            )}
          </div>
          <div className="flex flex-col gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/gif,image/webp"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void onUpload(f);
                e.target.value = "";
              }}
            />
            <button
              type="button"
              disabled={busy}
              onClick={() => fileInputRef.current?.click()}
              className="rounded-md border border-brand-border bg-white px-3 py-1.5 text-sm text-navy hover:border-ink transition disabled:opacity-50"
            >
              {project?.has_logo ? "Zamijeni logo" : "Postavi logo"}
            </button>
            {project?.has_logo && (
              <button
                type="button"
                disabled={busy}
                onClick={onDelete}
                className="rounded-md border border-brand-border px-3 py-1.5 text-sm text-[#A8392B] hover:border-[#A8392B] transition disabled:opacity-50"
              >
                Obriši logo
              </button>
            )}
          </div>
        </div>

        {err && (
          <p className="mt-3 text-sm text-[#A8392B]" aria-live="polite">
            {err}
          </p>
        )}
      </section>

      <section className="rounded-lg border border-brand-border bg-white p-6">
        <h2 className="font-display text-lg text-ink mb-1">Označeni primjeri</h2>
        <p className="text-sm text-muted mb-4">
          Izvoz svih stavki na kojima si označio nalaze (✓ Točno / ✗ Pogrešno)
          ili dodao ručne nalaze. Materijal služi kao few-shot primjeri za
          treniranje LLM analyzera.
        </p>

        <button
          type="button"
          disabled={exportBusy}
          onClick={onExportLabels}
          className="rounded-md border border-brand-border bg-white px-3 py-1.5 text-sm text-navy hover:border-ink transition disabled:opacity-50"
        >
          {exportBusy ? "Pripremam…" : "Preuzmi JSON"}
        </button>

        {exportErr && (
          <p className="mt-3 text-sm text-[#A8392B]" aria-live="polite">
            {exportErr}
          </p>
        )}
      </section>
    </div>
  );
}
