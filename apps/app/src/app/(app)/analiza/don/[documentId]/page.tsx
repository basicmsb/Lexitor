"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useAnalysisStream } from "@/hooks/useAnalysisStream";
import { api } from "@/lib/api";
import type { AnalysisItemPublic, DocumentPublic } from "@/lib/types";

/**
 * DON analiza — adaptira AnalysisItemPublic (isti shape kao troškovnik)
 * na DON-specific 3-kolone layout: sidebar TOC (chapter hijerarhija
 * kroz metadata.chapter_path) | centar blokovi | desno LA findings.
 *
 * Items dolaze iz backend analyzer-a (markdown_parser → analyzer →
 * AnalysisItem rows). Section_header items grade TOC, ostali (paragraph,
 * requirement, criterion, deadline, list, table) su blokovi.
 */

const STATUS_COLORS: Record<string, string> = {
  ok: "#3F7D45",
  warn: "#B8893E",
  fail: "#A8392B",
  uncertain: "#3B82C4",
  neutral: "#9B9892",
  accepted: "#3B82C4",
};
const STATUS_LABELS: Record<string, string> = {
  ok: "USKLAĐENO",
  warn: "UPOZORENJE",
  fail: "KRŠENJE",
  uncertain: "PROVJERITI",
  neutral: "INFO",
  accepted: "PRIHVAĆENO",
};

const KIND_LABELS: Record<string, string> = {
  section_header: "Naslov",
  paragraph: "Paragraf",
  requirement: "Uvjet sposobnosti",
  criterion: "Kriterij",
  deadline: "Rok",
  list: "Lista",
  table: "Tablica",
};

type ChapterPath = Array<{ depth: number; title: string }>;

interface ChapterNode {
  depth: number;
  title: string;
  rb: string | null;
  startIndex: number;       // index u items array
  blockCount: number;
  issueCount: number;
}

function getChapterPath(item: AnalysisItemPublic): ChapterPath {
  const meta = (item.metadata_json ?? {}) as Record<string, unknown>;
  const path = meta.chapter_path;
  return Array.isArray(path) ? (path as ChapterPath) : [];
}

function getKind(item: AnalysisItemPublic): string {
  const meta = (item.metadata_json ?? {}) as Record<string, unknown>;
  return (meta.kind as string) || "paragraph";
}

function getRb(item: AnalysisItemPublic): string | null {
  const meta = (item.metadata_json ?? {}) as Record<string, unknown>;
  return (meta.rb as string | null) ?? null;
}

function getDepth(item: AnalysisItemPublic): number {
  const meta = (item.metadata_json ?? {}) as Record<string, unknown>;
  return (meta.depth as number) || 1;
}

function chapterKey(path: ChapterPath): string {
  return path.map((p) => `${p.depth}:${p.title}`).join("/") || "ROOT";
}

