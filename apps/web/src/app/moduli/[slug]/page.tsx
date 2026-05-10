import Link from "next/link";
import { notFound } from "next/navigation";

import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";

const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3001";

type ModuleData = {
  slug: string;
  title: string;
  emphasis: string;
  hero_subtitle: string;
  hero_description: string;
  hero_status: string;
  phases: { label: string; title: string; text: string }[];
  areas: { title: string; text: string }[];
  examples: { type: string; title: string; verdict: string; text: string }[];
  citation: { text: string; author: string };
  faqs: { q: string; a: string }[];
};

const MODULES: Record<string, ModuleData> = {
  "analiza-don": {
    slug: "analiza-don",
    title: "Validacija DON-a",
    emphasis: "prije objave",
    hero_subtitle: "Detekcija povreda u Dokumentaciji o nabavi",
    hero_description:
      "Lexitor čita tvoj DON protiv ZJN-a (čl. 200-320), pravilnika i 749 DKOM odluka. Označava povrede prije nego dokument ode u eOJN.",
    hero_status: "Dostupno",
    phases: [
      {
        label: "1. Učitavanje",
        title: "Učitaj DON",
        text: "PDF, DOCX, MD ili TXT. Pojedinačni fajl ili cijela mapa odjednom — Upute za ponuditelje, Kriteriji, Općg podaci, prilozi.",
      },
      {
        label: "2. Analiza",
        title: "Lexitor čita",
        text: "Parser razlaže dokument na blokove (zahtjevi, kriteriji, rokovi). Svaki blok ide kroz 12 deterministic + LLM pravila.",
      },
      {
        label: "3. Izvještaj",
        title: "Ispravi ili argumentiraj",
        text: "Vidiš svaki nalaz s ZJN člankom i DKOM presedanom. Prihvati, odbij ili dodaj komentar.",
      },
    ],
    areas: [
      {
        title: "Brand-lock",
        text: "Marka bez „ili jednakovrijedno” (ZJN čl. 207). 220+ brandova kroz industrije.",
      },
      {
        title: "Kratki rok",
        text: "Rok dostave ponude prekratak za vrstu postupka (čl. 219-220).",
      },
      {
        title: "Diskriminatorni uvjeti",
        text: "Uvjeti sposobnosti koji isključuju SME (čl. 256-272).",
      },
      {
        title: "Neprecizne specifikacije",
        text: "Kontradikcije i nejasnoće u tehničkim zahtjevima (čl. 280, 290).",
      },
      {
        title: "Krivo grupiranje",
        text: "Grupacija predmeta koja iskrivljuje konkurenciju (čl. 213).",
      },
      {
        title: "ESPD i dokazi",
        text: "Pretjerani ili neopravdani dokazi sposobnosti (čl. 263-266).",
      },
      {
        title: "Vague kriteriji",
        text: "Kriterij odabira ENP bez mjerljivih sub-kriterija (čl. 284).",
      },
      {
        title: "Jamstva",
        text: "Prekomjerna jamstva za ozbiljnost ponude (čl. 214 max 1.5%).",
      },
    ],
    examples: [
      {
        type: "Brand-lock",
        title: "Sika 300 PP",
        verdict: "Kršenje · ZJN čl. 207",
        text: "Tehnička specifikacija navodi „Sika 300 PP, debljine 2mm” bez klauzule „ili jednakovrijedno”. DKOM je u UP/II-034-02/26-01/176 takvu specifikaciju proglasio diskriminatornom.",
      },
      {
        type: "Kratki rok",
        title: "18 dana za otvoreni postupak",
        verdict: "Upozorenje · ZJN čl. 219",
        text: "Rok dostave od 18 dana za otvoreni postupak s nadvrijednosnim pragom — minimum je 30 dana. Skraćivanje moguće samo uz objavu prethodne informacije.",
      },
      {
        type: "Vague kriterij",
        title: "„Kvaliteta” bez težinskog udjela",
        verdict: "Upozorenje · ZJN čl. 284",
        text: "ENP kriterij navodi „kvaliteta proizvoda” kao 30%, ali nema definirane mjerljive sub-kriterije. DKOM traži objektivne sub-kriterije za svaki ne-cijeni kriterij.",
      },
    ],
    citation: {
      text: "„Lexitor je za nas pravi par očiju prije svakog objavljivanja. Ono što bi inače trebalo sat-dva pregleda, sada radimo u 10 minuta.”",
      author: "Marko V., voditelj nabave, KBC Zagreb",
    },
    faqs: [
      {
        q: "Koliki DON može učitati?",
        a: "Maksimum 50 MB po fajlu, do 20 fajlova po projektu. Veće dokumente podijeli ili kontaktiraj nas za Enterprise.",
      },
      {
        q: "Što ako moj DON nema standardnu strukturu?",
        a: "Lexitor koristi 3 detektora strukture (markdown headeri, rb prefiksi, ALL CAPS). Ako parser pogriješi, javi nam — ručno dodajemo edge case.",
      },
      {
        q: "Mogu li dodati svoja pravila?",
        a: "Trenutno ne — Lexitor koristi unifikovan skup pravila kalibriran na 749 DKOM odluka. Custom pravila planiramo u Faze 2.",
      },
    ],
  },

  "analiza-troskovnika": {
    slug: "analiza-troskovnika",
    title: "Provjera troškovnika",
    emphasis: "bez matematičkih grešaka",
    hero_subtitle: "Validacija stavki, kol × jed.cijena, podstavki, rekapitulacija",
    hero_description:
      "Lexitor parsira Arhigon i Excel troškovnike, provjerava matematiku i jezik svake stavke. Brand-lock, prazne cijene, krivi SUM-ovi — sve označeno.",
    hero_status: "Dostupno",
    phases: [
      {
        label: "1. Učitavanje",
        title: "XLSX ili .arhigon",
        text: "Učitaj troškovnik u kanonskom Arhigon formatu (XLSX) ili izvornom .arhigon ZIP-u s BoQ.xml.",
      },
      {
        label: "2. Analiza",
        title: "Matematika + jezik",
        text: "Svaka stavka prolazi kroz 8 deterministic pravila: math, brand-lock, group_sum, recap reference, podstavke.",
      },
      {
        label: "3. Označavanje",
        title: "Po sheet-u, po stavki",
        text: "Vidiš svaku stavku s nalazom. Ovjeri svoj rad: prihvati ili odbij Lexitor-ov verdikt, eksportiraj PDF.",
      },
    ],
    areas: [
      {
        title: "Aritmetička greška",
        text: "Kol × jed.cijena ≠ ukupno. Decimalni offset, krivi zaokruživanja.",
      },
      {
        title: "Group sum nepoklap",
        text: "SUM formula ne pokriva sve matematičke retke u rasponu.",
      },
      {
        title: "Recap ref nepoklap",
        text: "Cross-sheet referenca ne pokazuje na pravu UKUPNO ćeliju.",
      },
      {
        title: "Brand-lock u stavkama",
        text: "Stavka navodi marku bez „ili jednakovrijedno”. 220+ brandova.",
      },
      {
        title: "Prazna jed. cijena",
        text: "Ponudbeni troškovnik: prazno = OK. Procjena: obavezna popunjena.",
      },
      {
        title: "Više od 2 decimale",
        text: "Cijene s 3+ decimala (osim u opravdanim slučajevima — npr. cijena/kg).",
      },
      {
        title: "Podstavke i strukture",
        text: "12 varijanti stavki iz tutoriala — sn/st mini-headeri, x markeri.",
      },
      {
        title: "Vague opis",
        text: "Stavka „Razno”, „Po dogovoru” bez konkretne specifikacije.",
      },
    ],
    examples: [
      {
        type: "Aritmetika",
        title: "12 × 50 ≠ 650",
        verdict: "Kršenje · math_row",
        text: "Stavka 2.5.: količina 12, jed.cijena 50.00 €, ukupno 650.00 €. Lexitor pretpostavlja 600.00 €. Razlika +50 € (8.3%).",
      },
      {
        type: "Brand-lock",
        title: "Geberit u sanitariji",
        verdict: "Kršenje · ZJN čl. 207",
        text: "Stavka 5.12.: „Vodokotlić Geberit Sigma 70, 6/3L” — bez „ili jednakovrijedno”. Sika spomenuta u 4 stavke, Geberit u 7.",
      },
      {
        type: "Recap nepoklap",
        title: "UKUPNO ZIDARSKI ne pokriva sve",
        verdict: "Upozorenje · group_sum",
        text: "Rekapitulacija UKUPNO ZIDARSKI = SUM(D14:D87) — ali matematičke stavke su u D14:D92 (5 stavki izvan range-a, ukupno 12.450 €).",
      },
    ],
    citation: {
      text: "„Kvaliteta troškovnika u javnim natječajima ima domaću tradiciju 'pa-ko-zna'. Lexitor je prvi alat koji mi ozbiljno provjeri rad.”",
      author: "Ana K., projektant, Zagreb",
    },
    faqs: [
      {
        q: "Koji formati su podržani?",
        a: ".xlsx, .xls, .arhigon, .arhigonfile. PDF troškovnici su u radu — trenutno preporučamo XLSX export.",
      },
      {
        q: "Što ako moj troškovnik nije u Arhigon formatu?",
        a: "Lexitor podržava i Layout B (legacy Arhigon format prije 2024). Custom format-i — javi nam, ručno mapiramo kolone.",
      },
      {
        q: "Razumije li podstavke i pravilne hijerarhije?",
        a: "Da — 12 varijanti stavki iz Arhigon tutoriala. Sn/st mini-headeri, x markeri za didaktičke primjere.",
      },
    ],
  },

  zalbe: {
    slug: "zalbe",
    title: "Žalbe asistent",
    emphasis: "iz prakse, ne iz teorije",
    hero_subtitle: "Generiraj nacrt žalbe iz DKOM presedana",
    hero_description:
      "Žalbe modul koristi bazu 749 ekstrahiranih DKOM odluka. Za tvoj predmet pronalazi slične, prikazuje success rate, generira nacrt žalbe.",
    hero_status: "Faza 2 · u razvoju",
    phases: [
      {
        label: "1. Učitavanje",
        title: "Tvoj predmet",
        text: "Učitaj DON i odluku o odabiru. Lexitor identificira što osporavaš i tko ti je naručitelj.",
      },
      {
        label: "2. Slični predmeti",
        title: "Iz prakse DKOM-a",
        text: "Lexitor vraća top 10 sličnih predmeta s ishodom (uvazen/odbijen) i statistikom po vijeću.",
      },
      {
        label: "3. Nacrt žalbe",
        title: "Argumentacija + citate",
        text: "Generira nacrt žalbe s navodima žalitelja, citatom ZJN-a, te referencom na uspješne presedane.",
      },
    ],
    areas: [
      {
        title: "Predviđanje ishoda",
        text: "Success rate tvog argumenta na temelju povijesne prakse (uvazen/odbijen).",
      },
      {
        title: "Sastav vijeća",
        text: "Kojem će vijeću ići — njihova praksa po claim type-u.",
      },
      {
        title: "Slični predmeti",
        text: "Top 10 sličnih DKOM odluka s žaliteljevim argumentom i obrazloženjem.",
      },
      {
        title: "ZJN argumentacija",
        text: "Auto-citat ZJN članaka koje DKOM najčešće prihvaća za tvoj tip argumenta.",
      },
      {
        title: "Nacrt žalbe",
        text: "Generirani tekst žalbe spreman za uređivanje. Možeš editovati prije slanja.",
      },
      {
        title: "Anti-pattern check",
        text: "Upozorava ako tvoj argument tipično DKOM odbija — predlaže drugu strategiju.",
      },
      {
        title: "Rok i taksa",
        text: "Auto-izračun žalbenog roka i takse prema vrijednosti nabave.",
      },
      {
        title: "Odgovor na žalbu",
        text: "Naručitelj? Lexitor priprema i odgovor na tuđu žalbu, s argumentacijom.",
      },
    ],
    examples: [
      {
        type: "Uvažena žalba",
        title: "Brand-lock argument",
        verdict: "82% success rate",
        text: "U 23 DKOM odluke s identičnim brand-lock argumentom, 19 je uvaženo, 4 odbijeno. Tvoj predmet ima 82% šansu uspjeha.",
      },
      {
        type: "Anti-pattern",
        title: "„Pravna nesigurnost”",
        verdict: "12% success rate",
        text: "Argument „dokumentacija stvara pravnu nesigurnost” DKOM uvažava samo u 12% slučajeva. Predlažemo konkretnije navedi član ZJN-a.",
      },
      {
        type: "Vijeće",
        title: "Antolković · Gortan Krnić · Majdak Huljev",
        verdict: "Trio s 75% uvažen rate",
        text: "Tvoj predmet ide pred ovaj trio. Njihov povijesni rate za brand-lock je 75% (vs. 64% prosjek DKOM-a).",
      },
    ],
    citation: {
      text: "„Pisanje žalbe je 80% citiranja prethodne prakse. Lexitor mi je u 5 minuta dao više materijala nego što bih pronašao za pola dana.”",
      author: "Petar S., odvjetnik specijaliziran za javnu nabavu",
    },
    faqs: [
      {
        q: "Kad će Žalbe modul biti dostupan?",
        a: "U razvoju, planirana objava Q3 2026. Trenutno radimo na DKOM dataset-u i pattern detection-u.",
      },
      {
        q: "Hoće li raditi i za VUS (Visoki upravni sud)?",
        a: "Druga faza Žalbe modula — VUS odluke za žalbe protiv DKOM presuda. Korpus se trenutno skuplja.",
      },
      {
        q: "Mogu li koristiti generirani tekst direktno?",
        a: "Ne — Lexitor je asistent, ne pravnik. Generirani tekst je nacrt koji ti ili tvoj odvjetnik treba pregledati i prilagoditi.",
      },
    ],
  },
};

