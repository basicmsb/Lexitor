# Lexitor

> *Onaj koji se brine za zakon.*

**AI asistent za usklađenost dokumentacije javne nabave.**

[![Status](https://img.shields.io/badge/status-pre--alpha-orange)]() [![License](https://img.shields.io/badge/license-proprietary-blue)]() [![Made in](https://img.shields.io/badge/made%20in-Croatia%20🇭🇷-red)]() [![Powered by](https://img.shields.io/badge/by-Arhigon-darkblue)]()

Lexitor analizira dokumentaciju javne nabave (DON i troškovnike) protiv Zakona o javnoj nabavi, prakse DKOM-a, VUS-a i Suda EU - i upozorava korisnika na rizike **prije** nego što dođe do žalbenog postupka.

**🌐 Domena:** [lexitor.eu](https://lexitor.eu) *(u izgradnji)*
**🏢 Vlasnik:** Arhigon d.o.o.
**📍 Status:** Pre-alpha (PoC u razvoju)
**📅 MVP target:** Q3-Q4 2026

---

## 📖 Sadržaj

- [Što je Lexitor?](#-što-je-lexitor)
- [Problem koji rješavamo](#-problem-koji-rješavamo)
- [Kako Lexitor radi](#-kako-lexitor-radi)
- [Korisničke grupe](#-korisničke-grupe)
- [Tržište i strategija](#-tržište-i-strategija)
- [Arhitektura](#️-arhitektura)
- [Tehnološki stack](#-tehnološki-stack)
- [Struktura repozitorija](#-struktura-repozitorija)
- [Roadmap](#️-roadmap)
- [Kako koristiti dokumentaciju](#-kako-koristiti-dokumentaciju)
- [Status i sljedeći koraci](#-status-i-sljedeći-koraci)
- [Tim i kontakt](#-tim-i-kontakt)

---

## 🎯 Što je Lexitor?

Lexitor je **samostalna SaaS platforma** koja koristi umjetnu inteligenciju za analizu i kontrolu dokumentacije javne nabave. Pomaže svim sudionicima postupka:

- **Naručiteljima** - validira DON i troškovnike prije objave
- **Projektantima** - provjerava troškovnike prije slanja naručitelju
- **Ponuditeljima** - analizira DON-ove iz perspektive natjecatelja, generira upite i nacrte žalbi
- **Pravnicima i konzultantima** - ubrzava njihov rad uz puno bolju pretragu pravne prakse

### Tri ključne sposobnosti

1. **🔍 Detekcija prekršaja** - prepoznaje 6 tipova najčešćih kršenja zakona u troškovnicima i DON-ovima
2. **📝 Generiranje dokumenata** - piše nacrte žalbi, odgovora na žalbe i zahtjeva za pojašnjenje
3. **📊 Praćenje ishoda** - povezuje korisničke slučajeve sa stvarnim DKOM/VUS odlukama i uči iz njih

### Što Lexitor NIJE

- ❌ Nije zamjena za pravnika ili stručnjaka za javnu nabavu
- ❌ Ne preuzima pravnu odgovornost za sadržaj dokumentacije
- ❌ Nije generički AI alat - **specijaliziran isključivo za javnu nabavu**
- ❌ Nije online odvjetnička usluga (regulatorno odvojeno)

---

## 🔥 Problem koji rješavamo

### Pravna kompleksnost javne nabave

Postupci javne nabave u RH (i EU) generiraju **velik broj žalbi** zbog:

- **Brendova bez "ili jednakovrijedno"** u tehničkim specifikacijama
- **Diskriminatornih opisa** koji favoriziraju određene proizvode
- **Manipulacije jediničnim cijenama** u troškovnicima
- **Neproporcionalnih uvjeta sposobnosti**
- **Neispravne strukture troškovnika** (komplet vs pojedinačne stavke)
- **Nedosljednosti DON-a i troškovnika**
- ...i mnogih drugih slučajeva pokrivenih opsežnom praksom DKOM-a

### Posljedice za sve sudionike

| Sudionik | Posljedice |
|----------|------------|
| **Naručitelj** | Kašnjenje projekta, dodatni troškovi, poništenje postupka, reputacijski rizik |
| **Projektant** | Reputacijska šteta, zahtjevi za doradu, gubitak povjerenja klijenta |
| **Ponuditelj** | Nepravedno odbijanje, gubitak prilike, sudski troškovi |
| **Pravnik** | Vrijeme potrošeno na pretragu prakse, nemogućnost obrade više slučajeva |

### Zašto sadašnji alati ne rade

- **EOJN sustav** - centralizirani sustav države, ali **bez ikakve kontrole kvalitete**
- **Pravne baze** (Ius-Info, Lex...) - statične, traže ručnu pretragu, **ne razumiju kontekst dokumenta**
- **AI generalisti** (ChatGPT, Claude) - nemaju indeksiranu pravnu bazu, **haluciniraju citate**
- **Pravne usluge** - kvalitetne ali **skupe i sporo skalabilne**

Lexitor popunjava točno **tu prazninu**: AI specijaliziran za javnu nabavu, sa ažuriranom pravnom bazom i mehanizmom učenja iz stvarne prakse.

---

## ⚙️ Kako Lexitor radi

### Pojednostavljeni tijek

```
┌─────────────────────┐
│   1. Korisnik       │  Učita dokument (DON ili troškovnik)
│   učitava dokument  │  Format: PDF, DOCX, XLSX
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   2. Lexitor        │  Razlaže dokument na "stavke"
│   parsira sadržaj   │  Prepoznaje strukturu (poglavlja, tablice)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   3. AI Engine      │  Za svaku stavku:
│   analizira         │  → Pretraži pravnu bazu (RAG)
│                     │  → Pošalji Claude AI s relevantnim odredbama
│                     │  → Klasificiraj rizik (zeleno/žuto/crveno)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   4. Rezultati      │  Korisnik vidi:
│   prikazani         │  → Status svake stavke
│                     │  → Citate iz ZJN/DKOM/VUS
│                     │  → Prijedlog ispravka
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   5. Korisnik daje  │  Ocjenjuje relevantnost
│   feedback          │  Korigira analizu (ako se ne slaže)
│                     │  Sustav uči iz korekcija
└─────────────────────┘
```

### Detaljnija slika za napredne korisnike

Lexitor radi na **četiri sloja podataka**:

1. **Sirova pravna baza** - skinuti PDF-ovi i HTML stranice ZJN, DKOM, VUS, Sud EU
2. **Strukturirano znanje** - knowledge graph s vezama između dokumenata
3. **Korisničko znanje** - korekcije, ocjene, ljudske izmjene generiranih dokumenata
4. **Verifikacijsko znanje** - stvarni ishodi DKOM/VUS koji potvrđuju ili opovrgavaju Lexitor predikcije

📖 **Detalji:** vidi [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 👥 Korisničke grupe

Lexitor opslužuje **5 različitih tipova korisnika**, svaki sa specifičnim potrebama i tier-om pretplate.

### 🏗️ Projektant

**Tko je to:** Arhitekt, građevinski/strojarski/elektro inženjer koji izrađuje troškovnike za naručitelje.

**Glavni problem:** Treba brzo provjeriti da troškovnik ne sadrži pravne probleme prije slanja naručitelju.

**Što Lexitor pruža:**
- Provjera troškovnika na 6 Tier 1 prekršaja
- Vizualni indikatori uz svaku stavku (zeleno/žuto/crveno)
- Prijedlozi ispravka stavki
- Povijest analiza po projektima

**Tipičan plan:** Solo (49 EUR/mj) ili Team (149 EUR/mj)

---

### 🏛️ Naručitelj (javni)

**Tko je to:** Jedinice lokalne samouprave, javna poduzeća, komunalna poduzeća, ministarstva, agencije.

**Glavni problem:** Treba osigurati da DON i objavljeni troškovnik ne provociraju žalbe ponuditelja.

**Što Lexitor pruža:**
- Provjera kompletne DON
- Provjera troškovnika
- **Generiranje odgovora na žalbu** (ako dođe)
- Statistike: vjerojatnost uspjeha žalbe protiv vašeg DON-a
- Audit log za internu kontrolu

**Tipičan plan:** Team (149 EUR/mj) ili Premium (299 EUR/mj)

---

### 💼 Ponuditelj ⭐

**Tko je to:** Tvrtka koja se prijavljuje na natječaje javne nabave (građevinske firme, IT firme, dobavljači, konzultanti).

**Glavni problem:** Treba brzo procijeniti je li natječaj pošten, identificirati rizike, znati može li se žaliti, kako pisati pojašnjenja.

**Što Lexitor pruža:**
- Analiza objavljene DON iz perspektive ponuditelja
- **Generiranje upita za pojašnjenje** (rana faza)
- **Generiranje prijedloga izmjene** u savjetovanju
- **Generiranje nacrta žalbe** s pravnom argumentacijom
- Pretraga sličnih presedana ("u sličnim slučajevima DKOM je odlučio...")
- Vodič kroz proceduralne korake (npr. "moraš prvo postaviti pitanje da bi mogao žaliti")

**Tipičan plan:** Solo (49 EUR/mj) ili Team (149 EUR/mj)

---

### 👨‍⚖️ Pravnik / Stručnjak za javnu nabavu

**Tko je to:** Odvjetnici specijalizirani za JN, certificirani stručnjaci za JN, savjetnici.

**Glavni problem:** Treba brzo pretraživati ogromnu bazu prakse, izrađivati dokumente za više klijenata, pratiti aktualne odluke.

**Što Lexitor pruža:**
- Sve što i drugi korisnici, plus:
- **Edukacijski mod** - "kako AI razmišlja u ovom slučaju"
- **Knowledge management** - vlastita arhiva slučajeva
- **Multi-client view** - rad za više klijenata istovremeno
- **API pristup** za vlastite alate

**Tipičan plan:** Premium (299 EUR/mj) ili Enterprise (po dogovoru)

---

### 🏢 Konzultantska kuća

**Tko je to:** Firme koje pripremaju nabavnu dokumentaciju ili savjetuju u JN postupcima (često pripremaju i EU fond projekte).

**Glavni problem:** Skaliranje ekspertize na više klijenata, edukacija juniora, kontrola kvalitete.

**Što Lexitor pruža:**
- Sve gore + multi-tenant struktura
- Workflow management
- Reporting prema klijentima
- White-label opcija (prikazati Lexitor pod svojim brendom)

**Tipičan plan:** Enterprise (po dogovoru)

---

## 🌍 Tržište i strategija

### Faze tržišnog širenja

| Faza | Tržište | Vremenski okvir | Procijenjeni TAM |
|------|---------|-----------------|------------------|
| **Faza 1** | Hrvatska - PoC + early adopters | Q2-Q3 2026 | ~5M EUR/godišnje |
| **Faza 2** | Hrvatska - puna komercijalizacija | Q4 2026 - Q1 2027 | (gore) |
| **Faza 3** | Slovenija + BiH | Q2 2027 | +~3M EUR |
| **Faza 4** | Srbija + Crna Gora + N. Makedonija | Q3-Q4 2027 | +~5M EUR |
| **Faza 5** | EU (DE, AT, IT, ostali) | 2028+ | +~50M EUR |

### Strateška pretpostavka

**Tehnička platforma je univerzalna - mijenja se samo pravna baza po jurisdikciji.**

To znači da kad jednom imamo radni sustav za Hrvatsku, širenje je **operativno**, ne tehničko:
- Skupiti i indeksirati pravnu bazu nove zemlje
- Lokalizirati UI prijevod
- Pravnik te jurisdikcije validira definicije prekršaja
- Komercijalni launch

**Procijenjeno trajanje širenja na novu zemlju:** 3-6 mjeseci po zemlji.

### Konkurentska pozicija

| Aspekt | Lexitor | Pravne baze (Ius-Info) | Generic AI (ChatGPT) | Pravnici |
|--------|---------|------------------------|----------------------|----------|
| **Specijalizacija** | ✅ JN | ⚠️ Široka | ❌ Generički | ✅ JN (top) |
| **AI razumijevanje konteksta** | ✅ Da | ❌ Ne | ⚠️ Bez prave baze | ✅ Da |
| **Citiranje izvora** | ✅ Verificirano | ✅ Da | ❌ Halucinira | ✅ Da |
| **Cijena** | 💰 49-299 EUR/mj | 💰 ~100 EUR/mj | 💰 20 EUR/mj | 💰💰💰 100-300 EUR/h |
| **Brzina** | ✅ Sekunde | ⚠️ Manualno | ✅ Sekunde | ❌ Dani |
| **Generiranje dokumenata** | ✅ Da | ❌ Ne | ⚠️ Loša kvaliteta | ✅ Da |
| **Učenje iz ishoda** | ✅ Auto | ❌ Ne | ❌ Ne | ⚠️ Iskustvo |

### Data Moat (jaz od podataka)

Najvažnija konkurentska prednost koju gradimo:

```
Mjesec 6:    100 korisnika × 5 slučajeva = 500 zabilježenih analiza
             100 ljudskih validacija
             50 stvarnih DKOM ishoda

Mjesec 12:   500 korisnika × 5 slučajeva = 2.500 analiza
             500 ljudskih validacija
             300 stvarnih ishoda

Mjesec 24:   2.000 korisnika = 10.000+ analiza
             2.000 ljudskih validacija
             1.500+ stvarnih ishoda
```

**Konkurencija koja krene godinu kasnije ne može reproducirati 1.500 verificiranih ishoda.** To je naš dugoročni "moat".

📖 **Detaljna roadmap:** vidi [PHASES.md](./PHASES.md)

---

## 🏗️ Arhitektura

### High-level slika

```
                      ┌─────────────────────────────────┐
                      │         LEXITOR PLATFORMA       │
                      │           (lexitor.eu)          │
                      └────────────────┬────────────────┘
                                       │
           ┌───────────────────────────┼───────────────────────────┐
           │                           │                           │
           ▼                           ▼                           ▼
   ┌───────────────┐          ┌───────────────┐         ┌───────────────┐
   │   Web UI      │          │   REST API    │         │  Admin/Stats  │
   │ (registracija │          │ (enterprise   │         │   Dashboard   │
   │  korisnika)   │          │  klijenti)    │         │ (interno)     │
   └───────┬───────┘          └───────┬───────┘         └───────┬───────┘
           │                          │                         │
           └──────────────────────────┼─────────────────────────┘
                                      │
                                      ▼
                         ┌──────────────────────┐
                         │   Core AI Engine     │
                         │ ┌──────────────────┐ │
                         │ │  RAG Retriever   │ │
                         │ ├──────────────────┤ │
                         │ │  LLM Analyzer    │ │
                         │ │  (Claude API)    │ │
                         │ ├──────────────────┤ │
                         │ │  Document Gen    │ │
                         │ ├──────────────────┤ │
                         │ │  Result Builder  │ │
                         │ └──────────────────┘ │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
      ┌──────────────┐    ┌──────────────────┐  ┌──────────────────┐
      │   Qdrant     │    │   PostgreSQL     │  │   Azure Blob     │
      │  (vektorska  │    │   (korisnici,    │  │   (PDF arhiva    │
      │    baza)     │    │   audit, feed)   │  │  pravne baze)    │
      └──────────────┘    └──────────────────┘  └──────────────────┘
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  Knowledge Graph     │
                         │  (Neo4j ili pg)      │
                         │  Veze između         │
                         │  pravnih izvora      │
                         └──────────────────────┘
```

### Glavne komponente

1. **Web UI** - Streamlit (MVP) → Next.js 14 (Faza 2)
2. **REST API** - FastAPI sa OpenAPI dokumentacijom
3. **Core AI Engine** - LangChain + Claude Sonnet 4.5
4. **Vector DB** - Qdrant (samohostani na Azure Container Apps)
5. **Knowledge Graph** - PostgreSQL sa pgvector ili Neo4j
6. **Storage** - Azure Blob (PDF-ovi), PostgreSQL (metapodaci)
7. **PDF Parsing** - Hibrid: pdfplumber/Camelot (default) + Azure Document Intelligence (premium)

📖 **Tehnički detalji:** vidi [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 🛠️ Tehnološki stack

### Backend

| Komponenta | Tehnologija | Razlog odabira |
|------------|-------------|----------------|
| Jezik | Python 3.11+ | Najbolji ekosustav za AI/RAG |
| Web framework | FastAPI | Brz, asinkron, OpenAPI dokumentacija |
| AI orkestracija | LangChain | Standard za RAG pipeline |
| Validacija | Pydantic v2 | Type-safe, brz |
| Async jobs | Celery + Redis | Za duže analize |

### AI / ML

| Komponenta | Tehnologija | Mjesečni trošak (PoC) |
|------------|-------------|----------------------|
| LLM | Claude Sonnet 4.5 (Anthropic API) | ~50-200 EUR |
| Embeddings | Cohere embed-multilingual-v3 | ~0-50 EUR (free tier) |
| Vector DB | Qdrant (self-hosted) | 0 EUR (server) |
| PDF Parsing premium | Azure AI Document Intelligence | ~30-50 EUR/1000 str |

### Frontend

| Komponenta | Tehnologija | Domena | Namjena |
|------------|-------------|--------|---------|
| Web (marketing) | Next.js 14 + Tailwind + shadcn/ui | `lexitor.eu` | Landing, blog, moduli, o nama, paketi |
| App (auth) | Next.js 14 + Tailwind + shadcn/ui | `app.lexitor.eu` | Analiza dokumenata, žalbe, dashboard |

Web i App su **odvojeni Next.js projekti** unutar monorepo-a (pnpm workspaces) — dijele UI komponente i types kroz `packages/`, ali rade na različitim poddomenama radi **origin isolation** (cookies, CSP, 3rd-party scripts).

### Infrastruktura (Azure)

| Servis | Namjena |
|--------|---------|
| Azure Container Apps | Python servis (auto-scaling) |
| Azure Database for PostgreSQL | Korisnici, audit, feedback |
| Azure Blob Storage | PDF dokumenti |
| Azure Key Vault | API ključevi, tajne |
| Azure Application Insights | Monitoring, logging |
| Azure AD B2C | Autentikacija korisnika |

### DevOps

| Alat | Namjena |
|------|---------|
| Docker | Kontejnerizacija |
| GitHub Actions | CI/CD |
| GitHub | Verzionirajući kod i dokumentacija |
| VS Code + Claude Code | IDE za razvoj |

📖 **Detalji:** vidi [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 📂 Struktura repozitorija (monorepo)

```
lexitor/                       ← root (pnpm workspace + docker-compose)
├── README.md                  ← OVDJE STE - glavna ulazna točka
├── PROJECT.md                 ← Vizija, opseg, ciljne grupe
├── ARCHITECTURE.md            ← Tehnička arhitektura
├── PHASES.md                  ← Fazni plan razvoja
├── DECISIONS.md               ← Live tracker odluka
├── FOR_DEVELOPER.md           ← Brief za developera
├── DESIGN_BRIEF.md            ← Design smjernice
│
├── package.json               ← root pnpm scripts (dev/build/lint)
├── pnpm-workspace.yaml        ← workspace deklaracija
├── docker-compose.yml         ← postgres, redis, qdrant
│
├── apps/
│   ├── backend/               ← FastAPI (Python 3.12)
│   │   ├── pyproject.toml     ← Poetry config
│   │   ├── alembic.ini
│   │   ├── .env / .env.example
│   │   ├── src/
│   │   │   ├── api/           ← FastAPI endpoints
│   │   │   ├── core/          ← Analyzer, retriever, generator
│   │   │   ├── knowledge_base/← Scrapers, embeddings, indexing
│   │   │   ├── document_parser/← PDF/DOCX/XLSX/.arhigonfile parsing
│   │   │   ├── feedback/
│   │   │   ├── models/        ← SQLAlchemy + Pydantic
│   │   │   ├── workers/       ← Celery
│   │   │   ├── utils/
│   │   │   └── db/            ← Session + migrations
│   │   └── tests/             ← unit / integration / e2e
│   │
│   ├── web/                   ← Next.js 14 — lexitor.eu (marketing/public)
│   │   ├── src/app/           ← Landing, blog, moduli, o nama, paketi
│   │   ├── tailwind.config.ts
│   │   └── package.json
│   │
│   └── app/                   ← Next.js 14 — app.lexitor.eu (auth required)
│       ├── src/app/(app)/     ← Dashboard, analiza, žalbe, članci, upute, paketi
│       ├── tailwind.config.ts
│       └── package.json
│
├── packages/
│   ├── ui/                    ← Shared React komponente (cn helper, Button, Card…)
│   ├── types/                 ← Shared TS types (auto-gen iz OpenAPI)
│   └── config/                ← Shared Tailwind/ESLint config (kasnije)
│
├── docs/                      ← Detaljna dokumentacija
│   ├── 01-domain-knowledge/   ← Pravna domena, tipovi prekršaja
│   ├── 02-data-models/
│   ├── 03-api/
│   ├── 04-prompts/            ← LLM prompts (verzionirani)
│   └── 05-deployment/         ← Azure, CI/CD
│
├── data/                      ← Pravna baza (gitignored)
│   ├── 01-zakoni/             ← ZJN, pravilnici, uredbe
│   ├── 02-dkom-odluke/
│   ├── 03-vus-presude/
│   ├── 04-sud-eu/
│   ├── 05-templates/
│   └── 06-strucni-clanci/
│
└── scripts/                   ← Standalone skripte (scraping, indeksiranje, eval)
```

---

## 🗺️ Roadmap

### Faza 1A: PoC - Core analiza (2-3 mjeseca) 🎯 TRENUTNI FOKUS

**Cilj:** Dokazati da AI razumije domenu i kvalitetno detektira prekršaje.

**Što gradimo:**
- ✅ Pravna baza (scraping i indeksiranje ZJN, DKOM, VUS, Sud EU)
- ✅ RAG engine za pretragu pravne baze
- ✅ LLM Analyzer za detekciju 6 Tier 1 prekršaja
- ✅ Web UI (Streamlit) za internu uporabu
- ✅ Knowledge Graph (osnovna verzija)
- ✅ Feedback sustav (sva 3 sloja od početka)

**Korisnici:** Naručitelj, projektant (interno testiranje)

### Faza 1B: Ponuditelj kao perspektiva (1 mjesec)

**Cilj:** Validirati da sustav radi i s druge strane (ponuditelj).

**Što dodajemo:**
- Analiza DON-a iz perspektive ponuditelja
- Identifikacija proceduralnih koraka (kad i kako reagirati)
- Pretraga "presedana" za sličan slučaj

### Faza 2: Generiranje dokumenata (3-4 mjeseca)

**Cilj:** Lexitor postaje alat koji **piše**, ne samo analizira.

**Što dodajemo:**
- Generator žalbi (za ponuditelje)
- Generator odgovora na žalbu (za naručitelje)
- Generator zahtjeva za pojašnjenje
- **Asinkrona kolaboracija** (premium feature)
- Human-in-the-loop validacija (pravnik može pregledati prije slanja)

### Faza 3: Strategic Advisor (2-3 mjeseca)

**Cilj:** Inteligentni savjetnik, ne samo izvršitelj.

**Što dodajemo:**
- Statistike i vjerojatnost uspjeha
- Sinkrona kolaboracija (Google Docs stil)
- Multi-tenant funkcionalnosti za enterprise
- White-label opcija

### Komercijalizacija + EU širenje

**Q1-Q2 2027:** Marketing, prvi pravi korisnici, validacija pricing modela
**Q3-Q4 2027:** Slovenija, BiH (lokalizacija pravne baze)
**2028+:** Šire EU tržište

📖 **Detaljan plan po fazama:** vidi [PHASES.md](./PHASES.md)

---

## 📚 Kako koristiti dokumentaciju

Dokumentacija Lexitor projekta je **strukturirana po publici**. Ovisno o tvojoj ulozi, prvo čitaš:

### Ako si **Project Manager (PM)**
1. Ovaj README.md
2. [PROJECT.md](./PROJECT.md) - vizija i poslovni kontekst
3. [PHASES.md](./PHASES.md) - što kad i tko
4. [DECISIONS.md](./DECISIONS.md) - što je odlučeno, što nije

### Ako si **Developer (informatičar)**
1. Ovaj README.md
2. [FOR_DEVELOPER.md](./FOR_DEVELOPER.md) - tvoj brief
3. [ARCHITECTURE.md](./ARCHITECTURE.md) - tehnička arhitektura
4. `docs/03-api/` - API ugovori
5. `docs/05-deployment/` - kako deployati

### Ako si **Pravnik / Stručnjak za JN**
1. Ovaj README.md
2. `docs/01-domain-knowledge/tier-1-violations.md` - definicije prekršaja (validiraj!)
3. `docs/04-prompts/` - kako AI razmišlja (validiraj prompts!)
4. [DECISIONS.md](./DECISIONS.md) - otvorena pitanja koja trebaju pravnu odluku

### Ako si **Claude Code AI asistent**
- Pročitaj sve dokumente jednom
- Za konkretan zadatak, fokusiraj se na relevantni folder unutar `docs/`
- Slijedi konvencije iz `ARCHITECTURE.md` i `FOR_DEVELOPER.md`

---

## 📊 Status i sljedeći koraci

### ✅ Završeno

- [x] Definicija vizije i opsega
- [x] Odluka o samostalnom SaaS pristupu (vs Arhigon-only modul)
- [x] Odabir tehnološkog stacka
- [x] Brand i domena (Lexitor, lexitor.eu kupljena)
- [x] Analiza strukture DKOM rješenja (na uzorcima)
- [x] Analiza strukture VUS presuda
- [x] Identifikacija 6 Tier 1 prekršaja
- [x] Definicija 5 korisničkih grupa
- [x] Strategija feedback sustava (4 sloja)
- [x] Pricing model (Tier struktura)
- [x] Strategija PDF parsing (hibrid open source + Azure premium)

### 🔄 U tijeku

- [ ] Priprema dokumentacije za Claude Code
- [ ] Validacija definicija Tier 1 prekršaja s pravnikom
- [ ] Prikupljanje DKOM odluka (ručno/scraping)

### ⏭️ Sljedeći koraci

1. **Završetak dokumentacije** (1-2 tjedna)
2. **Sastanak s pravnikom** - validacija domain knowledge
3. **Prikupljanje pravne baze** (paralelno)
4. **Predaja developeru** kad je sve spremno
5. **Početak Faze 1A** razvoja

📖 **Otvorena pitanja i odluke:** vidi [DECISIONS.md](./DECISIONS.md)

---

## 👨‍💼 Tim i kontakt

### Vlasnik proizvoda
**Arhigon d.o.o.**

### Project Manager
- Strateške odluke
- Definicija domain knowledge
- Komunikacija s pravnicima
- Evaluacija kvalitete

### Tehnički tim
- **Senior Developer (.NET)** - integracija s Arhigon ekosistemom
- **Developer (Python)** - Lexitor core (uključuje se kasnije)
- **Claude Code (AI asistent)** - pair programming, dokumentacija

### Pravni savjetnici
- Stručnjak za javnu nabavu (vanjski)
- Pravnik specijaliziran za JN (po potrebi)

---

## 📜 Licenca i pravna napomena

**Status:** Proprietary software u vlasništvu Arhigon d.o.o.

**Disclaimer:** Lexitor je AI alat za pomoć u radu. **Nije zamjena za pravni savjet.** Svi rezultati moraju biti pregledani od strane kvalificiranog stručnjaka prije korištenja u službenim postupcima. Arhigon d.o.o. ne preuzima odgovornost za odluke donesene na temelju Lexitor analize.

---

*Dokument verzija: 1.0*
*Zadnje ažurirano: svibanj 2026.*
*Sljedeći pregled: po završetku Faze 1A*