export default function DonDetailPage() {
  const params = useParams<{ documentId: string }>();
  const router = useRouter();
  const documentId = params?.documentId;

  const [document, setDocument] = useState<DocumentPublic | null>(null);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [bootstrapError, setBootstrapError] = useState<string | null>(null);
  const stream = useAnalysisStream(analysisId);
  const [historicalItems, setHistoricalItems] = useState<AnalysisItemPublic[]>([]);
  const [activeChapter, setActiveChapter] = useState<string | null>(null);
  const [activeBlockId, setActiveBlockId] = useState<string | null>(null);

  const bootstrap = useCallback(async () => {
    if (!documentId) return;
    setBootstrapping(true);
    setBootstrapError(null);
    try {
      const doc = await api.getDocument(documentId);
      setDocument(doc);
      const existing = await api.listDocumentAnalyses(documentId);
      if (existing.length === 0) {
        const started = await api.startAnalysis(documentId);
        setAnalysisId(started.analysis_id);
        setHistoricalItems([]);
      } else {
        const latest = existing[0];
        setAnalysisId(latest.id);
        if (latest.status === "complete" || latest.status === "error") {
          const detail = await api.getAnalysis(latest.id);
          setHistoricalItems(detail.items);
        }
      }
    } catch (err) {
      setBootstrapError(err instanceof Error ? err.message : "Greška.");
    } finally {
      setBootstrapping(false);
    }
  }, [documentId]);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  const items = stream.items.length > 0 ? stream.items : historicalItems;

  // Group blokovi po chapter_path
  const { chapters, blocksByChapter } = useMemo(() => {
    const chMap = new Map<string, ChapterNode>();
    const bMap = new Map<string, AnalysisItemPublic[]>();
    items.forEach((it, idx) => {
      const path = getChapterPath(it);
      const key = chapterKey(path);
      if (!chMap.has(key)) {
        const top = path[0];
        chMap.set(key, {
          depth: top?.depth ?? 0,
          title: top?.title ?? "(uvod)",
          rb: getRb(it),
          startIndex: idx,
          blockCount: 0,
          issueCount: 0,
        });
        bMap.set(key, []);
      }
      const ch = chMap.get(key)!;
      const arr = bMap.get(key)!;
      const kind = getKind(it);
      if (kind !== "section_header") {
        arr.push(it);
        ch.blockCount += 1;
        if (it.status === "warn" || it.status === "fail") {
          ch.issueCount += 1;
        }
      }
    });
    // Stable order: po startIndex
    const sorted = Array.from(chMap.entries())
      .sort((a, b) => a[1].startIndex - b[1].startIndex)
      .map(([key, ch]) => ({ key, ...ch }));
    return { chapters: sorted, blocksByChapter: bMap };
  }, [items]);

  // Prvi chapter automatski aktiviran
  useEffect(() => {
    if (chapters.length === 0) return;
    if (!activeChapter || !chapters.find((c) => c.key === activeChapter)) {
      setActiveChapter(chapters[0].key);
    }
  }, [chapters, activeChapter]);

  const visibleBlocks = useMemo(() => {
    if (!activeChapter) return [];
    return blocksByChapter.get(activeChapter) ?? [];
  }, [activeChapter, blocksByChapter]);

  // Summary
  const summary = useMemo(() => {
    let ok = 0, warn = 0, fail = 0, neutral = 0;
    for (const it of items) {
      if (getKind(it) === "section_header") continue;
      if (it.status === "ok") ok++;
      else if (it.status === "warn") warn++;
      else if (it.status === "fail") fail++;
      else neutral++;
    }
    return { ok, warn, fail, neutral };
  }, [items]);

  const restart = async () => {
    if (!documentId) return;
    setHistoricalItems([]);
    setAnalysisId(null);
    try {
      const started = await api.startAnalysis(documentId);
      setAnalysisId(started.analysis_id);
    } catch (err) {
      setBootstrapError(err instanceof Error ? err.message : "Greška.");
    }
  };

  if (!documentId) return null;
  if (bootstrapping) return <p className="text-sm text-muted">Pripremam analizu…</p>;
  if (bootstrapError)
    return (
      <p className="text-sm bg-[#A8392B]/10 border border-[#A8392B]/30 text-[#7C2A21] rounded-md px-3 py-2">
        {bootstrapError}
      </p>
    );

  const isAnalyzing =
    stream.status === "running" || stream.status === "pending";

  return (
    <div className="flex flex-col gap-4 h-[calc(100vh-180px)]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <button
            type="button"
            onClick={() => router.push("/analiza/don")}
            className="text-sm text-muted hover:text-ink mb-2 transition"
          >
            ← Natrag na popis
          </button>
          <h1 className="font-display text-2xl text-ink">
            {document?.filename ?? "DON analiza"}
          </h1>
        </div>
        <button
          type="button"
          onClick={restart}
          className="rounded-md border border-brand-border px-3 py-1.5 text-sm text-navy hover:border-ink transition"
        >
          Pokreni ponovno
        </button>
      </div>

      <div className="flex items-center gap-4 px-4 py-2 rounded-md border border-brand-border bg-white text-sm flex-wrap">
        <span className="text-ink font-medium">
          {isAnalyzing
            ? `Analiza u tijeku… ${stream.progress}%`
            : "Analiza završena"}
        </span>
        <span>•</span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#3F7D45] inline-block" />
          {summary.ok} usklađenih
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#B8893E] inline-block" />
          {summary.warn} upozorenja
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#A8392B] inline-block" />
          {summary.fail} kršenja
        </span>
        {summary.neutral > 0 && (
          <span className="inline-flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#9B9892] inline-block" />
            {summary.neutral} info
          </span>
        )}
      </div>

      <div className="flex-1 grid grid-cols-12 gap-4 overflow-hidden">
        {/* LIJEVO: Stablo poglavlja */}
        <aside className="col-span-3 overflow-y-auto border-r border-brand-border pr-2">
          <div className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-3">
            Sadržaj ({chapters.length} poglavlja)
          </div>
          <ul className="space-y-1">
            {chapters.map((ch) => {
              const isActive = ch.key === activeChapter;
              const indent = ch.depth >= 4 ? "ml-9" : ch.depth >= 3 ? "ml-6" : ch.depth >= 2 ? "ml-3" : "";
              return (
                <li key={ch.key}>
                  <button
                    type="button"
                    onClick={() => {
                      setActiveChapter(ch.key);
                      setActiveBlockId(null);
                    }}
                    className={`w-full text-left px-2 py-1.5 rounded text-sm transition ${indent} ${
                      isActive
                        ? "bg-ink/5 text-ink font-medium"
                        : "text-navy hover:bg-surface-2"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate">
                        {ch.rb && (
                          <span className="font-mono text-muted text-xs mr-2">
                            {ch.rb}
                          </span>
                        )}
                        {ch.title}
                      </span>
                      {ch.issueCount > 0 && (
                        <span className="text-[10px] bg-[#A8392B]/10 text-[#A8392B] px-1.5 py-0.5 rounded shrink-0">
                          {ch.issueCount}
                        </span>
                      )}
                    </div>
                    <div className="text-[10px] text-muted mt-0.5">
                      {ch.blockCount}{" "}
                      {ch.blockCount === 1 ? "blok" : "blokova"}
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        </aside>

        {/* CENTAR: Blokovi */}
        <main className="col-span-6 overflow-y-auto pr-2 space-y-3">
          {visibleBlocks.length === 0 ? (
            <p className="text-sm text-muted italic">
              Nema blokova u ovom poglavlju.
            </p>
          ) : (
            visibleBlocks.map((block) => {
              const status = block.status || "neutral";
              const accent = STATUS_COLORS[status] || "#D5D2C7";
              const kind = getKind(block);
              const rb = getRb(block);
              const isActive = activeBlockId === block.id;
              return (
                <article
                  key={block.id}
                  onClick={() => setActiveBlockId(block.id)}
                  className={`rounded-lg border bg-white p-5 border-l-4 cursor-pointer transition ${
                    isActive
                      ? "border-brand-border ring-2 ring-ink/10"
                      : "border-brand-border"
                  }`}
                  style={{ borderLeftColor: accent }}
                >
                  <header className="flex items-baseline gap-3 mb-2">
                    <span className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted">
                      {KIND_LABELS[kind] || kind}
                    </span>
                    {rb && (
                      <span className="text-sm text-muted font-mono">{rb}</span>
                    )}
                  </header>
                  <p className="text-sm text-navy leading-relaxed whitespace-pre-line">
                    {block.text}
                  </p>
                </article>
              );
            })
          )}
        </main>

        {/* DESNO: LA findings za aktivni blok */}
        <aside className="col-span-3 overflow-y-auto pl-2 border-l border-brand-border space-y-3">
          {(() => {
            const block =
              visibleBlocks.find((b) => b.id === activeBlockId) ??
              visibleBlocks[0];
            if (!block) {
              return (
                <p className="text-sm text-muted italic">
                  Klikni na blok lijevo za prikaz LA analize.
                </p>
              );
            }
            const findings = block.findings ?? [];
            if (findings.length === 0) {
              return (
                <div className="rounded-lg border border-brand-border bg-white p-4 border-l-4 border-l-[#3F7D45]">
                  <div className="text-[11px] uppercase tracking-[0.18em] font-semibold text-[#3F7D45]">
                    USKLAĐENO
                  </div>
                  <p className="text-xs text-muted mt-2">
                    Lexitor analiza nije našla problem u ovom bloku.
                  </p>
                </div>
              );
            }
            return findings.map((f, idx) => (
              <article
                key={idx}
                className="rounded-lg border border-brand-border bg-white p-4 border-l-4"
                style={{ borderLeftColor: STATUS_COLORS[f.status] || "#D5D2C7" }}
              >
                <header className="flex items-start justify-between gap-2 mb-3">
                  <span
                    className="inline-flex items-center gap-2 text-[11px] uppercase tracking-wider font-semibold"
                    style={{ color: STATUS_COLORS[f.status] || "#9B9892" }}
                  >
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: STATUS_COLORS[f.status] || "#9B9892" }}
                    />
                    {STATUS_LABELS[f.status] || f.status.toUpperCase()}
                  </span>
                  <span className="text-[10px] uppercase tracking-[0.18em] text-muted">
                    Lexitor
                  </span>
                </header>
                {f.explanation && (
                  <>
                    <div className="text-[11px] uppercase tracking-wider text-muted font-semibold mb-1">
                      Zašto
                    </div>
                    <p className="text-sm text-navy leading-relaxed mb-3">
                      {f.explanation}
                    </p>
                  </>
                )}
                {f.suggestion && (
                  <>
                    <div className="text-[11px] uppercase tracking-wider text-muted font-semibold mb-1">
                      Predloženi ispravak
                    </div>
                    <p className="text-sm text-navy leading-relaxed mb-3">
                      {f.suggestion}
                    </p>
                  </>
                )}
                {f.citations && f.citations.length > 0 && (
                  <>
                    <hr className="my-3 border-brand-border" />
                    <ul className="space-y-1 text-[11px] font-mono text-muted">
                      {f.citations.map((c, ci) => (
                        <li key={ci}>
                          <span className="text-navy">
                            {(c.source || "OTHER").toUpperCase()} {c.reference}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </article>
            ));
          })()}
        </aside>
      </div>
    </div>
  );
}
