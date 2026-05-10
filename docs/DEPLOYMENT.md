# Lexitor — Production Deployment (Azure)

Vodič za prebacivanje Lexitor-a iz dev (lokalno) u produkciju (Azure + Vercel
+ domain). Pretpostavlja: već imaš Azure subscription i kreditnu karticu.

**Procijenjeno vrijeme:** 1-2 dana rada + nekoliko sati DNS propagacije.
**Procijenjena mjesečna cijena:** ~80-150 € (uskaljena ovisno o korištenju).

---

## Architecture overview

```
┌─────────────────────────────────────────────────────────────────┐
│  KORISNIK                                                       │
│  ├── https://lexitor.eu       → Marketing (apps/web)            │
│  ├── https://app.lexitor.eu   → Proizvod (apps/app)             │
│  └── https://api.lexitor.eu   → Backend API                     │
└─────────────────────────────────────────────────────────────────┘
              │                                       │
              ▼                                       ▼
   ┌────────────────────┐               ┌──────────────────────────┐
   │  VERCEL            │               │  AZURE                   │
   │  ├── apps/web      │  HTTP API     │  ├── Container Apps      │
   │  └── apps/app      │ ─────────────▶│  │   └── lexitor-api     │
   │                    │               │  ├── PostgreSQL Flexible │
   │  CDN, edge, auto   │               │  ├── Cache for Redis     │
   │  SSL, preview env. │               │  ├── Qdrant (self-host)  │
   └────────────────────┘               │  └── Blob Storage        │
                                        │      (uploaded docs)     │
                                        └──────────────────────────┘
```

**Zašto ova podjela:**
- **Vercel za frontend** — besplatan tier dovoljan za ~100k posjeta/mj,
  edge CDN, auto SSL, preview deploy-i za svaki PR. Manja briga, viša brzina.
- **Azure za backend i podatke** — kontrola, EU region (Frankfurt = niska
  latencija za HR korisnike), jedna invoice s Arhigon-om.

---

## 1. Domena — postavka

### 1.1 Kupnja domene

**Preporuka: Cloudflare Registrar** (cijena na trošak + 0%, najjeftinije + DNS najbolji).

Alternative:
- Namecheap (~10 €/god, simpler UI)
- GoDaddy (NE preporučujem, skup)
- Plata.hr (HR registrar za .hr domene)

Kupi:
- `lexitor.eu` (primarna, EU oznaka)
- `lexitor.hr` (opcionalno, zaštita brand-a)

### 1.2 DNS preko Cloudflare (besplatan)

Bez obzira gdje si kupio domenu, **prebaci DNS na Cloudflare**:
1. Registriraj besplatan Cloudflare račun
2. "Add site" → `lexitor.eu`
3. Cloudflare scaniraj postojeće DNS recorde (ako ih ima)
4. Cloudflare ti da 2 nameservera (npr. `harper.ns.cloudflare.com`)
5. U registrar UI-u, zamijeni default nameservere s Cloudflare-ovima
6. Propagacija: 1-24h

### 1.3 DNS recordi koje treba dodati

Nakon što Cloudflare aktivan:

```
TYPE   NAME    VALUE                              PROXY
─────  ──────  ──────────────────────────────────  ─────
A      @       <Vercel IP — saznaj iz Vercel>     ON
CNAME  www     cname.vercel-dns.com               ON
CNAME  app     cname.vercel-dns.com               ON
CNAME  api     lexitor-api.<azure-region>.azurecontainerapps.io  ON
TXT    @       v=spf1 include:_spf.resend.com -all  OFF   ← za email
MX     @       feedback-smtp.eu-west-1.amazonses.com  10   ← inbound
```

Email rekorde popunit ćemo kasnije kad podesi Resend (1 sat rada).

---

## 2. Azure setup

### 2.1 Resurcna grupa

```
Group: lexitor-prod
Region: West Europe (Amsterdam) ili North Europe (Dublin)
```

EU regije su obavezne radi GDPR-a + niska latencija za HR.

### 2.2 Azure Container Registry (ACR)

Mjesto gdje pohranjuješ Docker image-e za backend:

```bash
az group create --name lexitor-prod --location westeurope
az acr create \
  --resource-group lexitor-prod \
  --name lexitoracr \
  --sku Basic \
  --admin-enabled true
```

Cijena: ~5 €/mj.

### 2.3 PostgreSQL — Azure Database for PostgreSQL Flexible Server

