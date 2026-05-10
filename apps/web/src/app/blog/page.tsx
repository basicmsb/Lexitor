import Link from "next/link";

import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";

const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3001";

type Post = {
  slug: string;
  title: string;
  excerpt: string;
  date: string;
  category: string;
  featured?: boolean;
};

const posts: Post[] = [
  {
    slug: "predmet-nabave-mora-biti-jednoznacno-odreden",
    title: "„Predmet nabave mora biti jednoznačno određen.”",
    excerpt:
      "Pregled DKOM odluka iz 2025-2026. koje su poništene zbog nedovoljno preciznih tehničkih specifikacija. Što naručitelj može učiniti drugačije.",
    date: "5. svi 2026.",
    category: "Praksa DKOM-a",
    featured: true,
  },
  {
    slug: "odluka-142-24-mijenja-tumacenje",
    title: "Što odluka 142/24 mijenja u tumačenju — i razloi bi vas trebala zanimati",
    excerpt:
      "DKOM je u travnju 2026. donio odluku koja djelomično mijenja praksu u području ENP kriterija. Razloi kompleksniji nego što izgleda.",
    date: "2. svi 2026.",
    category: "Analiza odluke",
  },
  {
    slug: "diskriminatorni-kriteriji-i-kako-prepoznati",
    title: "Diskriminatorni kriteriji i kako ih prepoznati u dokumentaciji",
    excerpt:
      "Praktični vodič kroz DKOM odluke u kojima su uvjeti sposobnosti proglasili diskriminatornima. Primjeri i savjeti za naručitelja.",
    date: "29. tra 2026.",
    category: "Vodič",
  },
  {
    slug: "referenca-objektiva-kratki-postupak",
    title: "Referenca objektivna i kratki postupak",
    excerpt:
      "DKOM-ova praksa o objektivnim referencama u skraćenom postupku — kako ih formulirati ispravno.",
    date: "25. tra 2026.",
    category: "Praksa DKOM-a",
  },
  {
    slug: "ekonomski-najpovoljnija-bez-bodovanja",
    title: "Ekonomski najpovoljnija ponuda — bez bodovanja",
    excerpt:
      "Kako objaviti ENP kriterij bez popunjavanja sub-kriterija — i zašto to obično završi žalbom.",
    date: "20. tra 2026.",
    category: "Vodič",
  },
  {
    slug: "praksa",
    title: "Praksa",
    excerpt:
      "Pregled tjednih trendova u DKOM praksi. Što je u zadnjih 7 dana zaprimljeno, što odlučeno, što naručit.",
    date: "Tjedno",
    category: "Tjednik",
  },
  {
    slug: "ne-stavljajte-ovo-ime-proizvodaca",
    title: "Ne stavljajte ovo ime proizvođača",
    excerpt:
      "30+ DKOM odluka u kojima naručitelj namjenski navodi brand „Sika”, „Geberit”, „Knauf” — i zašto je svaka pala.",
    date: "DKOM 22/05/24",
    category: "Anti-pattern",
  },
  {
    slug: "ponder-cijena-90-koliko-je-pravo",
    title: "Ponder cijena 90% — koliko je pravo",
    excerpt:
      "Praksa DKOM-a u slučajevima ENP kriterija s nadmoćnim cijenovnim faktorom. Kad je 90% previše, kad je u redu.",
    date: "DKOM 02 02 24",
    category: "Analiza",
  },
];

const tags = ["Sve", "Praksa DKOM-a", "Vodič", "Analiza odluke", "Anti-pattern", "Tjednik"];

