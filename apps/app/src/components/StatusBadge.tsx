import type { AnalysisItemStatus } from "@/lib/types";

const STYLES: Record<
  AnalysisItemStatus,
  { label: string; description: string; bgClass: string; textClass: string; dotHex: string }
> = {
  ok: {
    label: "Usklađeno",
    description: "Sustav nije našao problem.",
    bgClass: "bg-status-ok/10 border-status-ok/30",
    textClass: "text-[#2C5832]",
    dotHex: "#3F7D45",
  },
  warn: {
    label: "Upozorenje",
    description: "Mogući problem, vrijedi pregled.",
    bgClass: "bg-[#A87F2E]/10 border-[#A87F2E]/30",
    textClass: "text-gold",
    dotHex: "#A87F2E",
  },
  fail: {
    label: "Kršenje",
    description: "Visoka vjerojatnost kršenja ZJN-a.",
    bgClass: "bg-status-fail/10 border-status-fail/30",
    textClass: "text-status-fail",
    dotHex: "#A8392B",
  },
  uncertain: {
    label: "Pravna nesigurnost",
    description: "Suprotni presedani DKOM/VUS.",
    bgClass: "bg-[#6B4A8E]/10 border-[#6B4A8E]/30",
    textClass: "text-[#503770]",
    dotHex: "#6B4A8E",
  },
  accepted: {
    label: "Prihvaćen rizik",
    description: "Korisnik svjesno prihvatio.",
    bgClass: "bg-[#2A6DB0]/10 border-[#2A6DB0]/30",
    textClass: "text-[#1F5083]",
    dotHex: "#2A6DB0",
  },
  neutral: {
    label: "Nije provjereno",
    description: "Nije bilo u opsegu analize.",
    bgClass: "bg-[#7B7363]/10 border-[#7B7363]/30",
    textClass: "text-[#5A5447]",
    dotHex: "#7B7363",
  },
};

export function StatusDot({ status }: { status: AnalysisItemStatus }) {
  const s = STYLES[status];
  return (
    <span
      aria-hidden
      // Explicit min-width / shrink-0 prevents the flex parent from
      // squashing the dot into a vertical bar when sibling text grows.
      // 10×10 px (w-2.5 h-2.5) renders as a stable circle across the
      // colour palette — at 8×8 the anti-aliasing on saturated reds /
      // oranges read as a thin rectangle next to the muted green.
      className="inline-block w-2.5 h-2.5 min-w-[0.625rem] shrink-0 rounded-full"
      style={{ backgroundColor: s.dotHex }}
    />
  );
}

export function StatusBadge({ status }: { status: AnalysisItemStatus }) {
  const s = STYLES[status];
  return (
    <span
      className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-md border text-xs font-medium ${s.bgClass} ${s.textClass}`}
      title={s.description}
    >
      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: s.dotHex }} />
      {s.label}
    </span>
  );
}

export function statusLabel(status: AnalysisItemStatus): string {
  return STYLES[status].label;
}

export function statusDescription(status: AnalysisItemStatus): string {
  return STYLES[status].description;
}

export function statusAccent(status: AnalysisItemStatus): string {
  return STYLES[status].dotHex;
}
