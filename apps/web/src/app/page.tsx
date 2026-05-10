import Link from "next/link";

import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";

const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3001";

const steps = [
  {
    label: "1. Upload",
    title: "Učitaj DON ili troškovnik",
    text: "PDF, DOCX, XLSX, ARHIGON. Pojedinačni fajl ili cijela mapa nabave odjednom.",
  },
  {
    label: "2. Analiza",
    title: "Lexitor čita protiv ZJN-a",
    text: "Detektira brand-lock, neprecizne specifikacije, kratke rokove, diskriminatorne uvjete. Citira članak i presedan.",
  },
  {
    label: "3. Odluka",
    title: "Ispravi ili argumentiraj",
    text: "Prihvati nalaz, dodaj svoj komentar, ili eksportiraj PDF izvještaj za naručitelja.",
  },
];

const modules = [
  {
    href: "/moduli/analiza-don",
    name: "Analiza DON-a",
    text: "Detekcija povreda u Dokumentaciji o nabavi prije objave.",
  },
  {
    href: "/moduli/analiza-troskovnika",
    name: "Analiza troškovnika",
    text: "Matematska + leksička validacija stavki. Brand-lock, podstavke, rekapitulacije.",
  },
  {
    href: "/moduli/zalbe",
    name: "Žalbe asistent",
    text: "Nacrt žalbe iz DKOM presedana. Predvidi success rate.",
  },
];

const fourFeatures = [
  {
    title: "Praksa DKOM-a kao temelj",
    text: "749 odluka ekstrahirano kroz LLM, indeksirano po klauzulama. Svaki nalaz ima konkretan presedan.",
  },
  {
    title: "Citat, ne halucinacija",
    text: "Lexitor ne izmišlja članke. Svaki nalaz povezan je s realnom ZJN odredbom ili DKOM odlukom.",
  },
  {
    title: "Po-vijeću statistika",
    text: "Sastav DKOM vijeća utječe na ishod. Lexitor zna povijesnu praksu svakog člana.",
  },
  {
    title: "Hrvatski jezik, hrvatsko pravo",
    text: "Sve odluke, dokumenti i sučelje na hrvatskom. Pravo Republike Hrvatske, ne EU generika.",
  },
];

