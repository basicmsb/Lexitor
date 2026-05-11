# Lexitor — Community Reviewer Program

**Status:** plan dokument (čeka launch-fazu za implementaciju)
**Datum:** 2026-05-11
**Inicijator:** Marko Bašić — ideja za rješavanje bias-a u DKOM dataset spot-check-u

## Cilj

Crowdsource feedback nabavnih stručnjaka o kvaliteti LLM kategorizacije
DKOM claims-ova, **kao i** o ispravnosti generiranih DON nalaza. Korisnici
dobivaju produženu pretplatu kao nagradu.

**Primarni problem:** single-person bias. Jedna osoba ne može precizno
klasificirati 2275 pravnih argumenata kroz 12 kategorija — ni vlasnik,
ni jedna pravnica.

**Sekundarni cilj:** kontinuirana validacija kako Lexitor evolvira. Novi
DKOM odluke (scrape svaki tjedan), novi DON rule-ovi — sve treba reviewer
feedback.

## Vrijednosna ravnoteža

| Strana | Ulaže | Dobija |
|---|---|---|
| **Korisnik** | ~30 min × 200 reviews = 100 sati godišnje | 2 mjeseca produžene pretplate (~60€ vrijednost) |
| **Lexitor** | ~60€ trial cost × 50 reviewers = 3000€/god | 10,000+ expert-validated labels, immune to single-person bias |

**ROI za Lexitor: ~10×** (expert labeling u industriji košta 1-3€ po label).

## Što reviewer radi

### Tipovi review-a

1. **DKOM claim categorization** (početni use case)
   - LLM rekao "neprecizna_specifikacija", reviewer kaže točno/krivo
   - Ako krivo, biraš pravu kategoriju iz 12
   - Tipično 30 sec po claim-u

2. **DON finding validation** (future)
   - Lexitor je flagao stavku kao brand_lock — je li to stvarno povreda?
   - Y/N/Nesigurno + razlog
   - Tipično 1 min po finding-u (zahtjevnije)

3. **Anti-pattern annotation** (future)
   - "Ovaj argument bi DKOM odbio jer X" — reviewer dodaje strukturirano objašnjenje
   - Najvjerojatnije advanced reviewers (Trust Level 3+)

## Reward struktura

### Nivoi
- **Bronze (50 reviews)**: 1 mjesec produžene pretplate
- **Silver (150 reviews)**: 2 mjeseca produžene pretplate
- **Gold (300 reviews)**: 4 mjeseca + "Community Validator" badge na profilu
- **Platinum (500+ reviews)**: 6 mjeseci + 20% trajni popust + invite na Lexitor Advisory Board

### Decay (anti-spam)
- Prvih 200 reviewa: 1 review = 1 punkt
- 200-400: 1 review = 0.7 punkta
- 400+: 1 review = 0.5 punkta

Time se nagrada veže s vrijednošću, ne s brojem klikova.

## Quality control — anti-spam i bias

### 1. Calibration claims (golden answers)
- 10% random claim-ova ima "golden label" (set od ~50 koje smo ručno (super-admin) označili)
- Reviewer ne zna koji su calibration
- Threshold: **80% accuracy na calibration** za uračunavanje review-a
- Ispod 80% → tagged "needs review", lokal feedback ne primjenjuje se u dataset
- Reviewer dobiva email "vaše review-i trebaju dodatno pažljiv pristup"

### 2. Multi-reviewer consensus
- Svaki claim mora imati **3 reviewa** prije primjene
- Consensus: 2+ slažu se → primjenjuje se
- Disagreement: 3 različita odgovora → eskalira u "expert queue" za super-admin

### 3. Reputation / Trust Levels

| Level | Cri | Privileges |
|---|---|---|
| **L1 New** | <50 reviews ili <80% calibration | Feedback se akumulira, ali ne primjenjuje (samo brojimo) |
| **L2 Trusted** | 50+ reviews + 85%+ calibration | Feedback primjenjuje se u consensus |
| **L3 Expert** | 200+ reviews + 90%+ calibration | Vidi "expert queue" disagreement cases |
| **L4 Validator** | Advisory Board invite | Vidi sve, može over-ride consensus |

### 4. Anti-bot mehanizmi
- **Min vrijeme** po review-u: 8 sekundi (mjeri se backend-om)
- **Anomaly detection** — npr. ako reviewer 100% klika `Y` u svih 50 reviewa → flagged
- **CAPTCHA** na registraciji + email verification
- **One account per OIB** (pravna osoba)

### 5. Audit log
- Sav feedback append-only u DB s timestamp, user_id, time-on-task
- Super-admin može audit-irati pojedinačnog reviewera

## Tehnički dizajn

### Backend modeli (proširenja postojećeg)

