# Lexitor - Design Brief

> **Za Claude Design / dizajnere**
> Skraćeni brief za razvoj UI/UX dizajna Lexitor platforme.

---

## 🎯 Što je Lexitor?

Lexitor je **AI asistent za usklađenost dokumentacije javne nabave**.

Korisnici učitavaju dokumente (DON, troškovnici, žalbe), AI ih analizira protiv Zakona o javnoj nabavi i prakse DKOM-a/VUS-a, vraća nalaze sa citatima i prijedlozima ispravka.

**Vlasnik:** Arhigon d.o.o.
**Domena:** lexitor.eu
**Tržište:** Hrvatska → eks-Yu → EU

---

## 👥 Korisnici (5 tipova)

| Persona | Što radi | Ključna potreba |
|---------|----------|-----------------|
| 🏗️ **Projektant** | Izrađuje troškovnike | Brza provjera prije slanja naručitelju |
| 🏛️ **Naručitelj** | Priprema DON | Validacija pred objavu, odgovori na žalbe |
| 💼 **Ponuditelj** | Prijavljuje se na natječaje | Analiza DON-a, generiranje žalbi i upita |
| 👨‍⚖️ **Pravnik / Stručnjak za JN** | Savjetuje klijente | Brza pretraga prakse, kvalitetni dokumenti |
| 🏢 **Konzultantska kuća** | Skalira ekspertizu | Multi-client view, white-label opcija |

---

## 🎨 Brand karakter

### Vizualni ton

- **Profesionalan, ne korporativni** - ozbiljnost ali ne hladnoća
- **Pravnička težina** - latinska elegancija (brand "Lexitor" = "onaj koji se brine za zakon")
- **Moderna, ne staromodna** - SaaS feel, ne stari pravnički bilteni
- **Pouzdana, ne "AI hype"** - dovoljno tehnologije, ali fokus na rezultate

### Vizualni reference (smjer)

**DA, više kao:**
- Linear (linear.app) - elegancija + funkcionalnost
- Notion - čistoća, fokus na sadržaj
- Vercel - moderna ozbiljnost
- Mercury (banking) - profesionalna pouzdanost

**NE, manje kao:**
- Stari pravnički sajtovi (zatrpani tekstom)
- Genericki AI alati (preglasno "AI POWERED!")
- Korporativni softver (sivo, dosadno)

### Boje (preporuka)