const faqs = [
  {
    q: "Mogu li probati prije nego se odlučim?",
    a: "Da — 30 dana, 3 DON analize, bez kartice. Nakon trial-a odlučuješ koje module pretplatiti.",
  },
  {
    q: "Što ako Lexitor pogriješi?",
    a: "Označi nalaz kao 'prihvaćen rizik' ili 'odbijen' i nastavi. Lexitor je asistent, ne odluka — finalnu odgovornost nosi pravnik.",
  },
  {
    q: "Tko vidi moje dokumente?",
    a: "Samo članovi tvoje organizacije i super-admin za podršku. Dokumenti se ne dijele s drugim korisnicima ni s LLM provajderima izvan obrade.",
  },
  {
    q: "Imam DKOM žalbu — što sad?",
    a: "Žalbe modul (Faza 2) generira nacrt žalbe iz tvog DON-a i presedana. U razvoju, javit ćemo se kad bude dostupan.",
  },
];

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1">
        {/* HERO — dark */}
        <section className="bg-[#0B1320] text-[#F7F5F0]">
          <div className="mx-auto max-w-6xl px-6 py-24 md:py-32 grid md:grid-cols-2 gap-12 items-center">
            <div>
              <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-gold mb-5">
                Lexitor · v1
              </p>
              <h1 className="font-display text-5xl md:text-6xl font-medium tracking-tight leading-[1.05]">
                Objavi DON i troškovnik{" "}
                <em className="text-gold not-italic font-serif italic">
                  bez straha od žalbe.
                </em>
              </h1>
              <p className="mt-8 text-lg text-[#F7F5F0]/70 leading-relaxed max-w-lg">
                Lexitor čita tvoju dokumentaciju protiv Zakona o javnoj nabavi i
                749 DKOM odluka. Označava rizike <em>prije</em> nego dođe do
                žalbe.
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
                  Pogledaj cjenik
                </Link>
              </div>
              <p className="mt-6 text-xs text-[#F7F5F0]/50">
                30 dana · 3 DON analize · bez kartice
              </p>
            </div>

            {/* Hero card — mockup-style preview */}
            <div className="rounded-lg border border-[#F7F5F0]/15 bg-[#1A2332] p-6 shadow-2xl">
              <div className="flex items-center gap-2 mb-4 text-[10px] text-[#F7F5F0]/40 font-mono">
                <span className="w-2 h-2 rounded-full bg-status-fail" />
                <span className="w-2 h-2 rounded-full bg-gold" />
                <span className="w-2 h-2 rounded-full bg-status-ok" />
                <span className="ml-2">DON · Upute za ponuditelje</span>
              </div>
              <div className="space-y-3">
                <div className="rounded border-l-4 border-l-status-fail bg-[#0B1320]/60 p-3">
                  <p className="text-[10px] uppercase tracking-wider text-status-fail font-semibold mb-1">
                    Kršenje · ZJN čl. 207
                  </p>
                  <p className="text-xs text-[#F7F5F0]/80">
                    Tehnička specifikacija navodi „Sika 300 PP” bez klauzule „ili
                    jednakovrijedno”.
                  </p>
                </div>
                <div className="rounded border-l-4 border-l-gold bg-[#0B1320]/60 p-3">
                  <p className="text-[10px] uppercase tracking-wider text-gold font-semibold mb-1">
                    Upozorenje · Rok dostave
                  </p>
                  <p className="text-xs text-[#F7F5F0]/80">
                    Rok od 18 dana može biti kratak za složenu tehničku
                    specifikaciju.
                  </p>
                </div>
                <div className="rounded border-l-4 border-l-status-ok bg-[#0B1320]/60 p-3">
                  <p className="text-[10px] uppercase tracking-wider text-status-ok font-semibold mb-1">
                    Usklađeno
                  </p>
                  <p className="text-xs text-[#F7F5F0]/80">
                    Kriterij ENP ima jasno definirane težinske udjele (cijena 90%, rok 10%).
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* 3 KORAKA */}
        <section className="border-b border-brand-border">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="text-center mb-14">
              <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-3">
                Kako radi
              </p>
              <h2 className="font-serif text-3xl md:text-4xl text-ink">
                Tri koraka od učitavanja{" "}
                <em className="text-gold not-italic font-serif italic">
                  do usklađenog dokumenta
                </em>
              </h2>
            </div>
            <div className="grid gap-8 md:grid-cols-3">
              {steps.map((s, i) => (
                <div key={s.label} className="relative">
                  <div className="flex items-baseline gap-3 mb-3">
                    <span className="font-display text-4xl text-gold">{i + 1}</span>
                    <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted">
                      {s.label.split(". ")[1]}
                    </p>
                  </div>
                  <h3 className="font-serif text-xl text-ink mb-3">{s.title}</h3>
                  <p className="text-muted leading-relaxed text-sm">{s.text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* RAZLIKA — before/after */}
        <section className="border-b border-brand-border bg-surface-2/40">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="text-center mb-14">
              <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-3">
                Razlika
              </p>
              <h2 className="font-serif text-3xl md:text-4xl text-ink">
                Razlika koju Lexitor donosi je{" "}
                <em className="text-gold not-italic font-serif italic">jak presedan</em>.
              </h2>
            </div>
            <div className="grid gap-6 md:grid-cols-2">
              <div className="rounded-lg border border-status-fail/30 bg-surface p-6">
                <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-status-fail mb-3">
                  Generički AI
                </p>
                <h3 className="font-serif text-lg text-ink mb-3">
                  „Provjeri svojom dokumentacijom”
                </h3>
                <p className="text-sm text-muted leading-relaxed">
                  Vraća općenite savjete o praksi javne nabave bez konkretnog
                  članka ili presedana. Halucinira reference koje ne postoje. Ne
                  zna hrvatsko pravo.
                </p>
              </div>
              <div className="rounded-lg border border-status-ok/30 bg-surface p-6">
                <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-status-ok mb-3">
                  Lexitor
                </p>
                <h3 className="font-serif text-lg text-ink mb-3">
                  „ZJN čl. 207 · UP/II-034-02/26-01/176”
                </h3>
                <p className="text-sm text-muted leading-relaxed">
                  Svaki nalaz povezan s konkretnim člankom ZJN-a i sličnom DKOM
                  odlukom. Možeš provjeriti citat u istom kliku.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* MODULI */}
        <section className="border-b border-brand-border">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="text-center mb-14">
              <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-3">
                Birate samo što vam treba
              </p>
              <h2 className="font-serif text-3xl md:text-4xl text-ink">
                Tri modula{" "}
                <em className="text-gold not-italic font-serif italic">à la carte</em>
              </h2>
            </div>
            <div className="grid gap-6 md:grid-cols-3">
              {modules.map((m) => (
                <Link
                  key={m.href}
                  href={m.href}
                  className="group rounded-lg border border-brand-border bg-surface p-7 hover:border-ink transition flex flex-col"
                >
                  <h3 className="font-serif text-xl text-ink mb-3">{m.name}</h3>
                  <p className="text-sm text-muted leading-relaxed flex-1">{m.text}</p>
                  <p className="mt-5 text-sm text-signal opacity-70 group-hover:opacity-100 transition">
                    Saznaj više →
                  </p>
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* CITAT */}
        <section className="border-b border-brand-border bg-surface-2/40">
          <div className="mx-auto max-w-4xl px-6 py-20 text-center">
            <p className="font-accent text-2xl md:text-3xl text-ink italic leading-relaxed">
              „Lexitor je za nas postao prvi par očiju prije svakog javnog
              objavljivanja. Štedi nam ponavljanje istog rada i krati raspravu s
              naručiteljem.”
            </p>
            <p className="mt-6 text-sm text-muted">
              — Ivana M., konzultantica za javnu nabavu, Zagreb
            </p>
          </div>
        </section>

        {/* 4 FEATURES */}
        <section className="border-b border-brand-border">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="text-center mb-14">
              <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-3">
                Što vas razlikuje
              </p>
              <h2 className="font-serif text-3xl md:text-4xl text-ink">
                Četiri stvari koje{" "}
                <em className="text-gold not-italic font-serif italic">nećete naći drugdje</em>
              </h2>
            </div>
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
              {fourFeatures.map((f) => (
                <div
                  key={f.title}
                  className="rounded-lg border border-brand-border bg-surface p-6"
                >
                  <h3 className="font-serif text-lg text-ink mb-3">{f.title}</h3>
                  <p className="text-sm text-muted leading-relaxed">{f.text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="border-b border-brand-border bg-surface-2/40">
          <div className="mx-auto max-w-3xl px-6 py-20">
            <div className="text-center mb-12">
              <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-3">
                Pitanja
              </p>
              <h2 className="font-serif text-3xl text-ink">Pitanja koja čujemo</h2>
            </div>
            <div className="space-y-3">
              {faqs.map((faq) => (
                <details
                  key={faq.q}
                  className="group rounded-lg border border-brand-border bg-surface p-5 [&_summary]:cursor-pointer"
                >
                  <summary className="flex items-center justify-between font-medium text-ink list-none">
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
              Probajte na svom predmetu.
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
                href="/kontakt"
                className="rounded-md border border-[#F7F5F0]/20 px-7 py-3.5 text-[#F7F5F0] hover:border-[#F7F5F0]/50 transition"
              >
                Razgovaraj s nama
              </Link>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
