# Lexitor backend skripte

Standalone skripte za pripremu pravne baze i evaluaciju modela.

## `scrape_dkom.py` — DKOM odluke scraper

Skida odluke s [dkom.hr](https://www.dkom.hr/javna-objava-odluka/10) i sprema ih lokalno u `data/02-dkom-odluke/`.

### Brzi pregled (dry-run)

```powershell
cd apps\backend
poetry run python scripts/scrape_dkom.py --year 2026 --max 5 --dry-run
```

### Skidanje

```powershell
poetry run python scripts/scrape_dkom.py --year 2026 --max 50 --verbose
```

### Argumenti

| Flag | Default | Opis |
|------|---------|------|
| `--year YYYY` | (sve) | Filtriraj odluke iz zadane godine |
| `--max N` | (sve) | Maksimalan broj odluka |
| `--output PATH` | `data/02-dkom-odluke` | Output direktorij |
| `--delay SEC` | `1.0` | Pauza između download-a (rate limit) |
| `--dry-run` | off | Samo prikaži, ne skidaj |
| `--timeout SEC` | `30.0` | HTTP timeout |
| `--verbose` | off | Detaljniji ispis |

### Output

```
data/02-dkom-odluke/
├── index.csv              # append-only log skidanja
├── 2026/
│   ├── UP-II-034-02-26-01-125.pdf
│   ├── UP-II-034-02-26-01-125.json   # metadata (klasa, naručitelj, predmet, …)
│   └── …
├── 2025/
└── …
```

### Napomene

- Postojeći PDF-ovi se preskaču (idempotentno).
- Skripta poštuje `--delay` da ne preopterećuje DKOM server.
- `data/` je u `.gitignore` — pravna baza se ne commita.
- Prije masivnog skidanja, uvijek provjeri s `--dry-run --max 5`.