```python
class ReviewerProfile(Base):
    user_id: UUID  # FK to User
    trust_level: Enum["L1_new", "L2_trusted", "L3_expert", "L4_validator"]
    total_reviews: int
    calibration_score: float  # 0-1
    consensus_agreement_rate: float  # 0-1
    earned_months: int  # akumulirano za reward
    redeemed_months: int  # already applied to subscription
    created_at, updated_at

class CalibrationClaim(Base):
    claim_id: str  # FK to dkom claim
    golden_label: ClaimType  # super-admin-set
    note: str  # zašto je ova odgovor točan
    set_by_user_id: UUID

class ReviewRecord(Base):
    id: UUID
    claim_id: str
    reviewer_user_id: UUID
    verdict: Literal["correct", "wrong", "uncertain", "skip"]
    correct_category: ClaimType | None
    time_on_task_seconds: int
    is_calibration: bool
    matches_golden: bool | None  # samo ako is_calibration=True
    matches_consensus: bool | None  # populated kad consensus achieved
    created_at

class ClaimConsensus(Base):
    """Računan svaki put kad claim dobije 3rd review."""
    claim_id: str
    consensus_category: ClaimType | None  # None ako nije postignut
    reviews_count: int
    confidence: float  # 0-1
    last_calculated: timestamp
```

### Endpoints

```
GET  /reviewer/dashboard         → moji statsi, trust level, earned months
GET  /reviewer/next-claim         → vrati sljedeći claim (preferira calibration + needed-reviews)
POST /reviewer/submit             → submit review s time_on_task
GET  /reviewer/leaderboard        → public top 10 (anonimizirano)
POST /reviewer/redeem             → konvertira earned_months u subscription extension
GET  /admin/calibration/claims    → super-admin: lista calibration claim-ova
POST /admin/calibration/set       → super-admin označava claim kao calibration s golden label
GET  /admin/consensus/queue       → super-admin: disagreement cases (escalations)
```

### Frontend

- `/reviewer` — landing page s call-to-action (gamification: progress bar do 50/150/300)
- `/reviewer/review` — actual review UI (proširenje postojećeg /admin/dkom-spotcheck)
- `/reviewer/leaderboard` — top 10 reviewera (anonimizirano, ali ima badges)
- `/reviewer/profile` — moji statistici, trust level

### Gamifikacija UX
- **Streak counter** ("3 dana zaredom!") 
- **Progress bar** prema sljedećem milestone-u
- **Badge sistem** (Bronze/Silver/Gold/Platinum)
- **Lakomotive zvuk** kad klikneš (opcionalno, dopamine hit)
- **Daily challenge** ("Pregledaj 10 claim-ova danas za bonus +1 punkt")

## Faze implementacije

### Faza 0 — sad (predradnja)
- ✅ Dokumentacija (ovaj fajl)
- ✅ Spot-check UI postoji (`/admin/dkom-spotcheck`)
- ✅ Feedback storage (`spotcheck_feedback.jsonl`)

### Faza 1 — MVP nakon launch-a (~3 dana rada)
- ReviewerProfile model + migracija
- CalibrationClaim setup — super-admin označi 50 golden claims
- Modifikacija postojećeg spot-check UI-a:
  - Time-on-task tracking
  - Trust level display
  - Progress to next milestone
- `/reviewer` landing s opt-in
- Reward redemption automatizacija

### Faza 2 — full system (~1 tjedan rada)
- Multi-reviewer consensus mechanism
- Leaderboard + badges
- Advanced anti-spam (anomaly detection)
- Expert queue za disagreement cases

### Faza 3 — proširenje na DON findings (~1 tjedan rada)
- Reviewer može pregledati Lexitor-ove DON nalaze
- "Ovaj brand_lock flag je točan / pogrešan / nesiguran"
- Calibration extending na DON nalaze

## Marketinška priča

> *"Lexitor analiza temelji se na dataset-u validiran od 100+ nabavnih
> stručnjaka diljem Hrvatske. Svaki nalaz koji vidite prošao je
> trostruku provjeru — algoritam, pravnu odluku DKOM-a, i ručnu
> validaciju community-ja stručnjaka."*

Ovo je tvrdnja koju **konkurencija ne može imitirati** bez godina rada
i baze korisnika. **Strukturna prednost.**

## Otvorena pitanja (riješiti prije implementacije)

1. **Tko može biti reviewer?** Samo pravnici? Samo postojeći Lexitor korisnici? Otvoreno svima?
2. **Da li reviewer mora biti registriran u tvrtku?** OIB validacija?
3. **Kako rješavati sukob interesa?** Reviewer ne smije reviewirati svoje predmete.
4. **Cap na earned months?** Max 12 mjeseci besplatno godišnje?
5. **Da li dijelimo dataset s reviewer-ima?** "Vidi sve odluke koje si revieware-ao u jednom kliku" feature?

## Pravne stvari (riješiti s pravnikom)

- **EULA za Reviewer program** — odricanje od odgovornosti za Lexitor output
- **Anonymisation** — reviewer feedback se objavljuje agregirano, nikad pojedinačno
- **Right to delete** — reviewer može tražiti brisanje svog feedback-a (GDPR)
- **Conflict of interest disclosure** — pravnici koji su radili kao stranke u DKOM postupku treba flagati

---

**Bottom line:** Idea je excellent strategic move. Implementacija čeka launch
fazu. Ovaj dokument čuva sve detalje da kad budemo spremni, samo izvršavamo.
