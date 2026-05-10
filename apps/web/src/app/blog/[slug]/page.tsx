import Link from "next/link";

import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export default async function BlogArticlePage({ params }: PageProps) {
  const { slug } = await params;
  // Placeholder članak — pravi sadržaj će se učitavati iz CMS-a ili MDX-a
  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1">
        {/* HEADER ČLANKA */}
        <section className="bg-[#0B1320] text-[#F7F5F0]">
          <div className="mx-auto max-w-3xl px-6 py-20">
            <Link
              href="/blog"
              className="text-sm text-[#F7F5F0]/60 hover:text-gold transition mb-8 inline-block"
            >
              ← Natrag na blog
            </Link>
            <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-gold mb-5">
              Praksa DKOM-a · 5. svibnja 2026.
            </p>
            <h1 className="font-display text-4xl md:text-5xl font-medium tracking-tight leading-[1.1]">
              „Predmet nabave mora biti{" "}
              <em className="text-gold not-italic font-serif italic">
                jednoznačno određen
              </em>
              .”
            </h1>
            <p className="mt-6 text-lg text-[#F7F5F0]/70 leading-relaxed">
              Pregled DKOM odluka iz 2025-2026. koje su poništene zbog
              nedovoljno preciznih tehničkih specifikacija.
            </p>
            <div className="mt-8 flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-[#F7F5F0]/10 flex items-center justify-center font-display text-sm text-gold">
                MB
              </div>
              <div>
                <p className="text-sm text-[#F7F5F0]">Marko Bašić</p>
                <p className="text-xs text-[#F7F5F0]/50">8 min čitanja</p>
              </div>
            </div>
          </div>
        </section>

        {/* SADRŽAJ ČLANKA */}
        <article className="border-b border-brand-border">
          <div className="mx-auto max-w-3xl px-6 py-20 prose-content">
            <p className="text-lg text-ink leading-relaxed mb-6">
              Pažljivi pregled DKOM odluka iz 2025-2026. otkriva pattern koji se
              ponavlja: <strong>jedna trećina</strong> uspješnih žalbi temelji
              se na argumentu da naručitelj nije jednoznačno odredio predmet
              nabave.
            </p>

            <h2 className="font-serif text-2xl text-ink mt-12 mb-4">
              Što ZJN zahtijeva
            </h2>
            <p className="text-navy leading-relaxed mb-6">
              Članci 280. i 290. ZJN-a 2016 jasno propisuju da tehnička
              specifikacija mora omogućiti ravnopravno tržišno natjecanje. To u
              praksi znači:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-navy mb-6">
              <li>
                Specifikacija ne smije isključivo upućivati na konkretnog
                proizvođača bez klauzule „ili jednakovrijedno”.
              </li>
              <li>
                Tehničke karakteristike moraju biti opisno detaljne — minimum
                dimenzija, materijal, performanse, ovjernost.
              </li>
              <li>
                Kontradikcije između različitih dijelova dokumentacije
                automatski stvaraju pravnu nesigurnost.
              </li>
            </ul>

            <h2 className="font-serif text-2xl text-ink mt-12 mb-4">
              Tri tipična propusta
            </h2>

            <h3 className="font-serif text-xl text-ink mt-8 mb-3">
              1. Brand naveden bez „jednakovrijedno”
            </h3>
            <p className="text-navy leading-relaxed mb-4">
              Najčešća greška. DKOM ju je u 2026. označio kao automatsku povredu
              čl. 207, bez obzira na obrazloženje naručitelja.
            </p>
            <blockquote className="border-l-4 border-gold bg-surface-2 pl-6 py-4 my-6 italic text-navy">
              „Hidroizolacija krova mora biti Sika 300 PP, debljine 2mm.”
              <footer className="not-italic text-sm text-muted mt-2">
                — Tipičan brand-lock primjer (UP/II-034-02/26-01/176)
              </footer>
            </blockquote>

            <h3 className="font-serif text-xl text-ink mt-8 mb-3">
              2. Tehnička specifikacija s nejasnim parametrima
            </h3>
            <p className="text-navy leading-relaxed mb-4">
              Drugi po čestoći. Naručitelj navodi „mobilna zaštita od RTG
              zračenja, min 0,3 Pb, 1 kom” bez dimenzija, materijala, namjene.
            </p>

            <h3 className="font-serif text-xl text-ink mt-8 mb-3">
              3. Kontradikcije između dijelova dokumentacije
            </h3>
            <p className="text-navy leading-relaxed mb-4">
              Dokumentacija u jednom dijelu kaže da je životopis stručnjaka
              dobrovoljan, u drugom da je obavezan za bodovanje. DKOM to
              tretira kao pravnu nesigurnost koja ide na štetu ponuditelja.
            </p>

            <h2 className="font-serif text-2xl text-ink mt-12 mb-4">
              Kako Lexitor pomaže
            </h2>
            <p className="text-navy leading-relaxed mb-6">
              Naša brand_lock detekcija pokriva 220+ brandova kroz industrije —
              ne samo građevinske. Za 3. točku radimo LLM-driven detekciju
              kontradikcija (Faza 2 plan, dostupno Q3 2026.).
            </p>

            <div className="mt-12 p-6 rounded-lg bg-surface-2 border border-brand-border">
              <p className="text-sm text-muted mb-3">Probajte sami:</p>
              <p className="font-serif text-xl text-ink mb-4">
                Učitaj DON i vidi jesi li napravio neki od ovih propusta.
              </p>
              <Link
                href="/cjenik"
                className="inline-block rounded-md bg-ink px-6 py-3 text-sm font-medium text-surface hover:bg-navy transition"
              >
                Pogledaj cjenik →
              </Link>
            </div>
          </div>
        </article>

        {/* RELATED ARTICLES */}
        <section className="bg-surface-2/40">
          <div className="mx-auto max-w-6xl px-6 py-16">
            <h2 className="font-serif text-2xl text-ink mb-8 text-center">
              Slični članci
            </h2>
            <div className="grid gap-6 md:grid-cols-3">
              {[
                {
                  title: "Diskriminatorni kriteriji i kako ih prepoznati",
                  date: "29. tra 2026.",
                  cat: "Vodič",
                },
                {
                  title: "Što odluka 142/24 mijenja u tumačenju",
                  date: "2. svi 2026.",
                  cat: "Analiza",
                },
                {
                  title: "Ne stavljajte ovo ime proizvođača",
                  date: "Anti-pattern",
                  cat: "DKOM 22/05/24",
                },
              ].map((r) => (
                <Link
                  key={r.title}
                  href={`/blog/${slug}`}
                  className="group rounded-lg border border-brand-border bg-surface overflow-hidden hover:border-ink transition"
                >
                  <div className="aspect-[16/9] bg-surface-2 flex items-center justify-center text-xs text-muted">
                    {r.date}
                  </div>
                  <div className="p-5">
                    <p className="text-[10px] uppercase tracking-[0.18em] font-semibold text-gold mb-2">
                      {r.cat}
                    </p>
                    <h3 className="font-serif text-base text-ink group-hover:text-gold transition">
                      {r.title}
                    </h3>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
