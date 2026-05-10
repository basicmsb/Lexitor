"""Extract strukturirane podatke iz DKOM odluka pomoću Claude Sonnet 4.5.

Za svaku odluku iz `data/02-dkom-odluke/{year}/*.pdf`, izvuče:
- ishod (usvojena/odbijena/odbačena/obustavljen) + razlog
- članovi vijeća (3 osobe + uloga)
- vrsta postupka (otvoreni/ograničeni/pregovarački/...)
- metadata: žalitelj/naručitelj OIB, vrijednost nabave, datumi, broj objave EOJN, trošak postupka
- claims: svaki argument žalitelja + obrana naručitelja + DKOM verdikt + obrazloženje + citirani članak
- citirane prethodne DKOM odluke

Output: `data/02-dkom-odluke/extracted/<klasa-slug>.json` (idempotentno, preskače
already-extracted slučajeve). Plus master `extracted/all.jsonl` za batch query.

Usage:
    python scripts/extract_dkom.py --limit 20          # sample mode
    python scripts/extract_dkom.py                      # svih 749
    python scripts/extract_dkom.py --force <klasa-slug> # re-extract specifični
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError, model_validator

# Anthropic SDK
import anthropic

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("extract_dkom")


# ---------------------------------------------------------------------------
# Schema (Pydantic za validaciju; prosljeđuje se Claude-u kao tool input_schema)

class Member(BaseModel):
    ime: str = Field(description="Puno ime i prezime u nominativu (npr. 'Danijela Antolković')")
    uloga: Literal["predsjednik", "zamjenik_predsjednika", "clan"] = Field(
        description="Uloga u vijeću"
    )


class Claim(BaseModel):
    type: Literal[
        "brand_lock",
        "kratki_rok",
        "vague_kriterij",
        "diskrim_uvjeti",
        "neprecizna_specifikacija",
        "neispravna_grupacija",
        "kriterij_odabira",
        "ocjena_ponude",
        "espd_dokazi",
        "jamstvo",
        "trosak_postupka",
        "ostalo",
    ] = Field(
        description=(
            "Kategorija argumenta: brand_lock (marka bez 'ili jednakovrijedno'), "
            "kratki_rok (rok dostave ponude prekratak), vague_kriterij (neobjektivan "
            "kriterij odabira), diskrim_uvjeti (diskriminatorni uvjeti sposobnosti), "
            "neprecizna_specifikacija (specifikacije nejasne/kontradiktorne), "
            "neispravna_grupacija (krivo grupiranje ili negrupiranje), "
            "kriterij_odabira (problem s kriterijem odabira ENP), "
            "ocjena_ponude (ocjena ili odbijanje ponude), "
            "espd_dokazi (ESPD ili dokazi sposobnosti), "
            "jamstvo (jamstva za ozbiljnost/dobro izvršenje), "
            "trošak_postupka (sam trošak žalbenog postupka), "
            "ostalo (sve ostalo)"
        )
    )
    argument_zalitelja: str = Field(
        description="Što žalitelj tvrdi (jedna ili dvije rečenice, sažeto)"
    )
    obrana_narucitelja: str | None = Field(
        default=None, description="Što naručitelj odgovara, ako je navedeno"
    )
    dkom_verdict: Literal["uvazen", "djelomicno_uvazen", "odbijen", "ne_razmatra"] = Field(
        description="Kako je DKOM odlučio o OVOM specifičnom argumentu"
    )
    dkom_obrazlozenje: str = Field(
        description="DKOM-ovo obrazloženje OVOG argumenta (1-3 rečenice)"
    )
    violated_article_claimed: str | None = Field(
        default=None, description="Članak koji žalitelj tvrdi da je prekršen, npr. 'ZJN čl. 207'"
    )


def _coerce_str_to_list(value: Any) -> Any:
    """Ako je input string koji izgleda kao JSON array, parse-aj ga.
    Claude ponekad serijalizira nested liste kao JSON-encoded string."""
    if isinstance(value, str) and value.strip().startswith("["):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            log.warning("  json.loads failed na liste-string: %s", exc)
    return value


class DkomDecision(BaseModel):
    klasa: str = Field(description="Klasa odluke, npr. 'UP/II-034-02/26-01/176'")
    predmet: str = Field(description="Predmet nabave (kraći opis)")
    vrsta_postupka: Literal[
        "otvoreni",
        "ograniceni",
        "pregovaracki",
        "natjecateljski_dijalog",
        "jednostavna_nabava",
        "nepoznat",
    ] = Field(description="Vrsta postupka javne nabave")
    outcome: Literal["usvojena", "djelomicno_usvojena", "odbijena", "odbacena", "obustavljen"] = Field(
        description=(
            "Ishod žalbe: usvojena (poništava se odluka/dokumentacija/postupak), "
            "djelomično_usvojena, odbijena (odbija se kao neosnovana), "
            "odbačena (procedurally — zakašnjelo/neuredno), obustavljen (žalitelj odustao)"
        )
    )
    outcome_reason: str = Field(
        description="Kratko obrazloženje ishoda (jedna rečenica)"
    )
    vijece: list[Member] = Field(
        description="Članovi vijeća DKOM-a koji su donijeli ovu odluku (obično 3 osobe)"
    )
    zalitelj_ime: str | None = None
    zalitelj_oib: str | None = None
    narucitelj_ime: str | None = None
    narucitelj_oib: str | None = None
    vrijednost_nabave: float | None = Field(
        default=None,
        description="Procijenjena ili ugovorena vrijednost nabave (broj, bez valute)",
    )
    valuta: Literal["EUR", "HRK", "USD"] | None = None
    broj_objave_eojn: str | None = Field(
        default=None,
        description="Broj objave EOJN, npr. '2025/S F02-0013326'",
    )
    datum_objave: str | None = Field(
        default=None, description="Datum objave nabave (ISO YYYY-MM-DD)"
    )
    datum_predaje_zalbe: str | None = None
    datum_odluke: str | None = None
    trosak_postupka_eur: float | None = Field(
        default=None,
        description="Koliko naručitelj plaća žalitelju za trošak postupka (EUR)",
    )
    claims: list[Claim] = Field(
        description="Svaki posebni argument žalitelja kao zaseban Claim"
    )
    citirane_prethodne_odluke: list[str] = Field(
        default_factory=list,
        description="Klase prethodnih DKOM odluka koje su citirane u obrazloženju",
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_string_lists(cls, data: Any) -> Any:
        """Ako je Claude vratio bilo koji list-field kao JSON-encoded string,
        parse-aj ga u listu prije Pydantic validacije."""
        if isinstance(data, dict):
            for key in ("vijece", "claims", "citirane_prethodne_odluke"):
                if key in data:
                    data[key] = _coerce_str_to_list(data[key])
        return data


# ---------------------------------------------------------------------------
# Cost tracking

PRICE_INPUT_PER_MTOK = 3.0  # USD per million tokens (Sonnet 4.5)
PRICE_OUTPUT_PER_MTOK = 15.0
PRICE_CACHE_WRITE_PER_MTOK = 3.75  # 25% surcharge on cache writes
PRICE_CACHE_READ_PER_MTOK = 0.30  # 90% discount on cache reads


@dataclass
class CostTracker:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    cases_processed: int = 0
    cases_skipped: int = 0
    cases_failed: int = 0

    @property
    def total_usd(self) -> float:
        return (
            self.input_tokens * PRICE_INPUT_PER_MTOK / 1_000_000
            + self.output_tokens * PRICE_OUTPUT_PER_MTOK / 1_000_000
            + self.cache_creation_tokens * PRICE_CACHE_WRITE_PER_MTOK / 1_000_000
            + self.cache_read_tokens * PRICE_CACHE_READ_PER_MTOK / 1_000_000
        )


# ---------------------------------------------------------------------------
# PDF → text

def extract_text(pdf_path: Path) -> str:
    try:
        out = subprocess.run(
            ["pdftotext", "-layout", "-enc", "UTF-8", str(pdf_path), "-"],
            capture_output=True,
            timeout=45,
        )
        return out.stdout.decode("utf-8", errors="ignore")
    except Exception as exc:  # noqa: BLE001
        log.error("pdftotext failed za %s: %s", pdf_path.name, exc)
        return ""


# ---------------------------------------------------------------------------
# Claude extraction

SYSTEM_PROMPT = """Ti si pravni asistent specijaliziran za hrvatsko pravo javne nabave (ZJN). Tvoj zadatak je iz teksta DKOM (Državna komisija za kontrolu postupaka javne nabave) odluke izvući strukturirane podatke pozivajući tool `record_decision`.

