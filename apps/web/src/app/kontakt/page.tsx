import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";

export default function KontaktPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1">
        <section className="bg-[#0B1320] text-[#F7F5F0]">
          <div className="mx-auto max-w-3xl px-6 py-20 text-center">
            <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-gold mb-5">
              Kontakt
            </p>
            <h1 className="font-display text-5xl md:text-6xl font-medium tracking-tight leading-[1.05]">
              Razgovor s{" "}
              <em className="text-gold not-italic font-serif italic">timom</em>
            </h1>
            <p className="mt-8 text-lg text-[#F7F5F0]/70 leading-relaxed">
              Pošalji nam upit, javit ćemo se u roku od 24h. Demo, pretplate,
              partnerstva, bugs — sve preko ovog forma.
            </p>
          </div>
        </section>

        <section className="border-b border-brand-border">
          <div className="mx-auto max-w-2xl px-6 py-20">
            <form className="space-y-5">
              <div className="grid md:grid-cols-2 gap-5">
                <div>
                  <label
                    htmlFor="name"
                    className="block text-sm font-medium text-ink mb-2"
                  >
                    Ime i prezime
                  </label>
                  <input
                    id="name"
                    type="text"
                    required
                    className="w-full rounded-md border border-brand-border bg-surface-2 px-4 py-2.5 text-sm text-ink focus:border-signal transition"
                  />
                </div>
                <div>
                  <label
                    htmlFor="email"
                    className="block text-sm font-medium text-ink mb-2"
                  >
                    Email
                  </label>
                  <input
                    id="email"
                    type="email"
                    required
                    className="w-full rounded-md border border-brand-border bg-surface-2 px-4 py-2.5 text-sm text-ink focus:border-signal transition"
                  />
                </div>
              </div>
              <div>
                <label
                  htmlFor="company"
                  className="block text-sm font-medium text-ink mb-2"
                >
                  Tvrtka / organizacija
                </label>
                <input
                  id="company"
                  type="text"
                  className="w-full rounded-md border border-brand-border bg-surface-2 px-4 py-2.5 text-sm text-ink focus:border-signal transition"
                />
              </div>
              <div>
                <label
                  htmlFor="topic"
                  className="block text-sm font-medium text-ink mb-2"
                >
                  Tema
                </label>
                <select
                  id="topic"
                  className="w-full rounded-md border border-brand-border bg-surface-2 px-4 py-2.5 text-sm text-ink focus:border-signal transition"
                >
                  <option>Demo i evaluacija</option>
                  <option>Enterprise pretplata</option>
                  <option>Partnerstvo</option>
                  <option>Tehnička podrška</option>
                  <option>Bug ili problem</option>
                  <option>Ostalo</option>
                </select>
              </div>
              <div>
                <label
                  htmlFor="message"
                  className="block text-sm font-medium text-ink mb-2"
                >
                  Poruka
                </label>
                <textarea
                  id="message"
                  rows={6}
                  required
                  className="w-full rounded-md border border-brand-border bg-surface-2 px-4 py-2.5 text-sm text-ink focus:border-signal transition resize-y"
                />
              </div>
              <button
                type="submit"
                className="w-full md:w-auto rounded-md bg-ink px-7 py-3 text-sm font-medium text-surface hover:bg-navy transition"
              >
                Pošalji upit
              </button>
            </form>

            <div className="mt-16 pt-10 border-t border-brand-border grid md:grid-cols-3 gap-8 text-sm">
              <div>
                <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-2">
                  Email
                </p>
                <a
                  href="mailto:hello@lexitor.eu"
                  className="text-ink hover:text-gold transition"
                >
                  hello@lexitor.eu
                </a>
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-2">
                  Adresa
                </p>
                <p className="text-ink">
                  Arhigon technologies d.o.o.
                  <br />
                  Zagreb, Hrvatska
                </p>
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-2">
                  Radno vrijeme
                </p>
                <p className="text-ink">
                  Pon–Pet: 09–17h
                  <br />
                  Odgovor: ≤24h
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
