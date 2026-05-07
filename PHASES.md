# PHASES.md - Lexitor fazni plan razvoja

> Detaljan plan razvoja po fazama, sa zadacima, vlasnicima i kriterijima završetka.
> Namijenjeno PM-u i developerima za praćenje napretka.

---

## 📑 Sadržaj

- [Pregled svih faza](#pregled-svih-faza)
- [Faza 0: Predpriprema](#faza-0-predpriprema-pm-vlasnik)
- [Faza 1A: PoC - Core analiza](#faza-1a-poc---core-analiza)
- [Faza 1B: Ponuditelj kao perspektiva](#faza-1b-ponuditelj-kao-perspektiva)
- [Faza 2: Generiranje dokumenata](#faza-2-generiranje-dokumenata)
- [Faza 3: Strategic Advisor](#faza-3-strategic-advisor)
- [Komercijalizacija](#komercijalizacija)
- [Širenje na regiju](#širenje-na-regiju)

---

## Pregled svih faza

| Faza | Naziv | Trajanje | Status | Tim | Cilj |
|------|-------|----------|--------|-----|------|
| **0** | Predpriprema | 4-6 tjedana | 🔄 U tijeku | PM | Dokumentacija, pravna baza, dizajn |
| **1A** | PoC - Core analiza | 8-12 tjedana | ⏳ Slijedi | PM + Dev (Python) | AI razumije domenu |
| **1B** | Ponuditelj perspektiva | 4 tjedna | ⏳ | PM + Dev | Sustav radi i s druge strane |
| **2** | Generiranje dokumenata | 12-16 tjedana | ⏳ | PM + Dev + Pravnik | Lexitor piše dokumente |
| **3** | Strategic Advisor | 8-12 tjedana | ⏳ | PM + Dev + Pravnik | Inteligentni asistent |
| **K** | Komercijalizacija | 8-12 tjedana | ⏳ | Cijeli tim | Pravi korisnici, prihod |
| **Š** | Širenje (eks-Yu, EU) | 6+ mjeseci | ⏳ | Cijeli tim | Nova tržišta |

**Ukupno do MVP komercijalnog launcha:** ~12-15 mjeseci.

**Ukupno do "punog Lexitora" (kraj Faze 3):** ~10-12 mjeseci.

---

## Faza 0: Predpriprema (PM vlasnik)

**Trajanje:** 4-6 tjedana
**Vlasnik:** Project Manager
**Cilj:** Sve potrebno za developera da krene "u trku".

### Tjedni 1-2: Dokumentacija

- [x] Definicija vizije i opsega
- [x] Brand i domena (Lexitor, lexitor.eu)
- [x] Tehnološke odluke
- [ ] **README.md** - glavna ulazna točka
- [ ] **PROJECT.md** - poslovna vizija
- [ ] **ARCHITECTURE.md** - tehnička arhitektura
- [ ] **PHASES.md** - ovaj dokument
- [ ] **DECISIONS.md** - tracker odluka
- [ ] **FOR_DEVELOPER.md** - brief za informatičara
- [ ] **DESIGN_BRIEF.md** - za dizajnera

### Tjedni 2-3: Pravna baza (paralelno)

- [ ] Dogovor sa pravnikom (ili eksternim stručnjakom)
- [ ] Validacija definicija 6 Tier 1 prekršaja
- [ ] Početak prikupljanja DKOM odluka (cilj: 50-100)
- [ ] Skidanje cijelog ZJN, pravilnika, uredbi
- [ ] Skidanje VUS odluka (relevantnih)
- [ ] Folder struktura za dokumente

### Tjedni 3-4: Test podaci

- [ ] **Ground truth troškovnik** - 15-20 stavki sa poznatim greškama
- [ ] **Anotirani DKOM odluke** - po 5 primjera za svaki Tier prekršaja
- [ ] **Test scenariji** - što sve sustav mora prepoznati

### Tjedni 4-5: Dizajn paralelno

- [ ] Logo i brand identitet (Claude Design)
- [ ] Landing page mockup
- [ ] Glavni rezultati ekran mockup
- [ ] Dashboard mockup

### Tjedni 5-6: Final priprema

- [ ] Azure account setup
- [ ] GitHub organizacija + repo
- [ ] API ključevi (Anthropic, Cohere)
- [ ] Stripe account za naplatu (kasnije)
- [ ] Domain config (lexitor.eu)
- [ ] Briefing developera (kad bude spreman)

### Kriteriji završetka Faze 0

- ✅ Sva dokumentacija gotova i validirana
- ✅ Pravnik validirao definicije prekršaja
- ✅ Pravna baza pripremljena (minimum 50 dokumenata)
- ✅ Ground truth test set spreman
- ✅ Početni dizajn (logo + 3 ključna ekrana)
- ✅ Sva infrastruktura account-i kreirani
- ✅ Developer raspoređen i briefan

---

## Faza 1A: PoC - Core analiza

**Trajanje:** 8-12 tjedana (ovisno o iskustvu developera)
**Vlasnik:** Developer (Python) + PM (validacija)
**Cilj:** Dokazati da AI razumije domenu i kvalitetno detektira prekršaje.

### Sprint 1: Setup i osnovna infrastruktura (1 tjedan)

- [ ] Repo setup (struktura foldera prema [README.md](./README.md))
- [ ] Virtual environment + dependencies (poetry/uv)
- [ ] Docker setup (lokalni development)
- [ ] FastAPI "Hello World" + health check endpoint
- [ ] PostgreSQL lokalno
- [ ] Qdrant lokalno (Docker)
- [ ] Environment varijable (.env)
- [ ] Anthropic + Cohere API testirani
- [ ] CI/CD osnovni (lint, test)

**Demo:** API odgovara na `/health`, sve servise se pokreću lokalno.

### Sprint 2: Document Parser (2 tjedna)

- [ ] PDF parser (pdfplumber + Camelot)
- [ ] DOCX parser (python-docx)
- [ ] XLSX parser (openpyxl)
- [ ] Tipologija detekcija (DON / Troškovnik / Žalba)
- [ ] Strukturirani output (JSON)
- [ ] Validacija parsing kvalitete
- [ ] Unit testovi

**Demo:** Korisnik upload-a DKOM PDF, sustav ga parsira u strukturiran JSON.

### Sprint 3: Knowledge Base ingestion (2 tjedna)

- [ ] Scraper za dkom.hr
- [ ] Loader za ZJN (Narodne novine)
- [ ] Scraper za VUS odluke
- [ ] Chunking strategija (po tipu izvora)
- [ ] Cohere embeddings generiranje
- [ ] Qdrant indexing
- [ ] Metadata pohranjivanje (PostgreSQL)
- [ ] Knowledge Graph osnove

**Demo:** Pravna baza indeksirana, search po riječima vraća relevantne dokumente.

### Sprint 4: RAG Retriever (1 tjedan)

- [ ] Vector search implementation
- [ ] Hybrid search (vector + keyword/BM25)
- [ ] Re-ranking
- [ ] Filteri (tip izvora, godina, jurisdikcija)
- [ ] Performance optimization
- [ ] Unit testovi

**Demo:** Za zadanu stavku troškovnika, sustav vraća top 10 relevantnih pravnih odredbi.

### Sprint 5: LLM Analyzer - Tier 1.1 (2 tjedna)

- [ ] Master prompt design
- [ ] Tier 1.1 prompt (brendovi bez "ili jednakovrijedno")
- [ ] Anthropic API integracija sa Citations
- [ ] JSON schema za odgovor
- [ ] Citation validation
- [ ] Cache mehanizam (po hash-u stavke)
- [ ] Unit + integration testovi
- [ ] Evaluacija na ground truth-u

**Demo:** Sustav prepoznaje brendove bez "ili jednakovrijedno" sa 80%+ recall-om.

### Sprint 6: LLM Analyzer - Ostali Tier-i (3 tjedna)

- [ ] Tier 1.2 prompt (diskriminatorne specifikacije)
- [ ] Tier 1.3 prompt (nepotpuni opisi)
- [ ] Tier 1.4 prompt (manipulacije cijenama)
- [ ] Tier 1.5 prompt (nedosljednost DON-a i troškovnika)
- [ ] Tier 1.6 prompt (komplet vs pojedinačne stavke)
- [ ] Cross-tier konzistentnost
- [ ] Granični slučajevi handling
- [ ] Evaluacija svake po posebno

**Demo:** Sustav detektira sve 6 tipova prekršaja sa target metrikama.

### Sprint 7: API i Result Builder (1 tjedan)

- [ ] POST /analyze endpoint
- [ ] Request validation (Pydantic)
- [ ] Async job queue (Celery)
- [ ] Progress reporting
- [ ] Result aggregation
- [ ] Error handling
- [ ] OpenAPI dokumentacija

**Demo:** Cijeli flow: upload → analiza → rezultati preko API-ja.

### Sprint 8: Web UI (Next.js) i Feedback (2-3 tjedna)

Frontend je **Next.js 14 + Tailwind + shadcn/ui** od dana 1 (preskočili smo Streamlit fazu — vidi DECISIONS D-036).

- [ ] `apps/web` — landing page (lexitor.eu)
- [ ] `apps/app` — auth required UI (app.lexitor.eu)
- [ ] Login + register flow (NextAuth.js ili JWT s backend-om)
- [ ] Upload screen (PDF/XLSX/.arhigonfile drag&drop)
- [ ] Rezultati screen — lijevo stablo navigacije, desno stavke + Lexitor analiza
- [ ] Streaming rezultata kroz Server-Sent Events
- [ ] Citation prikaz s referencama na ZJN/DKOM/VUS
- [ ] Feedback komponente (Sloj 1, 2, 3)
- [ ] DKOM auto-tracker (Sloj 4) — osnovna verzija

**Demo:** Korisnik kroz UI: upload → analiza streama stavku-po-stavku → vidi rezultate → daje feedback.

### Sprint 9: Evaluacija i tuning (1-2 tjedna)

- [ ] Pokretanje na ground truth set-u
- [ ] Mjerenje metrika (precision, recall, F1)
- [ ] Tuning prompts
- [ ] Tuning retrieval parametara
- [ ] Edge cases handling
- [ ] Pravnik validira rezultate na 5-10 stvarnih DKOM odluka
- [ ] Dokumentacija nalaza

### Kriteriji završetka Faze 1A

- ✅ Sustav indeksira ZJN + 50+ DKOM + 20+ VUS odluka
- ✅ API odgovara unutar 60 sekundi za 20 stavki
- ✅ Recall ≥ 80% na ground truth setu
- ✅ Precision ≥ 70% na ground truth setu
- ✅ Citation accuracy 100% (svi citati postoje u izvoru)
- ✅ Web UI radi end-to-end
- ✅ Feedback se sprema u sva 4 sloja
- ✅ Pravnik potvrdio kvalitetu na uzorku

**Output:** Funkcionalni PoC koji pokazuje da Lexitor radi. Spreman za internu validaciju i prve eksterne korisnike (beta).

---

## Faza 1B: Ponuditelj kao perspektiva

**Trajanje:** 4 tjedna
**Vlasnik:** Developer + PM
**Cilj:** Sustav radi i s druge strane (ponuditelj koji analizira tuđi DON).

### Sprint 1: Ponuditelj user-flow (1 tjedan)

- [ ] Definicija "Ponuditelj" persona u sistemu
- [ ] Različit prikaz rezultata (perspektiva: gdje su moji rizici?)
- [ ] Wizard: "Što tražiš?" (objaviti rizike, pripremiti upit, žaliti se)

### Sprint 2: Procesna logika (1 tjedan)

- [ ] Detekcija faze postupka (savjetovanje / objavljen DON / nakon odluke)
- [ ] Različite preporuke ovisno o fazi
- [ ] Vodič kroz proceduralne korake (rokovi, prethodne radnje)

### Sprint 3: Pretraga presedana (1 tjedan)

- [ ] "Sličan slučaj" funkcija
- [ ] Filteri po ishodu (uspjeh/neuspjeh)
- [ ] Statistika ("U sličnim slučajevima DKOM je odlučio...")

### Sprint 4: Validacija (1 tjedan)

- [ ] Test sa ponuditeljskim use case-om
- [ ] Pravnik validira logiku
- [ ] Edge cases

### Kriteriji završetka Faze 1B

- ✅ Sustav prepoznaje 3 različite perspektive (naručitelj, projektant, ponuditelj)
- ✅ Različiti prikazi rezultata po perspektivi
- ✅ Detekcija faze postupka radi
- ✅ Pretraga presedana funkcionalna

---

## Faza 2: Generiranje dokumenata

**Trajanje:** 12-16 tjedana
**Vlasnik:** Developer + PM + Pravnik (pojačan angažman)
**Cilj:** Lexitor postaje alat koji **piše**, ne samo analizira.

⚠️ **NAJVAŽNIJA FAZA** - ovdje proizvod prelazi iz "alata za provjeru" u "alata za pravni rad".

### Sprint 1-2: Dokumentnih template-a (3 tjedna)

- [ ] Pravnik pripremi template-e za:
  - Žalbu na odluku o odabiru
  - Žalbu na DON
  - Odgovor na žalbu (naručitelj)
  - Zahtjev za pojašnjenje
  - Prijedlog izmjene DON-a (savjetovanje)
- [ ] Strukturirani format template-a
- [ ] Testiranje na primjerima

### Sprint 3-4: Generator žalbe (3 tjedna)

- [ ] Wizard: koja vrsta žalbe?
- [ ] Korisnik unosi situaciju
- [ ] Sustav pretraži pravnu bazu za:
  - Relevantne članke ZJN
  - Slične DKOM/VUS odluke
  - Argumentacijske obrasce
- [ ] LLM generira nacrt žalbe
- [ ] Validation (citati, pravna logika, struktura)
- [ ] Korisnik dobiva nacrt + objašnjenje

**Demo:** Korisnik unosi "Naručitelj me odbio jer X", sustav generira nacrt žalbe.

### Sprint 5-6: Generator odgovora na žalbu (3 tjedna)

- [ ] Korisnik (naručitelj) upload-a žalbu
- [ ] Sustav parsira žalbene navode
- [ ] Pretraga **suprotnih** presedana
- [ ] LLM generira nacrt odgovora
- [ ] Procjena vjerojatnosti uspjeha žalbe

**Demo:** Naručitelj upload-a žalbu, sustav generira nacrt odgovora.

### Sprint 7: Generator pojašnjenja (1 tjedan)

- [ ] Jednostavniji od žalbe
- [ ] Strukturirani upit prema naručitelju
- [ ] Citati ZJN o pravu na pojašnjenje

### Sprint 8-10: Track changes editor (3 tjedna)

- [ ] Editor sa diff prikazom (originalni AI tekst vs korisničke izmjene)
- [ ] Komentari uz dijelove teksta
- [ ] Verzioniranje
- [ ] Export (PDF, DOCX)

### Sprint 11-12: Asinkrona kolaboracija (3 tjedna)

- [ ] Share dokument (link, email)
- [ ] Permissions (read / comment / edit)
- [ ] Notifikacije
- [ ] Aktivnosti log

### Sprint 13-14: Human-in-the-loop validacija (2 tjedna)

- [ ] "Approval" workflow
- [ ] Pravnik može pregledati prije slanja
- [ ] Audit log promjena
- [ ] Approval status u UI-ju

### Sprint 15-16: Testiranje i tuning (2 tjedna)

- [ ] Pravnik validira generirane dokumente
- [ ] Testiranje na 20+ realnih scenarija
- [ ] Tuning prompts
- [ ] Edge cases

### Kriteriji završetka Faze 2

- ✅ Sva 4 tipa dokumenata se generiraju (žalba, odgovor, pojašnjenje, prijedlog izmjene)
- ✅ Track changes radi
- ✅ Asinkrona kolaboracija funkcionalna (do 5 osoba)
- ✅ Human-in-the-loop workflow implementiran
- ✅ Pravnik potvrdio kvalitetu generiranih dokumenata
- ✅ Stopa "ozbiljnih izmjena" od strane korisnika < 30%

**Output:** Lexitor je alat koji piše pravne dokumente sa kvalitetom dovoljnom za "first draft" koju pravnik dorađuje.

---

## Faza 3: Strategic Advisor

**Trajanje:** 8-12 tjedana
**Vlasnik:** Cijeli tim
**Cilj:** Inteligentni savjetnik, ne samo izvršitelj zadataka.

### Sprint 1-2: Statistike i analytics (3 tjedna)

- [ ] Dashboard "Vjerojatnost uspjeha"
- [ ] Statistike po tipu prekršaja
- [ ] Statistike po naručitelju (anonimizirano)
- [ ] Trendovi u DKOM/VUS praksi
- [ ] Predviđanje ishoda

### Sprint 3-4: Sinkrona kolaboracija (4 tjedna)

- [ ] WebSocket infrastruktura
- [ ] Real-time CRDT engine
- [ ] Live cursors
- [ ] Conflict resolution
- [ ] Presence indicators

### Sprint 5-6: Multi-tenant funkcionalnosti (3 tjedna)

- [ ] Organizacijska struktura
- [ ] Team management
- [ ] Role-based permissions
- [ ] Reporting po klijentima
- [ ] Billing po organizaciji

### Sprint 7-8: White-label opcija (2 tjedna)

- [ ] Custom branding
- [ ] Custom domena
- [ ] Email templates customizable
- [ ] Subset funkcionalnosti

### Kriteriji završetka Faze 3

- ✅ Statistike i predviđanja funkcionalna
- ✅ Sinkrona kolaboracija radi za do 10 korisnika
- ✅ Multi-tenant struktura implementirana
- ✅ White-label opcija dostupna za enterprise

---

## Komercijalizacija

**Trajanje:** 8-12 tjedana
**Vlasnik:** Cijeli tim + Marketing
**Cilj:** Pravi korisnici i prihod.

### Sprint 1-2: Pricing i naplata

- [ ] Stripe integracija
- [ ] Tier sustav (Free Trial / Solo / Team / Premium / Enterprise)
- [ ] Usage metering
- [ ] Upgrade/downgrade flow
- [ ] Invoice management

### Sprint 3-4: Marketing infrastruktura

- [ ] Landing page (lexitor.eu)
- [ ] Blog
- [ ] Documentation site
- [ ] Help center / FAQ
- [ ] Email marketing setup

### Sprint 5-6: Onboarding flow

- [ ] Registracija + email verifikacija
- [ ] Onboarding tutorial
- [ ] Demo project
- [ ] Sample data

### Sprint 7-8: Beta korisnici

- [ ] Pozvati 10-20 beta korisnika
- [ ] Direct support
- [ ] Iteracija na feedback
- [ ] Priče uspjeha (case studies)

### Sprint 9-10: Public launch

- [ ] Pricing public
- [ ] PR kampanja
- [ ] LinkedIn outreach
- [ ] Industry events

### Sprint 11-12: Stabilizacija

- [ ] Customer support setup
- [ ] Monitoring i alerts
- [ ] Performance optimization
- [ ] Bug fixing

### Kriteriji završetka

- ✅ Pricing i naplata radi
- ✅ Onboarding flow stabilan
- ✅ 50+ aktivnih korisnika
- ✅ Prvi paying customers
- ✅ Customer support uspostavljen

---

## Širenje na regiju

**Trajanje:** 6+ mjeseci
**Vlasnik:** Cijeli tim + lokalni partneri
**Cilj:** Slovenia, BiH, zatim ostatak regije.

### Po zemlji (3-6 mjeseci):

1. **Pravnička partnerstva** - lokalni pravnik specijaliziran za JN
2. **Pravna baza** - ZJN te zemlje, lokalna prakse
3. **Lokalizacija UI** - i18n
4. **Marketing prilagodba** - lokalni kanali
5. **Beta korisnici** - 10-20 ranih korisnika
6. **Public launch** - pricing, marketing

### Redoslijed:

1. **Slovenija** (Q3 2027) - sličan zakon, EU okvir
2. **BiH** (Q4 2027) - sličan jezik, manje EU integracije
3. **Srbija** (Q1 2028) - veće tržište, neki dijelovi različiti
4. **Crna Gora, Sj. Makedonija** (Q2 2028) - manja tržišta, kratki sprintovi
5. **EU - Njemačka, Austrija** (2028+) - ozbiljnija prilagodba

---

## 📊 Glavni KPI po fazama

| Faza | Glavni KPI | Target |
|------|-----------|--------|
| 0 | Dokumentacija gotova | 100% |
| 1A | AI točnost na ground truth | Recall ≥ 80%, Precision ≥ 70% |
| 1B | Korisničke perspektive rade | 3 perspektive |
| 2 | Stopa "ozbiljnih izmjena" generiranih dokumenata | < 30% |
| 3 | Statistike predviđanja točne | ≥ 70% |
| K | Aktivnih korisnika | 50+ |
| K | Paying customers | 10+ |
| Š | Aktivnih zemalja | 5+ (do kraja 2028) |

---

## 🚦 Rizici po fazama

### Faza 0
- Pravnik nije dostupan / preskup → backup: vanjski savjetnik
- Domain knowledge dokumentacija prekompleksna → backup: iterativno

### Faza 1A
- AI ne radi dovoljno dobro → backup: više vremena za prompt engineering
- Pravna baza prekomplicirana za scraping → backup: ručno prikupljanje
- Developer overwhelmed → backup: smanjiti opseg, fokus na 3 Tier-a umjesto 6

### Faza 1B
- Procesna logika prekomplicirana → backup: pojednostaviti

### Faza 2 ⚠️ NAJRIZIČNIJA
- Generirani dokumenti loše kvalitete → backup: više iteracija, više prompt engineering
- Pravnik ne može validirati u realnom vremenu → backup: kontrolne grupe, postupna isporuka
- Pravna odgovornost → backup: jasnije disclaimer, više warnings

### Faza 3
- Sinkrona kolaboracija prekomplicirana → backup: zadržati asinkronu, sinkroni manjak

### Komercijalizacija
- Nedostatak korisnika → backup: marketing iteracija, partnerstva
- Pricing nije optimalan → backup: A/B testing, korisnička istraživanja

---

## 📚 Reference

- [README.md](./README.md) - glavni overview
- [PROJECT.md](./PROJECT.md) - poslovni kontekst
- [ARCHITECTURE.md](./ARCHITECTURE.md) - tehnička arhitektura
- [DECISIONS.md](./DECISIONS.md) - sve odluke
- [FOR_DEVELOPER.md](./FOR_DEVELOPER.md) - praktičan brief

---

*Verzija: 1.0 | Svibanj 2026 | Lexitor by Arhigon*
