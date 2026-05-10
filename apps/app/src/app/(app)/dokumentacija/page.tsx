"use client";

import { useEffect, useMemo, useState } from "react";

import { api } from "@/lib/api";
import type { IndexedSource } from "@/lib/types";

const ZJN_URL = "https://narodne-novine.nn.hr/clanci/sluzbeni/2016_12_120_2607.html";

export default function DokumentacijaPage() {
  const [sources, setSources] = useState<IndexedSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const data = await api.listSources();
        setSources(data.items);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Greška pri dohvatu izvora.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const grouped = useMemo(() => {
    const zjn: IndexedSource[] = [];
    const dkom: IndexedSource[] = [];
    const ostalo: IndexedSource[] = [];
    for (const s of sources) {
      if (s.source === "zjn") zjn.push(s);
      else if (s.source === "dkom") dkom.push(s);
      else ostalo.push(s);
    }
    return { zjn, dkom, ostalo };
  }, [sources]);

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <h1 className="font-display text-3xl text-ink mb-2">Dokumentacija</h1>
        <p className="text-muted">
          Lexitor koristi sljedeće pravne izvore za semantičko pretraživanje i citiranje
          u analizi. Svaka odluka i članak otvara se klikom na izvorni dokument — Lexitor
          ne redistribuira sadržaj, samo indeksira radi pretrage.
        </p>
      </div>

      {error && (
        <p className="text-sm bg-status-fail/10 border border-status-fail/30 text-status-fail rounded-md px-3 py-2 mb-4">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-muted">Učitavam…</p>
      ) : (
        <div className="space-y-10">
          <SectionZjn items={grouped.zjn} />
          <SectionDkom items={grouped.dkom} />
          <SectionRoadmap />
        </div>
      )}
    </div>
  );
}

function SectionZjn({ items }: { items: IndexedSource[] }) {
  return (
    <section>
      <header className="mb-3 flex items-baseline justify-between">
        <h2 className="font-serif text-xl text-ink">
          Zakon o javnoj nabavi <span className="text-muted text-base">· NN 120/2016</span>
        </h2>
        <a
          href={ZJN_URL}
          target="_blank"
          rel="noreferrer"
          className="text-sm text-signal hover:underline"
        >
          Otvori cijeli zakon →
        </a>
      </header>
      <p className="text-sm text-muted mb-4">
        {items.length === 0
          ? "Nije još indeksirano. Pokreni scripts/index_zjn.py iz apps/backend."
          : `${items.length} članaka indeksirano.`}
      </p>

      {items.length > 0 && (
        <div className="rounded-lg border border-brand-border bg-surface-2">
          <ul className="divide-y divide-brand-border max-h-[400px] overflow-y-auto">
            {items.map((s) => (
              <li key={s.klasa} className="px-4 py-2.5 flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <p className="font-mono text-xs text-navy">
                    {s.article_number != null ? `Članak ${s.article_number}.` : s.klasa}
                  </p>
                  <p className="text-sm text-ink truncate">{s.predmet}</p>
                </div>
                {s.pdf_url && (
                  <a
                    href={s.pdf_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-signal shrink-0 hover:underline"
                  >
                    Otvori →
                  </a>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function SectionDkom({ items }: { items: IndexedSource[] }) {
  return (
    <section>
      <header className="mb-3 flex items-baseline justify-between">
        <h2 className="font-serif text-xl text-ink">
          DKOM odluke <span className="text-muted text-base">· dkom.hr</span>
        </h2>
        <a
          href="https://www.dkom.hr/javna-objava-odluka/10"
          target="_blank"
          rel="noreferrer"
          className="text-sm text-signal hover:underline"
        >
          Otvori javno objavljene odluke →
        </a>
      </header>
      <p className="text-sm text-muted mb-4">
        {items.length === 0
          ? "Još nije indeksirano. Pokreni scripts/scrape_dkom.py + scripts/index_dkom.py."
          : `${items.length} odluka indeksirano. Klikom na klasu otvara se PDF na DKOM serveru.`}
      </p>

      {items.length > 0 && (
        <div className="rounded-lg border border-brand-border bg-surface-2">
          <ul className="divide-y divide-brand-border">
            {items.map((s) => (
              <li key={s.klasa} className="px-4 py-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <p className="font-mono text-xs text-navy">{s.klasa}</p>
                    <p className="text-sm text-ink mt-1">{s.predmet}</p>
                    <p className="text-xs text-muted mt-1">
                      {s.narucitelj && <span>{s.narucitelj}</span>}
                      {s.vrsta && <span> · {s.vrsta}</span>}
                      {s.odluka_datum && <span> · {s.odluka_datum}</span>}
                    </p>
                  </div>
                  {s.pdf_url && (
                    <a
                      href={s.pdf_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-signal shrink-0 hover:underline"
                    >
                      Otvori PDF →
                    </a>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function SectionRoadmap() {
  return (
    <section>
      <h2 className="font-serif text-xl text-ink mb-3">Planirani izvori</h2>
      <ul className="rounded-lg border border-brand-border bg-surface-2 divide-y divide-brand-border">
        <RoadmapItem name="Pravilnici i uredbe Vlade RH" status="Faza 1A" />
        <RoadmapItem name="VUS presude (Visoki upravni sud)" status="Faza 1B" />
        <RoadmapItem name="Sud Europske unije — odabrane presude" status="Faza 2" />
        <RoadmapItem name="Stručna literatura (komentari, članci)" status="Faza 2" />
      </ul>
    </section>
  );
}

function RoadmapItem({ name, status }: { name: string; status: string }) {
  return (
    <li className="px-4 py-3 flex items-center justify-between">
      <span className="text-sm text-ink">{name}</span>
      <span className="text-xs text-gold font-medium">{status}</span>
    </li>
  );
}
