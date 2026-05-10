import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";

export default function UvjetiPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1 border-b border-brand-border">
        <div className="mx-auto max-w-3xl px-6 py-20">
          <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-3">
            Pravno · ažurirano 11.05.2026.
          </p>
          <h1 className="font-display text-4xl md:text-5xl text-ink mb-6">
            Uvjeti korištenja
          </h1>
          <p className="text-muted leading-relaxed mb-10">
            Korištenjem usluge Lexitor prihvaćate sljedeće uvjete. Ova stranica
            je preliminarna verzija — pravni tim će objaviti finalnu prije
            javnog launch-a.
          </p>

          <div className="space-y-8 text-navy leading-relaxed">
            <section>
              <h2 className="font-serif text-2xl text-ink mb-3">
                1. Što je Lexitor
              </h2>
              <p>
                Lexitor je AI asistent za analizu Dokumentacije o nabavi (DON) i
                troškovnika. Pruža informativnu analizu na temelju Zakona o javnoj
                nabavi (NN 120/16, 114/22) i prakse DKOM-a. Lexitor{" "}
                <strong className="text-ink">nije pravnik</strong> i ne
                zamjenjuje pravnu prosudbu.
              </p>
            </section>

            <section>
              <h2 className="font-serif text-2xl text-ink mb-3">
                2. Odgovornost
              </h2>
              <p>
                Korisnik snosi punu odgovornost za odluke donesene na temelju
                Lexitor analize. Lexitor garantira best-effort kvalitetu, ali ne
                jamči 100% točnost — finalnu provjeru radi pravnik.
              </p>
            </section>

            <section>
              <h2 className="font-serif text-2xl text-ink mb-3">
                3. Pretplata i otkaz
              </h2>
              <p>
                Pretplate su mjesečne ili godišnje. Otkaz vrijedi od kraja
                tekućeg platnog razdoblja, bez refunda osim u slučaju tehničkog
                problema na strani Lexitor-a.
              </p>
            </section>

            <section>
              <h2 className="font-serif text-2xl text-ink mb-3">
                4. Intelektualno vlasništvo
              </h2>
              <p>
                Dokumenti koje učitavate ostaju vaše vlasništvo. Lexitor koristi
                anonimizirane statističke podatke za poboljšanje sustava (npr.
                koliko je puta detektiran brand_lock).
              </p>
            </section>

            <section>
              <h2 className="font-serif text-2xl text-ink mb-3">
                5. Promjene uvjeta
              </h2>
              <p>
                Lexitor može promijeniti uvjete s 30 dana prethodne najave. Ako
                se ne slažete s promjenom, možete otkazati pretplatu prije
                stupanja na snagu.
              </p>
            </section>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
