# DON modul — manual test checklist

Iako Lexitor (zasad) nema automatizirane UI testove, ovaj dokument popisuje
**kritične scenarije** koje treba ručno provjeriti nakon izmjena u DON modulu.
Cilj: spriječiti regresije na bitnim user flow-ovima.

## Setup

1. Backend running (`uvicorn` na portu 8000)
2. Frontend running (`pnpm dev` na portu 3000)
3. Test data: ima barem **3 testna DON-a** u različitim formatima:
   - jedan **.md** (od EOJN-a)
   - jedan **.txt** (copy-paste iz Word/EOJN viewer-a)
   - jedan **.docx** (npr. "POS Vrlika" iz Marko-vog dropbox-a)
   - jedan **.pdf** s tekstom (može OCR-irati)

## Test scenariji

### 1. Upload pojedinačnog DON-a (legacy flow)

- [ ] Otvori `/analiza/don` → vidi se "Učitaj DON" sekcija
- [ ] Učitaj .docx s brand mention-ima (Sika, Knauf…)
- [ ] Auto-redirect na detail page nakon upload-a
- [ ] Analiza krene automatski, progress bar se popunjava
- [ ] Kad završi, prikaže se 3 stupca: TOC | blokovi+LA pairs
- [ ] Brand_lock nalazi su crveno označeni s ZJN čl. 207 citatom

### 2. DocumentSet (multi-file) flow

- [ ] U `/analiza/don` upiši ime nabave (npr. "TEST-25 — Sanacija krova")
- [ ] Drag-drop 4 fajla različitih formata (.docx, .pdf, .md, .txt)
- [ ] Sequential upload progress vidi se na overlay-u
- [ ] Redirect na `/analiza/don/sets/<id>` s tabovima za svaki fajl
- [ ] Klikaj između tab-ova — svaki fajl ima vlastitu analizu
- [ ] "Pokreni ponovno" na pojedinom tabu kreira novu analizu, ostala dokumenta su netaknuta
- [ ] Brisanje seta (✗ gumb na listingu) traži potvrdu i briše sve fajlove zajedno

### 3. Independent scroll (regresija 2026-05-10)

- [ ] U DON detail view sa puno blokova (npr. 30+)
- [ ] Scroll TOC sidebar gore-dolje — **ne pomiče srednje blokove**
- [ ] Scroll srednje blokove — **ne pomiče TOC sidebar**
- [ ] Pri scrollu strelice za TOC ne nestaju van vidnog polja viewport-a

### 4. Per-blok LA card (regresija 2026-05-10)

- [ ] Svaki blok u srednjoj koloni ima **vlastiti LA card** desno od sebe
- [ ] Ne treba klikati blok da se vidi LA — sve vidljivo odmah
- [ ] Blokovi s warn/fail status-om imaju coloured left border (zlatno/crveno)
- [ ] Blokovi bez nalaza imaju zeleni "USKLAĐENO" card

### 5. Error handling

- [ ] Učitaj nepodržani format (.doc — stari binary Word)
- [ ] Pokreni analizu — analiza fail-a
- [ ] U DON detail view, crveni banner "Greška u analizi" s porukom
- [ ] Status traka kaže "Analiza neuspjela" (ne "Analiza završena")
- [ ] "Pokreni ponovno" pokušava ponovo

### 6. Mobile responsive (≤ 768px width)

- [ ] Otvori DON detail na mobilnoj veličini (Chrome DevTools, iPhone preset)
- [ ] TOC sidebar **stack-a iznad** glavnih blokova, max ~30vh visina
- [ ] Svaki blok + LA par **stack-a vertikalno** (LA ispod bloka, ne pored)
- [ ] Tab-ovi (kod sets) horizontal-scrollable, ne lome layout
- [ ] Buttoni i tekst čitljivi bez zoom-a

### 7. Brand_lock detekcija (rule logic)

- [ ] Upload DON-a sa pasusom "Hidroizolacija mora biti Sika 300 PP" → 🔴 brand_lock
- [ ] Upload sa "Sika tipa kao MasterSeal 540 ili jednakovrijedno" → ✓ usklađeno (disclaimer prepoznat)
- [ ] Upload sa nepoznatim brandom "AcmeCorp 9000" → ✓ usklađeno (ne u listi)
- [ ] Tablica s više brandova: oba flagged-a u istom blokovu (`kind=table`)

## Pri svakom novom rule-u

Kad se doda novo pravilo (`kratki_rok`, `vague_kriterij` itd.):

1. Pisati unit test u `tests/unit/test_analyzer_*.py`
2. Dodati barem 2 manual scenarija u ovaj checklist
3. Provjeriti da ne regresira postojeća pravila — pokreni `pytest tests/unit/`

## Prije svakog deploy-a

- [ ] `pnpm tsc --noEmit` čisto (TypeScript)
- [ ] `pnpm lint` čisto (ESLint)
- [ ] `pytest tests/unit/` 100% pass
- [ ] Manual checklist iznad — minimum scenariji 1, 3, 4, 5 prošli