```
Tier: Burstable (B1ms) — 1 vCPU, 2 GB RAM
Storage: 32 GB SSD
PostgreSQL version: 16
Backup retention: 7 days
HA: disabled (uključit ako će se rasti)
```

Cijena: ~25 €/mj.

```bash
az postgres flexible-server create \
  --resource-group lexitor-prod \
  --name lexitor-pg \
  --location westeurope \
  --tier Burstable \
  --sku-name Standard_B1ms \
  --version 16 \
  --storage-size 32 \
  --admin-user lexitor \
  --admin-password <strong-password>
```

Public access samo s Azure resursa (firewall rule):

```bash
az postgres flexible-server firewall-rule create \
  --resource-group lexitor-prod \
  --name lexitor-pg \
  --rule-name allow-azure \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

### 2.4 Azure Cache for Redis

Za session store, SSE pub-sub, mali cache:

```
Tier: Basic C0 — 250 MB
```

Cijena: ~15 €/mj.

```bash
az redis create \
  --resource-group lexitor-prod \
  --name lexitor-redis \
  --location westeurope \
  --sku Basic \
  --vm-size C0
```

### 2.5 Qdrant — self-host na Container Apps

Qdrant Cloud je skuplji (~50€/mj), self-host na Container App je cca 15-20€/mj.

```bash
az containerapp env create \
  --name lexitor-env \
  --resource-group lexitor-prod \
  --location westeurope

az containerapp create \
  --name lexitor-qdrant \
  --resource-group lexitor-prod \
  --environment lexitor-env \
  --image qdrant/qdrant:latest \
  --target-port 6333 \
  --ingress internal \
  --min-replicas 1 \
  --max-replicas 1 \
  --cpu 0.5 \
  --memory 1Gi
```

**Persistencija:** Qdrant skladišti embeddings na disku. Za true persistencija
mountati Azure Files (ili kasnije migrirati na Qdrant Cloud).

### 2.6 Backend API — Container Apps

Sam Lexitor backend (FastAPI):

```bash
# Build i push image
docker build -t lexitor-api -f apps/backend/Dockerfile apps/backend
az acr login --name lexitoracr
docker tag lexitor-api lexitoracr.azurecr.io/lexitor-api:latest
docker push lexitoracr.azurecr.io/lexitor-api:latest

# Deploy
az containerapp create \
  --name lexitor-api \
  --resource-group lexitor-prod \
  --environment lexitor-env \
  --image lexitoracr.azurecr.io/lexitor-api:latest \
  --target-port 8000 \
  --ingress external \
  --registry-server lexitoracr.azurecr.io \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 0.5 \
  --memory 1Gi \
  --env-vars \
      DATABASE_URL="postgresql+psycopg://lexitor:<pwd>@lexitor-pg.postgres.database.azure.com:5432/lexitor" \
      REDIS_URL="redis://lexitor-redis.redis.cache.windows.net:6380?ssl=True" \
      QDRANT_URL="http://lexitor-qdrant" \
      ANTHROPIC_API_KEY="<key>" \
      COHERE_API_KEY="<key>" \
      JWT_SECRET="<random-256-bit>" \
      CORS_ORIGINS="https://lexitor.eu,https://app.lexitor.eu"
```

Cijena: ~20 €/mj base, skalira do ~50 €/mj na peak.

**Custom domain za API:**

```bash
az containerapp hostname add \
  --name lexitor-api \
  --resource-group lexitor-prod \
  --hostname api.lexitor.eu

az containerapp hostname bind \
  --name lexitor-api \
  --resource-group lexitor-prod \
  --hostname api.lexitor.eu \
  --environment lexitor-env
```

Onda u Cloudflare DNS: `api` CNAME na Container App URL.

### 2.7 Blob Storage — za uploaded dokumente

```bash
az storage account create \
  --name lexitorblob \
  --resource-group lexitor-prod \
  --location westeurope \
  --sku Standard_LRS \
  --kind StorageV2

az storage container create \
  --account-name lexitorblob \
  --name documents \
  --auth-mode login
