"use client";

import { useCallback, useMemo, useState, type FormEvent } from "react";

import { api } from "@/lib/api";
import type {
  SimilarPrecedent,
  ZalbeAnalyzeResponse,
  ZalbeClaimType,
  ZalbeGenerateResponse,
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

  // C.3 — generacija nacrta
  const [selectedKlase, setSelectedKlase] = useState<Set<string>>(new Set());
  const [predmet, setPredmet] = useState("");
  const [narucitelj, setNarucitelj] = useState("");
  const [brojObjave, setBrojObjave] = useState("");
  const [klasaOdluke, setKlasaOdluke] = useState("");
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);
  const [nacrt, setNacrt] = useState<ZalbeGenerateResponse | null>(null);

  const onSubmit = useCallback(async (e: FormEvent) => {
    e.preventDefault();
    if (argument.trim().length < 20) {
      setError("Argument mora imati barem 20 znakova.");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    setNacrt(null);
    setSelectedKlase(new Set());
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

  const toggleKlasa = useCallback((klasa: string) => {
    setSelectedKlase((prev) => {
      const next = new Set(prev);
      if (next.has(klasa)) {
        next.delete(klasa);
      } else {
        next.add(klasa);
      }
      return next;
    });
  }, []);

  const onGenerate = useCallback(async (e: FormEvent) => {
    e.preventDefault();
    if (!predmet.trim() || !narucitelj.trim()) {
      setGenError("Predmet nabave i naručitelj su obavezni.");
      return;
    }
    setGenerating(true);
    setGenError(null);
    setNacrt(null);
    try {
      const res = await api.generateZalba({
        argument,
        predmet: predmet.trim(),
        narucitelj: narucitelj.trim(),
        broj_objave_eojn: brojObjave.trim() || undefined,
        klasa_odluke: klasaOdluke.trim() || undefined,
        selected_precedents: selectedKlase.size > 0 ? Array.from(selectedKlase) : undefined,
      });
      setNacrt(res);
    } catch (err) {
      setGenError(err instanceof Error ? err.message : "Generiranje nije uspjelo.");
    } finally {
      setGenerating(false);
    }
  }, [argument, predmet, narucitelj, brojObjave, klasaOdluke, selectedKlase]);

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
      {result && (
        <ZalbeResults
          result={result}
          selectedKlase={selectedKlase}
          onToggleKlasa={toggleKlasa}
        />
      )}

      {/* C.3 — GENERIRANJE NACRTA */}
      {result && (
        <GenerateNacrtSection
          predmet={predmet}
          setPredmet={setPredmet}
          narucitelj={narucitelj}
          setNarucitelj={setNarucitelj}
          brojObjave={brojObjave}
          setBrojObjave={setBrojObjave}
          klasaOdluke={klasaOdluke}
          setKlasaOdluke={setKlasaOdluke}
          selectedKlaseCount={selectedKlase.size}
          generating={generating}
          genError={genError}
          onGenerate={onGenerate}
          nacrt={nacrt}
        />
      )}
    </div>
  );
}


function ZalbeResults({
  result,
  selectedKlase,
  onToggleKlasa,
}: {
  result: ZalbeAnalyzeResponse;
  selectedKlase: Set<string>;
  onToggleKlasa: (klasa: string) => void;
}) {
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
        <h2 className="font-serif text-xl text-ink mb-2">
          Slični DKOM presedani ({similar_precedents.length})
        </h2>
        <p className="text-xs text-muted mb-3">
          Označi presedane koje želiš citirati u nacrtu žalbe ↓
        </p>
        <ul className="space-y-3">
          {similar_precedents.map((p) => (
            <PrecedentCard
              key={`${p.klasa}-${p.argument_zalitelja.slice(0, 30)}`}
              precedent={p}
              selected={selectedKlase.has(p.klasa)}
              onToggle={() => onToggleKlasa(p.klasa)}
            />
          ))}
        </ul>
      </div>
    </div>
  );
}


