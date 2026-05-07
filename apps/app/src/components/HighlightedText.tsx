"use client";

import type { ReactNode } from "react";

import type { HighlightSpan } from "@/lib/types";

interface Props {
  text: string;
  highlights?: HighlightSpan[] | null;
  /** Hex colour of the surrounding status accent. */
  accent: string;
  className?: string;
}

/** Renders `text` with `<mark>` ranges for each highlight. Uses the same
 *  status accent colour as the surrounding card so the eye reads them
 *  as part of one signal. Whitespace inside the text is preserved
 *  (the parent should set `whitespace-pre-line`). */
export function HighlightedText({ text, highlights, accent, className }: Props) {
  if (!highlights || highlights.length === 0) {
    return <span className={className}>{text}</span>;
  }

  const sorted = [...highlights]
    .filter((h) => h.start < h.end && h.end <= text.length)
    .sort((a, b) => a.start - b.start);

  const parts: ReactNode[] = [];
  let cursor = 0;
  for (let i = 0; i < sorted.length; i++) {
    const h = sorted[i];
    if (h.start < cursor) continue; // skip overlaps
    if (h.start > cursor) parts.push(<span key={`t-${cursor}`}>{text.slice(cursor, h.start)}</span>);
    parts.push(
      <mark
        key={`h-${h.start}`}
        title={h.label}
        className="rounded px-[2px] -mx-[2px]"
        style={{ backgroundColor: `${accent}26`, color: accent, fontWeight: 500 }}
      >
        {text.slice(h.start, h.end)}
      </mark>,
    );
    cursor = h.end;
  }
  if (cursor < text.length) {
    parts.push(<span key={`t-end`}>{text.slice(cursor)}</span>);
  }
  return <span className={className}>{parts}</span>;
}
