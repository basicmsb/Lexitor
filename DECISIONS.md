# DECISIONS.md - Lexitor tracker odluka

> Živi dokument koji prati sve donesene odluke i otvorena pitanja.
> Ažurira se kontinuirano kako projekt napreduje.

---

## 📑 Sadržaj

- [Kako koristiti ovaj dokument](#kako-koristiti-ovaj-dokument)
- [Donesene odluke](#donesene-odluke)
  - [Strategija i poslovni model](#strategija-i-poslovni-model)
  - [Korisnici i tržište](#korisnici-i-tržište)
  - [Funkcionalnosti](#funkcionalnosti)
  - [Tehnologija](#tehnologija)
  - [Pravni okvir](#pravni-okvir)
- [Otvorena pitanja](#otvorena-pitanja)
  - [Kritična (blokiraju razvoj)](#kritična-blokiraju-razvoj)
  - [Važna (potrebna prije sljedeće faze)](#važna-potrebna-prije-sljedeće-faze)
  - [Nice to have (možemo kasnije)](#nice-to-have-možemo-kasnije)

---

## Kako koristiti ovaj dokument

### Format zapisa

Svaka odluka ima:
- **ID** (npr. `D-001`)
- **Datum donošenja**
- **Kategoriju**
- **Status** (📌 odlučeno / 🤔 raspravlja se / ❌ odbijeno)
- **Kontekst** (zašto se uopće postavilo pitanje)
- **Odluka** (što je odlučeno)
- **Obrazloženje** (zašto)
- **Implikacije** (što ovo znači za razvoj)

### Kako dodati novu odluku

```markdown
### D-XXX: [Naslov odluke]
- **Datum:** YYYY-MM-DD
- **Kategorija:** [strategija / korisnici / funkcionalnosti / tehnologija / pravo]
- **Status:** 📌 odlučeno
- **Kontekst:** [zašto se postavilo pitanje]
- **Odluka:** [što je odlučeno]
- **Obrazloženje:** [zašto]
- **Implikacije:** [posljedice]
```

---

## Donesene odluke

### Strategija i poslovni model

#### D-001: Lexitor je samostalan SaaS proizvod (a ne Arhigon modul)
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Kontekst:** Trebamo li Lexitor graditi kao modul unutar Arhigon aplikacije ili kao zaseban proizvod?
- **Odluka:** Samostalan SaaS proizvod, vlasnik Arhigon d.o.o.
- **Obrazloženje:** Tržište je puno veće od samo Arhigon korisnika; SaaS model omogućuje nezavisnu monetizaciju; tehnička arhitektura već podržava ovo (vanjska aplikacija s API-jem).
- **Implikacije:** Trebamo full SaaS infrastrukturu (registracija, billing, marketing); Arhigon je prvi enterprise klijent.

#### D-002: Brand i domena
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Kontekst:** Treba odabrati ime i domenu.
- **Odluka:** Lexitor, lexitor.eu
- **Obrazloženje:** Latinski "Lex" + sufiks "itor" (onaj koji se brine za zakon). Internacionalno, profesionalno, skalabilno na EU tržište.
- **Implikacije:** Branding mora biti latinsko-elegantni feel; domena već registrirana.

#### D-003: Subtilna povezanost s Arhigon brendom
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Kontekst:** Treba li Lexitor vizualno biti povezan s Arhigon-om?
- **Odluka:** Da, ali subtilno - "by Arhigon" u footeru, ne kao primarni brand.
- **Obrazloženje:** Daje kredibilitet (Arhigon je etabliran), ali ne ograničava Lexitor na Arhigon ekosustav.
- **Implikacije:** Logo i UI Lexitor-a su primarni; Arhigon spomenut u footeru i About sekciji.

#### D-004: Tržišna strategija - HR → eks-Yu → EU
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Kontekst:** Koja tržišta i kojim redoslijedom?
- **Odluka:** Faza 1-2: HR. Faza 3: SI, BiH. Faza 4: SR, ME, MK. Faza 5: EU (DE, AT, IT...).
- **Obrazloženje:** Tehnička platforma je univerzalna - mijenja se samo pravna baza; eks-Yu je prirodni sljedeći korak (sličan jezik, slična pravna tradicija).
- **Implikacije:** Sustav mora biti i18n-ready od dana 1; svaka zemlja traži lokalnog pravnika za validaciju.

#### D-005: EOJN integracija - reaktivna, ne proaktivna
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Kontekst:** Trebamo li aktivno tražiti integraciju s EOJN sustavom države?
- **Odluka:** Ne aktivno - oni dolaze nama kad budu spremni. Mi ostajemo PDF-import-first.
- **Obrazloženje:** Pregovaranje s državom traje godinama; bolja pozicija je "imamo proizvod, oni dolaze nama"; PDF import radi za 95%+ slučajeva.
- **Implikacije:** Investiramo u kvalitetan PDF parser, ne u API integracije s državom.

---

### Korisnici i tržište

#### D-010: Pet tipova korisnika
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Odluka:** Projektant, Naručitelj, Ponuditelj, Pravnik/Stručnjak za JN, Konzultantska kuća.
- **Obrazloženje:** Pokrivamo cijeli životni ciklus postupka javne nabave - od pripreme dokumentacije do žalbenog postupka.
- **Implikacije:** UI mora podržavati različite perspektive; Tier sustav prilagođen različitim potrebama.

#### D-011: Tier model (5 razina pretplate)
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Odluka:**
  - Free Trial (0 EUR, 3 analize/mj)
  - Solo (49 EUR, 20 analiza/mj)
  - Team (149 EUR, 100 analiza/mj, do 5 osoba)
  - Premium (299 EUR, 250 analiza/mj, sinkrona kolaboracija, privatnost)
  - Enterprise (po dogovoru, neograničeno)
- **Obrazloženje:** Pokrivamo različite veličine korisnika; pricing je orijentacijski - finalno se određuje nakon validacije.
- **Implikacije:** Razvoj billing sustava; Stripe integracija; usage metering.

---

### Funkcionalnosti

#### D-020: Tier 1 prekršaji (6 tipova)
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno (čeka pravničku validaciju)
- **Odluka:**
  - 1.1 Brendovi bez "ili jednakovrijedno"
  - 1.2 Diskriminatorne tehničke specifikacije
  - 1.3 Nepotpuni opisi stavki
  - 1.4 Manipulacije jediničnim cijenama
  - 1.5 Nedosljednost DON-a i troškovnika
  - 1.6 Komplet vs pojedinačne stavke
- **Obrazloženje:** Pokriva ~80% svih problema u praksi; analizirano na uzorku DKOM/VUS odluka.
- **Implikacije:** Razvoj 6 specijaliziranih prompts; ground truth set mora pokrivati sve 6 kategorija.

#### D-021: Knowledge Graph od dana 1
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Kontekst:** Treba li Knowledge Graph biti dio MVP-a ili kasnije?
- **Odluka:** Da, od dana 1 - barem osnovna verzija.
- **Obrazloženje:** Pravni izvori se međusobno referenciraju; bez KG-a sustav vidi samo izolirane dokumente; suprotne odluke (DKOM vs VUS) traže razumijevanje hijerarhije.
- **Implikacije:** PostgreSQL + custom graph queries za PoC; mogući prelazak na Neo4j kasnije.

#### D-022: Feedback sustav - sva 4 sloja od MVP-a
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Odluka:** Sloj 1 (korekcije analize), Sloj 2 (izmjene generiranih dokumenata), Sloj 3 (ocjene relevantnosti), Sloj 4 (stvarni DKOM/VUS ishodi).
- **Obrazloženje:** Konkurentska prednost ("data moat") - što ranije počnemo skupljati, to bolji sustav.
- **Implikacije:** UI mora omogućavati feedback; auto-tracker za DKOM ishode; tier-based privacy.

#### D-023: Privacy/sharing - Tier model
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Odluka:** Standard tier dijeli (anonimizirano), Premium tier privatno.
- **Obrazloženje:** Korisnici plaćaju za privatnost; jeftiniji tier dijeli sa zajednicom učenja.
- **Implikacije:** Anonimizacijski layer; eksplicitan consent u Terms of Service.

#### D-024: DKOM auto-tracking (scraper + manualno)
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Odluka:** Hibrid - automatski scraper za nove odluke + manualno (korisnik unese KLASA broj).
- **Obrazloženje:** Auto-scraper hvata većinu, ali korisnik može linkati ranije ako sustav ne uspije.
- **Implikacije:** Scheduled job (dnevni); UI za manualno povezivanje.

#### D-025: Generiranje dokumenata u Fazi 2
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Odluka:** Žalba, odgovor na žalbu, zahtjev za pojašnjenje (po važnosti).
- **Obrazloženje:** Najvažnije za korisnike; postupno pristup smanjuje rizik.
- **Implikacije:** Pravnik aktivno uključen u Fazu 2; svaki tip dokumenta validiran prije puštanja.

#### D-026: Human-in-the-loop od početka
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Odluka:** Pravnik može pregledati prije slanja - ugrađeno u dizajn od početka.
- **Obrazloženje:** Pravna odgovornost; kvaliteta generiranih dokumenata; zaštita korisnika.
- **Implikacije:** Approval workflow u UI-ju; audit log; status prikazi.

#### D-027: Asinkrona kolaboracija u MVP, sinkrona kasnije
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Odluka:** Faza 2 = asinkrona (track changes, komentari). Faza 3 = sinkrona (Google Docs stil).
- **Obrazloženje:** Asinkrona pokriva 90% potreba i puno je lakša za razvoj; sinkrona dolazi kao premium funkcionalnost.
- **Implikacije:** Asinkrona u 2-3 tjedna, sinkrona u 6-10 tjedana.

#### D-028: PDF parsing - hibrid (open source + Azure premium)
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Odluka:** Razina B+ - default je open source (pdfplumber + Camelot + Tesseract), premium je Azure AI Document Intelligence (po izboru).
- **Obrazloženje:** Niski operativni trošak za 95% slučajeva; premium kvaliteta dostupna kad treba; korisnik kontrolira trošak.
- **Implikacije:** Razvoj parsera u 6 tjedana (3 + 3 za Azure layer); fallback logika.

---

### Tehnologija

#### D-030: Python + FastAPI kao primarni stack
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Odluka:** Python 3.11+, FastAPI, Pydantic v2, Celery, Redis.
- **Obrazloženje:** Najbolji ekosustav za AI/RAG; brži razvoj od .NET-a; FastAPI je modern standard.
- **Implikacije:** Treba Python developer (ne samo .NET); .NET ostaje za Arhigon integraciju (komunicira preko API-ja).

#### D-031: Claude Sonnet 4.5 kao primarni LLM
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Odluka:** Anthropic Claude Sonnet 4.5 + Citations API.
- **Obrazloženje:** Najbolji za hrvatski jezik; veliki context window (200K tokens); Citations smanjuju halucinacije.
- **Implikacije:** Anthropic API ovisnost; treba budget za API pozive.

#### D-032: Cohere embed-multilingual-v3 za embeddings
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Odluka:** Cohere multilingual embedding model.
- **Obrazloženje:** Najbolji multilingvalni model za hrvatski; besplatna trial razina dovoljna za PoC.
- **Implikacije:** Cohere API ovisnost (uz Anthropic).

#### D-033: Qdrant kao vektorska baza
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Odluka:** Qdrant (self-hosted u Azure Container Apps).
- **Obrazloženje:** Otvoreni kod; brz; samohostani = niži trošak; dobra Python integracija.
- **Implikacije:** Treba upravljati infrastrukturom (vs managed Pinecone); ali znatno niži troškovi.

#### D-034: PostgreSQL kao glavna baza
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Odluka:** Azure Database for PostgreSQL (managed verzija).
- **Obrazloženje:** Industry standard; ACID transakcije za billing/audit; pgvector mogućnost za embeddings; JSON support.
- **Implikacije:** Standard relacijska baza; alembic za migracije.

#### D-035: Azure cloud
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Odluka:** Microsoft Azure (West Europe primary).
- **Obrazloženje:** Arhigon (vlasnik) već koristi Azure - operativna konzistencija; postojeća ekspertiza.
- **Implikacije:** Azure-first arhitektura; ali ne lock-in (kontejneri se mogu prebaciti).

#### D-036: UI - Next.js 14 od dana 1 (Streamlit preskočen)
- **Datum:** 2026-05-07 (revidirano)
- **Status:** 📌 odlučeno
- **Kontekst:** Inicijalno je plan bio Streamlit za PoC pa Next.js u Fazi 2. Nakon definicije strukture (web + app + blog + moduli + streaming UI), Streamlit ne pokriva potrebe.
- **Odluka:** **Next.js 14 + Tailwind + shadcn/ui od dana 1.** Bez Streamlit faze.
- **Obrazloženje:** Streamlit ne radi za SEO landing (lexitor.eu), blog, routing po modulima, ni streaming prikaz analize. Pisanje UI-a dvaput je gubljenje vremena. Brand brief već cilja "Linear/Notion/Vercel feel" — to je Next.js teritorij.
- **Implikacije:** Početni razvoj malo sporiji, ali ne radimo migraciju kasnije; Frontend tim trči odmah na finalnoj tehnologiji.

#### D-043: Monorepo (pnpm workspaces) struktura
- **Datum:** 2026-05-07
- **Status:** 📌 odlučeno
- **Kontekst:** Trebamo razdvojiti Web (lexitor.eu) i App (app.lexitor.eu), ali dijeliti komponente i types.
- **Odluka:** Monorepo s **pnpm workspaces**: `apps/backend` (FastAPI), `apps/web` (Next.js marketing), `apps/app` (Next.js auth), `packages/ui`, `packages/types`, `packages/config`.
- **Obrazloženje:** Code reuse kroz shared packages, jedan git repo, ali nezavisni deploy-i. Standardni pristup za moderne SaaS arhitekture.
- **Implikacije:** Treba pnpm 9+, Node 20+. Dodatna razina foldera (apps/, packages/) — sav backend kod sad u `apps/backend/`.

#### D-044: Web vs App razdvojeno na poddomene (sigurnost)
- **Datum:** 2026-05-07
- **Status:** 📌 odlučeno
- **Kontekst:** Treba odlučiti između jednog Next.js projekta s route grupama vs dva odvojena projekta na poddomenama.
- **Odluka:** **Dva odvojena projekta**, deploy na različite poddomene: `lexitor.eu` (web) i `app.lexitor.eu` (app).
- **Obrazloženje:** Origin isolation — XSS na blogu ne može ukrasti session cookie iz app-a. App može imati strogi CSP bez utjecaja na marketing 3rd-party scripte (GA, Calendly). Pravna dokumentacija = osjetljivi podaci, zaslužuje strogu izolaciju. Industry standard za sigurnosno svjesne SaaS-ove (Stripe, Supabase, Auth0).
- **Implikacije:** Different origin = treba CORS konfiguracija za API. White-label opcija je lakša (rebrand poddomene).

#### D-045: Streaming analize kroz Server-Sent Events (SSE)
- **Datum:** 2026-05-07
- **Status:** 📌 odlučeno
- **Kontekst:** Korisnik može vidjeti rezultate analize stavku-po-stavku, ne tek nakon završetka.
- **Odluka:** **Server-Sent Events (SSE)** preko FastAPI EventSourceResponse. Eventi: `item_started`, `item_completed`, `analysis_complete`, `error`.
- **Obrazloženje:** SSE je jednostavniji od WebSocket-a, dovoljan za jedan smjer (server→klijent), izvorno podržan u browserima (`EventSource` API). FastAPI native podrška kroz `sse-starlette`.
- **Implikacije:** Trebamo `sse-starlette` package, frontend hook `useEventSource`, fallback na polling za starije browser-e.

#### D-046: Blog i upute u MDX (ne CMS)
- **Datum:** 2026-05-07
- **Status:** 📌 odlučeno
- **Odluka:** Blog (web) i Upute za korištenje (app) pišu se u **MDX** datotekama unutar repa.
- **Obrazloženje:** Bez CMS troška, developer/PM commitira u git, brzo i jednostavno za PoC fazu. Migracija na headless CMS (Sanity/Contentful) je opcija u fazi komercijalizacije ako non-tech tim počne pisati.
- **Implikacije:** `@next/mdx` + remark/rehype plugin-ovi, `apps/web/content/blog/*.mdx`, `apps/app/content/upute/*.mdx`.

#### D-047: `.arhigonfile` format — interni Arhigon export
- **Datum:** 2026-05-07
- **Status:** 🤔 čeka specifikaciju
- **Kontekst:** Treba podržati treći upload format pored PDF i XLSX — interni `.arhigonfile` koji se exportira iz Arhigon-Ured aplikacije.
- **Odluka:** Parser će biti dio `apps/backend/src/document_parser/arhigon_parser.py`, čeka specifikacija formata.

#### D-037: LangChain za RAG orkestraciju
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Odluka:** LangChain za standardne RAG dijelove, custom kod za kritične.
- **Obrazloženje:** Mnogo gotovih komponenti; štedi vrijeme; ali ima neke probleme s apstrakcijom.
- **Implikacije:** Treba pratiti LangChain promjene; custom kod gdje je važno.

---

### Pravni okvir

#### D-040: Lexitor je informativan alat, ne pravna usluga
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Odluka:** Pozicioniramo Lexitor kao "AI alat za pomoć", ne "online pravna usluga".
- **Obrazloženje:** Regulatorni razlozi - pravne usluge su regulirane; alati su slobodni.
- **Implikacije:** Disclaimer u UI-ju; Terms of Service jasno navode da nije pravni savjet; korisnik je autor finalnog dokumenta.

#### D-041: Disclaimer obavezan
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Odluka:** Korisnik mora prihvatiti disclaimer prije prve analize.
- **Obrazloženje:** Pravna zaštita Arhigon-a; informiranost korisnika.
- **Implikacije:** Modal sa disclaimer-om pri onboardingu; tekst pregledan od strane pravnika.

#### D-042: GDPR compliance od dana 1
- **Datum:** 2026-05-06
- **Status:** 📌 odlučeno
- **Odluka:** Sustav je GDPR compliant od dana 1 (EU data residency, eksplicitan consent, pravo na brisanje, audit log).
- **Obrazloženje:** Zakonski obavezno za EU tržište; lakše implementirati od početka.
- **Implikacije:** Azure West Europe kao primary region; consent management; data export funkcionalnost.

---

## Otvorena pitanja

### Kritična (blokiraju razvoj)

#### Q-001: Validacija Tier 1 prekršaja sa pravnikom
- **Status:** 🤔 čeka rješenje
- **Pitanje:** Jesu li definicije 6 Tier 1 prekršaja pravnički točne i kompletne?
- **Tko odlučuje:** Pravnik / Stručnjak za JN (vanjski savjetnik)
- **Rok:** Prije Faze 1A početka
- **Posljedice ako ne riješeno:** Ne možemo pisati prompts za AI; risk lošeg PoC-a.

#### Q-002: Tekst disclaimer-a
- **Status:** 🤔 čeka rješenje
- **Pitanje:** Točan tekst disclaimer-a koji korisnik mora prihvatiti?
- **Tko odlučuje:** Pravnik (validacija) + PM (tekst)
- **Rok:** Prije objave Faze 1A za testne korisnike
- **Posljedice ako ne riješeno:** Pravna izloženost.

#### Q-003: Koja je 'minimalna pravna baza' za PoC?
- **Status:** 🤔 čeka rješenje
- **Pitanje:** Koliko DKOM odluka, VUS presuda, Sud EU presuda treba minimum za smisleni PoC?
- **Predlaganje:** 50 DKOM + 20 VUS + 5 Sud EU + cijeli ZJN + ključni pravilnici
- **Tko odlučuje:** PM + Pravnik
- **Rok:** Prije Sprint-a 3 Faze 1A
- **Posljedice ako ne riješeno:** Sustav nedovoljno upućen; loše predikcije.

### Važna (potrebna prije sljedeće faze)

#### Q-010: Cjenovni model - validacija
- **Status:** 🤔 raspravlja se
- **Pitanje:** Jesu li 49/149/299 EUR cijene optimalne?
- **Tko odlučuje:** PM nakon korisničkih intervjua
- **Rok:** Prije komercijalnog launcha (Faza K)

#### Q-011: White-label opcija - opseg
- **Status:** 🤔 raspravlja se
- **Pitanje:** Koliko duboko ide white-label opcija (samo logo? Custom domena? Custom funkcionalnosti?)
- **Tko odlučuje:** PM
- **Rok:** Prije Faze 3

#### Q-012: API pricing
- **Status:** 🤔 raspravlja se
- **Pitanje:** Kako naplaćivati API pristup za enterprise klijente (Arhigon, druge softvere)?
- **Tko odlučuje:** PM
- **Rok:** Prije Faze K

#### Q-013: Pravnička partnerstva
- **Status:** 🤔 raspravlja se
- **Pitanje:** Treba li uspostaviti partnerstva sa pravničkim uredima specijaliziranim za JN?
- **Tko odlučuje:** PM
- **Rok:** Tijekom Faze 2

#### Q-014: Edukacijska komponenta
- **Status:** 🤔 raspravlja se
- **Pitanje:** Treba li Lexitor imati edukacijski mod za studente prava ili junior pravnike?
- **Tko odlučuje:** PM
- **Rok:** Faza 3+

### Nice to have (možemo kasnije)

#### Q-020: Mobile app
- **Status:** 🤔 niski prioritet
- **Pitanje:** Treba li nativna iOS/Android aplikacija?
- **Trenutni stav:** Web responsive je dovoljno za sad.

#### Q-021: Voice interface
- **Status:** 🤔 niski prioritet
- **Pitanje:** Glasovni unos za pravnike (diktat)?
- **Trenutni stav:** Možda u dalekoj budućnosti.

#### Q-022: Integracije s drugim alatima
- **Status:** 🤔 niski prioritet
- **Pitanje:** Microsoft Word plugin? Google Docs ekstenzija?
- **Trenutni stav:** Možda nakon širenja.

#### Q-023: Chatbot interface
- **Status:** 🤔 niski prioritet
- **Pitanje:** Conversational interface za korisnike?
- **Trenutni stav:** Strukturirani UI je bolji za ovaj domain.

---

## Promjene odluka (changelog)

> Ako se neka odluka promijeni, ovdje se bilježi.

*(Trenutno nema promjena - svjež dokument.)*

---

## 📚 Reference

- [README.md](./README.md) - glavni overview
- [PROJECT.md](./PROJECT.md) - poslovni kontekst
- [ARCHITECTURE.md](./ARCHITECTURE.md) - tehnička arhitektura
- [PHASES.md](./PHASES.md) - fazni plan razvoja
- [FOR_DEVELOPER.md](./FOR_DEVELOPER.md) - praktičan brief

---

*Verzija: 1.0 | Svibanj 2026 | Lexitor by Arhigon*
*Sljedeće ažuriranje: kontinuirano kako odluke padaju*
