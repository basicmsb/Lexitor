"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { useAnalysisStream } from "@/hooks/useAnalysisStream";
import { api } from "@/lib/api";
import type {
  AnalysisItemPublic,
  DocumentPublic,
  FindingPublic,
} from "@/lib/types";

/**
 * Reusable DON analiza view — 3-kolone layout (TOC | blokovi | LA).
 * Koristi se i u /analiza/don/[documentId] (samostalan fajl) i u
 * /analiza/don/sets/[setId] (s tabs nad više fajlova istog seta).
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
  key: string;
  depth: number;
  title: string;
  rb: string | null;
  startIndex: number;
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
function chapterKey(path: ChapterPath): string {
  return path.map((p) => `${p.depth}:${p.title}`).join("/") || "ROOT";
}

interface Props {
  documentId: string;
  /** Prikaži vlastiti header (filename + Pokreni ponovno gumb).
   *  False kad je view embeddan u set tabs — header pripada parentu. */
  showHeader?: boolean;
  /** Vertikalna visina viewport-a koju view zauzima.
   *  Default fits when used as full page. */
  containerHeightClass?: string;
}

export function DonAnalysisView({
  documentId,
  showHeader = true,
  containerHeightClass = "h-[calc(100vh-180px)]",
}: Props) {
  const [document, setDocument] = useState<DocumentPublic | null>(null);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [bootstrapError, setBootstrapError] = useState<string | null>(null);
  const stream = useAnalysisStream(analysisId);
  const [historicalItems, setHistoricalItems] = useState<AnalysisItemPublic[]>([]);
  const [historicalError, setHistoricalError] = useState<string | null>(null);
  const [activeChapter, setActiveChapter] = useState<string | null>(null);

  const bootstrap = useCallback(async () => {
    if (!documentId) return;
    setBootstrapping(true);
    setBootstrapError(null);
    setActiveChapter(null);
    setAnalysisId(null);
    setHistoricalItems([]);
    setHistoricalError(null);
    try {
      const doc = await api.getDocument(documentId);
      setDocument(doc);
      const existing = await api.listDocumentAnalyses(documentId);
      if (existing.length === 0) {
        const started = await api.startAnalysis(documentId);
        setAnalysisId(started.analysis_id);
      } else {
        const latest = existing[0];
        setAnalysisId(latest.id);
        if (latest.status === "complete" || latest.status === "error") {
          const detail = await api.getAnalysis(latest.id);
          setHistoricalItems(detail.items);
          if (latest.status === "error") {
            setHistoricalError(latest.error_message ?? "Nepoznata greška");
          }
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

  const { chapters, blocksByChapter } = useMemo(() => {
    const chMap = new Map<string, ChapterNode>();
    const bMap = new Map<string, AnalysisItemPublic[]>();
    items.forEach((it, idx) => {
      const path = getChapterPath(it);
      const key = chapterKey(path);
      if (!chMap.has(key)) {
        const top = path[0];
        chMap.set(key, {
          key,
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
    const sorted = Array.from(chMap.values()).sort(
      (a, b) => a.startIndex - b.startIndex,
    );
    return { chapters: sorted, blocksByChapter: bMap };
  }, [items]);

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
  if (bootstrapping) {
    return (
      <div className="flex items-center gap-3 text-sm text-muted">
        <span className="inline-block w-3 h-3 rounded-full bg-muted/30 animate-pulse" />
        Pripremam analizu…
      </div>
    );
  }
  if (bootstrapError)
    return (
      <p className="text-sm bg-status-fail/10 border border-status-fail/30 text-status-fail rounded-md px-3 py-2">
        {bootstrapError}
      </p>
    );

  const isAnalyzing =
    stream.status === "running" || stream.status === "pending";
  const hasError = stream.status === "error";
  const errorMessage = stream.error ?? historicalError;

  return (
    <div className={`flex flex-col gap-4 min-h-0 ${containerHeightClass}`}>
      {showHeader && (
        <div className="flex items-start justify-between gap-4">
          <div>
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
      )}

      {hasError && (
        <div className="rounded-md border border-status-fail/30 bg-status-fail/5 px-4 py-3">
          <div className="text-[11px] uppercase tracking-[0.18em] font-semibold text-status-fail mb-1">
            Greška u analizi
          </div>
          <p className="text-sm text-status-fail">
            {errorMessage ?? "Analiza nije uspjela. Pokreni ponovno za novi pokušaj."}
          </p>
        </div>
      )}

      <div className="rounded-md border border-brand-border bg-surface-2">
        {isAnalyzing && (
          <div className="h-1 bg-surface-2 overflow-hidden rounded-t-md">
            <div
              className="h-full bg-signal transition-all duration-500"
              style={{ width: `${stream.progress}%` }}
            />
          </div>
        )}
        <div className="flex items-center gap-4 px-4 py-2 text-sm flex-wrap">
        <span className={hasError ? "text-status-fail font-medium" : "text-ink font-medium"}>
          {isAnalyzing
            ? `Analiza u tijeku… ${stream.progress}%`
            : hasError
              ? "Analiza neuspjela"
              : "Analiza završena"}
        </span>
        <span>•</span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-status-ok inline-block" />
          {summary.ok} usklađenih
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#B8893E] inline-block" />
          {summary.warn} upozorenja
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-status-fail inline-block" />
          {summary.fail} kršenja
        </span>
        {summary.neutral > 0 && (
          <span className="inline-flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#9B9892] inline-block" />
            {summary.neutral} info
          </span>
        )}
        {!showHeader && (
          <button
            type="button"
            onClick={restart}
            className="ml-auto rounded-md border border-brand-border px-3 py-1 text-xs text-navy hover:border-ink transition"
          >
            Pokreni ponovno
          </button>
        )}
        </div>
      </div>

      <div className="flex-1 min-h-0 grid grid-cols-1 md:grid-cols-12 gap-4 overflow-hidden">
        <aside className="md:col-span-3 min-h-0 max-h-[30vh] md:max-h-none md:h-full overflow-y-auto md:border-r border-brand-border md:pr-2 pb-2 md:pb-0 border-b md:border-b-0">
          <div className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-3">
            Sadržaj ({chapters.length} poglavlja)
          </div>
          <ul className="space-y-1">
            {chapters.map((ch) => {
              const isActive = ch.key === activeChapter;
              const indent =
                ch.depth >= 4 ? "ml-9" : ch.depth >= 3 ? "ml-6" : ch.depth >= 2 ? "ml-3" : "";
              return (
                <li key={ch.key}>
                  <button
                    type="button"
                    onClick={() => setActiveChapter(ch.key)}
                    className={`w-full text-left px-2 py-1.5 rounded text-sm transition ${indent} ${
                      isActive ? "bg-ink/5 text-ink font-medium" : "text-navy hover:bg-surface-2"
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
                        <span className="text-[10px] bg-status-fail/10 text-status-fail px-1.5 py-0.5 rounded shrink-0">
                          {ch.issueCount}
                        </span>
                      )}
                    </div>
                    <div className="text-[10px] text-muted mt-0.5">
                      {ch.blockCount} {ch.blockCount === 1 ? "blok" : "blokova"}
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        </aside>

        <main className="md:col-span-9 min-h-0 h-full overflow-y-auto pr-2 space-y-3">
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
              return (
                <div
                  key={block.id}
                  className="flex flex-col md:flex-row gap-4 md:items-stretch"
                >
                  <article
                    className="md:flex-[2] rounded-lg border border-brand-border bg-surface-2 p-5 border-l-4"
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
                  <div className="md:flex-1 space-y-3">
                    <BlockFindings findings={block.findings ?? []} />
                  </div>
                </div>
              );
            })
          )}
        </main>
      </div>
    </div>
  );
}

function BlockFindings({ findings }: { findings: FindingPublic[] }) {
  if (findings.length === 0) {
    return (
      <div className="rounded-lg border border-brand-border bg-surface-2 p-4 border-l-4 border-l-status-ok h-full">
        <div className="text-[11px] uppercase tracking-[0.18em] font-semibold text-status-ok">
          USKLAĐENO
        </div>
        <p className="text-xs text-muted mt-2">
          Lexitor analiza nije našla problem u ovom bloku.
        </p>
      </div>
    );
  }
  return (
    <>
      {findings.map((f, idx) => (
        <article
          key={idx}
          className="rounded-lg border border-brand-border bg-surface-2 p-4 border-l-4"
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
              <p className="text-[10px] uppercase tracking-[0.18em] font-semibold text-muted mb-2">
                Slični presedani
              </p>
              <ul className="space-y-3">
                {f.citations.map((c, ci) => {
                  const sourceLabel = (c.source || "OTHER").toUpperCase();
                  const isDkom = sourceLabel === "DKOM";
                  // Verdict styling — uvazen=zeleno (signal za detekciju),
                  // odbijen=crveno (anti-pattern), dijelom_uvazen=zlatno
                  const verdictColor =
                    c.verdict_raw === "uvazen"
                      ? "bg-status-ok/15 text-status-ok border-status-ok/30"
                      : c.verdict_raw === "odbijen"
                        ? "bg-status-fail/15 text-status-fail border-status-fail/30"
                        : c.verdict_raw === "djelomicno_uvazen"
                          ? "bg-gold/15 text-gold border-gold/30"
                          : "bg-muted/15 text-muted border-muted/30";
                  return (
                    <li
                      key={ci}
                      className="rounded-md border border-brand-border bg-surface-2/40 p-3"
                    >
                      <div className="flex items-start justify-between gap-2 mb-1.5">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span
                            className={`inline-flex items-center gap-1 text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded ${
                              isDkom
                                ? "bg-signal/15 text-signal"
                                : "bg-gold/15 text-gold"
                            }`}
                          >
                            {sourceLabel}
                          </span>
                          {c.verdict && (
                            <span
                              className={`inline-block text-[10px] font-medium px-1.5 py-0.5 rounded border ${verdictColor}`}
                              title={
                                c.verdict_raw === "uvazen"
                                  ? "DKOM uvažio žalbu — signal za detekciju"
                                  : c.verdict_raw === "odbijen"
                                    ? "DKOM odbio žalbu — anti-pattern (možda nije problem)"
                                    : "DKOM djelomično uvažio / ne razmatra"
                              }
                            >
                              {c.verdict}
                            </span>
                          )}
                          {c.confidence != null && (
                            <span
                              className="text-[10px] text-muted font-mono"
                              title={`Semantička sličnost: ${(c.confidence * 100).toFixed(1)}%`}
                            >
                              {(c.confidence * 100).toFixed(0)}%
                            </span>
                          )}
                        </div>
                        {c.url ? (
                          <a
                            href={c.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[10px] font-mono text-navy hover:text-signal hover:underline transition shrink-0"
                            title="Otvori PDF u novom tabu"
                          >
                            ↗
                          </a>
                        ) : null}
                      </div>
                      <p className="text-[11px] font-mono text-navy mb-1">
                        {c.url ? (
                          <a
                            href={c.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:text-signal hover:underline transition"
                          >
                            {c.reference}
                          </a>
                        ) : (
                          c.reference
                        )}
                      </p>
                      {c.snippet && (
                        <p className="text-xs text-muted leading-relaxed whitespace-pre-line">
                          {c.snippet}
                        </p>
                      )}
                    </li>
                  );
                })}
              </ul>
            </>
          )}
        </article>
      ))}
    </>
  );
}
