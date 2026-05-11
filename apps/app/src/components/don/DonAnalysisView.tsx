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

  // Linearan prikaz svih items (header + content blocks po redu).
  // Section_header-i ostaju INLINE u glavnom toku (crveni accent, bez LA).
  // Content blocks dobivaju plavi okvir + LA card pored sebe.
  // TOC sadrži oba: headers (boldano) + content blocks (kao kratki preview).
  const { tocEntries, allItems } = useMemo(() => {
    const list: AnalysisItemPublic[] = [];
    const toc: Array<{
      itemId: string;
      label: string;
      isHeader: boolean;
      depth: number;
      rb: string | null;
      issueCount: number;
    }> = [];
    items.forEach((it) => {
      list.push(it);
      const kind = getKind(it);
      const isHeader = kind === "section_header";
      // Label za TOC: ako je header, koristi title; ako blok, koristi prvih ~60 char teksta
      const meta = (it.metadata_json ?? {}) as Record<string, unknown>;
      const title = meta.title as string | undefined;
      let label: string;
      if (isHeader && title) {
        label = title;
      } else {
        const text = (it.text || "").replace(/\n+/g, " ").trim();
        label = text.length > 60 ? text.slice(0, 60) + "…" : text;
      }
      const hasIssue =
        !isHeader && (it.status === "warn" || it.status === "fail");
      toc.push({
        itemId: it.id,
        label,
        isHeader,
        depth: isHeader ? (meta.depth as number) ?? 1 : 0,
        rb: getRb(it),
        issueCount: hasIssue ? 1 : 0,
      });
    });
    return { tocEntries: toc, allItems: list };
  }, [items]);

  // Track active item za scroll-spy highlight u TOC-u
  useEffect(() => {
    if (allItems.length === 0) return;
    if (!activeChapter) {
      setActiveChapter(allItems[0].id);
    }
  }, [allItems, activeChapter]);

  const scrollToItem = useCallback((itemId: string) => {
    const el = window.document.querySelector(`[data-block-id="${itemId}"]`);
    el?.scrollIntoView({ behavior: "smooth", block: "start" });
    setActiveChapter(itemId);
  }, []);

  // Scroll-spy: prati koji item je u top 1/3 viewport-a i highlight TOC.
  useEffect(() => {
    if (allItems.length === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible.length > 0) {
          const id = visible[0].target.getAttribute("data-block-id");
          if (id) setActiveChapter(id);
        }
      },
      { rootMargin: "-20% 0px -60% 0px" },
    );
    const els = window.document.querySelectorAll("[data-block-id]");
    els.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [allItems]);

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
            Sadržaj ({tocEntries.length} stavki)
          </div>
          <ul className="space-y-0.5">
            {tocEntries.map((entry) => {
              const isActive = entry.itemId === activeChapter;
              // Indent: section_header-i koriste depth (1-6), content blokovi
              // su uvučeni pod zadnjim section_header-om
              const indent = entry.isHeader
                ? entry.depth >= 4 ? "ml-6" : entry.depth >= 3 ? "ml-4" : entry.depth >= 2 ? "ml-2" : ""
                : "ml-3"; // content blokovi uvučeni za 1 razinu od najmanjeg header-a
              const baseClasses = entry.isHeader
                ? "font-semibold text-ink"
                : "text-navy text-xs";
              return (
                <li key={entry.itemId}>
                  <button
                    type="button"
                    onClick={() => scrollToItem(entry.itemId)}
                    className={`w-full text-left px-2 py-1 rounded text-sm transition ${indent} ${baseClasses} ${
                      isActive ? "bg-signal/10 text-ink" : "hover:bg-surface-2"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate">
                        {entry.rb && (
                          <span className="font-mono text-muted text-[10px] mr-1.5">
                            {entry.rb}
                          </span>
                        )}
                        {entry.label}
                      </span>
                      {entry.issueCount > 0 && (
                        <span className="text-[9px] bg-status-fail/10 text-status-fail px-1 py-0.5 rounded shrink-0">
                          !
                        </span>
                      )}
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        </aside>

        <main className="md:col-span-9 min-h-0 h-full overflow-y-auto pr-2 space-y-3 scroll-smooth">
          {allItems.length === 0 ? (
            <p className="text-sm text-muted italic">
              Nema analiziranih blokova u dokumentu.
            </p>
          ) : (
            allItems.map((item) => {
              const kind = getKind(item);
              const rb = getRb(item);
              const isHeader = kind === "section_header";

              // SECTION HEADER — crveni accent, bez LA, vizualno "grupna"
              if (isHeader) {
                const meta = (item.metadata_json ?? {}) as Record<string, unknown>;
                const depth = (meta.depth as number) ?? 1;
                const headerSize =
                  depth === 1 ? "text-xl" : depth === 2 ? "text-lg" : "text-base";
                return (
                  <div
                    key={item.id}
                    data-block-id={item.id}
                    className="scroll-mt-4 pt-3"
                  >
                    <div
                      className={`flex items-baseline gap-3 pb-2 border-b-2 border-status-fail/40`}
                    >
                      {rb && (
                        <span className="font-mono text-sm text-status-fail/80 shrink-0">
                          {rb}
                        </span>
                      )}
                      <h2
                        className={`font-display ${headerSize} text-status-fail font-semibold uppercase tracking-wide`}
                      >
                        {item.text || (meta.title as string) || ""}
                      </h2>
                    </div>
                  </div>
                );
              }

              // CONTENT BLOCK — plavi okvir + LA pored
              const status = item.status || "neutral";
              const accent = STATUS_COLORS[status] || "#3B82C4"; // signal blue default
              return (
                <div
                  key={item.id}
                  data-block-id={item.id}
                  className="flex flex-col md:flex-row gap-4 md:items-stretch scroll-mt-4"
                >
                  <article
                    className="md:flex-[2] rounded-lg border-2 border-signal/40 bg-surface-2 p-4"
                    style={{ borderColor: accent }}
                  >
                    <header className="flex items-baseline gap-3 mb-1.5">
                      <span className="text-[10px] uppercase tracking-[0.18em] font-semibold text-muted">
                        {KIND_LABELS[kind] || kind}
                      </span>
                      {rb && (
                        <span className="text-xs text-muted font-mono">{rb}</span>
                      )}
                    </header>
                    <p className="text-sm text-navy leading-relaxed whitespace-pre-line">
                      {item.text}
                    </p>
                  </article>
                  <div className="md:flex-1 space-y-3">
                    <BlockFindings findings={item.findings ?? []} />
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
