"use client";

import { useMemo, useState } from "react";

import { StatusBadge, StatusDot } from "@/components/StatusBadge";
import type {
  AnalysisItemPublic,
  AnalysisStatus,
  AnalysisSummary,
  CitationPublic,
} from "@/lib/types";

const SOURCE_LABEL: Record<string, string> = {
  zjn: "ZJN",
  dkom: "DKOM",
  vus: "VUS",
  eu: "Sud EU",
  other: "Ostalo",
};

interface Props {
  status: AnalysisStatus;
  progress: number;
  items: AnalysisItemPublic[];
  summary: AnalysisSummary | null;
  error: string | null;
}

export function AnalysisResults({ status, progress, items, summary, error }: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selected = useMemo(
    () => items.find((it) => it.id === selectedId) ?? items[0] ?? null,
    [items, selectedId],
  );

  return (
    <div className="flex flex-col gap-4 h-[calc(100vh-200px)]">
      <Header status={status} progress={progress} summary={summary} error={error} count={items.length} />

      <div className="flex flex-1 gap-4 min-h-0">
        <aside className="w-72 shrink-0 rounded-lg border border-brand-border bg-white overflow-y-auto">
          {items.length === 0 ? (
            <p className="p-4 text-sm text-muted italic">
              {status === "running" ? "Čekam prve rezultate…" : "Nema stavki."}
            </p>
          ) : (
            <ul className="divide-y divide-brand-border">
              {items.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(item.id)}
                    className={`w-full text-left px-3 py-2 flex items-center gap-2 text-sm hover:bg-surface-2 transition ${
                      selected?.id === item.id ? "bg-surface-2 text-ink font-medium" : "text-navy"
                    }`}
                  >
                    <StatusDot status={item.status} />
                    <span className="truncate" title={item.text}>
                      {item.label ? `${item.label}: ${item.text}` : item.text}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>

        <section className="flex-1 rounded-lg border border-brand-border bg-white p-6 overflow-y-auto">
          {selected ? <ItemDetail item={selected} /> : <NoSelection />}
        </section>
      </div>
    </div>
  );
}

function Header({
  status,
  progress,
  summary,
  error,
  count,
}: {
  status: AnalysisStatus;
  progress: number;
  summary: AnalysisSummary | null;
  error: string | null;
  count: number;
}) {
  if (status === "error") {
    return (
      <div className="rounded-lg border border-[#A8392B]/30 bg-[#A8392B]/10 p-4 text-sm text-[#7C2A21]">
        Greška u analizi: {error ?? "nepoznat razlog."}
      </div>
    );
  }

  if (status === "complete" && summary) {
    return (
      <div className="rounded-lg border border-brand-border bg-white px-4 py-3 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
        <span className="font-medium text-ink">Analiza završena</span>
        <Pill color="#3F7D45" label={`${summary.ok} usklađenih`} />
        <Pill color="#A87F2E" label={`${summary.warn} upozorenja`} />
        <Pill color="#A8392B" label={`${summary.fail} kršenja`} />
        <span className="text-muted ml-auto">{summary.total} stavki ukupno</span>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-brand-border bg-white px-4 py-3">
      <div className="flex items-center justify-between text-sm mb-2">
        <span className="font-medium text-ink">
          {status === "running" ? "Analiza u tijeku…" : "Priprema analize…"}
        </span>
        <span className="text-muted">
          {count} stavki obrađeno · {progress}%
        </span>
      </div>
      <div className="w-full h-1.5 bg-surface-2 rounded-full overflow-hidden">
        <div className="h-full bg-ink transition-all" style={{ width: `${progress}%` }} />
      </div>
    </div>
  );
}

function Pill({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
      <span className="text-navy">{label}</span>
    </span>
  );
}

function NoSelection() {
  return <p className="text-sm text-muted">Odaberi stavku iz lijevog stabla.</p>;
}

function ItemDetail({ item }: { item: AnalysisItemPublic }) {
  return (
    <div>
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          {item.label && (
            <p className="text-xs uppercase tracking-wide text-muted mb-1">{item.label}</p>
          )}
          <h2 className="font-serif text-xl text-ink leading-snug">{item.text}</h2>
        </div>
        <StatusBadge status={item.status} />
      </div>

      {item.explanation && (
        <section className="mb-5">
          <h3 className="text-sm font-semibold text-ink mb-1">Objašnjenje</h3>
          <p className="text-sm text-navy leading-relaxed">{item.explanation}</p>
        </section>
      )}

      {item.suggestion && (
        <section className="mb-5">
          <h3 className="text-sm font-semibold text-ink mb-1">Prijedlog ispravka</h3>
          <p className="text-sm text-navy leading-relaxed">{item.suggestion}</p>
        </section>
      )}

      {item.citations.length > 0 && (
        <section className="mb-5">
          <h3 className="text-sm font-semibold text-ink mb-2">Citirani izvori</h3>
          <ul className="space-y-3">
            {item.citations.map((c) => (
              <CitationCard key={c.id} citation={c} />
            ))}
          </ul>
        </section>
      )}

      <div className="mt-6 pt-4 border-t border-brand-border flex flex-wrap gap-2">
        <button
          type="button"
          disabled
          className="rounded-md border border-brand-border px-3 py-1.5 text-sm text-navy disabled:opacity-50"
          title="Implementacija u Sprintu 2"
        >
          Ispravi
        </button>
        <button
          type="button"
          disabled
          className="rounded-md border border-brand-border px-3 py-1.5 text-sm text-navy disabled:opacity-50"
          title="Implementacija u Sprintu 2"
        >
          Prihvati rizik
        </button>
        <button
          type="button"
          disabled
          className="rounded-md border border-brand-border px-3 py-1.5 text-sm text-navy disabled:opacity-50"
          title="Implementacija u Sprintu 2"
        >
          Označi kao false positive
        </button>
      </div>
    </div>
  );
}

function CitationCard({ citation }: { citation: CitationPublic }) {
  return (
    <li className="rounded-md border border-brand-border bg-surface-2 p-3">
      <p className="text-xs font-mono uppercase tracking-wider text-navy mb-1">
        {SOURCE_LABEL[citation.source] ?? citation.source.toUpperCase()} · {citation.reference}
      </p>
      <p className="text-sm text-ink leading-relaxed">{citation.snippet}</p>
      {citation.url && (
        <a
          href={citation.url}
          target="_blank"
          rel="noreferrer"
          className="mt-2 inline-block text-xs text-signal hover:underline"
        >
          Otvori izvor →
        </a>
      )}
    </li>
  );
}
