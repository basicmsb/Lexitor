"""Scraper za Visoki upravni sud RH (VUS) — UsII odluke.

VUS sudi po žalbama protiv DKOM-ovih odluka. U ekstrahiranim DKOM odlukama
nailazimo na citate poput `UsII-507/19`, `UsII-151/20` — to su predmeti
VUS-a koji su revidirali DKOM presude.

**STATUS: SKELETON — još nije implementiran.**

Razlog: trebamo prvo identificirati javni endpoint za VUS odluke. Kandidati:
- https://sudskapraksa.pravosudje.hr — sudska praksa portal (svi sudovi)
- https://www.upravnisudrh.hr — sajt Visokog upravnog suda

Plan implementacije:

1. **Otkrivanje (manual research, ne automatski)**:
   - Naći službeni listing URL za UsII predmete
   - Provjeriti pruža li sudskapraksa.pravosudje.hr filter po "UsII" oznaci
   - Eventualno API endpoint za PDF download

2. **Reuse DKOM scraper pattern**:
   - Httpx + BeautifulSoup za HTML parsing (već koristimo u `scrape_dkom.py`)
   - Output dir: `data/03-vus-odluke/{year}/UsII-NN-YYYY.pdf`
   - JSON sidecar s metadata (datum, predmet, oznaka)
   - Index.csv kao u DKOM-u

3. **Priority cases**:
   - Citate iz DKOM korpusa imaju prioritet — to su odluke koje su
     već relevantne (vidi `citation_network` u `analyze_dkom.py`)
   - Skripta može uzeti listu citiranih UsII oznaka kao input i samo te
     skinuti, umjesto kompletnog scrape-a

4. **LLM ekstrakcija**:
   - Isti pattern kao `extract_dkom.py` — extraction → JSON sidecar
   - Schema treba dodatna polja: revidira_li_DKOM_odluku (klasa), suca,
     ishod (potvrđena/poništena DKOM odluka)

**Korak prema implementaciji**:
1. Korisnik ručno otvori 3-5 UsII predmeta iz DKOM citata na pravosuđu
2. Spremi URL-ove kao primjer
3. Ja onda napišem actual scraper based na tim URL-ovima

**Procijenjeni napor**: 2-4h razvoja + 1-2h LLM ekstrakcije po 100 odluka.
**Vrijednost**: srednje-visoka — VUS revizije DKOM-a su jaka argumentska
podrška za žalbe modul (drugi stupanj sudske prakse).
"""
from __future__ import annotations

import sys

print(__doc__)
print("\nSkripta još nije implementirana. Vidi docstring za plan.")
sys.exit(1)