Ključne upute:

1. **Ishod žalbe** — pažljivo pročitaj izreku (RJEŠENJE) pri vrhu odluke:
   - "Poništava se odluka/dokumentacija/postupak" ili "Usvaja se žalba" → outcome = "usvojena"
   - "Djelomično se usvaja žalba" → "djelomicno_usvojena"
   - "Odbija se žalba kao neosnovana" → "odbijena"
   - "Odbacuje se žalba" (zakašnjela, neuredna, nedopuštena) → "odbacena"
   - "Obustavlja se postupak po žalbi" → "obustavljen"

2. **Vijeće** — traži segment "u Vijeću sastavljenom od članova: …" ili "Vijeće DKOM-a u sastavu…". Imena uvijek pretvori u **nominativ** (npr. "Danijele Antolković" u tekstu → "Danijela Antolković" u outputu).

3. **Vrsta postupka** — najčešće u uvodu obrazloženja: "otvoreni postupak", "ograničeni postupak", "pregovarački postupak", "natjecateljski dijalog", "jednostavna nabava". Ako nije eksplicitno navedeno → "nepoznat".

4. **Claims** — svaki argument žalitelja je zaseban Claim. Često ih je 1-5. Za svaki claim trebaš identificirati DKOM-ov verdikt **na taj specifični argument** (ne ukupni outcome žalbe — žalba može biti odbijena ali jedan claim usvojen i obrnuto):
   - "Žaliteljev navod o … je osnovan" → dkom_verdict = "uvazen"
   - "Žaliteljev navod o … nije osnovan" / "neosnovan je" → "odbijen"
   - "Žaliteljevi navodi o X dijelom su osnovani" → "djelomicno_uvazen"
   - Ako DKOM nije razmatrao taj argument (npr. zbog odbacivanja žalbe) → "ne_razmatra"