export function generateStaticParams() {
  return Object.keys(MODULES).map((slug) => ({ slug }));
}

interface PageProps {
  params: Promise<{ slug: string }>;
}

export default async function ModulPage({ params }: PageProps) {
  const { slug } = await params;
  const mod = MODULES[slug];
  if (!mod) return notFound();

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1">
        {/* HERO */}
        <section className="bg-[#0B1320] text-[#F7F5F0]">
          <div className="mx-auto max-w-6xl px-6 py-20 grid md:grid-cols-2 gap-12 items-center">
            <div>
              <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-gold mb-5">
                Modul · {mod.hero_status}
              </p>
              <h1 className="font-display text-5xl md:text-6xl font-medium tracking-tight leading-[1.05]">
                {mod.title}{" "}
                <em className="text-gold not-italic font-serif italic">
                  {mod.emphasis}
                </em>
                .
              </h1>
              <p className="mt-6 text-base text-[#F7F5F0]/60">
                {mod.hero_subtitle}
              </p>
              <p className="mt-4 text-lg text-[#F7F5F0]/80 leading-relaxed max-w-lg">
                {mod.hero_description}
              </p>
              <div className="mt-10 flex flex-col sm:flex-row gap-3">
                <a
                  href={APP_URL}
                  className="rounded-md bg-gold px-7 py-3.5 text-[#0B1320] font-medium hover:bg-gold/90 transition"
                >
                  Probaj besplatno
                </a>
                <Link
                  href="/cjenik"
                  className="rounded-md border border-[#F7F5F0]/20 px-7 py-3.5 text-[#F7F5F0] hover:border-[#F7F5F0]/50 transition"
                >
                  Cjenik
                </Link>
              </div>
            </div>

            {/* Hero preview */}
            <div className="rounded-lg border border-[#F7F5F0]/15 bg-[#1A2332] p-6 shadow-2xl">
              <div className="flex items-center gap-2 mb-4 text-[10px] text-[#F7F5F0]/40 font-mono">
                <span className="w-2 h-2 rounded-full bg-status-fail" />
                <span className="w-2 h-2 rounded-full bg-gold" />
                <span className="w-2 h-2 rounded-full bg-status-ok" />
                <span className="ml-2">{mod.title}</span>
              </div>
              <div className="space-y-3">
                {mod.examples.slice(0, 3).map((ex, i) => {
                  const accentColor =
                    i === 0
                      ? "border-l-status-fail bg-status-fail/5"
                      : i === 1
                        ? "border-l-gold bg-gold/5"
                        : "border-l-status-ok bg-status-ok/5";
                  const textColor =
                    i === 0
                      ? "text-status-fail"
                      : i === 1
                        ? "text-gold"
                        : "text-status-ok";
                  return (
                    <div
                      key={ex.title}
                      className={`rounded border-l-4 p-3 ${accentColor}`}
                    >
                      <p
                        className={`text-[10px] uppercase tracking-wider font-semibold mb-1 ${textColor}`}
                      >
                        {ex.verdict}
                      </p>
                      <p className="text-xs text-[#F7F5F0]/80">{ex.text.substring(0, 130)}…</p>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </section>

        {/* 3 FAZE */}
        <section className="border-b border-brand-border">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="text-center mb-14">
              <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-3">
                Tok rada
              </p>
              <h2 className="font-serif text-3xl md:text-4xl text-ink">
                Validacija u tri faze.{" "}
                <em className="text-gold not-italic font-serif italic">
                  Bez čekanja.
                </em>
              </h2>
            </div>
            <div className="grid gap-8 md:grid-cols-3">
              {mod.phases.map((p, i) => (
                <div key={p.label}>
                  <div className="flex items-baseline gap-3 mb-3">
                    <span className="font-display text-4xl text-gold">{i + 1}</span>
                    <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted">
                      {p.label.split(". ")[1]}
                    </p>
                  </div>
                  <h3 className="font-serif text-xl text-ink mb-3">{p.title}</h3>
                  <p className="text-muted leading-relaxed text-sm">{p.text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* AREAS */}
        <section className="border-b border-brand-border bg-surface-2/40">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="text-center mb-14">
              <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-3">
                Što se provjerava
              </p>
              <h2 className="font-serif text-3xl md:text-4xl text-ink">
                Osam područja{" "}
                <em className="text-gold not-italic font-serif italic">
                  po čl. 200-320 ZJN-a
                </em>
              </h2>
            </div>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {mod.areas.map((a) => (
                <div
                  key={a.title}
                  className="rounded-lg border border-brand-border bg-surface p-5"
                >
                  <h3 className="font-serif text-base text-ink mb-2">{a.title}</h3>
                  <p className="text-xs text-muted leading-relaxed">{a.text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* EXAMPLES */}
        <section className="border-b border-brand-border">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="text-center mb-14">
              <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-3">
                Iz prakse
              </p>
              <h2 className="font-serif text-3xl md:text-4xl text-ink">
                Tri tipična propusta{" "}
                <em className="text-gold not-italic font-serif italic">iz prakse</em>
              </h2>
            </div>
            <div className="grid gap-6 md:grid-cols-3">
              {mod.examples.map((ex) => (
                <div
                  key={ex.title}
                  className="rounded-lg border border-brand-border bg-surface p-6"
                >
                  <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-status-fail mb-2">
                    {ex.verdict}
                  </p>
                  <h3 className="font-serif text-lg text-ink mb-3">{ex.title}</h3>
                  <p className="text-sm text-muted leading-relaxed">{ex.text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CITATION */}
        <section className="border-b border-brand-border bg-surface-2/40">
          <div className="mx-auto max-w-4xl px-6 py-20 text-center">
            <p className="font-accent text-2xl md:text-3xl text-ink italic leading-relaxed">
              {mod.citation.text}
            </p>
            <p className="mt-6 text-sm text-muted">— {mod.citation.author}</p>
          </div>
        </section>

        {/* FAQ */}
        <section className="border-b border-brand-border">
          <div className="mx-auto max-w-3xl px-6 py-20">
            <div className="text-center mb-12">
              <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-3">
                Pitanja
              </p>
              <h2 className="font-serif text-3xl text-ink">
                Pitanja o modulu {mod.title}
              </h2>
            </div>
            <div className="space-y-3">
              {mod.faqs.map((faq) => (
                <details
                  key={faq.q}
                  className="group rounded-lg border border-brand-border bg-surface p-5"
                >
                  <summary className="flex items-center justify-between font-medium text-ink cursor-pointer list-none">
                    <span>{faq.q}</span>
                    <span className="text-muted text-xl group-open:rotate-45 transition-transform">
                      +
                    </span>
                  </summary>
                  <p className="mt-3 text-sm text-muted leading-relaxed">{faq.a}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* DARK CTA */}
        <section className="bg-[#0B1320] text-[#F7F5F0]">
          <div className="mx-auto max-w-4xl px-6 py-20 text-center">
            <h2 className="font-display text-4xl md:text-5xl">
              Validirajte {mod.title.split(" ")[1] || "modul"} prije objave.
              <br />
              <em className="text-gold not-italic font-serif italic">
                Tri analize besplatno
              </em>
              .
            </h2>
            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3">
              <a
                href={APP_URL}
                className="rounded-md bg-gold px-7 py-3.5 text-[#0B1320] font-medium hover:bg-gold/90 transition"
              >
                Otvori račun
              </a>
              <Link
                href="/cjenik"
                className="rounded-md border border-[#F7F5F0]/20 px-7 py-3.5 text-[#F7F5F0] hover:border-[#F7F5F0]/50 transition"
              >
                Cjenik
              </Link>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
