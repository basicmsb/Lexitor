# ARCHITECTURE.md - Lexitor tehnička arhitektura

> Detaljan tehnički opis arhitekture, tehnoloških odluka i obrazloženja.
> Namijenjeno developerima, tech lead-ovima i Claude Code AI asistentu.
> Za poslovni kontekst, vidi [PROJECT.md](./PROJECT.md).

---

## 📑 Sadržaj

- [1. Pregled arhitekture](#1-pregled-arhitekture)
- [2. Komponente sustava](#2-komponente-sustava)
- [3. Slojevi podataka](#3-slojevi-podataka)
- [4. AI / RAG arhitektura](#4-ai--rag-arhitektura)
- [5. Knowledge Graph](#5-knowledge-graph)
- [6. Feedback sustav](#6-feedback-sustav)
- [7. Sigurnost](#7-sigurnost)
- [8. Skalabilnost](#8-skalabilnost)
- [9. Deployment (Azure)](#9-deployment-azure)
- [10. Tehnološke odluke i obrazloženja](#10-tehnološke-odluke-i-obrazloženja)

---

## 1. Pregled arhitekture

### 1.1. High-level dijagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        KORISNICI                                 │
│  Projektant  │  Naručitelj  │  Ponuditelj  │  Pravnik  │  Konzultant │
└──────┬──────────┬───────────────┬──────────────┬─────────┬──────┘
       │          │               │              │         │
       └──────────┴───────────────┴──────────────┴─────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                            │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌─────────┐   │
│  │  Web UI    │  │  REST API  │  │   Admin    │  │ Webhooks│   │
│  │  (Next.js) │  │  (FastAPI) │  │ Dashboard  │  │         │   │
│  └────────────┘  └────────────┘  └────────────┘  └─────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │             API Gateway (FastAPI)                       │    │
│  │  Auth │ Rate Limit │ Routing │ Validation              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ Document │  │ Analyzer │  │Generator │  │ Collaboration│   │
│  │  Parser  │  │  Service │  │ Service  │  │   Service    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │
│                              │                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ Feedback │  │ Knowledge│  │  Auth /  │  │   Billing /  │   │
│  │  Service │  │  Service │  │  Users   │  │   Tier Mgmt  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AI / DATA LAYER                               │
│  ┌──────────────────────────────────────────────────────┐       │
│  │           Core AI Engine (LangChain)                 │       │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌────────┐ │       │
│  │  │  RAG    │  │   LLM   │  │ Document│  │ Result │ │       │
│  │  │Retriever│  │ Analyzer│  │Generator│  │Builder │ │       │
│  │  └─────────┘  └─────────┘  └─────────┘  └────────┘ │       │
│  └──────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │  Qdrant  │  │PostgreSQL│  │   Blob   │  │  Knowledge   │   │
│  │ (Vector) │  │  (Users, │  │  Storage │  │    Graph     │   │
│  │          │  │  Audit)  │  │  (PDFs)  │  │              │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ Anthropic│  │  Cohere  │  │  Azure   │  │ DKOM Scraper │   │
│  │  (LLM)   │  │(Embeddings)│ │  Doc AI  │  │   (custom)   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2. Glavne arhitekturalne odluke

| Odluka | Razlog |
|--------|--------|
| **Mikroservis arhitektura** (umjeren stupanj) | Različite komponente skaliraju različito - AI je CPU intensive, kolaboracija je IO intensive |
| **Python kao primarni jezik** | Najbolji ekosustav za AI/RAG (LangChain, sentence-transformers) |
| **FastAPI nad Flask/Django** | Async-first, automatska OpenAPI dokumentacija, type safety |
| **Qdrant nad Pinecone/Weaviate** | Self-hosted = niži trošak; brz; dobra Python integracija |
| **PostgreSQL kao "single source of truth"** | Industry standard, relacijski i JSON support, pgvector mogućnost |
| **Azure cloud** | Korisnik (Arhigon) već koristi Azure |
| **Stateless API** | Lakše skaliranje, bolja pouzdanost |

---

## 2. Komponente sustava

### 2.1. Document Parser Service

**Odgovornost:** Pretvaranje korisnikovog dokumenta (PDF/DOCX/XLSX) u strukturirani JSON.

**Tehnologija:**
- **Default (Razina B):** `pdfplumber` + `Camelot` + `Tesseract OCR` (open source)
- **Premium (Razina C):** Azure AI Document Intelligence (po izboru)

**Tijek:**
```
Dokument (PDF) → Tipologija (DON/Troškovnik/Žalba) →
   → Layout detekcija → Tablice extraction → Tekst extraction →
   → Strukturirani JSON
```

**Output schema:**
```json
{
  "document_id": "uuid",
  "type": "don|troskovnik|zalba|other",
  "metadata": {
    "filename": "...",
    "pages": 47,
    "extraction_method": "pdfplumber|azure_doc_ai",
    "extraction_confidence": 0.95
  },
  "structure": {
    "sections": [...],
    "tables": [...],
    "stavke": [...]
  }
}
```

### 2.2. Analyzer Service

**Odgovornost:** Detekcija prekršaja u učitanom dokumentu.

**Tijek:**
```
Strukturirani JSON → Stavka po stavku:
   → RAG Retriever (pronađi relevantne pravne odredbe)
   → LLM Analyzer (Claude evaluira stavku)
   → Result Builder (strukturira odgovor)
   → Cache (pohrani rezultat po hash-u stavke)
   → Feedback hooks (omogući korisniku reakciju)
```

**Glavni zadaci:**
- Detekcija 6 Tier 1 prekršaja
- Citiranje izvora (Anthropic Citations API)
- Klasifikacija rizika (zeleno/žuto/crveno)
- Generiranje prijedloga ispravka

### 2.3. Generator Service (Faza 2)

**Odgovornost:** Generiranje pravnih dokumenata.

**Tipovi dokumenata:**
- Žalba (za ponuditelja)
- Odgovor na žalbu (za naručitelja)
- Zahtjev za pojašnjenje (za ponuditelja)
- Prijedlog izmjene DON-a (za ponuditelja u savjetovanju)

**Tijek:**
```
Korisnikova situacija → Pretraga relevantnih presedana →
   → Izbor template-a → LLM generiranje →
   → Validation (citati, pravna logika) →
   → Korisnik prima nacrt → Track changes → Final dokument
```

### 2.4. Collaboration Service (Faza 2)

**Odgovornost:** Asinkrona kolaboracija na dokumentima.

**Funkcionalnost:**
- Verzioniranje dokumenata
- Track changes (CRDT-based)
- Komentari uz dijelove teksta
- Share linkovi sa pravima (read/comment/edit)
- Notifikacije

**Faza 3 nadogradnja:** Sinkrona kolaboracija (WebSockets, real-time CRDT).

### 2.5. Feedback Service

**Odgovornost:** Prikupljanje i obrada korisničkog feedback-a (4 sloja podataka).

**Vidi poglavlje [6. Feedback sustav](#6-feedback-sustav).**

### 2.6. Knowledge Service

**Odgovornost:** Upravljanje pravnom bazom (CRUD, indeksiranje, search).

**Funkcionalnost:**
- Upload novih pravnih dokumenata
- Re-indexing pri ažuriranjima
- Knowledge Graph upravljanje
- Pretraga prakse (za UI Knowledge Base ekran)

### 2.7. Auth / Users Service

**Odgovornost:** Autentikacija, autorizacija, upravljanje korisnicima.

**Tehnologija:**
- Azure AD B2C (eksterna autentikacija)
- JWT tokeni za API pristup
- Role-based access control (RBAC)
- Multi-tenant struktura (organizacije)

### 2.8. Billing / Tier Management

**Odgovornost:** Upravljanje pretplatama i limitima.

**Funkcionalnost:**
- Stripe integracija za naplatu
- Tier enforcement (broj analiza, korisnika, itd.)
- Usage metering
- Upgrade/downgrade flow

---

## 3. Slojevi podataka

Lexitor radi na **4 sloja podataka**, svaki sa specifičnom svrhom:

### Sloj 1: Sirova pravna baza

**Što:** Originalni PDF/HTML dokumenti pravnih izvora.

**Sadržaj:**
- ZJN (Zakon o javnoj nabavi) - sve verzije
- Pravilnici i uredbe
- DKOM odluke (sve godine)
- VUS presude
- Sud EU presude (relevantne)
- Direktive EU

**Storage:** Azure Blob Storage
**Veličina (procjena):** ~10-20 GB za HR jurisdikciju
**Update frequency:** Tjedno (auto scraper) + manualno

### Sloj 2: Strukturirano znanje (Knowledge Graph)

**Što:** Veze između pravnih izvora, tematske kategorije, doktrine.

**Sadržaj:**
- Tematska kategorizacija
- Hijerarhijski odnosi (DKOM → VUS → Sud EU)
- Argumentativne veze ("argument X uspio u slučaju Y")
- Citation graph (tko koga citira)

**Storage:** PostgreSQL (s pgvector ekstenzijom) + custom graph queries
**Veličina:** ~100 MB metadata
**Update frequency:** Pri svakom novom dokumentu (semi-automatski + ručni review)

**Vidi poglavlje [5. Knowledge Graph](#5-knowledge-graph).**

### Sloj 3: Korisničko znanje

**Što:** Korekcije, ocjene, ljudske izmjene generiranih dokumenata.

**Sadržaj:**
- Korisnikove korekcije analize ("ne slažem se zato što...")
- Diff između AI nacrta i finalne ljudske verzije
- Ocjene relevantnosti (👍 / 👎)
- Tagovi i komentari

**Storage:** PostgreSQL
**Veličina:** Raste sa korisnicima (~100 MB / 1000 korisnika)
**Privacy:** Tier-based (Standard share-uje anonimizirano, Premium privatno)

### Sloj 4: Verifikacijsko znanje ⭐

**Što:** Stvarni ishodi DKOM/VUS odluka koji potvrđuju ili opovrgavaju Lexitor predikcije.

**Sadržaj:**
- KLASA broj DKOM odluke
- Lexitor predikcija (vjerojatnost uspjeha)
- Korisnikova izmjena (delta od AI nacrta)
- DKOM stvarni ishod (odbijena/prihvaćena)
- Točnost predikcije

**Storage:** PostgreSQL + linkovi na Sloj 1 (PDF odluka)
**Update:** Auto-scraper + manualno (korisnik unese KLASA)

**Vrijednost:** Ovo je naš **data moat** - što više imamo, to bolji sustav.

---

## 4. AI / RAG arhitektura

### 4.1. RAG Pipeline

```
USER QUERY (stavka troškovnika)
       │
       ▼
┌──────────────────────────────────────┐
│  1. Embed Query                      │
│     Cohere embed-multilingual-v3     │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  2. Vector Search                    │
│     Qdrant - top 20 najsličnijih     │
│     filteri: tip izvora, godina      │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  3. Hybrid Search                    │
│     + Keyword search (BM25)          │
│     + Re-ranking                     │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  4. Context Building                 │
│     Top 10 chunks → formatirano      │
│     Anthropic Citations format       │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  5. LLM Analysis                     │
│     Claude Sonnet 4.5                │
│     Specijalizirani prompt po Tier   │
│     Citations on                     │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  6. Validation                       │
│     - Citati postoje?                │
│     - JSON schema valid?             │
│     - Logički konzistentno?          │
└──────────────────────────────────────┘
       │
       ▼
   STRUKTURIRANI ODGOVOR
```

### 4.2. Chunking strategija

**Različite strategije za različite tipove dokumenata:**

#### ZJN i pravilnici
- **Granulacija:** Po stavku/članku
- **Razlog:** Svaka stavka ima pravnu samostalnost
- **Metadata:** broj članka, broj stavka, naslov poglavlja

#### DKOM odluke
- **Granulacija:** Po sekciji obrazloženja + cijela odluka
- **Razlog:** Fakti, žalbeni navodi, ocjena vijeća su zasebni
- **Metadata:** KLASA, datum, ishod, primijenjeni članci

#### VUS presude
- **Granulacija:** Po točci obrazloženja
- **Razlog:** Točke su numerirane i logički cjelovite
- **Metadata:** poslovni broj, datum, ishod, pred-instanca (DKOM rješenje)

### 4.3. Prompt Engineering

**Master prompt** (osnovni, za sve Tier-e):
- Definicija Lexitor-a kao asistenta
- Pravna domena javne nabave
- Format odgovora (JSON schema)
- Instrukcije za citiranje
- Anti-halucinacijska pravila

**Tier-specific prompts** - dodatne instrukcije za svaki tip prekršaja:
- Tier 1.1: Brendovi bez "ili jednakovrijedno"
- Tier 1.2: Diskriminatorne specifikacije
- Tier 1.3: Nepotpuni opisi
- Tier 1.4: Manipulacije cijenama
- Tier 1.5: Nedosljednost DON-a i troškovnika
- Tier 1.6: Komplet vs pojedinačne stavke

**Verzioniranje promptova** - svaka promjena prompta = nova verzija u `docs/04-prompts/`. Audit log čuva koji je prompt korišten za koju analizu.

### 4.4. Anthropic Citations API

Lexitor koristi **Citations** funkcionalnost Claude API-ja:
- LLM vraća strukturirane citate koji **garantirano postoje** u izvoru
- Smanjuje halucinacije
- Korisnik može direktno provjeriti svaki citat

**Validation layer:**
- Sustav dodatno provjerava citate
- Ako Claude promaši, sustav označi nalaz kao "low confidence"
- Korisniku se prikaže s upozorenjem

---

## 5. Knowledge Graph

### 5.1. Zašto Knowledge Graph?

Pravni izvori **nisu izolirani dokumenti** - oni se međusobno referenciraju, citiraju, opovrgavaju.

**Primjer iz stvarnosti:**
- DKOM rješenje X primijenilo doktrinu A
- VUS poništio DKOM-ov stav, donio doktrinu B
- DKOM kasnije slijedi doktrinu B u rješenju Y
- Sud EU u presudi Z ima drugačije tumačenje

Bez Knowledge Graph-a, sustav bi vidio 4 nezavisna dokumenta. **Sa KG-om, sustav razumije pravnu hijerarhiju i evoluciju doktrine.**

### 5.2. Što čvorovi predstavljaju?

```
ČVOROVI:
- PravniDokument (tip: ZJN, DKOM, VUS, Sud EU, Direktiva)
- PravniČlanak (član ZJN-a, čl. 280, čl. 290...)
- Doktrina (apstraktni pravni stav)
- Tematska kategorija (npr. "Tehničke specifikacije", "Manipulacije cijenama")
- Žalbeni navod (apstraktni argument)

VEZE:
- CITIRA: dokument X citira dokument Y
- PRIMJENJUJE: rješenje primjenjuje članak X
- PONIŠTAVA: VUS poništava DKOM
- SLIJEDI: DKOM slijedi VUS doktrinu
- OPOVRGAVA: dokument X opovrgava doktrinu Y
- KATEGORIZIRA: dokument je u tematskoj kategoriji X
- ARGUMENT: dokument koristi argument X
```

### 5.3. Implementacija

**Pristup za PoC:** PostgreSQL sa relacijskim modelom + pgvector
- Tablice: `nodes`, `edges`, `embeddings`
- Brze pretrage uz indekse
- Cypher-like queries kroz custom funkcije

**Eventualna nadogradnja:** Neo4j ili Apache AGE
- Ako KG bude vrlo gust (50K+ čvorova)
- Bolje performanse za dubinsko traženje

### 5.4. Kako se gradi?

**Faza 1 - automatski:**
- Parser izvlači citate iz dokumenata (regex + LLM)
- "Članak 280. ZJN" → veza prema ZJN čl. 280
- "DKOM KLASA UP/II-..." → veza prema toj odluci

**Faza 2 - polu-automatski:**
- LLM klasificira dokumente u tematske kategorije
- LLM detektira doktrine ("ovaj dokument zauzima stav...")
- Pravnik validira i koriguje

**Faza 3 - korisničko obogaćivanje:**
- Korisnici tagiraju i komentiraju
- Sustav uči obrasce

---

## 6. Feedback sustav

### 6.1. Cilj

**Stvoriti sustav koji uči iz prakse - i to po više dimenzija odjednom.**

### 6.2. 4 sloja feedback-a

#### Sloj 1: Korekcije analize

**Korisnik kaže: "AI je rekao X, ja se ne slažem - evo zašto."**

```json
{
  "feedback_id": "uuid",
  "analysis_id": "uuid",
  "stavka_id": "uuid",
  "user_id": "uuid",
  "ai_status": "krsenje",
  "user_correction": "uskladeno",
  "category": "false_positive",
  "reason": "Stavka ima 'ili jednakovrijedno' koje AI nije prepoznao",
  "evidence": "screenshot ili tekstualni dokaz",
  "timestamp": "..."
}
```

#### Sloj 2: Izmjene generiranih dokumenata

**Korisnik prepravi AI nacrt prije slanja.**

```json
{
  "diff_id": "uuid",
  "document_id": "uuid",
  "original_ai_text": "...",
  "final_user_text": "...",
  "changes": [
    {
      "type": "addition|deletion|modification",
      "location": "paragraph_3",
      "before": "...",
      "after": "...",
      "ai_classification": "stilska|argumentativna|citatna"
    }
  ],
  "user_id": "uuid",
  "timestamp": "..."
}
```

#### Sloj 3: Vlastite ocjene relevantnosti

**Korisnik na svakom rezultatu može dati 👍 / 👎 / komentar.**

```json
{
  "rating_id": "uuid",
  "result_id": "uuid",
  "rating": "positive|negative|partial",
  "comment": "...",
  "timestamp": "..."
}
```

#### Sloj 4: Stvarni ishodi DKOM/VUS ⭐

**Najvažniji sloj - povezuje korisnikov slučaj sa stvarnim pravnim ishodom.**

```json
{
  "outcome_id": "uuid",
  "case_id": "uuid",  // korisnikov slučaj
  "lexitor_prediction": {
    "outcome": "uspjeh|neuspjeh",
    "probability": 0.75,
    "key_arguments": [...]
  },
  "user_modification": "...",  // što je čovjek promijenio
  "actual_outcome": {
    "source": "dkom|vus",
    "klasa": "UP/II-034-02/...",
    "decision": "odbijena|prihvaćena|djelomično",
    "decision_date": "...",
    "decision_url": "..."
  },
  "lexitor_was_correct": true,
  "extraction_method": "auto_scraper|manual_user"
}
```

### 6.3. Privacy i Tier model

**Standard tier:**
- Korisnikov feedback se anonimizira (uklonimo OIB-e, tvrtke, KLASA brojeve)
- Anonimizirani feedback se koristi za poboljšanje AI sustava
- Korisnik to **eksplicitno prihvaća** u Terms of Service

**Premium tier:**
- Korisnikov feedback se **NE dijeli** sa drugima
- Koristi se samo za personaliziranje **njegovog** iskustva

### 6.4. Auto-tracking DKOM ishoda

**Sustav radi sljedeće u pozadini (background job, dnevno):**

```python
# Pseudokod
def auto_track_outcomes():
    # 1. Pronađi nove DKOM odluke
    new_dkom = scrape_dkom_new_decisions(since=last_run)
    
    # 2. Za svaku, pokušaj povezati sa korisnikovim slučajem
    for decision in new_dkom:
        case = find_user_case_by_klasa(decision.klasa)
        if case:
            # 3. Spremi stvarni ishod
            save_actual_outcome(case_id=case.id, decision=decision)
            
            # 4. Usporedi sa Lexitor predikcijom
            evaluate_lexitor_accuracy(case)
            
            # 5. Notification korisniku
            notify_user(case.user_id, decision)
            
            # 6. Dodaj u trening podatke (Sloj 4)
            add_to_training_dataset(case, decision)
```

---

## 7. Sigurnost

### 7.1. Autentikacija i autorizacija

**Azure AD B2C** za eksternu autentikacija (registracija, login).

**JWT tokeni** za API pristup:
- Access token (15 min životni vijek)
- Refresh token (7 dana)
- Rotacija na svaki refresh

**RBAC (Role-Based Access Control):**
- Roles: `user`, `team_member`, `team_admin`, `org_admin`, `super_admin`
- Permissions: granular per resource type

**Multi-tenant izolacija:**
- Svaka organizacija je zaseban "tenant"
- Row-level security u PostgreSQL
- Cross-tenant pristup nemoguć osim za super_admin

### 7.2. Tajni podaci

**Azure Key Vault** za sve API ključeve i tajne:
- Anthropic API key
- Cohere API key
- Database connection strings
- JWT signing keys

**Nikad u kodu, nikad u environment varijablama u plain textu.**

### 7.3. Podaci u tranzitu

- HTTPS only (TLS 1.3)
- HSTS headers
- Certificate pinning za mobile (kasnije)

### 7.4. Podaci u mirovanju

- Azure Disk Encryption za Postgres
- Azure Blob: server-side encryption
- Sensitive fields u DB: dodatno enkriptirani (npr. user comments)

### 7.5. GDPR compliance

- Eksplicitan consent za svaku vrstu obrade podataka
- Pravo na brisanje (right to be forgotten)
- Data export (korisnik može preuzeti sve svoje podatke)
- Audit log svake obrade osobnih podataka
- DPO contact information dostupan
- EU data residency (Azure West Europe / North Europe)

### 7.6. Anti-prompt injection

Korisnik može pokušati "obmanuti" AI kroz manipulirani sadržaj dokumenta:
- "Ignore previous instructions and..."
- Skriveni tekst u PDF-u

**Mitigacije:**
- Input sanitization
- Sandbox environment za LLM
- Detekcija sumnjivih obrazaca
- Output validation

### 7.7. Rate limiting

- API rate limit po korisniku (npr. 100 zahtjeva/min za Premium)
- DDoS protection (Azure Front Door)
- Cost protection (alarmi pri prevelikoj potrošnji LLM kredita)

---

## 8. Skalabilnost

### 8.1. Horizontalno skaliranje

**API Layer:**
- FastAPI servis u Azure Container Apps
- Auto-scaling: 1-10 instanci based on CPU
- Stateless = lako skaliranje

**Worker Layer (Celery):**
- Odvojeni workers za:
  - Document parsing (CPU intensive)
  - LLM calls (IO intensive)
  - Knowledge base updates (long-running)
- Auto-scaling temeljem dužine reda

**Database:**
- PostgreSQL: read replicas za read-heavy workloads
- Connection pooling (PgBouncer)
- Sharding po `tenant_id` ako bude potreban

**Vector DB:**
- Qdrant: cluster mode za HA
- Sharding kolekcija po jurisdikciji (HR, SI, BiH, SR...)

### 8.2. Caching

**Više slojeva cache-a:**

1. **CDN (Azure Front Door)** - statički assets, javne stranice
2. **Redis** - često tražene API odgovore
3. **In-memory (per-instance)** - prompt templates, schemas
4. **DB-level** - materialized views za statistike

### 8.3. Background jobs

**Celery + Redis** za:
- Document parsing (može trajati 30s+)
- Bulk analiza (cijeli DON može imati 200+ stavki)
- Knowledge base updates
- DKOM scraper (dnevni job)
- Email notifications

**Scheduled tasks (Celery Beat):**
- Daily: DKOM scraper
- Weekly: VUS scraper
- Monthly: Re-evaluation analytics

### 8.4. Monitoring i Observability

**Azure Application Insights:**
- Request tracing
- Performance counters
- Custom metrics (LLM token usage, costs)
- Alerts (errors, latency, costs)

**Strukturirani logging:**
- JSON format
- Correlation IDs
- Tenant ID, user ID, request ID

**Custom dashboards:**
- LLM cost monitoring
- Analiza po Tier-u (uspjeh/neuspjeh)
- Korisnička retencija
- Slowest queries

---

## 9. Deployment (Azure)

### 9.1. Azure resursi

| Servis | Namjena | Konfiguracija |
|--------|---------|---------------|
| **Azure Container Apps** | API servis (FastAPI) | 1-10 replica, 2 vCPU / 4 GB |
| **Azure Container Apps** | Workers (Celery) | 1-5 replica, varies |
| **Azure Container Apps** | Qdrant | 2 replica, 4 vCPU / 8 GB / 100 GB SSD |
| **Azure Database for PostgreSQL** | Glavna baza | Burstable B2s, 100 GB, HA |
| **Azure Cache for Redis** | Cache + Celery broker | Standard C1, 1 GB |
| **Azure Blob Storage** | PDF arhiva | Standard, RA-GRS |
| **Azure Key Vault** | Tajne | Standard tier |
| **Azure Front Door** | CDN + DDoS | Standard tier |
| **Azure Application Insights** | Monitoring | Pay-as-you-go |
| **Azure AD B2C** | Auth | Per-user (besplatno do 50K MAU) |

### 9.2. Environments

**Development:**
- Lokalno + cloud sandbox za AI
- Manji resursi
- Test podaci

**Staging:**
- Identično produkciji ali sa scaled-down resursima
- Real-world testiranje
- UAT za pravnike

**Production:**
- Multi-region (Azure West Europe primary, North Europe DR)
- Auto-scaling enabled
- Backup retencija 30 dana

### 9.3. CI/CD Pipeline (GitHub Actions)

```yaml
# Pseudokod GitHub Actions workflow
on:
  push:
    branches: [main, staging]

jobs:
  test:
    - Lint (ruff, mypy)
    - Unit tests (pytest)
    - Integration tests
    - Security scan (Trivy)
  
  build:
    - Build Docker image
    - Push to Azure Container Registry
  
  deploy:
    - Deploy to staging (auto on staging branch)
    - Wait for manual approval
    - Deploy to production (on main branch)
    - Run smoke tests
    - Notify Slack
```

### 9.4. Database migracije

- **Alembic** za schema migracije (PostgreSQL)
- Migracije idu kroz CI/CD pipeline
- Rollback strategija za svaku migraciju
- Blue-green deployment za breaking changes

---

## 10. Tehnološke odluke i obrazloženja

### 10.1. Zašto Python (a ne .NET)?

**Razlozi:**
- ✅ Daleko najbolji ekosustav za AI/LLM (LangChain, sentence-transformers, HuggingFace)
- ✅ Brži razvoj prototipova
- ✅ Veća zajednica, više primjera, više tutoriala za RAG
- ✅ Standardni jezik za Data Science / ML

**Trade-off:**
- ⚠️ Arhigon ekosustav je .NET - ali Lexitor je samostalan, komunicira preko REST API-ja

### 10.2. Zašto FastAPI?

**Razlozi:**
- ✅ Async-first (važno za LLM pozive)
- ✅ Automatska OpenAPI dokumentacija
- ✅ Type-safe (Pydantic integracija)
- ✅ Industry standard za nove Python API-je
- ✅ Odlične performanse

### 10.3. Zašto Claude (a ne GPT)?

**Razlozi:**
- ✅ **Najbolji LLM za hrvatski** - kritično za PoC fazu
- ✅ Citations API (manje halucinacija)
- ✅ Veći context window (200K tokens) - cijeli dokument odjednom
- ✅ Bolji za pravno rezoniranje (anekdotski, ali konzistentno)

**Strategija:** LLM-agnostic dizajn - lako prebacivanje ako se okolnosti promijene.

### 10.4. Zašto Qdrant (a ne Pinecone/Weaviate)?

**Razlozi:**
- ✅ Self-hosted = bez external API ovisnosti
- ✅ Niži operativni trošak (samo server)
- ✅ Brz, dobre performanse
- ✅ Otvoreni kod (Apache 2.0)
- ✅ Dobra Python klijentska biblioteka

**Trade-off:**
- ⚠️ Treba upravljati infrastrukturom
- ⚠️ Manje "managed features"

### 10.5. Zašto PostgreSQL (a ne MongoDB)?

**Razlozi:**
- ✅ ACID transakcije (kritično za billing, audit)
- ✅ JSON support (jsonb) za fleksibilne schema
- ✅ pgvector za embeddings (alternativa Qdrant-u)
- ✅ Industry standard
- ✅ Azure managed verzija

### 10.6. Zašto LangChain?

**Razlozi:**
- ✅ Standard za RAG pipeline
- ✅ Mnogo gotovih komponenti
- ✅ Aktivna zajednica

**Trade-off:**
- ⚠️ Brzo se mijenja (breaking changes)
- ⚠️ Ponekad apstrakcija previše "leaky"

**Strategija:** Koristi LangChain za standardne dijelove, custom kod za kritične dijelove.

### 10.7. Zašto Streamlit za MVP UI?

**Razlozi:**
- ✅ Najbrži način za internal UI (1-2 dana razvoja)
- ✅ Python-only (jedan jezik)
- ✅ Dovoljno za testing sa pravnicima

**Migracija:** Faza 2 prelazi na Next.js za pune korisnike.

### 10.8. Zašto Azure (a ne AWS/GCP)?

**Razlog:** Korisnik (Arhigon) već koristi Azure. Operativna konzistencija, postojeći ugovori, postojeća ekspertiza.

---

## 📚 Reference

- [PROJECT.md](./PROJECT.md) - poslovni kontekst
- [PHASES.md](./PHASES.md) - fazni plan razvoja
- [DECISIONS.md](./DECISIONS.md) - sve odluke
- [FOR_DEVELOPER.md](./FOR_DEVELOPER.md) - praktičan brief

---

*Verzija: 1.0 | Svibanj 2026 | Lexitor by Arhigon*
