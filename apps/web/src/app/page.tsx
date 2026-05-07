import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-surface text-ink">
      <header className="border-b border-brand-border">
        <div className="mx-auto max-w-6xl px-6 py-5 flex items-center justify-between">
          <Link href="/" className="font-display text-2xl font-semibold tracking-tight">
            Lexitor
          </Link>
          <nav className="flex items-center gap-7 text-sm text-navy">
            <Link href="/moduli/analiza-troskovnika" className="hover:text-signal">
              Moduli
            </Link>
            <Link href="/blog" className="hover:text-signal">
              Blog
            </Link>
            <Link href="/o-nama" className="hover:text-signal">
              O nama
            </Link>
            <a
              href={process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3001"}
              className="rounded-md bg-ink px-4 py-2 text-surface hover:bg-navy transition"
            >
              Prijavi se
            </a>
          </nav>
        </div>
      </header>

      <section className="mx-auto max-w-4xl px-6 py-28 text-center">
        <p className="font-accent text-lg text-muted mb-6 italic">
          Mirno, precizno, suvremeno
        </p>
        <h1 className="font-display text-5xl md:text-7xl font-medium tracking-tight text-ink leading-[1.05]">
          Usklađenost <span className="text-gold">bez stresa</span>.
        </h1>
        <p className="mt-8 text-lg md:text-xl text-muted leading-relaxed max-w-2xl mx-auto">
          Lexitor analizira DON i troškovnike protiv Zakona o javnoj nabavi i prakse
          DKOM-a. Detektira rizike <strong className="text-ink">prije</strong> nego
          dođe do žalbe.
        </p>
        <div className="mt-12 flex items-center justify-center gap-4">
          <a
            href={process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3001"}
            className="rounded-md bg-ink px-7 py-3.5 text-surface font-medium hover:bg-navy transition"
          >
            Pokušaj besplatno
          </a>
          <Link
            href="/moduli/analiza-troskovnika"
            className="rounded-md border border-brand-border px-7 py-3.5 text-ink hover:border-navy transition"
          >
            Saznaj više
          </Link>
        </div>
      </section>

      <section className="border-t border-brand-border bg-surface-2">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <h2 className="font-serif text-3xl text-ink mb-12 text-center">
            Tri ključne sposobnosti
          </h2>
          <div className="grid gap-8 md:grid-cols-3">
            <Capability
              title="Detekcija prekršaja"
              text="Šest tipova kršenja Zakona o javnoj nabavi prepoznaje se u troškovnicima i DON-ovima."
            />
            <Capability
              title="Generiranje dokumenata"
              text="Nacrti žalbi, odgovora na žalbe i zahtjeva za pojašnjenje s pravnom argumentacijom."
            />
            <Capability
              title="Praćenje ishoda"
              text="Sustav uči iz stvarnih DKOM/VUS odluka i veže ih uz korisničke slučajeve."
            />
          </div>
        </div>
      </section>

      <footer className="border-t border-brand-border">
        <div className="mx-auto max-w-6xl px-6 py-10 text-sm text-muted flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
          <p>
            © {new Date().getFullYear()} Lexitor.{" "}
            <span className="text-ink/60">Powered by Arhigon d.o.o.</span>
          </p>
          <nav className="flex gap-6">
            <Link href="/o-nama" className="hover:text-ink">
              O nama
            </Link>
            <Link href="/uvjeti" className="hover:text-ink">
              Uvjeti
            </Link>
            <Link href="/privatnost" className="hover:text-ink">
              Privatnost
            </Link>
            <Link href="/kontakt" className="hover:text-ink">
              Kontakt
            </Link>
          </nav>
        </div>
      </footer>
    </main>
  );
}

function Capability({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-lg border border-brand-border bg-surface p-7">
      <h3 className="font-serif text-xl text-ink mb-3">{title}</h3>
      <p className="text-muted leading-relaxed">{text}</p>
    </div>
  );
}
