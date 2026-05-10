import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";

export default function PrivatnostPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1 border-b border-brand-border">
        <div className="mx-auto max-w-3xl px-6 py-20">
          <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-3">
            Pravno · ažurirano 11.05.2026.
          </p>
          <h1 className="font-display text-4xl md:text-5xl text-ink mb-6">
            Politika privatnosti
          </h1>
          <p className="text-muted leading-relaxed mb-10">
            Lexitor postupa s vašim podacima sukladno GDPR-u i hrvatskom Zakonu
            o zaštiti osobnih podataka.
          </p>

          <div className="space-y-8 text-navy leading-relaxed">
            <section>
              <h2 className="font-serif text-2xl text-ink mb-3">
                1. Koje podatke skupljamo
              </h2>
              <ul className="list-disc pl-6 space-y-2">
                <li>Email, ime i prezime, organizacija — pri registraciji</li>
                <li>Dokumenti koje učitavate — pohranjeni u našoj infrastrukturi</li>
                <li>Metapodaci korištenja (kada, koje analize, koliko)</li>
                <li>OIB tvrtke i adresa — za fakturiranje (Stripe ili manual)</li>
              </ul>
            </section>

            <section>
              <h2 className="font-serif text-2xl text-ink mb-3">
                2. Tko ima pristup
              </h2>
              <ul className="list-disc pl-6 space-y-2">
                <li>Članovi vaše organizacije s odgovarajućim pravima</li>
                <li>Super-admin za podršku (Marko Bašić)</li>
                <li>LLM provajder (Anthropic) — samo tekst za analizu, ne metapodaci</li>
                <li>Stripe — samo billing podaci za pretplatu</li>
              </ul>
            </section>

            <section>
              <h2 className="font-serif text-2xl text-ink mb-3">3. Vaša prava</h2>
              <p className="mb-3">Imate pravo na:</p>
              <ul className="list-disc pl-6 space-y-2">
                <li>Pristup svojim podacima</li>
                <li>Ispravak netočnih podataka</li>
                <li>Brisanje („pravo na zaborav”)</li>
                <li>Prijenos podataka u drugu uslugu</li>
                <li>Prigovor na obradu</li>
              </ul>
              <p className="mt-3">
                Za bilo koje od ovih, javite se na{" "}
                <a
                  href="mailto:privatnost@lexitor.eu"
                  className="text-signal hover:text-ink transition"
                >
                  privatnost@lexitor.eu
                </a>
                .
              </p>
            </section>

            <section>
              <h2 className="font-serif text-2xl text-ink mb-3">
                4. Sigurnost
              </h2>
              <p>
                Podaci se prenose preko HTTPS-a. Lozinke su hashirane (bcrypt).
                Dokumenti su pohranjeni u EU regiji (Frankfurt).
              </p>
            </section>

            <section>
              <h2 className="font-serif text-2xl text-ink mb-3">
                5. Kolačići
              </h2>
              <p>
                Koristimo isključivo funkcionalne kolačiće (session, theme
                preference). Bez tracking-a, bez third-party reklama, bez
                analytics izvan internih.
              </p>
            </section>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
