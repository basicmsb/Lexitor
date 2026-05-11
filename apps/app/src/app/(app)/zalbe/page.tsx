"use client";

import { useCallback, useState, type FormEvent } from "react";

import { api } from "@/lib/api";
import type {
  ClaimType,
  SimilarPrecedent,
  ZalbeAnalyzeResponse,
  ZalbeClaimType,
} from "@/lib/types";

const CLAIM_TYPE_LABELS: Record<string, string> = {
  auto: "Auto-detekcija",
  brand_lock: "Brand-lock",
  kratki_rok: "Kratki rok",
  vague_kriterij: "Vague kriterij",
  diskrim_uvjeti: "Diskriminatorni uvjeti",
  neprecizna_specifikacija: "Neprecizna specifikacija",
  neispravna_grupacija: "Neispravna grupacija",
  kriterij_odabira: "Kriterij odabira",
  ocjena_ponude: "Ocjena ponude",
  espd_dokazi: "ESPD / dokazi",
  jamstvo: "Jamstvo",
  trosak_postupka: "Trošak postupka",
  ostalo: "Ostalo",
};

const VERDICT_COLORS: Record<string, string> = {
  uvazen: "bg-status-ok/15 text-status-ok border-status-ok/30",
  djelomicno_uvazen: "bg-gold/15 text-gold border-gold/30",
  odbijen: "bg-status-fail/15 text-status-fail border-status-fail/30",
  ne_razmatra: "bg-muted/15 text-muted border-muted/30",
};

