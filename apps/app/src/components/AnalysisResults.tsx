"use client";

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

import { StatusBadge, StatusDot } from "@/components/StatusBadge";
import type {
  AnalysisItemPublic,
  AnalysisStatus,
  AnalysisSummary,
  CitationPublic,
} from "@/lib/types";

function getSheet(item: AnalysisItemPublic): string {
  const meta = item.metadata_json as Record<string, unknown> | null | undefined;
  const sheet = meta?.sheet;
  return typeof sheet === "string" && sheet ? sheet : "Ostalo";
}

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
  const [activeSheet, setActiveSheet] = useState<string | null>(null);

  const sheetNames = useMemo(() => {
    const order: string[] = [];
    const seen = new Set<string>();
    for (const it of items) {
      const name = getSheet(it);
      if (!seen.has(name)) {
        seen.add(name);
        order.push(name);
      }
    }
    return order;
  }, [items]);

  // Auto-select the first sheet when items first arrive (or when active is gone).
  useEffect(() => {
    if (sheetNames.length === 0) {
      if (activeSheet !== null) setActiveSheet(null);
      return;
    }
    if (activeSheet === null || !sheetNames.includes(activeSheet)) {
      setActiveSheet(sheetNames[0]);
    }
  }, [sheetNames, activeSheet]);

  const filteredItems = useMemo(() => {
    if (activeSheet === null) return items;
    return items.filter((it) => getSheet(it) === activeSheet);
  }, [items, activeSheet]);

  const selected = useMemo(
    () =>
      filteredItems.find((it) => it.id === selectedId) ??
      filteredItems[0] ??
      null,
    [filteredItems, selectedId],
  );

  return (
    <div className="flex flex-col gap-4 h-[calc(100vh-200px)]">
      <Header status={status} progress={progress} summary={summary} error={error} count={items.length} />

      {sheetNames.length > 0 && (
        <SheetTabs
          sheetNames={sheetNames}
          activeSheet={activeSheet}
          onSelect={(name) => {
            setActiveSheet(name);
            setSelectedId(null);
          }}
          countsBySheet={items.reduce<Record<string, number>>((acc, it) => {
            const name = getSheet(it);
            acc[name] = (acc[name] ?? 0) + 1;
            return acc;
          }, {})}
        />
      )}

      <div className="flex flex-1 gap-4 min-h-0">
        <aside className="w-72 shrink-0 rounded-lg border border-brand-border bg-white overflow-y-auto">
          {filteredItems.length === 0 ? (
            <p className="p-4 text-sm text-muted italic">
              {status === "running" ? "Čekam prve rezultate…" : "Nema stavki."}
            </p>
          ) : (
            <ul className="divide-y divide-brand-border">
              {filteredItems.map((item) => (
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
                      {compactLabel(item)}
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

function SheetTabs({
  sheetNames,
  activeSheet,
  onSelect,
  countsBySheet,
}: {
  sheetNames: string[];
  activeSheet: string | null;
  onSelect: (name: string) => void;
  countsBySheet: Record<string, number>;
}) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const ghostRef = useRef<HTMLDivElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [visibleCount, setVisibleCount] = useState(sheetNames.length);

  // Measure ghost tabs and decide how many fit in the visible row.
  useLayoutEffect(() => {
    function measure() {
      const container = containerRef.current;
      const ghost = ghostRef.current;
      if (!container || !ghost) return;
      const ghostTabs = Array.from(
        ghost.querySelectorAll<HTMLElement>("[data-ghost-tab]"),
      );
      if (ghostTabs.length === 0) return;
      const containerWidth = container.clientWidth;
      const dropdownReserve = 84; // approx width of "Više ▾" button incl. border
      const gap = 4; // tailwind gap-1

      // Try fitting all tabs first (no dropdown)
      const totalWidth = ghostTabs.reduce(
        (acc, el, i) => acc + el.offsetWidth + (i > 0 ? gap : 0),
        0,
      );
      if (totalWidth <= containerWidth) {
        setVisibleCount(sheetNames.length);
        return;
      }

      const limit = containerWidth - dropdownReserve;
      let used = 0;
      let count = 0;
      for (let i = 0; i < ghostTabs.length; i++) {
        const w = ghostTabs[i].offsetWidth + (i > 0 ? gap : 0);
        if (used + w > limit) break;
        used += w;
        count++;
      }
      setVisibleCount(Math.max(1, count));
    }

    measure();
    const ro = new ResizeObserver(measure);
    if (containerRef.current) ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, [sheetNames]);

  // Close menu on outside click + escape
  useEffect(() => {
    if (!menuOpen) return;
    const onClick = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setMenuOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [menuOpen]);

  const visibleTabs = sheetNames.slice(0, visibleCount);
  const hiddenTabs = sheetNames.slice(visibleCount);
  const hasHidden = hiddenTabs.length > 0;
  const activeIsHidden =
    activeSheet !== null && hiddenTabs.includes(activeSheet);

  return (
    <>
      {/* Off-screen ghost row for measurement only — never visible. */}
      <div
        ref={ghostRef}
        aria-hidden
        className="invisible pointer-events-none fixed -top-[9999px] left-0 flex gap-1"
      >
        {sheetNames.map((name) => (
          <span
            key={name}
            data-ghost-tab
            className="shrink-0 px-3 py-2 text-sm whitespace-nowrap"
          >
            {name}
            <span className="ml-2 text-xs">{countsBySheet[name] ?? 0}</span>
          </span>
        ))}
      </div>

      <div
        ref={wrapRef}
        className="relative flex items-stretch border-b border-brand-border"
      >
        <div
          ref={containerRef}
          className="flex gap-1 flex-1 min-w-0 overflow-hidden pb-px -mb-px"
        >
          {visibleTabs.map((name) => {
            const isActive = name === activeSheet;
            return (
              <button
                key={name}
                type="button"
                onClick={() => onSelect(name)}
                className={`shrink-0 px-3 py-2 text-sm whitespace-nowrap border-b-2 transition ${
                  isActive
                    ? "border-ink text-ink font-medium"
                    : "border-transparent text-muted hover:text-ink"
                }`}
              >
                {name}
                <span className="ml-2 text-xs text-muted">{countsBySheet[name] ?? 0}</span>
              </button>
            );
          })}
        </div>

        {hasHidden && (
          <div className="relative flex items-stretch border-l border-brand-border shrink-0 bg-surface">
            <button
              type="button"
              onClick={() => setMenuOpen((o) => !o)}
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              className={`px-3 py-2 text-sm transition flex items-center gap-1 border-b-2 ${
                activeIsHidden
                  ? "border-ink text-ink font-medium"
                  : "border-transparent text-navy hover:text-ink hover:bg-surface-2"
              }`}
            >
              Više
              <span className="text-xs text-muted">+{hiddenTabs.length}</span>
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </button>
            {menuOpen && (
              <div
                role="menu"
                className="absolute right-0 top-full z-20 mt-1 w-72 max-h-80 overflow-y-auto rounded-md border border-brand-border bg-white shadow-lg py-1"
              >
                {hiddenTabs.map((name) => {
                  const isActive = name === activeSheet;
                  return (
                    <button
                      key={name}
                      role="menuitem"
                      type="button"
                      onClick={() => {
                        onSelect(name);
                        setMenuOpen(false);
                      }}
                      className={`w-full text-left px-3 py-2 text-sm flex items-center justify-between gap-3 hover:bg-surface-2 transition ${
                        isActive ? "font-medium text-ink bg-surface-2" : "text-navy"
                      }`}
                    >
                      <span className="truncate">{name}</span>
                      <span className="text-xs text-muted shrink-0">
                        {countsBySheet[name] ?? 0}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}

/** Tree row label — drop the "sheet · row N" prefix because the sheet tab
 *  already shows it. Prefer block label (rb + title) when available. */
function compactLabel(item: AnalysisItemPublic): string {
  if (item.label && !item.label.includes(" · red ")) {
    return item.label;
  }
  const text = item.text.split("\n")[0] ?? item.text;
  return text.length > 80 ? `${text.slice(0, 77)}…` : text;
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