- **Primary:** Duboka plava (#1E3A8A ili slično) - autoritet, povjerenje
- **Accent:** Topla zlatna (#D4A24E) ili svijetla cyan (#0EA5E9) - moderni dodatak
- **Status:** Crvena (kršenje), žuta (upozorenje), zelena (usklađeno)
- **Pozadina:** Čista bijela ili vrlo svijetlo siva (#FAFAFA)

### Tipografija

- **Naslovi:** Serif sa karakterom (npr. *Fraunces*, *Source Serif*) - daje pravnički ton
- **Tijelo teksta:** Sans-serif moderan (*Inter*, *DM Sans*) - čitljivost
- **Kod / citati:** Monospace (*JetBrains Mono*) - tehnički dijelovi

### Logo (ideje)

Brand "Lexitor" - mogući smjerovi:
- Stilizirana slova "Lx" sa pravničkim elementom (vaga, paragraf)
- Latinski "L" sa kompasom ili lupa (vodič kroz pravo)
- Minimalistički wordmark

---

## 🖼️ Glavni ekrani / tijekovi

### 1. Landing page (lexitor.eu)

**Cilj:** uvjeriti posjetitelja u 30 sekundi.

**Elementi:**
- Hero: "Lexitor - Usklađenost javne nabave bez stresa." + CTA "Pokušaj besplatno"
- Tri ključne funkcije (kartice): Analiza, Generiranje, Učenje iz prakse
- Kome je namijenjeno (5 persona kartica)
- Social proof (testimonials, brojke)
- Pricing
- "Powered by Arhigon" subtilno u footeru

### 2. Dashboard (nakon login-a)

**Cilj:** brzi pregled stanja.

**Elementi:**
- Lijevi sidebar: navigacija (Analiza, Dokumenti, Pravna baza, Postavke)
- Glavni prostor: nedavne analize (kartice), brzi statistike
- Top desno: notifikacije, profil, plan

### 3. Upload + Analiza

**Cilj:** jednostavno učitavanje dokumenta i prikaz analize.

**Elementi:**
- Veliki drag & drop area
- Tipovi dokumenata: DON, Troškovnik, Žalba, Drugo
- Tijekom analize: progress sa porukama ("Analiziram stavku 3 od 47...")
- Estimirano vrijeme

### 4. Rezultati analize ⭐ NAJVAŽNIJI EKRAN

**Cilj:** jasno pokazati nalaze i omogućiti reakciju.

**Layout:**
```
┌────────────────────────────────────────────────────┐
│  📊 Analiza: DON_2026_05_06.pdf                    │
│  ✅ 142 stavke usklađeno  🟡 8 upozorenja  🔴 3 kršenja │
└────────────────────────────────────────────────────┘
┌─────────────┬──────────────────────────────────────┐
│  Lijevi     │  Glavni prostor:                     │
│  panel:     │                                      │
│  - Lista    │  Otvorena stavka sa:                 │
│    stavki   │  - Tekst stavke                      │
│  - Filteri  │  - Status + objašnjenje              │
│  - Sažetak  │  - Citirani izvori (collapsible)     │
│             │  - Prijedlog ispravka                │
│             │  - Akcije: Ispravi / Prihvati rizik /│
│             │    Označi kao false positive         │
│             │  - Feedback (👍 👎)                  │
└─────────────┴──────────────────────────────────────┘
```

**Vizualni status indikatori:**
- 🟢 Tanki zeleni rub uz stavku - usklađeno
- 🟡 Žuta pozadina + ikona - upozorenje
- 🔴 Crvena pozadina + ikona - kršenje
- ⚪ Sivo - nije provjereno

### 5. Document Generator (Faza 2)

**Cilj:** generirati nacrt žalbe / odgovora / pojašnjenja.

**Elementi:**
- Wizard: 1) Tip dokumenta → 2) Konkretni slučaj → 3) Generiranje → 4) Editor
- Generirani tekst sa **track changes** mogućnostima
- Sidebar sa citiranim izvorima
- Export: PDF, DOCX

### 6. Kolaboracija (asinkrona, Faza 2)

**Elementi:**
- Share dokument sa drugima (link, email)
- Komentari uz dijelove teksta (kao Google Docs)
- Track changes (tko je što promijenio)
- Verzije dokumenta
- "Approve" workflow za pravnike

### 7. Knowledge Base / Pretraga prakse

**Cilj:** direktna pretraga pravne baze.

**Elementi:**
- Search bar (semantic search)
- Filteri: tip izvora (ZJN/DKOM/VUS/Sud EU), godina, tema
- Rezultati sa highlights, citatima
- "Sličan slučaj" preporuke

### 8. Postavke / Plan / Tim

- Profil korisnika
- Plan i naplata (Tier model)
- Tim (za Team/Premium plan) - dodaj članove, dodijeli uloge
- API ključevi (za Enterprise)
- Privacy postavke (sharing/private)

---

## 💰 Pricing tier (vizualni prikaz)

| Tier | Cijena/mj | Fokus |
|------|-----------|-------|
| **Free Trial** | 0 EUR | 3 analize/mj, solo, demo |
| **Solo** | 49 EUR | 20 analiza/mj, share read-only |
| **Team** | 149 EUR | 100 analiza/mj, do 5 osoba, kolaboracija |
| **Premium** | 299 EUR | 250 analiza/mj, sinkrona kolaboracija, privatnost |
| **Enterprise** | Po dogovoru | Bez limita, white-label, API, custom |

---

## 🌍 Lokalizacija

**MVP:** Hrvatski jezik, hrvatski pravni okvir
**Faza 3:** Slovenski, srpski, bosanski (eks-Yu)
**Faza 5:** Engleski + njemački + ostali EU jezici

UI mora biti **strukturiran za laku translaciju** (i18n od dana 1).

---

## 📱 Responzivnost