export default function BlogPage() {
  const featured = posts.find((p) => p.featured);
  const rest = posts.filter((p) => !p.featured);

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1">
        {/* HERO */}
        <section className="bg-[#0B1320] text-[#F7F5F0]">
          <div className="mx-auto max-w-4xl px-6 py-20 text-center">
            <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-gold mb-5">
              Blog · Praksa · Vodiči · Tjednik
            </p>
            <h1 className="font-display text-5xl md:text-6xl font-medium tracking-tight leading-[1.05]">
              Praksa DKOM-a,
              <br />
              <em className="text-gold not-italic font-serif italic">
                jednom mjesečno
              </em>
              .
            </h1>
            <p className="mt-8 text-lg text-[#F7F5F0]/70 leading-relaxed max-w-2xl mx-auto">
              Pretpregled tjedna javne nabave, komentari, trendovi, podsjetnici
              za naručitelje i savjeti za ponuditelje.
            </p>
          </div>
        </section>

        {/* FEATURED + TAGOVI */}
        <section className="border-b border-brand-border">
          <div className="mx-auto max-w-6xl px-6 py-16">
            {/* Tagovi */}
            <div className="flex flex-wrap gap-2 mb-12 justify-center">
              {tags.map((t) => (
                <button
                  key={t}
                  type="button"
                  className={`px-4 py-1.5 text-sm rounded-full border transition ${
                    t === "Sve"
                      ? "bg-ink text-surface border-ink"
                      : "border-brand-border text-navy hover:border-ink"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>

            {/* Featured */}
            {featured && (
              <div className="grid gap-8 md:grid-cols-2 items-center mb-16 rounded-lg border border-brand-border bg-surface p-8">
                <div className="aspect-[4/3] rounded-md bg-surface-2 flex items-center justify-center text-muted text-sm">
                  [Slika članka]
                </div>
                <div>
                  <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-gold mb-3">
                    {featured.category}
                  </p>
                  <Link href={`/blog/${featured.slug}`}>
                    <h2 className="font-serif text-3xl text-ink mb-4 hover:text-gold transition">
                      {featured.title}
                    </h2>
                  </Link>
                  <p className="text-muted leading-relaxed mb-5">
                    {featured.excerpt}
                  </p>
                  <div className="flex items-center justify-between text-sm text-muted">
                    <span>{featured.date}</span>
                    <Link
                      href={`/blog/${featured.slug}`}
                      className="text-signal hover:text-ink transition"
                    >
                      Pročitaj članak →
                    </Link>
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* GRID OSTALIH */}
        <section className="border-b border-brand-border bg-surface-2/40">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {rest.map((post) => (
                <Link
                  key={post.slug}
                  href={`/blog/${post.slug}`}
                  className="group rounded-lg border border-brand-border bg-surface overflow-hidden hover:border-ink transition"
                >
                  <div className="aspect-[16/9] bg-surface-2 flex items-center justify-center text-xs text-muted">
                    {post.date}
                  </div>
                  <div className="p-5">
                    <p className="text-[10px] uppercase tracking-[0.18em] font-semibold text-gold mb-2">
                      {post.category}
                    </p>
                    <h3 className="font-serif text-lg text-ink mb-2 group-hover:text-gold transition">
                      {post.title}
                    </h3>
                    <p className="text-sm text-muted leading-relaxed">
                      {post.excerpt}
                    </p>
                  </div>
                </Link>
              ))}
            </div>

            <div className="mt-12 text-center">
              <button
                type="button"
                className="rounded-md border border-brand-border px-6 py-2.5 text-sm text-ink hover:border-ink transition"
              >
                Učitaj više članaka
              </button>
            </div>
          </div>
        </section>

        {/* NEWSLETTER CTA */}
        <section className="bg-[#0B1320] text-[#F7F5F0]">
          <div className="mx-auto max-w-3xl px-6 py-20 text-center">
            <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-gold mb-5">
              Tjednik
            </p>
            <h2 className="font-display text-3xl md:text-4xl mb-4">
              Kratki izvod ključnih DKOM odluka,
              <br />
              <em className="text-gold not-italic font-serif italic">
                jednom mjesečno u inbox
              </em>
              .
            </h2>
            <form className="mt-10 flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
              <input
                type="email"
                placeholder="ime@tvojadomena.hr"
                className="flex-1 rounded-md border border-[#F7F5F0]/20 bg-[#1A2332] px-4 py-3 text-sm text-[#F7F5F0] placeholder:text-[#F7F5F0]/40 focus:border-gold transition"
              />
              <button
                type="submit"
                className="rounded-md bg-gold px-6 py-3 text-sm font-medium text-[#0B1320] hover:bg-gold/90 transition"
              >
                Prijavi se
              </button>
            </form>
            <p className="mt-3 text-xs text-[#F7F5F0]/50">
              Bez spama, bez prodaje. Otkaži jednim klikom.
            </p>
          </div>
        </section>

        {/* SECONDARY CTA */}
        <section className="bg-[#0B1320] text-[#F7F5F0] border-t border-[#F7F5F0]/10">
          <div className="mx-auto max-w-4xl px-6 py-16 text-center">
            <p className="text-sm text-[#F7F5F0]/70 mb-5">
              Pratiš DKOM-a, a još koristiš generički AI alat?
            </p>
            <a
              href={APP_URL}
              className="inline-block rounded-md bg-gold px-7 py-3.5 text-[#0B1320] font-medium hover:bg-gold/90 transition"
            >
              Probaj Lexitor besplatno
            </a>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