5. **Type kategorija** — koristiš jedan od dvanaest predefiniranih tipova. Mapiranje:
   - "tehnička specifikacija navodi marku" → "brand_lock"
   - "rok za dostavu ponude prekratak" → "kratki_rok"
   - "kriterij za odabir je subjektivan/neobjektivan" → "vague_kriterij"
   - "uvjet sposobnosti je diskriminatoran/prestrog" → "diskrim_uvjeti"
   - "specifikacija je nejasna/kontradiktorna" → "neprecizna_specifikacija"
   - "krivo grupiranje predmeta nabave" → "neispravna_grupacija"
   - "ENP/kriteriji odabira sami" → "kriterij_odabira"
   - "ocjena ili odbijanje ponude (post-rok)" → "ocjena_ponude"
   - "ESPD obrazac / dokazi sposobnosti" → "espd_dokazi"
   - "jamstvo za ozbiljnost ponude / dobro izvršenje" → "jamstvo"
   - "trošak žalbenog postupka" → "trošak_postupka"
   - sve ostalo → "ostalo"

6. **Datumi** — uvijek u ISO formatu YYYY-MM-DD. Hrvatski tekst "22. travnja 2026." → "2026-04-22".

7. **OIB** — uvijek 11 znamenki bez razmaka. Ako nije naveden, ostavi null.

8. **Vrijednost nabave** — broj (decimal), bez valute. Valuta zasebno. "1.250.000,00 eura" → vrijednost_nabave=1250000.00, valuta="EUR".

9. **Citirane prethodne odluke** — traži unutar obrazloženja izraze poput "u skladu s odlukom UP/II-…", "ranija praksa DKOM-a (npr. UP/II-…)". Lista klasa.

10. **Sažetost** — argument_zalitelja, obrana_narucitelja, dkom_obrazloženje sve treba biti **1-3 rečenice**. Ne kopiraj cijele paragrafe iz odluke.

