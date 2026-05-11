"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import type {
  ClaimSample,
  ClaimType,
  SpotcheckBatch,
  SpotcheckStats,
  SpotcheckVerdict,
} from "@/lib/types";

const CLAIM_TYPES: { value: ClaimType; label: string }[] = [
  { value: "brand_lock", label: "Brand-lock" },
  { value: "kratki_rok", label: "Kratki rok" },
  { value: "vague_kriterij", label: "Vague kriterij" },
  { value: "diskrim_uvjeti", label: "Diskriminatorni uvjeti" },
  { value: "neprecizna_specifikacija", label: "Neprecizna specifikacija" },
  { value: "neispravna_grupacija", label: "Neispravna grupacija" },
  { value: "kriterij_odabira", label: "Kriterij odabira" },
  { value: "ocjena_ponude", label: "Ocjena ponude" },
  { value: "espd_dokazi", label: "ESPD / dokazi" },
  { value: "jamstvo", label: "Jamstvo" },
  { value: "trosak_postupka", label: "Trošak postupka" },
  { value: "ostalo", label: "Ostalo" },
];

const VERDICT_LABEL = (cat: ClaimType): string => {
  return CLAIM_TYPES.find((t) => t.value === cat)?.label ?? cat;
};

/**
 * Parsiraj reference na članke ZJN-a iz teksta i vrati segmente (text + link?).
 * Primjer ulaza: "ZJN 2016 čl. 280 st. 4, čl. 290 st. 1"
 * Linkamo prepoznate "čl. N" na našu pretragu prakse.
 */
function parseArticleRefs(text: string): { text: string; href?: string }[] {
  // Match "čl. NNN" (sa eventualnim "st. M")
  const regex = /(čl(?:ank[au]?)?\.?\s*\d+\.?(?:\s*st(?:av(?:ak|ka)?)?\.?\s*\d+\.?)?)/gi;
  const segments: { text: string; href?: string }[] = [];
  let lastEnd = 0;
  for (const match of text.matchAll(regex)) {
    if (match.index !== undefined && match.index > lastEnd) {
      segments.push({ text: text.slice(lastEnd, match.index) });
    }
    segments.push({
      text: match[0],
      href: `/pretraga?q=${encodeURIComponent(`ZJN ${match[0]}`)}`,
    });
    lastEnd = (match.index ?? 0) + match[0].length;
  }
  if (lastEnd < text.length) {
    segments.push({ text: text.slice(lastEnd) });
  }
  return segments.length ? segments : [{ text }];
}


