"use client";

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

import { HighlightedText } from "@/components/HighlightedText";
import { StatusDot, statusAccent, statusLabel } from "@/components/StatusBadge";
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
  const [activeSheet, setActiveSheet] = useState<string | null>(null);
  const [visibleId, setVisibleId] = useState<string | null>(null);

  const scrollRootRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<Map<string, HTMLDivElement>>(new Map());

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

  // Track which item is most-visible in the scroll viewport so the sidebar
  // can highlight it as the user scrolls. The rootMargin biases the
  // intersection toward the top of the viewport.
  useEffect(() => {
    const root = scrollRootRef.current;
    if (!root) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const top = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (top) {
          const id = top.target.getAttribute("data-item-id");
          if (id) setVisibleId(id);
        }
      },
      {
        root,
        rootMargin: "-10% 0px -70% 0px",
        threshold: [0, 0.25, 0.5, 0.75, 1],
      },
    );
    itemRefs.current.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [filteredItems]);

  const scrollToItem = (id: string) => {
    const el = itemRefs.current.get(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      setVisibleId(id);
    }
  };

  return (
    <div className="flex flex-col gap-4 h-[calc(100vh-200px)]">
      <Header status={status} progress={progress} summary={summary} error={error} count={items.length} />

      {sheetNames.length > 0 && (
        <SheetTabs
          sheetNames={sheetNames}
          activeSheet={activeSheet}
          onSelect={(name) => setActiveSheet(name)}
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
                    onClick={() => scrollToItem(item.id)}
                    className={`w-full text-left px-3 py-2 flex items-center gap-2 text-sm hover:bg-surface-2 transition ${
                      visibleId === item.id ? "bg-surface-2 text-ink font-medium" : "text-navy"
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

        <div
          ref={scrollRootRef}
          className="flex-1 min-w-0 overflow-y-auto flex flex-col gap-4 pr-1"
        >
          {filteredItems.length === 0 ? (
            <p className="text-sm text-muted italic px-1">
              {status === "running" ? "Čekam prve rezultate…" : "Nema stavki."}
            </p>
          ) : (
            filteredItems.map((item) => (
              <div
                key={item.id}
                data-item-id={item.id}
                ref={(el) => {
                  if (el) itemRefs.current.set(item.id, el);
                  else itemRefs.current.delete(item.id);
                }}
              >
                <ItemDetail item={item} />
              </div>
            ))
          )}
        </div>
      </div>
    </div>
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

/** Best-effort split of an existing `label` like "1.1.1 · Uređenje gradilišta"
 *  into rb + naslov. Falls back to the full label as title. */
function splitLabel(label: string | null): { rb: string | null; title: string | null } {
  if (!label) return { rb: null, title: null };
  const idx = label.indexOf(" · ");
  if (idx === -1) return { rb: null, title: label };
  return { rb: label.slice(0, idx), title: label.slice(idx + 3) };
}

interface MathRow {
  row?: number;
  jm?: string | null;
  kol?: number | string | null;
  cijena?: number | string | null;
  iznos?: number | string | null;
  iznos_is_formula?: boolean;
  computed_iznos?: number | null;
  position_label?: string | null;
}

function getMathRows(item: AnalysisItemPublic): MathRow[] {
  const meta = item.metadata_json as Record<string, unknown> | null | undefined;
  const rows = meta?.math_rows;
  if (!Array.isArray(rows)) return [];
  return rows as MathRow[];
}

function rowsHavePositions(rows: MathRow[]): boolean {
  return rows.some((r) => typeof r.position_label === "string" && r.position_label.length > 0);
}

function rowsHaveExcelRow(rows: MathRow[]): boolean {
  return rows.some((r) => typeof r.row === "number" && Number.isFinite(r.row));
}

function trimPositionsFromText(text: string): string {
  // Drop everything from the "POZICIJE:" line onward — that list is
  // already shown as the first column of the math table, repeating it
  // in the prose adds noise.
  const re = /(^|\n)\s*(POZICIJE|POZICIJA|POPIS|SUBPOZICIJE|STAVKE|RAZRADA|RAZRAĐUJE)\s*:?\s*\n/i;
  const m = re.exec(text);
  if (!m) return text;
  return text.slice(0, m.index).trimEnd();
}

function formatNumber(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "number" ? value : Number(value);
  if (Number.isFinite(n)) {
    return new Intl.NumberFormat("hr-HR", { maximumFractionDigits: 4 }).format(n);
  }
  return String(value);
}

/** Always renders with 2 decimals — used for monetary columns where
 *  "7.074" alone is ambiguous (looks like 7,074 in en-US convention). */
function formatCurrency(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "number" ? value : Number(value);
  if (Number.isFinite(n)) {
    return new Intl.NumberFormat("hr-HR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(n);
  }
  return String(value);
}

function toNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  const s = String(value).replace(",", ".").trim();
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

/** True if `value` carries precision beyond two decimal places. EUR
 *  amounts shouldn't have a third decimal — values like 7.07423 hidden
 *  inside a cell that displays as 7.07 are a classic source of
 *  "računska greška" mismatches between displayed totals and the real
 *  number Excel uses for downstream sums. */
function hasMoreThanTwoDecimals(value: number): boolean {
  if (!Number.isFinite(value)) return false;
  const cents = value * 100;
  return Math.abs(Math.round(cents) - cents) > 0.005;
}

function ProvjeraCell({
  isFormula,
  excel,
  computed,
  hasExcelValue,
}: {
  isFormula: boolean;
  excel: number | null;
  computed: number | null;
  hasExcelValue: boolean;
}) {
  // Mismatch wins over everything else
  if (
    hasExcelValue &&
    excel !== null &&
    computed !== null &&
    excel !== computed
  ) {
    return (
      <span
        className="text-[#A8392B] text-xs font-medium"
        title={`Excel: ${formatCurrency(excel)} · Lexitor: ${formatCurrency(computed)}`}
      >
        ✗ {formatCurrency(computed)}
      </span>
    );
  }

  // Precision issue (>2 decimals anywhere) — flag even when totals match
  const precisionIssue =
    (excel !== null && hasMoreThanTwoDecimals(excel)) ||
    (computed !== null && hasMoreThanTwoDecimals(computed));
  if (precisionIssue) {
    const offending = excel !== null && hasMoreThanTwoDecimals(excel) ? excel : computed;
    return (
      <span
        className="text-[#A8392B] text-xs font-medium"
        title={`Iznos sadrži više od 2 decimale: ${offending} — moguća računska greška jer cijena u EUR ima 2 decimale.`}
      >
        ✗ ra. greška
      </span>
    );
  }

  if (isFormula) {
    return <span className="text-[#3F7D45] text-xs">✓ formula</span>;
  }
  if (computed === null) {
    return <span className="text-muted text-xs">—</span>;
  }
  if (!hasExcelValue) {
    return (
      <span
        className="text-xs text-muted"
        title="Iznos računa Lexitor (kol × cijena) — Excel ćelija prazna"
      >
        ∑ {formatCurrency(computed)}
      </span>
    );
  }
  return <span className="text-[#3F7D45] text-xs">✓ točno</span>;
}

function kindLabel(kind: string, isRollup = false): string {
  switch (kind) {
    case "recap_subtotal":
      return "Rekapitulacija — međusuma";
    case "recap_total":
      return "Rekapitulacija — UKUPNO";
    case "recap_grand":
      return "Rekapitulacija — SVEUKUPNO";
    case "recap_pdv":
      return "Rekapitulacija — PDV";
    case "recap_line":
      return "Rekapitulacija — stavka";
    case "recap_extra":
      return "Rekapitulacija — dodatak";
    case "recap_section":
      return "Rekapitulacija — grupa";
    case "group_sum":
    default:
      return isRollup ? "Rollup suma" : "Grupna suma";
  }
}

function SectionHeaderDetail({
  item,
  kind,
}: {
  item: AnalysisItemPublic;
  kind: string;
}) {
  const meta = (item.metadata_json ?? {}) as Record<string, unknown>;
  const depth = typeof meta.depth === "number" ? meta.depth : 0;
  const rb = typeof meta.rb === "string" ? meta.rb : null;
  const title = typeof meta.title === "string" ? meta.title : null;
  const fallbackLabel =
    kind === "recap_section" ? "Rekapitulacija — grupa" : "Sekcija";

  // Wider indent for deeper levels, capped so the layout stays readable.
  const indentClass =
    depth >= 4 ? "ml-12" : depth >= 3 ? "ml-8" : depth >= 2 ? "ml-4" : "";

  return (
    <article
      className={`rounded-lg border border-brand-border bg-surface-2/40 px-6 py-3 ${indentClass}`}
    >
      <span className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted">
        {fallbackLabel}
        {depth > 0 && (
          <span className="ml-2 text-muted/70 normal-case tracking-normal">
            razina {depth}
          </span>
        )}
      </span>
      <h3 className="font-display text-lg text-ink leading-snug mt-1 flex items-baseline gap-3">
        {rb && <span className="font-mono text-muted text-sm">{rb}</span>}
        <span>{title || item.text || item.label}</span>
      </h3>
    </article>
  );
}

interface CrossSheetRef {
  sheet: string;
  col: string;
  row: number;
}

function RecapLineDetail({
  item,
  accent,
  label,
  kind,
}: {
  item: AnalysisItemPublic;
  accent: string;
  label: string;
  kind: string;
}) {
  const meta = (item.metadata_json ?? {}) as Record<string, unknown>;
  const titleRow = typeof meta.title_row === "number" ? meta.title_row : null;
  const formula = typeof meta.formula === "string" ? meta.formula : null;
  const refs: CrossSheetRef[] = Array.isArray(meta.cross_sheet_refs)
    ? (meta.cross_sheet_refs as CrossSheetRef[])
    : [];
  const iznos = (meta.iznos as number | string | null | undefined) ?? null;
  const section = typeof meta.section === "string" ? meta.section : null;

  return (
    <div className="grid gap-4 lg:grid-cols-3 items-start">
      <article
        className="rounded-lg border border-brand-border bg-white p-6 lg:col-span-2 border-l-4"
        style={{ borderLeftColor: accent }}
      >
        <header className="flex items-start justify-between gap-4 mb-3">
          <span className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted">
            {kindLabel(kind)}
          </span>
          {section && (
            <span className="text-xs text-muted font-mono">{section}</span>
          )}
        </header>

        <div className="flex items-baseline gap-3 mb-3">
          <span className="text-[11px] text-muted font-mono shrink-0 w-8 text-right pt-2 tabular-nums">
            {titleRow ?? ""}
          </span>
          <h2 className="font-display text-xl text-ink leading-snug max-w-prose">
            {item.text || item.label}
          </h2>
        </div>

        <div className="ml-11 space-y-2">
          {iznos !== null && iznos !== undefined && iznos !== "" && (
            <p className="text-sm">
              <span className="text-muted">Iznos:</span>{" "}
              <span className="font-mono text-ink">
                {formatCurrency(iznos)}
              </span>
            </p>
          )}
          {formula && (
            <p className="text-xs text-muted font-mono break-all">
              {formula}
            </p>
          )}
          {refs.length > 0 && (
            <div className="text-sm">
              <span className="text-muted">Referencira:</span>{" "}
              <ul className="inline-flex flex-wrap gap-2 ml-1">
                {refs.map((r, idx) => (
                  <li
                    key={idx}
                    className="font-mono text-xs text-signal bg-signal/10 px-2 py-0.5 rounded"
                  >
                    {r.sheet}!{r.col}
                    {r.row}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {kind === "recap_extra" && !formula && (
            <p className="text-xs text-[#A87F2E]">
              Hardkodirana vrijednost — bez formule.
            </p>
          )}
        </div>
      </article>

      <div className="lg:col-span-1 flex flex-col gap-3">
        <FindingCard
          accent={accent}
          label={label}
          explanation={item.explanation}
          suggestion={item.suggestion}
          citations={item.citations}
        />
      </div>
    </div>
  );
}

interface GroupSumMathRef {
  row: number;
  iznos?: number | string | null;
  computed_iznos?: number | null;
  block_label?: string | null;
  block_title?: string | null;
}

function GroupSumDetail({
  item,
  accent,
  label,
  kind = "group_sum",
}: {
  item: AnalysisItemPublic;
  accent: string;
  label: string;
  kind?: string;
}) {
  const meta = (item.metadata_json ?? {}) as Record<string, unknown>;
  const titleRow = typeof meta.title_row === "number" ? meta.title_row : null;
  const formula = typeof meta.formula === "string" ? meta.formula : null;
  const isRollup = Boolean(meta.is_rollup);
  const summedRows: number[] = Array.isArray(meta.summed_rows)
    ? (meta.summed_rows as number[])
    : [];
  const effectiveRows: number[] = Array.isArray(meta.effective_summed_rows)
    ? (meta.effective_summed_rows as number[])
    : summedRows;
  const inRange: GroupSumMathRef[] = Array.isArray(meta.math_rows_in_range)
    ? (meta.math_rows_in_range as GroupSumMathRef[])
    : [];
  const missingRows: GroupSumMathRef[] = Array.isArray(meta.missing_rows)
    ? (meta.missing_rows as GroupSumMathRef[])
    : [];
  const effectiveSet = new Set(effectiveRows);
  const missingCount = missingRows.length;

  return (
    <div className="grid gap-4 lg:grid-cols-3 items-start">
      <article
        className="rounded-lg border border-brand-border bg-white p-6 lg:col-span-2 border-l-4"
        style={{ borderLeftColor: accent }}
      >
        <header className="flex items-start justify-between gap-4 mb-3">
          <span className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted">
            {kindLabel(kind, isRollup)}
          </span>
        </header>

        <div className="flex items-baseline gap-3 mb-3">
          <span className="text-[11px] text-muted font-mono shrink-0 w-8 text-right pt-2 tabular-nums">
            {titleRow ?? ""}
          </span>
          <h2 className="font-display text-2xl text-ink leading-snug max-w-prose">
            {item.text || "UKUPNO"}
          </h2>
        </div>

        {formula && (
          <p className="text-xs text-muted font-mono ml-11 mb-3 break-all">
            {formula}
          </p>
        )}

        <p className="text-sm text-navy ml-11 mb-4">
          {isRollup
            ? `Rollup pokriva ${inRange.length} matematičkih redova kroz podgrupne UKUPNO retke`
            : `Pokriva ${inRange.length} matematičkih redova`}
          {missingCount > 0 ? ` — nedostaje ${missingCount} u rasponu.` : "."}
        </p>

        {(inRange.length > 0 || missingRows.length > 0) && (
          <div className="mt-2 overflow-x-auto">
            <table className="text-sm w-full">
              <thead>
                <tr className="text-[11px] uppercase tracking-wider text-muted">
                  <th style={{ width: "2rem" }} className="py-1" aria-hidden />
                  <th className="pl-3 pr-4 py-1 text-left font-medium">Stavka</th>
                  <th className="pr-4 py-1 text-right font-medium">Iznos</th>
                  <th className="py-1 text-right font-medium">Uključeno</th>
                </tr>
              </thead>
              <tbody className="text-navy font-mono">
                {inRange.map((r, idx) => {
                  const value = r.iznos ?? r.computed_iznos ?? null;
                  // After transitive expansion, every row in `inRange`
                  // is by definition covered. We still keep the column
                  // so users can scan visually.
                  const included = effectiveSet.has(r.row);
                  return (
                    <tr key={`in-${idx}`} className="border-t border-brand-border">
                      <td
                        style={{ width: "2rem" }}
                        className="py-1.5 text-right text-muted tabular-nums text-[11px]"
                      >
                        {r.row}
                      </td>
                      <td className="pl-3 pr-4 py-1.5 font-sans">
                        {r.block_title || r.block_label || (
                          <span className="text-muted italic">—</span>
                        )}
                      </td>
                      <td className="pr-4 py-1.5 text-right">
                        {formatCurrency(value)}
                      </td>
                      <td className="py-1.5 text-right">
                        {included ? (
                          <span className="text-[#3F7D45] text-xs">✓</span>
                        ) : (
                          <span className="text-muted text-xs">·</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
                {missingRows.map((r, idx) => {
                  const value = r.iznos ?? r.computed_iznos ?? null;
                  return (
                    <tr
                      key={`miss-${idx}`}
                      className="border-t border-brand-border bg-[#A8392B]/5"
                    >
                      <td
                        style={{ width: "2rem" }}
                        className="py-1.5 text-right text-muted tabular-nums text-[11px]"
                      >
                        {r.row}
                      </td>
                      <td className="pl-3 pr-4 py-1.5 font-sans">
                        {r.block_title || r.block_label || (
                          <span className="text-muted italic">—</span>
                        )}
                      </td>
                      <td className="pr-4 py-1.5 text-right">
                        {formatCurrency(value)}
                      </td>
                      <td className="py-1.5 text-right">
                        <span
                          className="text-[#A8392B] text-xs font-medium"
                          title="Stavka u rasponu, ali nije pokrivena ovom SUM formulom"
                        >
                          ✗ izostavljeno
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </article>

      <div className="lg:col-span-1 flex flex-col gap-3">
        <FindingCard
          accent={accent}
          label={label}
          explanation={item.explanation}
          suggestion={item.suggestion}
          citations={item.citations}
        />
      </div>
    </div>
  );
}

function ItemDetail({ item }: { item: AnalysisItemPublic }) {
  const accent = statusAccent(item.status);
  const label = statusLabel(item.status);
  const { rb, title } = splitLabel(item.label);
  const meta = (item.metadata_json ?? {}) as Record<string, unknown>;
  const kind = typeof meta.kind === "string" ? meta.kind : "stavka";
  const isGroupSum = kind === "group_sum";
  const isRecapSection = kind === "recap_section";
  const isRecapSumLike =
    kind === "recap_subtotal" || kind === "recap_total" || kind === "recap_grand";
  const isRecapLine = kind === "recap_line";
  const isRecapPdv = kind === "recap_pdv";
  const isRecapExtra = kind === "recap_extra";
  const titleRow = typeof meta.title_row === "number" ? meta.title_row : null;
  const rawTextRows = Array.isArray(meta.text_rows)
    ? (meta.text_rows as Array<{ row: number; text: string }>)
    : [];
  const path: Array<{ label?: string; title?: string }> = Array.isArray(meta.path)
    ? (meta.path as Array<{ label?: string; title?: string }>)
    : [];
  const mathRows = getMathRows(item);
  const hasPositions = rowsHavePositions(mathRows);
  const hasExcelRow = rowsHaveExcelRow(mathRows);

  if (isGroupSum || isRecapSumLike) {
    return (
      <GroupSumDetail item={item} accent={accent} label={label} kind={kind} />
    );
  }
  if (isRecapSection || kind === "section_header") {
    return <SectionHeaderDetail item={item} kind={kind} />;
  }
  if (isRecapLine || isRecapPdv || isRecapExtra) {
    return (
      <RecapLineDetail item={item} accent={accent} label={label} kind={kind} />
    );
  }

  // Build per-line segments mapped to their Excel row + char offsets in
  // item.text. We rely on the parser's invariant that item.text is
  // [title, ...trimmed text rows] joined by "\n", with empties dropped.
  const segments = (() => {
    const titleStripped = title ? title.trim() : "";
    const headerRe = /^\s*(POZICIJE|POZICIJA|POPIS|SUBPOZICIJE|STAVKE|RAZRADA|RAZRAĐUJE)\s*:?\s*$/i;
    let cursor = titleStripped ? titleStripped.length + 1 : 0;
    const out: Array<{ row: number; text: string; start: number; end: number }> = [];
    for (const tr of rawTextRows) {
      const t = (tr.text ?? "").trim();
      if (!t) continue;
      out.push({ row: tr.row, text: t, start: cursor, end: cursor + t.length });
      cursor += t.length + 1; // +1 for the "\n" separator
    }
    // Drop the POZICIJE: list (header line + everything after) — those
    // are already shown in the math table's "Podstavka" column.
    const cutIdx = out.findIndex((seg) => headerRe.test(seg.text));
    return cutIdx === -1 ? out : out.slice(0, cutIdx);
  })();

  // Fallback when the parser didn't supply text_rows (older imports,
  // non-xlsx sources). Keep the old single-paragraph rendering with
  // highlights translated for the trimmed title prefix.
  const cleanText = (() => {
    let result = item.text;
    if (title) {
      const firstLine = result.split("\n", 1)[0];
      if (firstLine === title) {
        result = result.slice(firstLine.length).replace(/^[\s\n]+/, "");
      }
    }
    if (hasPositions) result = trimPositionsFromText(result);
    return result;
  })();
  const trimOffset = item.text.length - cleanText.length;
  const adjustedHighlights = item.highlights
    ?.map((h) => ({ ...h, start: h.start - trimOffset, end: h.end - trimOffset }))
    .filter((h) => h.start >= 0 && h.end <= cleanText.length);

  function lineHighlights(seg: { start: number; end: number }) {
    return (item.highlights ?? [])
      .filter((h) => h.start >= seg.start && h.end <= seg.end)
      .map((h) => ({ ...h, start: h.start - seg.start, end: h.end - seg.start }));
  }

  // The right column is a vertical stack so a single stavka can carry
  // multiple Lexitor findings (e.g., one card for "brand mention", another
  // for "decimal precision"). For now the API still returns one finding
  // per item — render it as the only card in the stack.
  const findings = [{
    accent,
    label,
    explanation: item.explanation,
    suggestion: item.suggestion,
    citations: item.citations,
  }];

  return (
    <div className="grid gap-4 lg:grid-cols-3 items-start">
      {/* LEFT (2/3) — STAVKA: contents from the troskovnik itself */}
      <article
        className="rounded-lg border border-brand-border bg-white p-6 lg:col-span-2 border-l-4"
        style={{ borderLeftColor: accent }}
      >
        {path.length > 0 && (
          <nav
            aria-label="Hijerarhija"
            className="text-[11px] text-muted mb-2 flex flex-wrap items-center gap-x-2 gap-y-1"
          >
            {path.map((p, idx) => (
              <span key={idx} className="inline-flex items-center gap-2">
                {idx > 0 && <span className="text-muted/50">›</span>}
                {p.label && (
                  <span className="font-mono">{p.label}</span>
                )}
                {p.title && (
                  <span className="uppercase tracking-wider">{p.title}</span>
                )}
              </span>
            ))}
          </nav>
        )}
        <header className="flex items-start justify-between gap-4 mb-3">
          <span className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted">
            Stavka
          </span>
          {rb && <span className="text-sm text-muted font-mono">{rb}</span>}
        </header>

        {title && (
          <div className="flex items-baseline gap-3 mb-3">
            <span
              className="text-[11px] text-muted font-mono shrink-0 w-8 text-right pt-2 tabular-nums"
              title="Excel red"
            >
              {titleRow ?? ""}
            </span>
            <h2 className="font-display text-2xl text-ink leading-snug max-w-prose">
              {title}
            </h2>
          </div>
        )}

        {segments.length > 0 ? (
          <div className="text-sm text-navy leading-relaxed max-w-prose space-y-1">
            {segments.map((seg, idx) => (
              <div key={`${seg.row}-${idx}`} className="flex gap-3">
                <span className="text-[11px] text-muted font-mono shrink-0 w-8 text-right pt-px tabular-nums">
                  {seg.row}
                </span>
                <span className="whitespace-pre-line">
                  <HighlightedText
                    text={seg.text}
                    highlights={lineHighlights(seg)}
                    accent={accent}
                  />
                </span>
              </div>
            ))}
          </div>
        ) : (
          cleanText && (
            <p className="text-sm text-navy leading-relaxed whitespace-pre-line max-w-prose">
              <HighlightedText
                text={cleanText}
                highlights={adjustedHighlights}
                accent={accent}
              />
            </p>
          )
        )}

        {mathRows.length > 0 && (
          <div className="mt-5 overflow-x-auto">
            <table className="text-sm w-full">
              <thead>
                <tr className="text-[11px] uppercase tracking-wider text-muted">
                  {hasExcelRow && (
                    <th style={{ width: "2rem" }} className="py-1" aria-hidden />
                  )}
                  <th
                    className={`${hasExcelRow ? "pl-3" : ""} pr-4 py-1 text-left font-medium`}
                  >
                    Podstavka
                  </th>
                  <th className="pr-4 py-1 text-left font-medium">Jed. mjere</th>
                  <th className="pr-4 py-1 text-right font-medium">Količina</th>
                  <th className="pr-4 py-1 text-right font-medium">Jed. cijena</th>
                  <th className="pr-4 py-1 text-right font-medium">Iznos</th>
                  <th className="py-1 text-right font-medium">Provjera</th>
                </tr>
              </thead>
              <tbody className="text-navy font-mono">
                {mathRows.map((row, idx) => {
                  const computed = row.computed_iznos ?? null;
                  const excelNum = toNumber(row.iznos);
                  const hasExcelValue =
                    row.iznos !== null && row.iznos !== undefined && row.iznos !== "";
                  const displayedExcel = hasExcelValue ? formatCurrency(row.iznos) : "—";
                  const isExcelMissing = !hasExcelValue && computed !== null;
                  return (
                    <tr key={idx} className="border-t border-brand-border">
                      {hasExcelRow && (
                        <td
                          style={{ width: "2rem" }}
                          className="py-1.5 text-right text-muted tabular-nums text-[11px]"
                        >
                          {typeof row.row === "number" ? row.row : ""}
                        </td>
                      )}
                      <td
                        className={`${hasExcelRow ? "pl-3" : ""} pr-4 py-1.5 font-sans`}
                      >
                        {row.position_label || (
                          <span className="text-muted italic">—</span>
                        )}
                      </td>
                      <td className="pr-4 py-1.5">{row.jm || "—"}</td>
                      <td className="pr-4 py-1.5 text-right">{formatNumber(row.kol)}</td>
                      <td className="pr-4 py-1.5 text-right">{formatCurrency(row.cijena)}</td>
                      <td
                        className={`pr-4 py-1.5 text-right ${
                          isExcelMissing ? "italic text-muted" : ""
                        }`}
                      >
                        {isExcelMissing ? formatCurrency(computed) : displayedExcel}
                      </td>
                      <td className="py-1.5 text-right">
                        <ProvjeraCell
                          isFormula={!!row.iznos_is_formula}
                          excel={excelNum}
                          computed={computed}
                          hasExcelValue={hasExcelValue}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </article>

      {/* RIGHT (1/3) — vertical stack of ANALIZA cards (one per finding) */}
      <div className="lg:col-span-1 flex flex-col gap-3">
        {findings.map((f, idx) => (
          <FindingCard key={idx} {...f} />
        ))}
      </div>
    </div>
  );
}

function FindingCard({
  accent,
  label,
  explanation,
  suggestion,
  citations,
}: {
  accent: string;
  label: string;
  explanation: string | null;
  suggestion: string | null;
  citations: CitationPublic[];
}) {
  return (
    <article
      className="rounded-lg border border-brand-border bg-white p-6 border-l-4"
      style={{ borderLeftColor: accent }}
    >
      <header className="flex items-start justify-between gap-4 mb-4">
        <span
          className="inline-flex items-center gap-2 text-xs uppercase tracking-wider font-semibold"
          style={{ color: accent }}
        >
          <span
            aria-hidden
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: accent }}
          />
          {label}
        </span>
        <span className="text-[11px] uppercase tracking-[0.18em] font-medium text-muted">
          Lexitor analiza
        </span>
      </header>

      {explanation && (
        <Section accent={accent} title="Zašto">
          {explanation}
        </Section>
      )}

      {suggestion && (
        <Section accent={accent} title="Predloženi ispravak">
          {suggestion}
        </Section>
      )}

      {!explanation && !suggestion && (
        <p className="text-sm text-muted italic">
          Sustav nije našao problem u ovoj stavci.
        </p>
      )}

      {citations.length > 0 && (
        <>
          <hr className="my-5 border-brand-border" />
          <ul className="space-y-1 text-xs font-mono text-muted">
            {citations.map((c) => (
              <li key={c.id}>
                <span className="text-navy">
                  {SOURCE_LABEL[c.source] ?? c.source.toUpperCase()} {c.reference}
                </span>
                {c.url && (
                  <>
                    {" · "}
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-signal hover:underline"
                    >
                      otvori izvor
                    </a>
                  </>
                )}
              </li>
            ))}
          </ul>
        </>
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
    </article>
  );
}

function Section({
  accent,
  title,
  children,
}: {
  accent: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mb-4">
      <h3
        className="text-[11px] uppercase tracking-[0.18em] font-semibold mb-1.5"
        style={{ color: accent }}
      >
        {title}
      </h3>
      <p className="text-sm text-navy leading-relaxed">{children}</p>
    </section>
  );
}
