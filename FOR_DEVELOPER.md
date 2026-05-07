# FOR_DEVELOPER.md - Brief za informatičara

> Praktičan dokument koji daje developeru sve što treba za "ulazak u trku".
> Skraćeni vodič bez nepotrebne teorije - samo ono što ti treba.

---

## 📑 Sadržaj

- [TL;DR za novog developera](#-tldr-za-novog-developera)
- [Što gradiš](#-što-gradiš)
- [Što očekujemo od tebe](#-što-očekujemo-od-tebe)
- [Tehnološki stack - cheat sheet](#️-tehnološki-stack---cheat-sheet)
- [Setup - prvi koraci](#-setup---prvi-koraci)
- [Struktura projekta](#-struktura-projekta)
- [Razvojni workflow](#-razvojni-workflow)
- [Što imaš spremno (kao input)](#-što-imaš-spremno-kao-input)
- [Što ti treba odlučiti](#-što-ti-treba-odlučiti)
- [Komunikacija s timom](#-komunikacija-s-timom)
- [Reference](#-reference)

---

## 🎯 TL;DR za novog developera

**Ime projekta:** Lexitor
**Što je:** AI asistent za usklađenost javne nabave (RAG + LLM)
**Tvoj jezik:** Python 3.11+
**Glavni framework:** FastAPI + LangChain + Claude API
**Vlasnik:** Arhigon d.o.o. (radi se kao samostalni SaaS)
**Trenutna faza:** Faza 1A - PoC (8-12 tjedana)
**Pristup:** Iterativni razvoj uz Claude Code u VS Code-u

**Ako imaš samo 5 minuta, pročitaj:**
1. Ovaj poglavlje
2. [Setup - prvi koraci](#-setup---prvi-koraci)
3. [Što imaš spremno (kao input)](#-što-imaš-spremno-kao-input)

Ostatak je referentno gradivo.

---

## 🏗️ Što gradiš

Lexitor je **RAG-based AI sustav** koji analizira dokumente javne nabave (DON, troškovnike, žalbe) i vraća strukturirane nalaze sa citatima iz pravnih izvora (ZJN, DKOM, VUS, Sud EU).

### Glavna tri use case-a

1. **Analiza dokumenta** - korisnik upload-a PDF, sustav pronađe Tier 1 prekršaje
2. **Generiranje pravnih dokumenata** (Faza 2) - sustav piše nacrt žalbe / odgovora / pojašnjenja
3. **Pretraga prakse** - korisnik pretražuje DKOM/VUS bazu

### Što tehnički radiš (Faza 1A)

```python
# Pseudokod tvog rada
def build_lexitor_poc():
    # Tjedan 1: Setup
    setup_python_env()
    setup_docker_local()
    setup_postgres_qdrant_redis()
    
    # Tjedan 2-3: Document Parser
    build_pdf_parser()
    build_docx_parser()
    build_xlsx_parser()
    
    # Tjedan 3-5: Knowledge Base
    scrape_dkom()
    scrape_vus()
    load_zjn()
    chunk_and_embed()
    index_in_qdrant()
    
    # Tjedan 5-6: RAG Retriever
    build_vector_search()
    build_hybrid_search()
    build_reranker()
    
    # Tjedan 6-9: LLM Analyzer (najvažnije!)
    write_master_prompt()
    write_tier_1_prompts()  # 6 Tier-a
    integrate_claude_api()
    add_citations_validation()
    add_caching()
    
    # Tjedan 9-10: API
    build_fastapi_endpoints()
    add_celery_jobs()
    add_progress_reporting()
    
    # Tjedan 10-11: UI (Streamlit)
    build_upload_screen()
    build_results_screen()
    build_feedback_components()
    
    # Tjedan 11-12: Evaluation
    run_ground_truth_evaluation()
    tune_prompts()
    fix_edge_cases()
    
    return PoC_ready
```

---

## 📋 Što očekujemo od tebe

### Glavni outputi

1. **Funkcionalan PoC** koji prolazi kriterije iz [PHASES.md](./PHASES.md):
   - Recall ≥ 80%, Precision ≥ 70% na ground truth setu
   - API odgovara unutar 60 sekundi za 20 stavki
   - Citation accuracy 100%
   - Web UI radi end-to-end

2. **Čist, dokumentiran kod** prema našim standardima (vidi dolje)

3. **Test coverage** ≥ 70% za core funkcionalnosti

4. **Deployment-ready** sustav (Docker + Azure)

### Soft skills

- **Iterativan rad** sa PM-om - tjedne sync sastanke (15-30 min)
- **Pitati za pomoć rano** - ako nešto ne razumiješ pravnu domenu, pitaj
- **Dokumentirati odluke** - svaka tehnička odluka ide u DECISIONS.md ili komentare koda
- **Komunikacija** - Slack/Teams dnevno, video call po potrebi

### Kvaliteta koda

- **Type hints** posvuda (`mypy` strict mode)
- **Docstrings** za sve public funkcije
- **Pydantic** za validaciju podataka
- **Async-first** gdje god ima smisla
- **No magic numbers** - sve konstante u config-u
- **Pre-commit hooks** (ruff, mypy, pytest)

---

## 🛠️ Tehnološki stack - cheat sheet

### Glavni alati

```toml
# pyproject.toml - ključne ovisnosti
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.110"
uvicorn = "^0.27"
pydantic = "^2.6"
langchain = "^0.1"
anthropic = "^0.20"
cohere = "^5.0"
qdrant-client = "^1.8"
psycopg = "^3.1"
sqlalchemy = "^2.0"
alembic = "^1.13"
celery = "^5.3"
redis = "^5.0"
pdfplumber = "^0.10"
python-docx = "^1.1"
openpyxl = "^3.1"
streamlit = "^1.30"
pytest = "^8.0"
pytest-asyncio = "^0.23"
pytest-cov = "^4.1"
ruff = "^0.3"
mypy = "^1.8"
```

### Servisi

| Servis | Lokalno | Production (Azure) |
|--------|---------|--------------------|
| Database | PostgreSQL 16 (Docker) | Azure Database for PostgreSQL |
| Vector DB | Qdrant (Docker) | Qdrant (Azure Container Apps) |
| Cache/Queue | Redis (Docker) | Azure Cache for Redis |
| Storage | Lokalni file system | Azure Blob Storage |
| Secrets | .env | Azure Key Vault |
| Auth | Bypass za MVP | Azure AD B2C |

### Eksterni API-ji

| API | Namjena | Pristup |
|-----|---------|---------|
| Anthropic Claude | LLM rezoniranje | API key u .env |
| Cohere | Embeddings | API key u .env |
| Azure AI Document Intelligence | Premium PDF parsing | Azure credentials |

---

## 🚀 Setup - prvi koraci

### Pretpostavke

- Windows / macOS / Linux
- Python 3.11+
- Docker Desktop
- Git
- VS Code (preporučeno)
- Claude Code ekstenzija

### Korak 1: Repo setup

```bash
git clone https://github.com/basicmsb/Lexitor.git
cd Lexitor
```

### Korak 2: Backend (Python 3.12 + Poetry)

```bash
# Backend živi u apps/backend
cd apps/backend

# Instaliraj Poetry (ako nemaš) — pipx install poetry==1.8.2
poetry install
cp .env.example .env
# Popuni ANTHROPIC_API_KEY i COHERE_API_KEY

cd ../..
```

### Korak 3: Frontend (Node 20 + pnpm 9)

```bash
# Iz root foldera
pnpm install
```

### Korak 4: Lokalni servisi (Docker)

```bash
docker compose up -d        # postgres, redis, qdrant
docker compose ps           # provjera statusa
```

### Korak 5: Migracije

```bash
cd apps/backend
poetry run alembic upgrade head
cd ../..
```

### Korak 6: Pokreni sve (3 terminala)

**Terminal 1 — Backend (FastAPI):**
```bash
pnpm dev:backend
# → http://localhost:8000 (i /docs za Swagger)
```

**Terminal 2 — Web (lexitor.eu, port 3000):**
```bash
pnpm dev:web
# → http://localhost:3000
```

**Terminal 3 — App (app.lexitor.eu, port 3001):**
```bash
pnpm dev:app
# → http://localhost:3001
```

Ili sve odjednom: `pnpm dev` (paralelno).

### Korak 7: Provjeri da radi

```bash
curl http://localhost:8000/health          # backend
curl http://localhost:3000                 # web (landing)
curl http://localhost:3001/dashboard       # app
```

---

## 📂 Struktura projekta

```
lexitor/
├── src/                          # Source kod
│   ├── api/                      # FastAPI endpoints
│   │   ├── main.py               # Entry point
│   │   ├── routes/               # API rute
│   │   ├── middleware/           # Auth, CORS, etc.
│   │   └── schemas/              # Pydantic request/response
│   │
│   ├── core/                     # Core business logic
│   │   ├── analyzer/             # LLM analiza
│   │   ├── retriever/            # RAG retrieval
│   │   ├── generator/            # Document generator (Faza 2)
│   │   └── prompts/              # Prompt templates
│   │
│   ├── document_parser/          # PDF/DOCX/XLSX parsing
│   │   ├── pdf_parser.py
│   │   ├── docx_parser.py
│   │   ├── xlsx_parser.py
│   │   └── azure_parser.py       # Premium fallback
│   │
│   ├── knowledge_base/           # Pravna baza
│   │   ├── scrapers/
│   │   │   ├── dkom_scraper.py
│   │   │   └── vus_scraper.py
│   │   ├── parsers/              # Parsiranje pravnih dokumenata
│   │   ├── chunker.py            # Chunking strategije
│   │   ├── embedder.py           # Cohere embeddings
│   │   └── indexer.py            # Qdrant indexing
│   │
│   ├── feedback/                 # Feedback sustav
│   │   ├── models.py
│   │   ├── correction_service.py    # Sloj 1
│   │   ├── diff_service.py          # Sloj 2
│   │   ├── rating_service.py        # Sloj 3
│   │   └── outcome_tracker.py       # Sloj 4
│   │
│   ├── collaboration/            # Asinkrona kolaboracija (Faza 2)
│   │
│   ├── models/                   # Pydantic + SQLAlchemy modeli
│   │   ├── user.py
│   │   ├── document.py
│   │   ├── analysis.py
│   │   └── feedback.py
│   │
│   ├── workers/                  # Celery workers
│   │   ├── analysis_worker.py
│   │   ├── parser_worker.py
│   │   └── scraper_worker.py
│   │
│   ├── ui/                       # Streamlit UI
│   │   ├── app.py
│   │   ├── pages/
│   │   └── components/
│   │
│   ├── utils/                    # Pomoćni alati
│   │   ├── config.py             # Settings (Pydantic Settings)
│   │   ├── logging.py
│   │   ├── cache.py
│   │   └── validators.py
│   │
│   └── db/                       # Database
│       ├── session.py
│       └── migrations/           # Alembic
│
├── tests/                        # Testovi
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/                 # Test podaci
│
├── data/                         # Pravna baza (gitignored)
│   ├── 01-zakoni/
│   ├── 02-dkom-odluke/
│   ├── 03-vus-presude/
│   └── 04-sud-eu/
│
├── scripts/                      # Standalone skripte
│   ├── scrape_dkom.py
│   ├── build_index.py
│   └── evaluate.py
│
├── deployment/                   # Deployment
│   ├── docker-compose.yml        # Lokalni development
│   ├── Dockerfile
│   ├── azure/                    # Azure resources
│   └── github-actions/           # CI/CD workflows
│
├── docs/                         # Detaljna dokumentacija
│   ├── 01-domain-knowledge/
│   ├── 02-data-models/
│   ├── 03-api/
│   ├── 04-prompts/
│   └── 05-deployment/
│
├── pyproject.toml                # Poetry config
├── poetry.lock
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── README.md                     # Glavni overview
├── PROJECT.md                    # Poslovna vizija
├── ARCHITECTURE.md               # Tehnička arhitektura
├── PHASES.md                     # Fazni plan
├── DECISIONS.md                  # Tracker odluka
└── FOR_DEVELOPER.md              # OVAJ DOKUMENT
```

---

## 🔄 Razvojni workflow

### Dnevni ritam

```
8-9h:    Sync sa PM-om (15 min) - što danas, blokirajuća pitanja
9-12h:   Glavni razvoj (deep work)
12-13h:  Pauza
13-15h:  Razvoj nastavak
15-16h:  Code review, dokumentacija, commit
16-17h:  Buffer za neočekivano
```

### Git workflow

```bash
# Feature branch
git checkout -b feature/dkom-scraper

# Razvoj + commits
git add .
git commit -m "feat: add DKOM scraper for new decisions"

# Push i Pull Request
git push origin feature/dkom-scraper
# Otvori PR na GitHub-u
```

**Commit konvencija:** Conventional Commits
- `feat:` nova funkcionalnost
- `fix:` bug fix
- `refactor:` refaktoriranje bez promjene funkcionalnosti
- `test:` dodani/promijenjeni testovi
- `docs:` dokumentacija
- `chore:` build, dependencies, etc.

### PR workflow

1. Kreiraj feature branch
2. Razvij + testiraj lokalno
3. Push i otvori PR
4. CI mora proći (lint, tests)
5. Review (od PM-a ili drugog dev-a)
6. Merge u main
7. Auto-deploy na staging

### Testiranje

```bash
# Pokreni sve testove
pytest

# Sa coverage
pytest --cov=src --cov-report=html

# Samo unit testove
pytest tests/unit/

# Specifični test
pytest tests/unit/test_analyzer.py::test_tier_1_1
```

### Lint i formatting

```bash
# Lint
ruff check src/

# Auto-fix
ruff check src/ --fix

# Format
ruff format src/

# Type check
mypy src/
```

---

## 📦 Što imaš spremno (kao input)

PM ti je pripremio sve potrebne ulaze prije nego si krenuo:

### 1. Pravna baza (u `data/` folderu)

- ZJN i pravilnici (PDF / Markdown)
- 50-100 DKOM odluka (PDF)
- 20-30 VUS presuda (PDF)
- Ključne Sud EU presude (PDF)
- Anotacije (Excel/CSV) - po godini, temi, tipu prekršaja

### 2. Ground truth test set

- `tests/fixtures/ground_truth_troskovnik.json` - 15-20 stavki sa poznatim greškama
- `tests/fixtures/ground_truth_don.pdf` - primjer DON-a
- `tests/fixtures/expected_results.json` - što sustav mora pronaći

### 3. Domain knowledge dokumenti

- `docs/01-domain-knowledge/tier-1-violations.md` - 6 Tier 1 prekršaja DETALJNO
- `docs/01-domain-knowledge/dkom-decision-structure.md` - kako parsirati DKOM
- `docs/01-domain-knowledge/legal-sources-inventory.md` - pregled izvora

### 4. Prompt templates (početni nacrti)

- `docs/04-prompts/master-prompt.md` - osnovni prompt
- `docs/04-prompts/tier-1-1-prompt.md` - za brendove
- `docs/04-prompts/tier-1-2-prompt.md` - za specifikacije
- ...itd za sve 6 Tier-a

### 5. Design assets

- Logo (Lexitor)
- Brand colors
- Mockup-i ključnih ekrana (DESIGN_BRIEF.md daje smjer)

### 6. API ključevi (sigurno čuvani)

- Anthropic API key
- Cohere API key
- Azure subscription detalji (ako trebaš)

---

## 🤔 Što ti treba odlučiti

Ne sve je odlučeno - neke tehničke odluke su **na tebi**:

### Tehničke odluke koje donosi developer

1. **Konkretna struktura prompts-a** - PM daje smjernice, ti dovršavaš
2. **Chunking strategija** - eksperimentiraj sa različitim veličinama
3. **Cache strategija** - što cache-irati, kako dugo
4. **Error handling pristup** - retry policy, fallback mehanizmi
5. **Logging granularnost** - što logirati, kako strukturirati
6. **Database schema detalji** - PM definira high-level, ti detalje
7. **API endpoint dizajn** - REST conventions, naming
8. **Test pristup** - što testirati prvo, što kasnije

### Što PM odlučuje (NE diraj)

- Definicija prekršaja (Tier 1.1 - 1.6)
- Format izlaza prema korisniku
- UX/UI tijek
- Pricing
- Pravna terminologija
- Tekst disclaimer-a

### Kad postane jasno da treba odluka

**Pitanje:** "Hej, treba mi odluka o X" → PM ti odgovori unutar 24h.
**Ako PM nije siguran:** otvorimo to u DECISIONS.md kao Q-XXX i raspravimo.

---

## 💬 Komunikacija s timom

### Sa PM-om

- **Daily sync** (15 min, ujutro): što danas, blokade
- **Weekly review** (60 min, petkom): što gotovo, što slijedi, riziki
- **Slack/Teams**: poruke u toku dana po potrebi
- **Demo dani**: kraj svake faze - prezentiraj rezultate

### Sa pravnikom (po potrebi)

- Kad imaš pitanje oko domain knowledge
- PM organizira sastanak (1-2x mjesečno)
- Najbolje pripremiti specifična pitanja unaprijed

### Sa Claude Code AI

- **Pair programming** stalno - ti si "pilot", Claude je "copilot"
- Čitaj sve `.md` dokumente u repo-u prije rada
- Koristi Claude za: brainstorming, code review, debugging, docs
- Nemoj koristiti Claude za: pravne odluke, business decisions

### Eskalacija problema

```
Problem male složenosti → riješiš sam ili pitaš Claude Code
Problem srednje složenosti → Slack PM-u
Problem velike složenosti / blokade → odmah call PM
Pravno pitanje → flag PM-u, on organizira pravnika
Tehnička odluka koju ne želiš sam donijeti → DECISIONS.md
```

---

## 🚦 Crvene zastavice (kad treba alarm)

Pošalji PM-u **odmah** ako:

- ⚠️ Anthropic API je preskup (potrošnja > 100 EUR/dan u dev-u)
- ⚠️ Sustav generira jasno pogrešne pravne savjete
- ⚠️ Halucinacije citate koji ne postoje u pravnoj bazi
- ⚠️ Performance je ispod target-a (analiza > 60s)
- ⚠️ GDPR ili security risk
- ⚠️ Bilo što što "ne sjeda" iz etičke perspektive

---

## 🎓 Kako učiti dok radiš

Lexitor traži znanje iz **tri područja**:

### 1. Python + AI (vjerojatno već znaš)

Resursi:
- LangChain dokumentacija (https://python.langchain.com/docs/)
- Anthropic API docs (https://docs.anthropic.com)
- FastAPI tutorials

### 2. RAG specifika

Resursi:
- "Retrieval-Augmented Generation" by Lewis et al. (paper)
- LangChain RAG tutorials
- Anthropic Cookbook

### 3. Domain knowledge (NOVO)

Najmanje vremena potrošiti, ali važno za razumijevanje:
- Pročitati `docs/01-domain-knowledge/public-procurement-basics.md`
- Pregledati 5-10 DKOM odluka
- Pričati s pravnikom (1-2 sata) o ključnim konceptima

---

## 📚 Reference

### Glavni dokumenti

- [README.md](./README.md) - glavni overview projekta
- [PROJECT.md](./PROJECT.md) - poslovna vizija (zašto radimo ovo)
- [ARCHITECTURE.md](./ARCHITECTURE.md) - **tehnička arhitektura (čitaj pažljivo!)**
- [PHASES.md](./PHASES.md) - fazni plan (gdje smo, što slijedi)
- [DECISIONS.md](./DECISIONS.md) - sve odluke (zašto smo odlučili nešto)

### Detaljna dokumentacija (u `docs/`)

- `docs/01-domain-knowledge/` - pravna domena
- `docs/02-data-models/` - JSON sheme
- `docs/03-api/` - API ugovori
- `docs/04-prompts/` - LLM prompts
- `docs/05-deployment/` - Azure i CI/CD

### Eksterni resursi

- [LangChain](https://python.langchain.com)
- [Anthropic API](https://docs.anthropic.com)
- [Cohere API](https://docs.cohere.com)
- [Qdrant](https://qdrant.tech/documentation/)
- [FastAPI](https://fastapi.tiangolo.com)

### Tools

- VS Code + Claude Code (osnovni IDE)
- Postman / Bruno (API testing)
- DBeaver / pgAdmin (DB GUI)
- Qdrant Cloud Web UI

---

## 🎯 Kriteriji uspjeha tvog rada

Kako ćeš znati da si dobro radio:

### Tehnički

- ✅ PoC prolazi sve kriterije iz [PHASES.md](./PHASES.md)
- ✅ Code review pozitivan
- ✅ Test coverage ≥ 70%
- ✅ Performance unutar target-a
- ✅ Deployment radi (lokalni + staging)

### Procesno

- ✅ PM zadovoljan ritmom napretka
- ✅ Komunikacija jasna i pravovremena
- ✅ Dokumentacija ažurna
- ✅ Nema "skrivenih" tehničkih dugovanja

### Profesionalno

- ✅ Naučio si nešto novo (RAG, LLM, domain knowledge)
- ✅ Doprinio si arhitektonskim odlukama
- ✅ Postao si ekspert u domeni

---

## 💡 Zadnji savjeti

1. **Domain knowledge je važniji od tehnologije** - razumi pravnu domenu ranije
2. **AI promiscuity** - eksperimentiraj sa promptima, mali zaokreti = velike razlike
3. **Strukturirani output** - JSON schema za sve, ne free text
4. **Cache aggressively** - LLM pozivi su skupi
5. **Validate everything** - ne vjeruj LLM-u na riječ
6. **Pravnik je tvoj prijatelj** - on zna ono što ti nikad nećeš znati
7. **Pitaj rano, pitaj često** - bolje sat razgovora nego tjedan krivog smjera

---

## 🚀 Sretno!

Lexitor je ozbiljan projekt sa potencijalom da postane **ozbiljan proizvod** za europsko tržište. Ti si dio tog putovanja.

**Welcome to the team!** 🎉

---

*Verzija: 1.0 | Svibanj 2026 | Lexitor by Arhigon*
*Ovaj dokument je živ - mijenja se kako projekt napreduje*
