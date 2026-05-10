import Link from "next/link";

import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";

const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3001";

type Plan = {
  name: string;
  price: string;
  period: string;
  description: string;
  features: string[];
  cta: string;
  ctaHref: string;
  featured?: boolean;
};

const plans: Plan[] = [
  {
    name: "Trial",
    price: "0 €",
    period: "30 dana",
    description: "Probaj prije nego odlučiš.",
    features: [
      "3 DON analize",
      "1 modul po izboru",
      "Email podrška (najduže 3 dana)",
      "Bez kartice",
    ],
    cta: "Pokušaj besplatno",
    ctaHref: APP_URL,
  },
  {
    name: "Pro",
    price: "149 €",
    period: "mjesečno · po modulu",
    description: "Za profesionalce s redovnim radom na nabavama.",
    features: [
      "50 analiza mjesečno po modulu",
      "Svi moduli dostupni",
      "DKOM presedan citati",
      "PDF izvještaji",
      "Prioritetna podrška (24h)",
      "Tim do 5 članova",
    ],
    cta: "Aktiviraj pretplatu",
    ctaHref: APP_URL,
    featured: true,
  },
  {
    name: "Enterprise",
    price: "Kontakt",
    period: "po dogovoru",
    description: "Za organizacije s velikim opsegom rada.",
    features: [
      "Neograničene analize",
      "Svi moduli + custom integracije",
      "On-premise opcija",
      "API pristup",
      "Dedicirani account manager",
      "SLA + manualna faktura",
    ],
    cta: "Razgovaraj s nama",
    ctaHref: "/kontakt",
  },
];

const comparisonRows = [
  { label: "Broj korisnika", trial: "1", pro: "5", enterprise: "Neograničeno" },
  { label: "DON analiza", trial: "3", pro: "50 / mj", enterprise: "Neograničeno" },
  { label: "Troškovnik analiza", trial: "—", pro: "50 / mj", enterprise: "Neograničeno" },
  { label: "Žalbe asistent", trial: "—", pro: "10 / mj", enterprise: "Neograničeno" },
  { label: "DKOM presedan citati", trial: "✓", pro: "✓", enterprise: "✓" },
  { label: "PDF izvještaj", trial: "✓", pro: "✓", enterprise: "✓ + branding" },
  { label: "API pristup", trial: "—", pro: "—", enterprise: "✓" },
  { label: "On-premise instalacija", trial: "—", pro: "—", enterprise: "✓" },
  { label: "SLA", trial: "—", pro: "—", enterprise: "✓" },
];

const addons = [
  {
    title: "Onboarding s konzultantom",
    text: "1h sesija sa naprednim korisnikom Lexitor-a. Pomoć s prvim učitavanjem, postavljanjem tima i workflow-om.",
  },
  {
    title: "Dodatne analize",
    text: "Ako prekoračiš mjesečnu kvotu, dodatne analize naplaćuju se 4 € po analizi (Pro) ili po dogovoru (Enterprise).",
  },
  {
    title: "Prilagođeni izvještaji",
    text: "Custom PDF template-i s tvojim brandiranjem, automatski izvoz u tvoj DMS sustav.",
  },
];

const faqs = [
  {
    q: "Mogu li otkazati pretplatu bilo kad?",
    a: "Da, otkazom u postavkama. Pretplata vrijedi do kraja platnog razdoblja, refunda nema osim u slučaju tehničkog problema.",
  },
  {
    q: "Plaćam li po korisniku ili po analizi?",
    a: "Pro plan ima fiksnu cijenu po modulu (149 €/mj) s kvotom od 50 analiza/mj. Enterprise je po dogovoru, obično neograničeno.",
  },
  {
    q: "Postoji li godišnja pretplata s popustom?",
    a: "Da — godišnja je 15% jeftinija (149 €/mj × 12 − 15% = ~1518 € godišnje umjesto 1788 €).",
  },
  {
    q: "Kako se izračunavaju kvote?",
    a: "Po kalendarskom mjesecu, resetira se 1. u mjesecu. Neiskorišteni kvota se ne prenosi.",
  },
  {
    q: "Što ako mi treba i Žalbe modul kad bude dostupan?",
    a: "Pro plan automatski uključuje sve module dok ih razvijamo. Trenutno: DON i Troškovnik. Žalbe stiže u Q3 2026.",
  },
];

