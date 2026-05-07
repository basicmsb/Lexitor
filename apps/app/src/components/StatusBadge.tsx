import type { AnalysisItemStatus } from "@/lib/types";

const STYLES: Record<AnalysisItemStatus, { label: string; bg: string; text: string; dot: string }> = {
  ok: {
    label: "Usklađeno",
    bg: "bg-green-50 border-green-200",
    text: "text-green-800",
    dot: "bg-status-ok",
  },
  warn: {
    label: "Upozorenje",
    bg: "bg-yellow-50 border-yellow-200",
    text: "text-yellow-800",
    dot: "bg-status-warn",
  },
  fail: {
    label: "Kršenje",
    bg: "bg-red-50 border-red-200",
    text: "text-red-800",
    dot: "bg-status-fail",
  },
  neutral: {
    label: "Nije provjereno",
    bg: "bg-slate-50 border-slate-200",
    text: "text-slate-700",
    dot: "bg-status-neutral",
  },
  accepted: {
    label: "Prihvaćen rizik",
    bg: "bg-blue-50 border-blue-200",
    text: "text-blue-800",
    dot: "bg-status-accepted",
  },
  uncertain: {
    label: "Pravna nesigurnost",
    bg: "bg-purple-50 border-purple-200",
    text: "text-purple-800",
    dot: "bg-status-uncertain",
  },
};

export function StatusDot({ status }: { status: AnalysisItemStatus }) {
  return <span className={`inline-block w-2 h-2 rounded-full ${STYLES[status].dot}`} />;
}

export function StatusBadge({ status }: { status: AnalysisItemStatus }) {
  const s = STYLES[status];
  return (
    <span
      className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-md border text-xs font-medium ${s.bg} ${s.text}`}
    >
      <span className={`w-2 h-2 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  );
}

export function statusLabel(status: AnalysisItemStatus): string {
  return STYLES[status].label;
}
