# Lexitor backend skripte

Standalone skripte za pripremu pravne baze i indeksiranje u Qdrant.

---

## `scrape_zjn.py` — Zakon o javnoj nabavi (NN 120/2016)

Jedan HTTP request na narodne-novine.nn.hr, parser razdjeljuje članke
("Članak 1.", "Članak 2." …) i sprema u `data/01-zakoni/zjn/articles.jsonl`.

```powershell
cd apps\backend
poetry run python scripts/scrape_zjn.py --verbose
```

| Flag | Default | Opis |
|------|---------|------|
| `--output PATH` | `data/01-zakoni/zjn` | Direktorij za HTML + articles.jsonl |
| `--force` | off | Pre-skinu HTML čak i ako lokalna kopija postoji |
| `--timeout SEC` | `60.0` | HTTP timeout |
| `--verbose` | off | Detaljniji ispis |

---

## `scrape_dkom.py` — DKOM odluke

Skida odluke s [dkom.hr](https://www.dkom.hr/javna-objava-odluka/10) i sprema
ih lokalno (gitignored). Podržava paginaciju i konzervativne pauze između
download-a kako bi se izbjegao IP rate-limit.

### Brzi pregled (dry-run)

```powershell
poetry run python scripts/scrape_dkom.py --start-page 1 --max 5 --dry-run
```

### Skidanje (s paginacijom)

```powershell
poetry run python scripts/scrape_dkom.py \
  --start-page 1 --end-page 3 --year 2026 --max 30 \
  --delay 5 --page-delay 10 --verbose
```

### Argumenti

| Flag | Default | Opis |
|------|---------|------|
| `--year YYYY` | (sve) | Filtriraj odluke iz zadane godine |
| `--max N` | (sve) | Maksimalan broj odluka po pokretanju |
| `--start-page` | `1` | Početna stranica DKOM listing-a |
| `--end-page` | (=start) | Zadnja stranica (uključujuća) |
| `--delay SEC` | `3.0` | Pauza između PDF download-a |
| `--page-delay SEC` | `8.0` | Pauza između listing stranica |
| `--output PATH` | `data/02-dkom-odluke` | Output direktorij |
| `--dry-run` | off | Samo prikaži, ne skidaj |
| `--timeout SEC` | `30.0` | HTTP timeout |
| `--verbose` | off | Detaljniji ispis |

### Output

```
data/02-dkom-odluke/
├── index.csv              # append-only log skidanja
├── 2026/
│   ├── UP-II-034-02-26-01-125.pdf
│   └── UP-II-034-02-26-01-125.json   (metadata: klasa, naručitelj, predmet, …)
├── 2025/
└── …
```

---

## `daily_dkom.py` — cron-friendly daily runner

Skida samo nove odluke s prve listing stranice (max 10 dnevno) i odmah ih
indeksira u Qdrant. Konzervativne defaultne pauze (5 s/PDF, 10 s/page).

```powershell
poetry run python scripts/daily_dkom.py
poetry run python scripts/daily_dkom.py --pages 2 --max 5
```

| Flag | Default | Opis |
|------|---------|------|
| `--pages N` | `1` | Koliko listing stranica provjeriti |
| `--max N` | `10` | Maksimum novih odluka po pokretanju |
| `--delay SEC` | `5.0` | Pauza između PDF-ova |
| `--page-delay SEC` | `10.0` | Pauza između stranica |
| `--skip-index` | off | Preskoči automatsko indeksiranje |

Idempotentno: postojeći PDF-ovi se preskaču, indexer ažurira deterministične
Qdrant point ID-eve.

**Windows Task Scheduler primjer:**
```
schtasks /create /tn "Lexitor DKOM Daily" /sc daily /st 06:00 ^
  /tr "C:\Dev\Lexitor\apps\backend\.venv\Scripts\python.exe C:\Dev\Lexitor\apps\backend\scripts\daily_dkom.py"
```

---

## `index_dkom.py` / `index_zjn.py` — Qdrant indexing

Čita lokalno skinute dokumente, chunka tekst, embedda kroz Cohere
`embed-multilingual-v3.0` i upserta u `dkom_decisions` Qdrant kolekciju.
Idempotentno (deterministični point ID-evi po klasi + chunk indeksu).

```powershell
poetry run python scripts/index_dkom.py --verbose
poetry run python scripts/index_zjn.py --verbose
```

Cohere trial key: `~80 calls/min` throttle + exponential backoff retry
ugrađen u `src/knowledge_base/embedder.py` — script radi i s rate-limited
trial ključem.

---

## Napomene

- Sav `data/` sadržaj je u `.gitignore` — pravna baza nikad ne ide u git.
- Lexitor **ne redistribuira** PDF-ove korisnicima; lokalne kopije služe samo
  za indeksiranje. UI uvijek linka na **izvor na DKOM/Narodnim novinama**.
- Prije masivnog skidanja, uvijek provjeri s `--dry-run`.