function PrecedentCard({
  precedent: p,
  selected,
  onToggle,
}: {
  precedent: SimilarPrecedent;
  selected: boolean;
  onToggle: () => void;
}) {
  const verdictColor = VERDICT_COLORS[p.dkom_verdict] || "bg-muted/15 text-muted border-muted/30";
  const verdictLabel = {
    uvazen: "uvazen",
    djelomicno_uvazen: "dijelom uvazen",
    odbijen: "odbijen",
    ne_razmatra: "ne razmatra",
  }[p.dkom_verdict] || p.dkom_verdict;

  return (
    <li className={`rounded-lg border p-5 transition ${selected ? "border-signal bg-signal/5" : "border-brand-border bg-surface-2"}`}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <label className="flex items-start gap-3 cursor-pointer min-w-0 flex-1">
          <input
            type="checkbox"
            checked={selected}
            onChange={onToggle}
            className="mt-1 h-4 w-4 rounded border-brand-border text-signal focus:ring-signal cursor-pointer"
          />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <span className="font-mono text-xs text-muted">
                {p.pdf_url ? (
                  <a
                    href={p.pdf_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
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
        </label>
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


function GenerateNacrtSection({
  predmet,
  setPredmet,
  narucitelj,
  setNarucitelj,
  brojObjave,
  setBrojObjave,
  klasaOdluke,
  setKlasaOdluke,
  selectedKlaseCount,
  generating,
  genError,
  onGenerate,
  nacrt,
}: {
  predmet: string;
  setPredmet: (v: string) => void;
  narucitelj: string;
  setNarucitelj: (v: string) => void;
  brojObjave: string;
  setBrojObjave: (v: string) => void;
  klasaOdluke: string;
  setKlasaOdluke: (v: string) => void;
  selectedKlaseCount: number;
  generating: boolean;
  genError: string | null;
  onGenerate: (e: FormEvent) => void;
  nacrt: ZalbeGenerateResponse | null;
}) {
  return (
    <div className="rounded-lg border border-brand-border bg-surface-2 p-5 space-y-4">
      <div>
        <h2 className="font-serif text-xl text-ink mb-1">Generiraj nacrt žalbe</h2>
        <p className="text-xs text-muted">
          LLM piše nacrt na temelju tvog argumenta i {selectedKlaseCount > 0
            ? <><strong className="text-ink">{selectedKlaseCount}</strong> odabranih presedana</>
            : "auto-odabranih sličnih presedana"
          }.
        </p>
      </div>

      <form onSubmit={onGenerate} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="predmet" className="block text-sm font-medium text-ink mb-2">
              Predmet nabave <span className="text-status-fail">*</span>
            </label>
            <input
              id="predmet"
              type="text"
              value={predmet}
              onChange={(e) => setPredmet(e.target.value)}
              placeholder="Izgradnja igrališta Bundek"
              className="w-full rounded-md border border-brand-border bg-surface px-3 py-2 text-sm text-navy placeholder:text-muted/70"
            />
          </div>

          <div>
            <label htmlFor="narucitelj" className="block text-sm font-medium text-ink mb-2">
              Naručitelj <span className="text-status-fail">*</span>
            </label>
            <input
              id="narucitelj"
              type="text"
              value={narucitelj}
              onChange={(e) => setNarucitelj(e.target.value)}
              placeholder="Grad Zagreb"
              className="w-full rounded-md border border-brand-border bg-surface px-3 py-2 text-sm text-navy placeholder:text-muted/70"
            />
          </div>

          <div>
            <label htmlFor="broj_objave" className="block text-sm font-medium text-ink mb-2">
              Broj objave EOJN <span className="text-muted">(opcionalno)</span>
            </label>
            <input
              id="broj_objave"
              type="text"
              value={brojObjave}
              onChange={(e) => setBrojObjave(e.target.value)}
              placeholder="2025/S 0F2-0012345"
              className="w-full rounded-md border border-brand-border bg-surface px-3 py-2 text-sm text-navy placeholder:text-muted/70 font-mono"
            />
          </div>

          <div>
            <label htmlFor="klasa_odluke" className="block text-sm font-medium text-ink mb-2">
              Klasa osporavane odluke <span className="text-muted">(opcionalno)</span>
            </label>
            <input
              id="klasa_odluke"
              type="text"
              value={klasaOdluke}
              onChange={(e) => setKlasaOdluke(e.target.value)}
              placeholder="406-01/25-01/N"
              className="w-full rounded-md border border-brand-border bg-surface px-3 py-2 text-sm text-navy placeholder:text-muted/70 font-mono"
            />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={generating || !predmet.trim() || !narucitelj.trim()}
            className="rounded-md bg-signal text-surface px-6 py-2.5 font-medium hover:bg-signal/90 transition disabled:opacity-50"
          >
            {generating ? "Generiram…" : "Generiraj nacrt"}
          </button>
          {genError && (
            <p className="text-sm text-status-fail">{genError}</p>
          )}
        </div>
      </form>

      {nacrt && <NacrtViewer nacrt={nacrt} />}
    </div>
  );
}


function NacrtViewer({ nacrt }: { nacrt: ZalbeGenerateResponse }) {
  const [copied, setCopied] = useState(false);

  const onCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(nacrt.nacrt_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  }, [nacrt.nacrt_text]);

  const downloadUrl = useMemo(() => {
    const blob = new Blob([nacrt.nacrt_text], { type: "text/plain;charset=utf-8" });
    return URL.createObjectURL(blob);
  }, [nacrt.nacrt_text]);

  return (
    <div className="rounded-lg border border-signal/30 bg-surface p-5 space-y-3">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3 text-xs text-muted">
          <span><strong className="text-ink font-mono">{nacrt.word_count}</strong> riječi</span>
          {nacrt.cited_precedents.length > 0 && (
            <span>· <strong className="text-ink">{nacrt.cited_precedents.length}</strong> presedana citirano</span>
          )}
          {nacrt.cited_zjn_articles.length > 0 && (
            <span>· <strong className="text-ink">{nacrt.cited_zjn_articles.length}</strong> ZJN čl.</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onCopy}
            className="rounded-md border border-brand-border bg-surface-2 hover:bg-surface px-3 py-1.5 text-xs text-navy transition"
          >
            {copied ? "Kopirano ✓" : "Kopiraj"}
          </button>
          <a
            href={downloadUrl}
            download={`nacrt-zalbe-${new Date().toISOString().slice(0, 10)}.txt`}
            className="rounded-md border border-brand-border bg-surface-2 hover:bg-surface px-3 py-1.5 text-xs text-navy transition"
          >
            Preuzmi .txt
          </a>
        </div>
      </div>

      <pre className="whitespace-pre-wrap font-serif text-sm text-ink leading-relaxed bg-surface-2 p-4 rounded border border-brand-border max-h-[600px] overflow-y-auto">
        {nacrt.nacrt_text}
      </pre>

      <p className="text-[11px] text-muted italic">
        Ovo je nacrt — provjeri činjenice, klase presedana i evidencijske brojeve prije podnošenja DKOM-u.
      </p>
    </div>
  );
}