Ako neki podatak nije naveden u tekstu, ostavi polje null (ako je opcionalno) ili koristi "nepoznat" enum. Ne izmišljaj podatke."""


def build_tool() -> dict[str, Any]:
    """Konvertira Pydantic schemu u Anthropic tool definition."""
    schema = DkomDecision.model_json_schema()
    return {
        "name": "record_decision",
        "description": "Spremi strukturirane podatke o DKOM odluci.",
        "input_schema": schema,
    }


def _call_claude(
    client: anthropic.Anthropic,
    model: str,
    pdf_text: str,
    klasa_hint: str,
    cost: CostTracker,
    extra_instruction: str = "",
) -> dict[str, Any] | None:
    """Jedan API call. Vrati tool_use input dict ili None."""
    tool = build_tool()
    user_content = (
        f"Sljedeći tekst je DKOM odluka (klasa hint: {klasa_hint}). "
        "Izvuci strukturirane podatke pozivanjem tool-a `record_decision`.\n\n"
    )
    if extra_instruction:
        user_content += f"VAŽNO: {extra_instruction}\n\n"
    user_content += f"=== TEKST ODLUKE ===\n{pdf_text}"

    try:
        msg = client.messages.create(
            model=model,
            max_tokens=8192,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[tool],
            tool_choice={"type": "tool", "name": "record_decision"},
            messages=[{"role": "user", "content": user_content}],
        )
    except anthropic.BadRequestError as exc:
        log.error("Bad request za %s: %s", klasa_hint, exc)
        return None
    except anthropic.APIError as exc:
        log.error("API error za %s: %s", klasa_hint, exc)
        return None

    # Track tokens
    usage = msg.usage
    cost.input_tokens += getattr(usage, "input_tokens", 0)
    cost.output_tokens += getattr(usage, "output_tokens", 0)
    cost.cache_creation_tokens += getattr(usage, "cache_creation_input_tokens", 0) or 0
    cost.cache_read_tokens += getattr(usage, "cache_read_input_tokens", 0) or 0

    # Find tool_use block
    for block in msg.content:
        if block.type == "tool_use" and block.name == "record_decision":
            return block.input  # type: ignore[return-value]
    return None


def extract_decision(
    client: anthropic.Anthropic,
    model: str,
    pdf_text: str,
    klasa_hint: str,
    cost: CostTracker,
) -> dict[str, Any] | None:
    """Pošalji PDF text Claudeu i vrati strukturirani output. Ako prvi
    pokušaj vrati malformiran rezultat (claims kao truncated string),
    retry-aj s eksplicitnom uputom da skrati obrazloženja."""
    if len(pdf_text) > 200_000:
        pdf_text = pdf_text[:200_000] + "\n\n[TEKST ODSJEČEN]"

    result = _call_claude(client, model, pdf_text, klasa_hint, cost)
    if result is None:
        return None

    # Quick check — ako claims ili vijece dolaze kao truncated string,
    # validation će fail-ati. Probaj odmah validation i ako ne prolazi,
    # retry s kraćim outputom.
    try:
        DkomDecision.model_validate(result)
        return result
    except ValidationError:
        log.info("  retry za %s — eksplicitno tražim kraći output", klasa_hint)
        result = _call_claude(
            client, model, pdf_text, klasa_hint, cost,
            extra_instruction=(
                "Prošli pokušaj je dao predugačak output koji je truncated. "
                "MAKSIMALNO SAŽMI: argument_zalitelja, obrana_narucitelja i "
                "dkom_obrazlozenje neka budu po JEDNA rečenica (do 200 znakova). "
                "Ako ima više od 4 claims-ova, obrai samo top 4 najvažnija. "
                "VRATI claims kao pravi JSON array, NE kao escape-iran string."
            ),
        )
        return result


# ---------------------------------------------------------------------------
# Main loop

def slug_from_klasa(klasa: str) -> str:
    """UP/II-034-02/26-01/176 → UP-II-034-02-26-01-176"""
    return klasa.replace("/", "-").replace(" ", "")


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Procesuiraj najviše N slučajeva")
    parser.add_argument("--year", type=str, default=None, help="Samo godina (2024/2025/2026)")
    parser.add_argument("--force", type=str, default=None, help="Force re-extract konkretne klase (npr. UP-II-034-02-26-01-176)")
    parser.add_argument("--dry-run", action="store_true", help="Ne zovi API, samo izbroji")
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY nije postavljen")
        return 1
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    log.info("Model: %s", model)

    root = Path("data/02-dkom-odluke")
    output_dir = root / "extracted"
    output_dir.mkdir(parents=True, exist_ok=True)
    aggregate = output_dir / "all.jsonl"

    # Skupi PDF-ove
    years = [args.year] if args.year else ["2026", "2025", "2024"]
    pdfs: list[Path] = []
    for y in years:
        ydir = root / y
        if ydir.exists():
            pdfs.extend(sorted(ydir.glob("*.pdf"), reverse=True))

    log.info("Pronađeno %d PDF-ova za obradu", len(pdfs))

    cost = CostTracker()
    client = anthropic.Anthropic(api_key=api_key)
    start = time.time()
    processed_paths: list[Path] = []

    for idx, pdf in enumerate(pdfs):
        slug = pdf.stem  # UP-II-034-02-26-01-176
        out_path = output_dir / f"{slug}.json"

        if args.force and args.force != slug:
            continue
        if out_path.exists() and args.force != slug:
            cost.cases_skipped += 1
            continue

        if args.limit and cost.cases_processed >= args.limit:
            break

        if args.dry_run:
            log.info("[%d/%d] DRY: %s", idx + 1, len(pdfs), slug)
            cost.cases_processed += 1
            continue

        log.info("[%d/%d] %s", idx + 1, len(pdfs), slug)
        text = extract_text(pdf)
        if not text or len(text) < 500:
            log.warning("  prazan/kratki text (%d chars), preskačem", len(text))
            cost.cases_failed += 1
            continue

        klasa_hint = slug.replace("-", "/").replace("UP/II/", "UP/II-").replace("/", "-", 1).replace("-", "/", 1)
        # bolji hint: probaj iz JSON sidecara koji već imamo
        json_sidecar = pdf.with_suffix(".json")
        if json_sidecar.exists():
            try:
                meta = json.loads(json_sidecar.read_text(encoding="utf-8"))
                klasa_hint = meta.get("klasa") or klasa_hint
            except Exception:  # noqa: BLE001
                pass

        result = extract_decision(client, model, text, klasa_hint, cost)
        if result is None:
            cost.cases_failed += 1
            continue

        # Validacija Pydantic schema-om
        try:
            validated = DkomDecision.model_validate(result)
        except ValidationError as exc:
            log.error("  schema validation fail za %s: %s", slug, exc.errors()[:2])
            cost.cases_failed += 1
            continue

        out_path.write_text(
            validated.model_dump_json(indent=2),
            encoding="utf-8",
        )
        processed_paths.append(out_path)
        cost.cases_processed += 1

        # Live cost log every 10 cases
        if cost.cases_processed % 10 == 0:
            elapsed = time.time() - start
            rate = cost.cases_processed / elapsed * 60
            log.info(
                "  -- %d procesuirano, $%.2f, %.1f/min --",
                cost.cases_processed, cost.total_usd, rate,
            )

    # Aggregate to all.jsonl
    if not args.dry_run:
        with aggregate.open("w", encoding="utf-8") as out:
            for jp in sorted(output_dir.glob("*.json")):
                if jp.name == "all.jsonl":
                    continue
                try:
                    obj = json.loads(jp.read_text(encoding="utf-8"))
                    out.write(json.dumps(obj, ensure_ascii=False) + "\n")
                except Exception:  # noqa: BLE001
                    continue

    elapsed = time.time() - start
    log.info("=" * 60)
    log.info("Procesuirano: %d", cost.cases_processed)
    log.info("Preskočeno (već ima .json): %d", cost.cases_skipped)
    log.info("Neuspjelo: %d", cost.cases_failed)
    log.info("Input tokens: %d", cost.input_tokens)
    log.info("Output tokens: %d", cost.output_tokens)
    log.info("Cache write: %d", cost.cache_creation_tokens)
    log.info("Cache read: %d", cost.cache_read_tokens)
    log.info("Trošak: $%.4f", cost.total_usd)
    log.info("Trajanje: %.1f s (%.1f/min)", elapsed, cost.cases_processed / max(elapsed, 1) * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
