import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-brand-border bg-surface-2/40">
      <div className="mx-auto max-w-6xl px-6 py-12">
        <div className="grid gap-10 md:grid-cols-4">
          <div>
            <Link
              href="/"
              className="font-display text-2xl font-semibold tracking-tight text-ink"
            >
              Lexitor
            </Link>
            <p className="mt-3 text-sm text-muted leading-relaxed">
              Mirno, precizno, suvremeno.
              <br />
              Usklađenost bez stresa.
            </p>
          </div>

          <div>
            <h4 className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-3">
              Proizvod
            </h4>
            <ul className="space-y-2 text-sm text-navy">
              <li>
                <Link href="/moduli/analiza-troskovnika" className="hover:text-ink transition">
                  Troškovnik
                </Link>
              </li>
              <li>
                <Link href="/moduli/analiza-don" className="hover:text-ink transition">
                  DON
                </Link>
              </li>
              <li>
                <Link href="/moduli/zalbe" className="hover:text-ink transition">
                  Žalbe
                </Link>
              </li>
              <li>
                <Link href="/cjenik" className="hover:text-ink transition">
                  Cjenik
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-3">
              Resursi
            </h4>
            <ul className="space-y-2 text-sm text-navy">
              <li>
                <Link href="/blog" className="hover:text-ink transition">
                  Blog
                </Link>
              </li>
              <li>
                <Link href="/o-nama" className="hover:text-ink transition">
                  O nama
                </Link>
              </li>
              <li>
                <Link href="/kontakt" className="hover:text-ink transition">
                  Kontakt
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-3">
              Pravno
            </h4>
            <ul className="space-y-2 text-sm text-navy">
              <li>
                <Link href="/uvjeti" className="hover:text-ink transition">
                  Uvjeti korištenja
                </Link>
              </li>
              <li>
                <Link href="/privatnost" className="hover:text-ink transition">
                  Privatnost
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-10 pt-6 border-t border-brand-border flex flex-col md:flex-row gap-4 items-start md:items-center justify-between text-sm text-muted">
          <p>
            © {new Date().getFullYear()} Lexitor.{" "}
            <span className="text-ink/60">Powered by Arhigon technologies d.o.o.</span>
          </p>
          <p className="text-xs">Zagreb, Hrvatska</p>
        </div>
      </div>
    </footer>
  );
}