```

Cijena: ~1 €/mj za prvih 100 GB.

**Migracija s lokalnog storage-a:**
- Trenutno backend sprema u `uploads/` lokalno
- Treba update `src/services/document_service.py` da koristi Azure Blob SDK
- 2-3 sata rada

---

## 3. Vercel deployment (Frontend)

### 3.1 Konekt repo na Vercel

1. Idi na vercel.com → New Project → Import Git Repository
2. Odaberi `basicmsb/Lexitor`
3. **Dva projekta** — jedan po Next.js app:

**Projekt 1: `lexitor-web`** (marketing)
- Root directory: `apps/web`
- Framework: Next.js (auto-detect)
- Environment variables:
  ```
  NEXT_PUBLIC_APP_URL=https://app.lexitor.eu
  ```

**Projekt 2: `lexitor-app`** (proizvod)
- Root directory: `apps/app`
- Framework: Next.js
- Environment variables:
  ```
  NEXT_PUBLIC_API_URL=https://api.lexitor.eu
  ```

### 3.2 Custom domene

U Vercel UI:
- `lexitor-web` → "Domains" → dodaj `lexitor.eu` i `www.lexitor.eu`
- `lexitor-app` → "Domains" → dodaj `app.lexitor.eu`

Vercel će ti dati CNAME/A vrijednosti — ti ih dodaj u Cloudflare DNS.

### 3.3 Auto-deploy

Vercel auto-build na svaki `git push` na `main`. Preview deploys za PR-ove.

Cijena: **0 €/mj** (Hobby plan dovoljan dok ne predeš 100GB bandwidth-a).

---

## 4. CI/CD pipeline

### 4.1 GitHub Actions za backend deploy

Stvori `.github/workflows/deploy-backend.yml`:

```yaml
name: Deploy Backend

on:
  push:
    branches: [main]
    paths:
      - 'apps/backend/**'
      - '.github/workflows/deploy-backend.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Azure Login
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      - name: Build & push Docker
        run: |
          az acr login --name lexitoracr
          docker build -t lexitoracr.azurecr.io/lexitor-api:${{ github.sha }} -f apps/backend/Dockerfile apps/backend
          docker tag lexitoracr.azurecr.io/lexitor-api:${{ github.sha }} lexitoracr.azurecr.io/lexitor-api:latest
          docker push lexitoracr.azurecr.io/lexitor-api:${{ github.sha }}
          docker push lexitoracr.azurecr.io/lexitor-api:latest
      - name: Deploy to Container Apps
        run: |
          az containerapp update \
            --name lexitor-api \
            --resource-group lexitor-prod \
            --image lexitoracr.azurecr.io/lexitor-api:${{ github.sha }}
      - name: Run migrations
        run: |
          az containerapp exec \
            --name lexitor-api \
            --resource-group lexitor-prod \
            --command "alembic upgrade head"
```

GitHub Secrets potrebni:
- `AZURE_CREDENTIALS` — service principal JSON
  ```bash
  az ad sp create-for-rbac --name lexitor-github \
    --role contributor \
    --scopes /subscriptions/<SUB-ID>/resourceGroups/lexitor-prod \
    --json-auth
  ```

Frontend deploy radi Vercel automatski.

---

## 5. Sigurnost & GDPR

### 5.1 Secrets management

NIKAD ne commit-aj secrets u git. Koristi:
- Azure Key Vault za backend secrets (DB password, JWT secret, API keys)
- Vercel Environment Variables za frontend
- GitHub Secrets za CI/CD

### 5.2 GDPR checklist

- ✅ EU region za sve podatke (West/North Europe)
- ☐ DPA s Anthropic-om (oni imaju standard DPA, signatorni proces ~15 min)
- ☐ DPA s Cohere-om
- ☐ Cookie banner (samo functional cookies = 0 banner-a po EU regulativi)
- ☐ Privatnost policy reviewed by lawyer
- ☐ Data export functionality (user može preuzeti svoje podatke)
- ☐ Data deletion (right to be forgotten — soft delete + 30 dana grace period)

### 5.3 Backup strategija

- **Postgres:** Azure auto-backup (7 dana retention u Burstable tier)
- **Blob Storage:** geo-replikacija na Standard_GRS (dvostruka cijena ali bullet-proof)
- **Qdrant:** snapshot na Blob Storage svakih 6h (cron job)

---

## 6. Monitoring & alerting

### 6.1 Azure Monitor (Application Insights)

Besplatan tier — 5GB logs/mj.

```bash
az monitor app-insights component create \
  --app lexitor-insights \
  --location westeurope \
  --resource-group lexitor-prod