export default function DkomSpotcheckPage() {
  const { me } = useAuth();
  const [batch, setBatch] = useState<SpotcheckBatch | null>(null);
  const [index, setIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [stats, setStats] = useState<SpotcheckStats | null>(null);
  const [batchSize, setBatchSize] = useState(50);
  const [selectedCategory, setSelectedCategory] = useState<ClaimType | null>(null);

  const loadBatch = useCallback(async (size: number) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getSpotcheckBatch(size, 42, true);
      setBatch(data);
      setIndex(0);
      setSelectedCategory(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Greška pri dohvatu.");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const s = await api.getSpotcheckStats();
      setStats(s);
    } catch {
      // tiho — stats nije kritično
    }
  }, []);

  useEffect(() => {
    if (me?.user?.is_super_admin) {
      void loadBatch(batchSize);
      void loadStats();
    }
  }, [me, loadBatch, loadStats, batchSize]);

  const submitVerdict = useCallback(
    async (verdict: SpotcheckVerdict, correctCategory?: ClaimType) => {
      if (!batch || !batch.items[index]) return;
      const claim = batch.items[index];
      setSubmitting(true);
      try {
        await api.submitSpotcheckFeedback(claim.id, verdict, correctCategory);
        setSelectedCategory(null);
        if (index + 1 >= batch.items.length) {
          await loadStats();
        } else {
          setIndex((i) => i + 1);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Greška pri spremanju.");
      } finally {
        setSubmitting(false);
      }
    },
    [batch, index, loadStats],
  );

  // Submit s aktualnim selected category — odlučuje correct/wrong
  const submitConfirm = useCallback(() => {
    if (!batch || !batch.items[index]) return;
    const claim = batch.items[index];
    const currentCat = selectedCategory ?? claim.llm_category;
    if (currentCat === claim.llm_category) {
      void submitVerdict("correct");
    } else {
      void submitVerdict("wrong", currentCat);
    }
  }, [batch, index, selectedCategory, submitVerdict]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (submitting || !batch) return;
      // Ne aktiviraj shortcut-e ako je fokus na input/select elementu
      const target = e.target as HTMLElement;
      if (target?.tagName === "SELECT" || target?.tagName === "INPUT") return;
      if (e.key === "Enter" || e.key === "y" || e.key === "Y") submitConfirm();
      else if (e.key === "?" || e.key === "u" || e.key === "U") void submitVerdict("uncertain");
      else if (e.key === "s" || e.key === "S" || e.key === "Escape")
        void submitVerdict("skip");
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [submitConfirm, submitVerdict, submitting, batch]);

  if (!me) return <p className="text-muted">Učitavam…</p>;
  if (!me.user.is_super_admin) {
    return (
      <div className="max-w-2xl">
        <h1 className="font-display text-2xl text-ink mb-3">Pristup ograničen</h1>
        <p className="text-muted">
          DKOM spot-check je dostupan samo super-administratorima.
        </p>
      </div>
    );
  }

  if (loading) return <p className="text-sm text-muted">Učitavam batch…</p>;
  if (error)
    return (
      <p className="text-sm bg-status-fail/10 border border-status-fail/30 text-status-fail rounded-md px-3 py-2">
        {error}
      </p>
    );

  if (!batch || batch.items.length === 0) {
    return (
      <div className="max-w-2xl space-y-6">
        <h1 className="font-display text-2xl text-ink">DKOM spot-check</h1>
        <p className="text-muted">
          Nema više claim-ova za pregled — svi {batch?.total_claims ?? "?"} su već
          ocjenjeni.
        </p>
        {stats && <StatsView stats={stats} />}
      </div>
    );
  }

  const completed = index >= batch.items.length;
  if (completed) {
    return (
      <div className="max-w-3xl space-y-6">
        <h1 className="font-display text-2xl text-ink">Batch završen 🎉</h1>
        <p className="text-muted">
          Pregledao si {batch.items.length} claim-ova. Učitaj novi batch ili
          pogledaj statistiku.
        </p>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => void loadBatch(batchSize)}
            className="rounded-md bg-ink px-5 py-2.5 text-sm font-medium text-surface hover:bg-navy transition"
          >
            Novi batch ({batchSize})
          </button>
          <select
            value={batchSize}
            onChange={(e) => setBatchSize(Number(e.target.value))}
            className="rounded-md border border-brand-border bg-surface-2 px-3 py-2.5 text-sm text-ink"
          >
            <option value={20}>20 sample</option>
            <option value={50}>50 sample</option>
            <option value={100}>100 sample</option>
          </select>
        </div>
        {stats && <StatsView stats={stats} />}
      </div>
    );
  }

  const claim = batch.items[index];
  const progress = ((index / batch.items.length) * 100).toFixed(0);

  return (
    <div className="max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl text-ink">DKOM spot-check</h1>
          <p className="text-sm text-muted">
            {index + 1} / {batch.items.length} · ukupno claim-ova u korpusu:{" "}
            {batch.total_claims} · prije pregledanih: {batch.already_reviewed_ids.length}
          </p>
        </div>
        <div className="text-right">
          {stats?.accuracy != null && (
            <p className="text-sm">
              Dosadašnja accuracy:{" "}
              <span className="font-mono text-ink">{(stats.accuracy * 100).toFixed(0)}%</span>
            </p>
          )}
          <p className="text-xs text-muted">{stats?.total_feedback ?? 0} pregledanih</p>
        </div>
      </div>

      {/* Instrukcija — što točno ocjenjujem */}
      <div className="rounded-lg border border-signal/30 bg-signal/5 p-4">
        <p className="text-sm text-ink">
          <span className="font-semibold">Što ocjenjujem:</span> je li{" "}
          <span className="text-gold font-medium">LLM kategorija</span> točan opis{" "}
          <span className="text-navy font-medium">Argumenta žalitelja</span>?
        </p>
        <p className="text-xs text-muted mt-1.5 leading-relaxed">
          DKOM obrazloženje i verdikt (UVAZEN/ODBIJEN) je samo <em>kontekst</em>{" "}
          — ne ocjenjuješ DKOM-ovu odluku, samo LLM-ovu klasifikaciju. Ako misliš
          da druga kategorija bolje opisuje argument → odaberi „Pogrešno”.
        </p>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-surface-2 rounded-full overflow-hidden">
        <div
          className="h-full bg-signal transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Claim card */}
      <article className="rounded-lg border border-brand-border bg-surface-2 p-6 space-y-4">
        <header className="flex items-start justify-between gap-4 pb-4 border-b border-brand-border">
          <div className="min-w-0 flex-1">
            <p className="font-mono text-xs mb-1">
              {claim.pdf_url ? (
                <a
                  href={claim.pdf_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-signal hover:text-ink hover:underline transition"
                  title="Otvori DKOM PDF u novom tabu"
                >
                  {claim.klasa} ↗
                </a>
              ) : (
                <span className="text-muted">{claim.klasa}</span>
              )}
            </p>
            <p className="text-sm text-ink">{claim.predmet}</p>
          </div>
          <div className="text-right shrink-0">
            <label className="block text-[10px] uppercase tracking-[0.18em] text-muted mb-1">
              Kategorija (klikni za promjenu)
            </label>
            <select
              value={selectedCategory ?? claim.llm_category}
              onChange={(e) => setSelectedCategory(e.target.value as ClaimType)}
              disabled={submitting}
              className={`rounded-md px-3 py-1.5 text-sm font-semibold transition border ${
                selectedCategory && selectedCategory !== claim.llm_category
                  ? "bg-status-fail/15 text-status-fail border-status-fail/40"
                  : "bg-gold/15 text-gold border-gold/30"
              }`}
            >
              {CLAIM_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
            {selectedCategory && selectedCategory !== claim.llm_category && (
              <p className="text-[10px] text-status-fail mt-1">
                Promijenjeno s „{VERDICT_LABEL(claim.llm_category)}”
              </p>
            )}
          </div>
        </header>

        <div>
          <p className="text-[10px] uppercase tracking-[0.18em] font-semibold text-muted mb-2">
            💬 Argument žalitelja
          </p>
          <p className="text-sm text-navy leading-relaxed whitespace-pre-line">
            {claim.argument_zalitelja}
          </p>
        </div>

        {claim.obrana_narucitelja && (
          <div>
            <p className="text-[10px] uppercase tracking-[0.18em] font-semibold text-muted mb-2">
              🛡 Obrana naručitelja
            </p>
            <p className="text-sm text-navy leading-relaxed whitespace-pre-line">
              {claim.obrana_narucitelja}
            </p>
          </div>
        )}

        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-[10px] uppercase tracking-[0.18em] font-semibold text-muted">
              ⚖ DKOM obrazloženje
            </p>
            <span
              className={`text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded ${
                claim.dkom_verdict === "uvazen"
                  ? "bg-status-ok/15 text-status-ok"
                  : claim.dkom_verdict === "odbijen"
                  ? "bg-status-fail/15 text-status-fail"
                  : "bg-muted/15 text-muted"
              }`}
            >
              {claim.dkom_verdict}
            </span>
          </div>
          <p className="text-sm text-navy leading-relaxed whitespace-pre-line">
            {claim.dkom_obrazlozenje}
          </p>
        </div>

        {claim.violated_article_claimed && (
          <p className="text-xs text-muted">
            📖 Citirani članak:{" "}
            <span className="font-mono">
              {parseArticleRefs(claim.violated_article_claimed).map((seg, i) =>
                seg.href ? (
                  <a
                    key={i}
                    href={seg.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-signal hover:text-ink hover:underline transition"
                    title="Otvori u pretrazi prakse"
                  >
                    {seg.text}
                  </a>
                ) : (
                  <span key={i}>{seg.text}</span>
                ),
              )}
            </span>
          </p>
        )}
      </article>

      {/* Verdict buttons — 3 opcije (kategorija je već dropdown) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <button
          type="button"
          disabled={submitting}
          onClick={() => submitConfirm()}
          className={`rounded-md px-4 py-3 font-medium transition disabled:opacity-50 ${
            selectedCategory && selectedCategory !== claim.llm_category
              ? "bg-status-fail text-surface hover:bg-status-fail/90"
              : "bg-status-ok text-surface hover:bg-status-ok/90"
          }`}
        >
          <span className="block text-sm">
            {selectedCategory && selectedCategory !== claim.llm_category
              ? "✓ Potvrdi promjenu"
              : "✓ Točno"}
          </span>
          <span className="text-[10px] opacity-70">[Y] / [Enter]</span>
        </button>
        <button
          type="button"
          disabled={submitting}
          onClick={() => void submitVerdict("uncertain")}
          className="rounded-md bg-gold px-4 py-3 text-ink font-medium hover:bg-gold/90 transition disabled:opacity-50"
        >
          <span className="block text-sm">? Nesigurno</span>
          <span className="text-[10px] opacity-70">[U]</span>
        </button>
        <button
          type="button"
          disabled={submitting}
          onClick={() => void submitVerdict("skip")}
          className="rounded-md border border-brand-border px-4 py-3 text-navy font-medium hover:border-ink transition disabled:opacity-50"
        >
          <span className="block text-sm">→ Skip</span>
          <span className="text-[10px] opacity-70">[S]</span>
        </button>
      </div>
      <p className="text-xs text-muted text-center">
        Promijeni kategoriju u dropdown-u gore, pa pritisni „Potvrdi promjenu”.
        Ili ostavi i pritisni „Točno”.
      </p>

      {stats && stats.total_feedback > 0 && (
        <details className="rounded-lg border border-brand-border bg-surface-2/40 p-4">
          <summary className="cursor-pointer text-sm font-medium text-ink">
            Statistika do sada (klikni za detalje)
          </summary>
          <div className="mt-4">
            <StatsView stats={stats} />
          </div>
        </details>
      )}
    </div>
  );
}

function StatsView({ stats }: { stats: SpotcheckStats }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="rounded-md border border-brand-border bg-surface p-3 text-center">
          <p className="text-[10px] uppercase tracking-wider text-muted mb-1">Total</p>
          <p className="font-display text-2xl text-ink">{stats.total_feedback}</p>
        </div>
        <div className="rounded-md border border-status-ok/30 bg-status-ok/5 p-3 text-center">
          <p className="text-[10px] uppercase tracking-wider text-status-ok mb-1">Točno</p>
          <p className="font-display text-2xl text-status-ok">
            {stats.by_verdict.correct ?? 0}
          </p>
        </div>
        <div className="rounded-md border border-status-fail/30 bg-status-fail/5 p-3 text-center">
          <p className="text-[10px] uppercase tracking-wider text-status-fail mb-1">
            Pogrešno
          </p>
          <p className="font-display text-2xl text-status-fail">
            {stats.by_verdict.wrong ?? 0}
          </p>
        </div>
        <div className="rounded-md border border-brand-border bg-surface p-3 text-center">
          <p className="text-[10px] uppercase tracking-wider text-muted mb-1">Accuracy</p>
          <p className="font-display text-2xl text-ink">
            {stats.accuracy != null ? `${(stats.accuracy * 100).toFixed(0)}%` : "—"}
          </p>
        </div>
      </div>

      {Object.keys(stats.by_category_accuracy).length > 0 && (
        <div>
          <h4 className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-2">
            Po kategoriji
          </h4>
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-brand-border">
                <th className="text-left py-2 text-muted text-xs">Kategorija</th>
                <th className="text-right py-2 text-muted text-xs">Točno</th>
                <th className="text-right py-2 text-muted text-xs">Pogrešno</th>
                <th className="text-right py-2 text-muted text-xs">Acc</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(stats.by_category_accuracy)
                .sort(([, a], [, b]) => b.correct + b.wrong - (a.correct + a.wrong))
                .map(([cat, s]) => (
                  <tr key={cat} className="border-b border-brand-border/40">
                    <td className="py-2 text-navy">{VERDICT_LABEL(cat as ClaimType)}</td>
                    <td className="py-2 text-right text-status-ok">{s.correct}</td>
                    <td className="py-2 text-right text-status-fail">{s.wrong}</td>
                    <td className="py-2 text-right font-mono text-ink">
                      {(s.accuracy * 100).toFixed(0)}%
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}

      {stats.miscls.length > 0 && (
        <div>
          <h4 className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-2">
            Najčešći miss-mapping-i
          </h4>
          <ul className="space-y-1.5 text-sm">
            {stats.miscls.slice(0, 10).map((m, i) => (
              <li key={i} className="text-navy">
                <span className="text-status-fail">{VERDICT_LABEL(m.llm_said as ClaimType)}</span>{" "}
                → <span className="text-status-ok">{VERDICT_LABEL(m.correct as ClaimType)}</span>{" "}
                <span className="text-muted">({m.count}×)</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
