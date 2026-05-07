import Link from "next/link";

type Card = { href: string; title: string; text: string; soon?: boolean };

const cards: Card[] = [
  {
    href: "/analiza/troskovnik",
    title: "Analiza troškovnika",
    text: "Učitaj troškovnik i provjeri stavke protiv ZJN-a i prakse DKOM-a.",
  },
  {
    href: "/analiza/don",
    title: "Analiza DON-a",
    text: "Provjeri dokumentaciju o nabavi prije objave.",
  },
  {
    href: "/zalbe",
    title: "Žalbe",
    text: "Generiraj nacrt žalbe ili odgovora na žalbu.",
    soon: true,
  },
];

export default function DashboardPage() {
  return (
    <div className="max-w-5xl">
      <div className="mb-10">
        <p className="font-accent text-base text-muted italic mb-2">Mirno, precizno, suvremeno</p>
        <h1 className="font-display text-4xl text-ink mb-3">Dobro došli u Lexitor</h1>
        <p className="text-muted text-lg">
          Pregled nedavnih analiza i brzih akcija pojavit će se ovdje.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {cards.map((c) => (
          <Link
            key={c.href}
            href={c.href}
            className="group block rounded-lg border border-brand-border bg-surface p-6 hover:border-ink transition"
          >
            <div className="flex items-start justify-between">
              <h3 className="font-serif text-xl text-ink">{c.title}</h3>
              {c.soon && (
                <span className="text-[10px] uppercase tracking-wider text-gold">Faza 2</span>
              )}
            </div>
            <p className="mt-3 text-sm text-muted leading-relaxed">{c.text}</p>
            <p className="mt-4 text-sm text-signal opacity-0 group-hover:opacity-100 transition">
              Otvori →
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}