**Prioritet:**
1. **Desktop (web app)** - glavni use case (analize, kolaboracija, generiranje)
2. **Tablet** - sekundarno (pregled, čitanje)
3. **Mobitel** - tertiarno (notifikacije, brzi pregled, ne za kompletan rad)

**Razlog:** Pravnici i naručitelji rade na laptopima. Mobile je samo za "vidim da je gotovo" trenutke.

---

## ♿ Accessibility (WCAG 2.1 AA)

- Kontrast minimum 4.5:1 za tekst
- Fokus indikatori jasni
- Tipke navigacije rade bez miša
- Screen reader friendly
- Status ne ovisi samo o boji (uvijek + tekst/ikona)

---

## 🚦 Status indikatori (jezik)

Konzistentno u cijeloj aplikaciji:

- ✅ **Usklađeno** - zeleno - sustav nije našao problem
- 🟡 **Upozorenje** - žuto - mogući problem, vrijedi pregled
- 🔴 **Kršenje** - crveno - visoka vjerojatnost kršenja
- ⚪ **Nije provjereno** - sivo - nije bilo u opsegu analize
- 🔵 **Prihvaćen rizik** - plavo - korisnik svjesno prihvatio
- 🟣 **Pravna nesigurnost** - ljubičasto - postoje suprotni presedani (DKOM vs VUS)

---

## 🎯 UX principi

### 1. AI mora biti razumljiv

Korisnik mora **uvijek znati zašto** je AI dao određeni nalaz. Citati, izvori, objašnjenja.

### 2. Čovjek je glavni

Lexitor predlaže, **korisnik odlučuje**. Svaki AI nalaz ima opcije: prihvati / odbij / koriguj.

### 3. Fail gracefully

Kad AI ne može odgovoriti, kaže to jasno. **Ne haluciniramo**.

### 4. Privacy-aware

Korisnik vidi gdje se njegovi podaci čuvaju, što se dijeli, može povući suglasnost.

### 5. Mobile last

Optimiziraj za desktop iskustvo. Mobile je nice-to-have.

---

## 🚫 Anti-patterns (čega se kloniti)

- ❌ Pretjerano "AI POWERED" branding (smanji povjerenje)
- ❌ Modal popups bez razloga
- ❌ Onboarding koji traje 10 minuta
- ❌ Skrivanje cijena ("kontaktiraj nas")
- ❌ Animacije koje usporavaju rad
- ❌ Dark patterns (lažno hitno, manipulacija)
- ❌ Pravnički žargon koji "obični" korisnik ne razumije

---

## ✅ Što želimo postići vizualno

**Korisnik treba osjećati:**
- "Ovaj alat zna što radi"
- "Mogu mu vjerovati"
- "Vidim jasno što treba ispraviti"
- "Imam kontrolu - alat me ne tjera"
- "Vrijedi mi mojih 49 EUR/mj"

**Korisnik NE treba osjećati:**
- "Zatrpan sam podacima"
- "Ne razumijem zašto AI to misli"
- "Strah me da ću nešto pogriješiti"
- "Ovo izgleda kao još jedan generički AI tool"

---

## 📋 Početni zadatak za dizajn

Predlažem ovaj redoslijed dizajn iteracija:

1. **Logo + brand identitet** (1-2 dana)
   - Wordmark, color palette, typography
2. **Landing page (lexitor.eu)** (3-5 dana)
   - Hero, features, pricing, testimonials
3. **Glavni rezultati ekran** (3-5 dana)
   - Najvažniji UX - tu se troši najviše vremena
4. **Dashboard** (2-3 dana)
   - Pregled, navigacija
5. **Upload + Wizard** (2-3 dana)
   - Tijekovi učitavanja
6. **Document Generator** (3-4 dana)
   - Faza 2, ali dobro je dizajnirati ranije
7. **Mobile responsive verzije** (paralelno)

---

## 📞 Kontakt za dizajn

Pitanja oko brifa: project manager (Arhigon)
Pravna validacija sadržaja: stručnjak za JN
Tehnička validacija: developer (uključuje se kasnije)

---

*Verzija: 1.0 | Svibanj 2026 | Lexitor by Arhigon*