```

Backend update u `src/api/main.py`:
```python
from azure.monitor.opentelemetry import configure_azure_monitor
configure_azure_monitor(connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"))
```

### 6.2 Alerts

Postaviti alerts za:
- API 5xx error rate > 1% u 5min
- Postgres CPU > 80% u 10min
- Qdrant container restart
- LLM API quota approaching

### 6.3 Uptime monitoring

Vanjski monitor (besplatan):
- UptimeRobot (https://uptimerobot.com) — 5 min check
- Postaviti za `https://api.lexitor.eu/health`

---

## 7. Email — Resend

Resend.com je modernizirani SMTP provider — najlakši za HR korisnike s
domain SPF/DKIM setup-om.

1. Registriraj račun, dodaj domenu `lexitor.eu`
2. Resend daje SPF + DKIM TXT recorde → dodaj u Cloudflare DNS
3. Verify domain (1 sat propagacija)
4. API key u backend env: `RESEND_API_KEY`
5. Backend implementacija: `pip install resend`

Cijena: **besplatan 3,000 emaila/mj**, dalje $1 per 1k.

---

## 8. Procjena cijene

| Stavka | Mjesečno |
|---|---|
| Azure Container Apps (API + Qdrant) | ~35 € |
| Azure Postgres Burstable | ~25 € |
| Azure Cache for Redis Basic C0 | ~15 € |
| Azure Container Registry | ~5 € |
| Azure Blob Storage (100GB) | ~2 € |
| Azure Application Insights (≤5GB) | 0 € |
| Vercel Hobby (web + app) | 0 € |
| Cloudflare DNS | 0 € |
| Domena `lexitor.eu` | ~1 € (12€/god) |
| Resend (≤3k email/mj) | 0 € |
| **UKUPNO baseline** | **~85 €/mj** |
| LLM trošak (Anthropic, korisničke analize) | varijabilno |
| Cohere embeddings (RAG queries) | ~5-10 € |

**Real total: 90-100 €/mj** za ~10-20 aktivnih korisnika.

Kad rasteš (100+ korisnika), Postgres preselit u Standard tier (~80 €/mj),
Container Apps skalira automatski. Total ~200-300 €/mj na 100 korisnika.

---

## 9. Deployment redoslijed (1-2 dana rada)

### Dan 1 (4-6h)

1. **Domena** — kupi `lexitor.eu`, Cloudflare DNS (1h)
2. **Azure setup** — resource group, ACR, Postgres, Redis (2h)
3. **Backend Dockerfile** — pisati ako nema (1h)
4. **First deploy backend** — manualan deploy, smoke test API (1-2h)

### Dan 2 (4-6h)

5. **Qdrant deploy** + index DKOM korpus iz backup-a (2h)
6. **Vercel frontend** — povezivanje, custom domains (1h)
7. **GitHub Actions** — CI/CD za backend (1-2h)
8. **End-to-end smoke** — registracija, upload, analiza, PDF export (1-2h)

### Dan 3 (polish, kasnije)

9. **Email setup** — Resend, transactional templates
10. **Monitoring** — Application Insights, UptimeRobot
11. **Backup automation** — Qdrant snapshot cron

---

## 10. Pre-launch checklist

Ne idi live dok nisu sve sljedeće provjereno:

- ☐ `.env.example` ažuriran — sve env vars dokumentirane
- ☐ Backend Dockerfile build success lokalno
- ☐ Postgres migracije rade na svježem DB-u (`alembic upgrade head` clean)
- ☐ Smoke test — register user, upload doc, analyze, view results
- ☐ HTTPS svuda (SSL cert active na sve 3 domene)
- ☐ CORS pravilno konfiguriran (samo lexitor.eu domene)
- ☐ Rate limiting na API (nginx ili fastapi-limiter — 100 req/min po IP-u)
- ☐ Cookie/session security (httpOnly, secure, sameSite=Lax)
- ☐ JWT secret rotated iz dev-a
- ☐ Anthropic + Cohere API keys različiti od dev-a
- ☐ DB backup test (restore from snapshot)
- ☐ Privatnost & Uvjeti — pravnik signoff
- ☐ Status page (status.lexitor.eu — UptimeRobot ima besplatan)

---

## Quick reference — komande

```bash
# Logs iz Container Apps
az containerapp logs show --name lexitor-api -g lexitor-prod --follow

# Shell u Container App
az containerapp exec --name lexitor-api -g lexitor-prod

# Restart
az containerapp revision restart --name lexitor-api -g lexitor-prod

# Skaliranje
az containerapp update --name lexitor-api -g lexitor-prod \
  --min-replicas 2 --max-replicas 5

# Postgres backup restore (point-in-time)
az postgres flexible-server restore \
  --resource-group lexitor-prod \
  --name lexitor-pg-restored \
  --source-server lexitor-pg \
  --restore-time "2026-05-11T10:00:00Z"
```