export default function CjenikPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1">
        {/* HERO */}
        <section className="bg-[#0B1320] text-[#F7F5F0]">
          <div className="mx-auto max-w-4xl px-6 py-20 text-center">
            <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-gold mb-5">
              Cjenik
            </p>
            <h1 className="font-display text-5xl md:text-6xl font-medium tracking-tight leading-[1.05]">
              Plaćaš{" "}
              <em className="text-gold not-italic font-serif italic">analize</em>,
              <br />
              ne licence.
            </h1>
            <p className="mt-8 text-lg text-[#F7F5F0]/70 leading-relaxed max-w-2xl mx-auto">
              Bez minimalnih ugovora, bez setup naplate, bez korisničkih licenci.
              Plaćaš pretplatu po modulu — koliko trebaš, toliko platiš.
            </p>
          </div>
        </section>

        {/* PRICING CARDS */}
        <section className="border-b border-brand-border">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="grid gap-6 md:grid-cols-3 items-start">
              {plans.map((plan) => (
                <div
                  key={plan.name}
                  className={`rounded-lg p-7 flex flex-col ${
                    plan.featured
                      ? "border-2 border-gold bg-[#0B1320] text-[#F7F5F0] shadow-xl md:-translate-y-4"
                      : "border border-brand-border bg-surface"
                  }`}
                >
                  {plan.featured && (
                    <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-gold mb-3">
                      Najpopularniji
                    </p>
                  )}
                  <h3
                    className={`font-serif text-2xl mb-2 ${
                      plan.featured ? "text-[#F7F5F0]" : "text-ink"
                    }`}
                  >
                    {plan.name}
                  </h3>
                  <p
                    className={`text-sm mb-5 ${
                      plan.featured ? "text-[#F7F5F0]/70" : "text-muted"
                    }`}
                  >
                    {plan.description}
                  </p>
                  <div className="mb-6">
                    <span
                      className={`font-display text-5xl ${
                        plan.featured ? "text-[#F7F5F0]" : "text-ink"
                      }`}
                    >
                      {plan.price}
                    </span>
                    <span
                      className={`block text-xs mt-1 ${
                        plan.featured ? "text-[#F7F5F0]/50" : "text-muted"
                      }`}
                    >
                      {plan.period}
                    </span>
                  </div>
                  <ul
                    className={`space-y-3 text-sm flex-1 mb-7 ${
                      plan.featured ? "text-[#F7F5F0]/80" : "text-navy"
                    }`}
                  >
                    {plan.features.map((f) => (
                      <li key={f} className="flex items-start gap-2">
                        <span
                          className={
                            plan.featured ? "text-gold" : "text-status-ok"
                          }
                        >
                          ✓
                        </span>
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                  {plan.ctaHref.startsWith("/") ? (
                    <Link
                      href={plan.ctaHref}
                      className={`block text-center rounded-md px-5 py-3 font-medium transition ${
                        plan.featured
                          ? "bg-gold text-[#0B1320] hover:bg-gold/90"
                          : "border border-brand-border text-ink hover:border-ink"
                      }`}
                    >
                      {plan.cta}
                    </Link>
                  ) : (
                    <a
                      href={plan.ctaHref}
                      className={`block text-center rounded-md px-5 py-3 font-medium transition ${
                        plan.featured
                          ? "bg-gold text-[#0B1320] hover:bg-gold/90"
                          : "border border-brand-border text-ink hover:border-ink"
                      }`}
                    >
                      {plan.cta}
                    </a>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* USPOREDBA */}
        <section className="border-b border-brand-border bg-surface-2/40">
          <div className="mx-auto max-w-5xl px-6 py-20">
            <div className="text-center mb-12">
              <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-3">
                Detalji
              </p>
              <h2 className="font-serif text-3xl text-ink">
                Što dobivate{" "}
                <em className="text-gold not-italic font-serif italic">u svakom planu</em>
              </h2>
            </div>
            <div className="overflow-x-auto rounded-lg border border-brand-border bg-surface">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-brand-border bg-surface-2/50">
                    <th className="text-left p-4 text-muted text-[11px] uppercase tracking-wider">
                      Funkcionalnost
                    </th>
                    <th className="p-4 text-center text-muted text-[11px] uppercase tracking-wider">
                      Trial
                    </th>
                    <th className="p-4 text-center text-gold text-[11px] uppercase tracking-wider font-semibold">
                      Pro
                    </th>
                    <th className="p-4 text-center text-muted text-[11px] uppercase tracking-wider">
                      Enterprise
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonRows.map((row, idx) => (
                    <tr
                      key={row.label}
                      className={idx % 2 ? "bg-surface-2/30" : ""}
                    >
                      <td className="p-4 text-navy">{row.label}</td>
                      <td className="p-4 text-center text-muted">{row.trial}</td>
                      <td className="p-4 text-center text-ink font-medium">
                        {row.pro}
                      </td>
                      <td className="p-4 text-center text-navy">
                        {row.enterprise}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* ADDONS */}
        <section className="border-b border-brand-border">
          <div className="mx-auto max-w-5xl px-6 py-20">
            <div className="text-center mb-12">
              <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-3">
                Po potrebi
              </p>
              <h2 className="font-serif text-3xl text-ink">
                Dodatne usluge{" "}
                <em className="text-gold not-italic font-serif italic">kad ih trebate</em>
              </h2>
            </div>
            <div className="grid gap-6 md:grid-cols-3">
              {addons.map((a) => (
                <div
                  key={a.title}
                  className="rounded-lg border border-brand-border bg-surface p-6"
                >
                  <h3 className="font-serif text-lg text-ink mb-3">{a.title}</h3>
                  <p className="text-sm text-muted leading-relaxed">{a.text}</p>
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
              <h2 className="font-serif text-3xl text-ink">Pitanja o cijenku</h2>
            </div>
            <div className="space-y-3">
              {faqs.map((faq) => (
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
