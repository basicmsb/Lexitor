import Link from "next/link";

import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";

const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3001";

const fourThings = [
  {
    title: "Pravo, ne marketing",
    text: "Lexitor ne sugerira što „možda bi moglo biti” — vraća konkretan članak ZJN-a i DKOM presedan. Halucinacija je neprihvatljiva.",
  },
  {
    title: "Hrvatski jezik, hrvatsko pravo",
    text: "Sve odluke i sučelje na hrvatskom. Naša domena je RH praksa, ne EU generika. Specijalizirani, ne univerzalni.",
  },
  {
    title: "Transparentnost u svemu",
    text: "Vidiš tačno koji LLM koristimo, koliko košta, koje pravilo flagga što. Bez black-box-a.",
  },
  {
    title: "Pravnik je glavni",
    text: "Lexitor je asistent. Završnu odluku donosiš ti — pravnik, projektant, službenik. Lexitor pruža materijal, ti potpisuješ.",
  },
];

const team = [
  {
    initials: "MB",
    name: "Marko Bašić",
    role: "Founder",
    bio: "Inženjer s 12 godina iskustva u građevinarstvu i javnoj nabavi. Arhigon je njegov drugi proizvod nakon Arhigon Ured CRM-a.",
  },
  {
    initials: "IM",
    name: "Iva Martić",
    role: "Pravna baza",
    bio: "Dipl. iur., specijalizirana za pravo javne nabave. Validira ekstrahirane DKOM podatke.",
  },
  {
    initials: "TM",
    name: "Tomislav Magić",
    role: "Backend",
    bio: "Python + LLM engineer. RAG pipeline, DKOM extraction, deterministic rule engine.",
  },
  {
    initials: "AŠ",
    name: "Ana Šimić",
    role: "Frontend",
    bio: "Next.js + TailwindCSS. UI dizajn temelj iz Figme, dovedeno u kod.",
  },
  {
    initials: "MH",
    name: "Marija Horvat",
    role: "Customer Success",
    bio: "Onboarding novih korisnika, prikupljanje feedback-a, podrška u radu.",
  },
  {
    initials: "PJ",
    name: "Petar Jurić",
    role: "Pravni asistent",
    bio: "Specijalist za pretpregled DKOM odluka i identifikaciju pattern-a u praksi.",
  },
];

const timeline = [
  {
    year: "2024",
    title: "Arhigon — prvi proizvod",
    text: "CRM za inženjere u građevinarstvu. Radi do danas, korisno za 30+ tvrtki.",
  },
  {
    year: "2025",
    title: "PoC analize troškovnika",
    text: "Eksperiment s lokalnim LLM-om za detekciju brand-lock-a u Arhigon troškovnicima.",
  },
  {
    year: "2025",
    title: "DKOM scraping",
    text: "Prikupljeno 749 odluka, indeksirano u Qdrant + Cohere embeddings.",
  },
  {
    year: "2026",
    title: "Javna beta",
    text: "Lexitor dostupan kao zatvorena beta. Prvih 5 korisnika iz mreže Arhigon-a.",
  },
  {
    year: "2026",
    title: "Prva pretplata",
    text: "Prvi plaćeni korisnik — KBC Zagreb. Prelazak iz „besplatno za feedback” u proizvod.",
  },
];

const testimonials = [
  {
    initials: "M.V.",
    name: "Marko V.",
    role: "Voditelj nabave, javna ustanova",
    text: "Lexitor mi je u 10 minuta pronašao tri stvari za koje bih inače dao odvjetniku — i platio 800 €.",
  },
  {
    initials: "A.K.",
    name: "Ana K.",
    role: "Projektantica, Zagreb",
    text: "Konačno alat koji razumije Arhigon format i hrvatsku praksu. Strani AI alati ne znaju o ZJN-u ništa.",
  },
  {
    initials: "P.S.",
    name: "Petar S.",
    role: "Odvjetnik za javnu nabavu",
    text: "Kao asistent za pretraživanje DKOM presedana — neusporedivo brži od ručnog rada. Ali ne zamjenjuje pravnu prosudbu.",
  },
];

