import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-screen">
      <header className="border-b border-slate-200">
        <div className="mx-auto max-w-6xl px-6 py-5 flex items-center justify-between">
          <Link href="/" className="font-serif text-2xl font-semibold tracking-tight">
            Lexitor
          </Link>
          <nav className="flex items-center gap-6 text-sm">
            <Link href="/moduli/analiza-troskovnika" className="hover:text-brand-600">
              Moduli
            </Link>
            <Link href="/blog" className="hover:text-brand-600">
              Blog
            </Link>
            <Link href="/o-nama" className="hover:text-brand-600">
              O nama
            </Link>
            <a
              href={process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3001"}
              className="rounded-md bg-brand-900 px-4 py-2 text-white hover:bg-brand-700"
            >
              Prijavi se
            </a>
          </nav>
        </div>
      </header>

      <section className="mx-auto max-w-4xl px-6 py-24 text-center">
        <h1 className="font-serif text-5xl md:text-6xl font-semibold tracking-tight text-slate-900">
          Usklađenost javne nabave{" "}
          <span className="text-brand-700">bez stresa</span>
        </h1>
        <p className="mt-6 text-lg md:text-xl text-slate-600 leading-relaxed">
          Lexitor analizira DON i troškovnike protiv Zakona o javnoj nabavi i prakse DKOM-a.
          Detektira rizike <strong>prije</strong> nego dođe do žalbe.
        </p>
        <div className="mt-10 flex items-center justify-center gap-4">
          <a
            href={process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3001"}
            className="rounded-md bg-brand-900 px-6 py-3 text-white font-medium hover:bg-brand-700"
          >
            Pokušaj besplatno
          </a>
          <Link
            href="/moduli/analiza-troskovnika"
            className="rounded-md border border-slate-300 px-6 py-3 text-slate-900 hover:border-slate-400"
          >
            Saznaj više
          </Link>
        </div>
      </section>

      <footer className="border-t border-slate-200 mt-24">
        <div className="mx-auto max-w-6xl px-6 py-10 text-sm text-slate-500 flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
          <p>© {new Date().getFullYear()} Lexitor. Powered by Arhigon d.o.o.</p>
          <nav className="flex gap-6">
            <Link href="/o-nama">O nama</Link>
            <Link href="/uvjeti">Uvjeti</Link>
            <Link href="/privatnost">Privatnost</Link>
            <Link href="/kontakt">Kontakt</Link>
          </nav>
        </div>
      </footer>
    </main>
  );
}
