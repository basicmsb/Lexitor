# Lexitor — sljedeći koraci

Konkretni TODO-ovi za DON modul i analiznu infrastrukturu. Sortirano po
prioritetu.

## P0 — čeka da current extraction završi (~5h)

- [ ] **DKOM 2025-2026 extraction** — running in background (~$30, 749 odluka)
- [ ] Pokrenuti `analyze_dkom.py` na full corpus-u → ground-truth statistike
- [ ] Pokrenuti `seed_dkom_rules.py` na full corpus-u → rule kandidati s primjerima

## P1 — implementacija pravila (na temelju seed-a)

Top kandidati prema seed analizi (29 odluka, indikativno):

1. `neprecizna_specifikacija` — 13 pojava, 68% uvazen rate, najčešće prema čl. 280, 290, 205
2. `ocjena_ponude` — high freq u DKOM-u, ALI izvan dosega DON checker-a (post-DON)
3. `espd_dokazi` — srednji rate
4. `kratki_rok` — deterministički, easy first win
5. `trosak_postupka` — irrelevantno za DON (samo žalbe modul)

Za svako pravilo:
- Implementirati funkciju u [`apps/backend/src/core/analyzer/don_rules.py`](src/core/analyzer/don_rules.py)
  s `@don_rule(name, applies_to, description)` dekoratorom
- Pisati 4-6 unit testova u `tests/unit/test_don_rule_<name>.py`
- Citation enrichment: pravilo vraća DKOM klase iz seed-a kao `citations`,
  pa `_enrich_findings_with_citations` ih zamijeni Qdrant retrieval rezultatima
- Manual test: učitati par DKOM-DON-ova i provjeriti je li rule pogodio
  očekivane povrede

## P2 — proširenje korpusa

- [ ] **DKOM 2024 backfill** — daje godinu duže za time-series:
  ```
  cd apps/backend
  python scripts/scrape_dkom.py --year 2024 --max 1000
  python scripts/extract_dkom.py --year 2024
  ```
  Procijenjen trošak: ~500 PDF-ova × $0.04 = $20 LLM. Vrijeme: ~3h.
  **Pričekati** dok current run ne završi (da ne miješamo).

- [ ] **VUS scraper** — vidi [`scrape_vus.py`](scripts/scrape_vus.py) docstring.
  Treba ručno otkriti URL pattern prije implementacije. Vrijednost srednja-visoka.

- [ ] **DKOM 2023 i ranije** — nakon 2024-a, ako želimo dublje time-series.
  Opcionalno za prvi PoC.

## P3 — žalbe modul (drugi prozor produkta)

Već imamo dataset koji to omogućuje:
- Per-claim verdict → "ako tvoj argument je tipa X, povijesno DKOM uvaži 47%"
- Per-member statistika → "tvoja žalba ide pred vijeće A+B+C, njihov rate je…"
- Citation network → "argumente ovog tipa najčešće potkrepljuje UsII-507/19"

Implementacija (zasebni Sprint):
- Backend: novi endpoint `/api/zalbe/analyze` koji prima argumente žalbe
  i vraća success probability + slične presedane
- Frontend: novi modul `/zalbe` paralelan s `/analiza/don`

## P4 — DON Faza 4 (LLM analyzer)

Sad imamo determinističku osnovu (brand_lock). Dalje:
- Top patterni iz seed-a koji NISU detectable regex-om → LLM judge
- Pipeline: parser → blokovi → deterministic rules → LLM za nepogodjene blokove
- Cost optimizacija: cache po block hash-u, model tiering (Haiku screen → Sonnet judge)

## Tehnički dug (manje urgentno)

- [ ] Dodati `rb` extraction iz docx Heading paragrafa (trenutno svi DON
  section headeri imaju `rb=null` kad dolazi iz .docx)
- [ ] UI: error_message u stream-u za historic load (sad to popravljeno u
  bootstrap, ali stream snapshot ne nosi error string)
- [ ] DKOM scraping mogao bi prepoznavati zatvorene rute (npr. 2023 archive)