export default function ONamaPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1">
        {/* HERO */}
        <section className="bg-[#0B1320] text-[#F7F5F0]">
          <div className="mx-auto max-w-6xl px-6 py-20 grid md:grid-cols-2 gap-12 items-center">
            <div>
              <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-gold mb-5">
                O nama
              </p>
              <h1 className="font-display text-5xl md:text-6xl font-medium tracking-tight leading-[1.05]">
                Pravnici, inženjeri,
                <br />
                i jako puno{" "}
                <em className="text-gold not-italic font-serif italic">
                  DKOM odluka
                </em>
                .
              </h1>
              <p className="mt-8 text-lg text-[#F7F5F0]/70 leading-relaxed max-w-lg">
                Lexitor je drugi proizvod Arhigon-a — tvrtke koja od 2014. radi
                softver za inženjere u građevinarstvu. Sad pomažemo i u javnoj
                nabavi.
              </p>
            </div>
            <div className="rounded-lg border border-gold/30 bg-[#1A2332] p-7">
              <p className="font-accent text-xl text-[#F7F5F0]/90 italic leading-relaxed">
                „Žalbe pred DKOM-om su skup proces — za naručitelja i za
                ponuditelja. Lexitor smanjuje broj žalbi tako što flagga rizike
                prije nego što dokumentacija ode u javnost.”
              </p>
              <p className="mt-5 text-sm text-gold">— Marko Bašić, founder</p>
            </div>
          </div>
        </section>

        {/* VRIJEDNOSTI */}
        <section className="border-b border-brand-border">
          <div className="mx-auto max-w-4xl px-6 py-20 text-center">
            <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-3">
              Naš pristup
            </p>
            <h2 className="font-serif text-3xl md:text-4xl text-ink">
              Pravo treba biti{" "}
              <em className="text-gold not-italic font-serif italic">provjerljivo</em>,
              ne neprozirno.
            </h2>
            <p className="mt-6 text-lg text-muted leading-relaxed">
              Strani AI alati halu-ciniraju članke ZJN-a koji ne postoje. Lexitor
              radi obrnuto: <strong className="text-ink">svaki nalaz</strong>{" "}
              povezan je s realnim člankom i odlukom — koji možeš direktno
              provjeriti.
            </p>
          </div>
        </section>

        {/* 4 STVARI */}
        <section className="border-b border-brand-border bg-surface-2/40">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="text-center mb-14">
              <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-3">
                Naša filozofija
              </p>
              <h2 className="font-serif text-3xl md:text-4xl text-ink">
                Četiri stvari koje{" "}
                <em className="text-gold not-italic font-serif italic">
                  nećemo iznevjeriti
                </em>
              </h2>
            </div>
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
              {fourThings.map((t) => (
                <div
                  key={t.title}
                  className="rounded-lg border border-brand-border bg-surface p-6"
                >
                  <h3 className="font-serif text-lg text-ink mb-3">{t.title}</h3>
                  <p className="text-sm text-muted leading-relaxed">{t.text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* TIM */}
        <section className="border-b border-brand-border">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="text-center mb-14">
              <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-3">
                Tim
              </p>
              <h2 className="font-serif text-3xl md:text-4xl text-ink">
                Šest ljudi.{" "}
                <em className="text-gold not-italic font-serif italic">
                  Sedam godina prosječnog iskustva u nabavi.
                </em>
              </h2>
            </div>
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {team.map((m) => (
                <div
                  key={m.name}
                  className="rounded-lg border border-brand-border bg-surface p-6"
                >
                  <div className="flex items-center gap-4 mb-4">
                    <div className="w-12 h-12 rounded-full bg-surface-2 flex items-center justify-center font-display text-lg text-ink">
                      {m.initials}
                    </div>
                    <div>
                      <h3 className="font-serif text-lg text-ink">{m.name}</h3>
                      <p className="text-xs text-gold uppercase tracking-wider">
                        {m.role}
                      </p>
                    </div>
                  </div>
                  <p className="text-sm text-muted leading-relaxed">{m.bio}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* TIMELINE */}
        <section className="border-b border-brand-border bg-surface-2/40">
          <div className="mx-auto max-w-4xl px-6 py-20">
            <div className="text-center mb-14">
              <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-3">
                Putovanje
              </p>
              <h2 className="font-serif text-3xl md:text-4xl text-ink">
                Kako smo dospjeli{" "}
                <em className="text-gold not-italic font-serif italic">do ovdje</em>
              </h2>
            </div>
            <div className="space-y-6">
              {timeline.map((event) => (
                <div
                  key={event.title}
                  className="flex gap-8 items-start border-l-2 border-gold/30 pl-6 relative"
                >
                  <div className="absolute -left-2 top-1 w-3 h-3 rounded-full bg-gold" />
                  <div className="w-16 shrink-0 font-mono text-sm text-gold pt-1">
                    {event.year}
                  </div>
                  <div>
                    <h3 className="font-serif text-lg text-ink mb-1">
                      {event.title}
                    </h3>
                    <p className="text-sm text-muted leading-relaxed">{event.text}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* TESTIMONIALS */}
        <section className="border-b border-brand-border">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="text-center mb-14">
              <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-muted mb-3">
                Iz prakse
              </p>
              <h2 className="font-serif text-3xl md:text-4xl text-ink">
                Ljudi koji kažu{" "}
                <em className="text-gold not-italic font-serif italic">
                  kad smo krivi
                </em>
              </h2>
            </div>
            <div className="grid gap-6 md:grid-cols-3">
              {testimonials.map((t) => (
                <div
                  key={t.name}
                  className="rounded-lg border border-brand-border bg-surface p-6"
                >
                  <p className="font-accent text-base italic text-ink leading-relaxed mb-4">
                    „{t.text}”
                  </p>
                  <div className="flex items-center gap-3 pt-4 border-t border-brand-border">
                    <div className="w-10 h-10 rounded-full bg-surface-2 flex items-center justify-center font-display text-sm text-ink">
                      {t.initials}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-ink">{t.name}</p>
                      <p className="text-xs text-muted">{t.role}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* DARK CTA */}
        <section className="bg-[#0B1320] text-[#F7F5F0]">
          <div className="mx-auto max-w-4xl px-6 py-20 text-center">
            <h2 className="font-display text-4xl md:text-5xl">
              <em className="text-gold not-italic font-serif italic">Razgovaramo?</em>
            </h2>
            <p className="mt-5 text-[#F7F5F0]/70 text-lg max-w-xl mx-auto">
              Ako želiš pravi razgovor s timom — ne demo formu — javi se. Bilo
              kako, mejlom ili WhatsApp-om.
            </p>
            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link
                href="/kontakt"
                className="rounded-md bg-gold px-7 py-3.5 text-[#0B1320] font-medium hover:bg-gold/90 transition"
              >
                Kontaktiraj nas
              </Link>
              <a
                href={APP_URL}
                className="rounded-md border border-[#F7F5F0]/20 px-7 py-3.5 text-[#F7F5F0] hover:border-[#F7F5F0]/50 transition"
              >
                Otvori račun
              </a>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
