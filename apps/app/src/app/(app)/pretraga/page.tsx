"use client";

import { useState, type FormEvent } from "react";

import { api } from "@/lib/api";
import type { KnowledgeHit } from "@/lib/types";

export default function PretragaPage() {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<KnowledgeHit[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.searchKnowledge(query, { limit: 10 });
      setHits(data.hits);
      setSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pretraga nije uspjela.");
      setHits([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <h1 className="font-display text-3xl text-ink mb-2">Pretraga prakse</h1>
        <p className="text-muted">
          Semantička pretraga DKOM odluka. Upiši pojam ili pitanje, sustav vraća
          najsličnije pasuse iz pravne baze.
        </p>
      </div>

      <form onSubmit={onSubmit} className="flex gap-2 mb-6">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder='npr. "ili jednakovrijedno", "diskriminatorne specifikacije"'
          className="flex-1 rounded-md border border-brand-border bg-white px-4 py-2.5 outline-none focus:border-signal focus:ring-2 focus:ring-signal/20 transition"
        />
        <button
          type="submit"
          disabled={loading || query.trim().length < 2}
          className="rounded-md bg-ink text-surface px-5 py-2.5 font-medium hover:bg-navy transition disabled:opacity-50"
        >
          {loading ? "Tražim…" : "Pretraži"}
        </button>
      </form>

      {error && (
        <p className="text-sm bg-[#A8392B]/10 border border-[#A8392B]/30 text-[#7C2A21] rounded-md px-3 py-2 mb-4">
          {error}
        </p>
      )}

      {searched && hits.length === 0 && !loading && !error && (
        <p className="text-sm text-muted italic">Nema rezultata.</p>
      )}

      <ul className="space-y-3">
        {hits.map((h, idx) => (
          <li
            key={`${h.klasa}-${h.chunk_index}-${idx}`}
            className="rounded-lg border border-brand-border bg-white p-5"
          >
            <div className="flex items-start justify-between gap-4 mb-2">
              <div className="min-w-0">
                <p className="font-mono text-xs uppercase tracking-wider text-navy">
                  DKOM · {h.klasa}
                </p>
                <p className="font-serif text-ink mt-1 leading-snug">{h.predmet}</p>
              </div>
              <div className="text-right shrink-0">
                <span className="text-xs text-muted">
                  relevantnost {(h.score * 100).toFixed(0)}%
                </span>
                {h.odluka_datum && (
                  <p className="text-xs text-muted mt-0.5">{h.odluka_datum}</p>
                )}
              </div>
            </div>

            <p className="text-sm text-navy leading-relaxed mt-3 whitespace-pre-line">
              {h.text}
            </p>

            <div className="mt-4 flex items-center gap-4 text-xs text-muted">
              {h.page !== null && <span>Stranica {h.page}</span>}
              {h.pdf_url && (
                <a
                  href={h.pdf_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-signal hover:underline"
                >
                  Otvori PDF →
                </a>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