export default function ZalbePage() {
  const [argument, setArgument] = useState("");
  const [claimType, setClaimType] = useState<ZalbeClaimType>("auto");
  const [vijeceText, setVijeceText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ZalbeAnalyzeResponse | null>(null);

  const onSubmit = useCallback(async (e: FormEvent) => {
    e.preventDefault();
    if (argument.trim().length < 20) {
      setError("Argument mora imati barem 20 znakova.");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const members = vijeceText
        .split(/[,;\n]/)
        .map((s) => s.trim())
        .filter((s) => s.length > 2);
      const res = await api.analyzeZalba({
        argument,
        claim_type: claimType,
        vijece_members: members.length > 0 ? members : undefined,
        limit: 10,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analiza nije uspjela.");
    } finally {
      setLoading(false);
    }
  }, [argument, claimType, vijeceText]);

  return (
    <div className="max-w-5xl space-y-6">
      <div>
        <h1 className="font-display text-3xl text-ink mb-2">Žalbe asistent</h1>
        <p className="text-muted">
          Unesi argument koji namjeravaš iznijeti u žalbi. Sustav pretražuje
          <strong className="text-ink"> 2287 DKOM claim-ova</strong> i procjenjuje
          šansu za uvaženje na temelju povijesnih presedana.
        </p>
      </div>

      {/* FORMA */}
      <form onSubmit={onSubmit} className="space-y-4 rounded-lg border border-brand-border bg-surface-2 p-5">
        <div>
          <label htmlFor="argument" className="block text-sm font-medium text-ink mb-2">
            Argument žalitelja
          </label>
          <textarea
            id="argument"
            value={argument}
            onChange={(e) => setArgument(e.target.value)}
            rows={6}
            placeholder="Primjer: Naručitelj je u stavkama troškovnika uputio na konkretnu marku „Sika 300 PP” bez navođenja kriterija jednakovrijednosti..."
            className="w-full rounded-md border border-brand-border bg-surface px-3 py-2 text-sm text-navy placeholder:text-muted/70 focus:outline-none focus:border-signal transition"
          />
          <p className="text-[11px] text-muted mt-1">
            Min. 20, max. 5000 znakova. {argument.length} / 5000.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="ctype" className="block text-sm font-medium text-ink mb-2">
              Tip povrede
            </label>
            <select
              id="ctype"
              value={claimType}
              onChange={(e) => setClaimType(e.target.value as ZalbeClaimType)}
              className="w-full rounded-md border border-brand-border bg-surface px-3 py-2 text-sm text-navy"
            >
              {Object.entries(CLAIM_TYPE_LABELS).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
            <p className="text-[11px] text-muted mt-1">
              „Auto-detekcija” — sustav sam odredi tip iz teksta
            </p>
          </div>

          <div>
            <label htmlFor="vijece" className="block text-sm font-medium text-ink mb-2">
              Sastav vijeća (opcionalno)
            </label>
            <input
              id="vijece"
              type="text"
              value={vijeceText}
              onChange={(e) => setVijeceText(e.target.value)}
              placeholder="Antolković, Jukić, Lozo"
              className="w-full rounded-md border border-brand-border bg-surface px-3 py-2 text-sm text-navy placeholder:text-muted/70"
            />
            <p className="text-[11px] text-muted mt-1">
              Imena članova razdvojena zarezom — dodaje per-vijeće rate
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={loading || argument.trim().length < 20}
            className="rounded-md bg-ink text-surface px-6 py-2.5 font-medium hover:bg-navy transition disabled:opacity-50"
          >
            {loading ? "Analiziram…" : "Analiziraj argument"}
          </button>
          {error && (
            <p className="text-sm text-status-fail">{error}</p>
          )}
        </div>
      </form>

      {/* REZULTATI */}
      {result && <ZalbeResults result={result} />}
    </div>
  );
}


function ZalbeResults({ result }: { result: ZalbeAnalyzeResponse }) {
  const { prediction, similar_precedents } = result;
  const successPercent = (prediction.success_rate * 100).toFixed(0);

  // Color logic: ≥60% green, 30-59% gold, <30% red
  const rateColor =
    prediction.success_rate >= 0.6
      ? "text-status-ok border-status-ok bg-status-ok/5"
      : prediction.success_rate >= 0.3
        ? "text-gold border-gold bg-gold/5"
        : "text-status-fail border-status-fail bg-status-fail/5";

  return (
    <div className="space-y-5">
      {/* PREDIKCIJA */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className={`rounded-lg border-2 p-5 ${rateColor}`}>
          <p className="text-[11px] uppercase tracking-[0.18em] font-semibold mb-2">
            Predikcija
          </p>
          <p className="font-display text-5xl">{successPercent}%</p>
          <p className="text-sm mt-1">
            uvaženje na temelju {prediction.n_similar} sličnih predmeta
          </p>
        </div>

        <div className="rounded-lg border border-brand-border bg-surface-2 p-5">
          <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-2">
            Tip povrede
          </p>
          <p className="font-display text-xl text-ink">
            {CLAIM_TYPE_LABELS[prediction.detected_claim_type] ?? prediction.detected_claim_type}
          </p>
          <p className="text-xs text-muted mt-2">
            Distribucija slučajeva po tipu:
          </p>
          <ul className="text-xs space-y-0.5 mt-1">
            {Object.entries(prediction.type_distribution)
              .sort(([, a], [, b]) => b - a)
              .slice(0, 4)
              .map(([type, n]) => (
                <li key={type} className="text-navy">
                  <span className="text-muted">·</span> {CLAIM_TYPE_LABELS[type] ?? type}: <span className="font-mono">{n}</span>
                </li>
              ))}
          </ul>
        </div>

        {prediction.panel_rate != null ? (
          <div className="rounded-lg border border-signal/30 bg-signal/5 p-5">
            <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-signal mb-2">
              Pred vašim vijećem
            </p>
            <p className="font-display text-4xl text-signal">
              {(prediction.panel_rate * 100).toFixed(0)}%
            </p>
            <p className="text-xs text-navy mt-2">
              uvaženje u {prediction.panel_n_cases} slučajeva s tim sastavom
            </p>
            {prediction.panel_members_found.length > 0 && (
              <p className="text-[11px] text-muted mt-2">
                Pronađeni: {prediction.panel_members_found.join(", ")}
              </p>
            )}
            {prediction.panel_members_unknown.length > 0 && (
              <p className="text-[11px] text-status-fail mt-1">
                Nepoznati: {prediction.panel_members_unknown.join(", ")}
              </p>
            )}
          </div>
        ) : (
          <div className="rounded-lg border border-brand-border bg-surface-2 p-5">
            <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-2">
              Per-vijeće rate
            </p>
            <p className="text-sm text-muted">
              Unesi sastav vijeća u formi za specifičnu predikciju.
            </p>
          </div>
        )}
      </div>

      {/* SLIČNI PRESEDANI */}
      <div>
        <h2 className="font-serif text-xl text-ink mb-3">
          Slični DKOM presedani ({similar_precedents.length})
        </h2>
        <ul className="space-y-3">
          {similar_precedents.map((p) => (
            <PrecedentCard key={`${p.klasa}-${p.argument_zalitelja.slice(0, 30)}`} precedent={p} />
          ))}
        </ul>
      </div>
    </div>
  );
}


function PrecedentCard({ precedent: p }: { precedent: SimilarPrecedent }) {
  const verdictColor = VERDICT_COLORS[p.dkom_verdict] || "bg-muted/15 text-muted border-muted/30";
  const verdictLabel = {
    uvazen: "uvazen",
    djelomicno_uvazen: "dijelom uvazen",
    odbijen: "odbijen",
    ne_razmatra: "ne razmatra",
  }[p.dkom_verdict] || p.dkom_verdict;

  return (
    <li className="rounded-lg border border-brand-border bg-surface-2 p-5">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="font-mono text-xs text-muted">
              {p.pdf_url ? (
                <a
                  href={p.pdf_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-signal hover:underline"
                >
                  {p.klasa} ↗
                </a>
              ) : (
                p.klasa
              )}
            </span>
            {p.datum_odluke && (
              <span className="text-xs text-muted">· {p.datum_odluke}</span>
            )}
            <span className={`inline-block text-[10px] font-medium px-1.5 py-0.5 rounded border ${verdictColor}`}>
              {verdictLabel}
            </span>
            <span className="text-[10px] text-muted font-mono ml-auto">
              {(p.similarity * 100).toFixed(0)}% sličnost
            </span>
          </div>
          <p className="text-sm text-ink font-medium">{p.predmet}</p>
          {p.narucitelj && (
            <p className="text-[11px] text-muted mt-0.5">Naručitelj: {p.narucitelj}</p>
          )}
        </div>
      </div>

      <details className="text-sm">
        <summary className="cursor-pointer text-navy hover:text-ink transition">
          <span className="text-[10px] uppercase tracking-wider text-muted font-semibold">
            Argument žalitelja
          </span>
          <span className="ml-2">{p.argument_zalitelja.slice(0, 160)}{p.argument_zalitelja.length > 160 ? "…" : ""}</span>
        </summary>
        <div className="mt-3 space-y-2 text-xs text-navy">
          <div>
            <span className="text-[10px] uppercase tracking-wider text-muted font-semibold">Cijeli argument:</span>
            <p className="mt-1 leading-relaxed">{p.argument_zalitelja}</p>
          </div>
          <div>
            <span className="text-[10px] uppercase tracking-wider text-muted font-semibold">DKOM obrazloženje:</span>
            <p className="mt-1 leading-relaxed">{p.dkom_obrazlozenje}</p>
          </div>
          {p.violated_article_claimed && (
            <p className="text-[11px] text-muted">
              <span className="font-semibold">Citirani članak:</span>{" "}
              <span className="font-mono">{p.violated_article_claimed}</span>
            </p>
          )}
          {p.vijece.length > 0 && (
            <p className="text-[11px] text-muted">
              <span className="font-semibold">Vijeće:</span> {p.vijece.join(", ")}
            </p>
          )}
        </div>
      </details>
    </li>
  );
}
