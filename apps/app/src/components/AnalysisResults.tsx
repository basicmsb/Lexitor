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

function ItemDetail({ item }: { item: AnalysisItemPublic }) {
  const accent = statusAccent(item.status);
  const label = statusLabel(item.status);
  const { rb, title } = splitLabel(item.label);
  const mathRows = getMathRows(item);
  const hasPositions = rowsHavePositions(mathRows);

  // Body text shown in the callout. If the title is repeated as the first
  // line of `text`, drop it so we don't show the same string twice.
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

  // Translate highlight offsets when we trimmed the title prefix
  const trimOffset = item.text.length - cleanText.length;
  const adjustedHighlights = item.highlights
    ?.map((h) => ({ ...h, start: h.start - trimOffset, end: h.end - trimOffset }))
    .filter((h) => h.start >= 0 && h.end <= cleanText.length);

  return (
    <div className="grid gap-4 lg:grid-cols-3 items-start">
      {/* LEFT (2/3) — STAVKA: contents from the troskovnik itself */}
      <section className="rounded-lg border border-brand-border bg-white p-6 lg:col-span-2">
        <header className="flex items-start justify-between gap-4 mb-3">
          <span className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted">
            Stavka
          </span>
          {rb && <span className="text-sm text-muted font-mono">{rb}</span>}
        </header>

        {title && (
          <h2 className="font-display text-2xl text-ink leading-snug mb-3 max-w-prose">
            {title}
          </h2>
        )}

        {cleanText && (
          <p className="text-sm text-navy leading-relaxed whitespace-pre-line max-w-prose">
            <HighlightedText
              text={cleanText}
              highlights={adjustedHighlights}
              accent={accent}
            />
          </p>
        )}

        {mathRows.length > 0 && (
          <div className="mt-5 overflow-x-auto">
            <table className="text-sm w-full">
              <thead>
                <tr className="text-[11px] uppercase tracking-wider text-muted">
                  {hasPositions && (
                    <th className="pr-4 py-1 text-left font-medium">Pozicija</th>
                  )}
                  <th className="pr-4 py-1 text-left font-medium">Jed. mjere</th>
                  <th className="pr-4 py-1 text-right font-medium">Količina</th>
                  <th className="pr-4 py-1 text-right font-medium">Jed. cijena</th>
                  <th className="pr-4 py-1 text-right font-medium">Iznos</th>
                  <th className="py-1 text-left font-medium">Provjera</th>
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
                      {hasPositions && (
                        <td className="pr-4 py-1.5 font-sans">
                          {row.position_label || (
                            <span className="text-muted italic">—</span>
                          )}
                        </td>
                      )}
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
                      <td className="py-1.5">
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
      </section>

      {/* RIGHT (1/3) — ANALIZA: lexitor commentary, status accent on the left */}
      <section
        className="rounded-lg border border-brand-border bg-white p-6 border-l-4 lg:col-span-1"
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

        {item.explanation && (
          <Section accent={accent} title="Zašto">
            {item.explanation}
          </Section>
        )}

        {item.suggestion && (
          <Section accent={accent} title="Predloženi ispravak">
            {item.suggestion}
          </Section>
        )}

        {!item.explanation && !item.suggestion && (
          <p className="text-sm text-muted italic">
            Sustav nije našao problem u ovoj stavci.
          </p>
        )}

        {item.citations.length > 0 && (
          <>
            <hr className="my-5 border-brand-border" />
            <ul className="space-y-1 text-xs font-mono text-muted">
              {item.citations.map((c) => (
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
      </section>
    </div>
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
