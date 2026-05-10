# Lexitor SaaS — arhitekturni plan

**Status:** plan dokument, čeka odobrenje prije implementacije.
**Datum:** 2026-05-11

## Cilj

Pretvoriti single-user PoC u multi-tenant SaaS:
- Tvrtke (Companies) s **više korisnika** unutar svake
- **À la carte** moduli — svaka tvrtka bira što plaća
- **Free trial** — 1 DON analiza / mjesec za nove tvrtke
- **Hibrid billing** — manual za Enterprise, Stripe za SMB
- **Admin panel** za super-administratora (Marko vidi i upravlja svim)

## Glavni entiteti (data model)

```
Company (tvrtka, "tenant")
├── id, name, oib, address, billing_email
├── stripe_customer_id (null za manual billing)
├── trial_started_at, trial_expires_at
└── users (CompanyUser join)

CompanyUser (M:N user-company)
├── user_id, company_id
├── role (owner / admin / member / viewer)
└── invited_by, joined_at

User
├── id, email, password_hash, full_name
├── is_super_admin (Marko, globalna razina)
└── companies (CompanyUser join)
- DROP: project_id (legacy, migracija)

Module (enum-like, ali ide u DB radi proširenja)
├── code (don_analiza, troskovnik, zalbe, rag_search)
├── name, description
└── default_quota (npr. 100 analiza/mj)

Subscription (Company × Module)
├── company_id, module_id
├── tier (free_trial / starter / pro / enterprise)
├── period_start, period_end
├── status (active / expired / cancelled / paused)
├── source (stripe / manual / trial)
├── stripe_subscription_id (null za manual)
└── quota_override (null = use module default)

UsageRecord (mjesečni brojač)
├── company_id, module_id
├── period_ym (npr. "2026-05")
├── count (broj analiza)
└── llm_cost_eur (akumulirani trošak nas)
```

## Permission model

Tri razine pristupa:

1. **Super Admin** (`is_super_admin=true`, vjerojatno samo Marko)
   - Vidi sve companies, sve subscriptions, sve usage
   - Može kreirati/mijenjati svaku subscription manualno
   - Pristup `/admin` panelu

2. **Company Owner / Admin** (per-company)
   - Owner: full pristup company-jevoj postavkama, billing, members
   - Admin: kao owner ali ne može brisati company
   - Pristup `/settings/company`

3. **Company Member / Viewer**
   - Member: koristi sve dostupne module (po company subscription-ima)
   - Viewer: read-only (vidi analize ali ne kreira)

## Subscription / modul logika

**Per-endpoint middleware** koji deklarira potrebni modul:

```python
@router.post("/documents/{id}/analyze")
@requires_module("don_analiza")  # decorator
async def analyze(...): ...
```

Middleware:
1. Tko je trenutni user? (iz JWT)
2. Koja je trenutno aktivna company? (header `X-Company-Id`)
3. Ima li ta company aktivnu subscription za `don_analiza`?
4. Ako da → check quota (UsageRecord za period_ym)
5. Ako quota OK → propusti zahtjev, inc. usage at end
6. Ako quota istekla → 429 s porukom "Pretplata istekla / kvota dosegnuta"

**Free trial logika:**
- Nova company automatski dobije Subscription s tier=free_trial,
  module=don_analiza, period 30 dana, quota=1
- Po isteku, status → expired, user vidi "Upgrade" CTA

## Frontend struktura

```
/                          → marketing/landing (kasnije)
/login, /register          → auth
/dashboard                 → home: što imam pretplaceno, last analizes
/analiza/don/*             → DON modul (requires don_analiza subscription)
/analiza/troskovnik/*      → Troskovnik (requires troskovnik subscription)
/analiza/zalbe/*           → Zalbe (requires zalbe subscription)
/settings/company          → company admin: members, billing, subscriptions
/settings/profile          → user profile
/admin                     → SUPER ADMIN ONLY: sve companies, subscriptions, usage
```

## Faze implementacije

### Phase 1 — Data model + migracija (~4-6h)
- [ ] Definirati nove modele (Company, CompanyUser, Module, Subscription, UsageRecord)
- [ ] Alembic migracija: kreirati tablice, seed Module entries
- [ ] Migrirati postojeće Project → Company (slug → oib, name → name)
- [ ] User: dodati is_super_admin, drop project_id, migrirati postojeće veze
- [ ] Pydantic schemas za sve nove entitete

### Phase 2 — Auth & permission middleware (~4-6h)
- [ ] JWT extension: claim `active_company_id` (može se mijenjati kroz header)
- [ ] `@requires_module(code)` decorator
- [ ] Endpoint `/auth/companies` (lista companies trenutnog usera)
- [ ] Endpoint `/auth/switch-company` (mijenja active company u session)
- [ ] Endpoint `/auth/me` proširen s active company + subscriptions

### Phase 3 — Company admin UI (~6-8h)
- [ ] `/settings/company` page (members lista + invite)
- [ ] Invitation flow (email link, accept page)
- [ ] Subscriptions tab (vidi što ima, expiration dates)
- [ ] Member CRUD (add/remove/role change)

### Phase 4 — Super Admin UI (~8h)
- [ ] `/admin` route + `is_super_admin` guard
- [ ] Lista svih companies + filters (active/expired)
- [ ] Per-company detail: subscriptions, usage, members
- [ ] Create/edit subscription manually (for Enterprise)
- [ ] Global dashboard: total MRR, top users, churn

### Phase 5 — Stripe integration (~6-8h)
- [ ] Stripe products & prices (1 product per modul × 3 tiers)
- [ ] Webhook handler za customer.subscription.*
- [ ] Checkout flow iz `/settings/company` ("Upgrade" gumb)
- [ ] Manual subscription override (Super Admin može isključiti Stripe za pojedinu company)

### Phase 6 — Free trial + onboarding (~3-4h)
- [ ] Nova registracija → kreira Company + auto-free-trial Subscription
- [ ] Welcome flow: "Imaš 30 dana besplatne DON analize, evo kako…"
- [ ] Trial expiration email + in-app CTA

**Ukupno: ~30-40h razvoja = 5-7 radnih dana**

## Što NE radimo u prvoj iteraciji

- Email obavijesti (samo logiranje u backend; UI feedback kasnije)
- Multi-currency (EUR samo)
- Tax/VAT logika (može se dodati u Stripe products)
- Audit log (ko što napravio kad) — kasnije, kroz append-only events tablicu
- 2FA (kasnije)
- API tokens / programmatic access — kasnije, kad bude potreba

## Otvorena pitanja za potvrdu

1. **Naziv "Company"** odgovara ili koristimo "Organization" / "Tenant"?
2. **Slug umjesto OIB** — OIB je primarni identifikator za hrvatske tvrtke,
   ali za međunarodne korisnike?
3. **Trial duration**: 30 dana / 1 DON analiza — slažeš se s tim?
4. **Tier-ovi** unutar svakog modula:
   - Starter (X analiza / mj, low price)
   - Pro (Y analiza / mj, mid price)
   - Enterprise (unlimited / custom, high price + manual billing)
   Slažeš se s 3 tier-a po modulu?
5. **Cijene** — imaš li okvire koliko želiš naplaćivati? Trebam to za Stripe
   konfiguraciju (može i kasnije, ali korisno da znam za UI mockup-e).
