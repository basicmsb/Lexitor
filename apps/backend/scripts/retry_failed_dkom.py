"""Retry failed DKOM extraction cases s lenient prompt-om.

Problem: ~5 odluka u korpusu se ekstrakcija ne uspjela jer Claude vraća
JSON s neeskape-iranim inch-mark-om (npr. `15.6"`) što razbije sintaksu.

Strategija:
1. Identificiraj PDF-ove bez .json sidecara
2. Pošalji Claude-u s EKSPLICITNOM instrukcijom da ne koristi `"` znak
3. Sanitiziraj output prije validacije (zamijeni razbijene escape sekvence)
4. Spremi kao .json kao i ostali

Usage:
    python scripts/retry_failed_dkom.py
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_dkom import (  # noqa: E402
    CostTracker, DkomDecision, SYSTEM_PROMPT, build_tool, extract_text,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("retry_failed_dkom")


LENIENT_PROMPT_ADDITION = """

DODATNE UPUTE ZA OVAJ POKUŠAJ (raniji pokušaji su pali zbog JSON sintakse):

1. NE KORISTI znak `"` (double quote) unutar tekstualnih polja
   (argument_zalitelja, obrana_narucitelja, dkom_obrazlozenje).
   - Umjesto `15.6"` napiši `15.6 inča` ili `15.6 cm` ili `15.6"` zamijeni s
     `15,6 inch-a` (decimal zarez + 'inch' bez navodnika).
   - Za citate koristi `„text"` (curly quotes) — JSON ih dozvoljava.

2. SKRATI obrazloženja na maksimalno **150 znakova** po polju (~1 rečenica).
   Ako odluka ima više detalja, fokus na ključnu poantu.

3. NIKAD ne vraćaj listu kao JSON-encoded string. `claims` MORA biti
   pravi JSON array, ne `"[{...},{...}]"`.

4. Ako predmet ima više od 3 claim-a, obrai samo TOP 3 najvažnija.
"""


def sanitize_response(data: dict) -> dict:
    """Zadnja linija obrane — sanitiziraj svaki text field da nema raw double-quote."""
    def fix_str(s):
        if not isinstance(s, str):
            return s
        # Zamijeni raw inch-mark (broj + ") s broj + ' inch'
        s = re.sub(r'(\d)\s*"', r"\1 inch", s)
        # Reduciraj 'curly' navodnike
        s = s.replace("„", "").replace(""", "'").replace(""", "'")
        return s

    if "claims" in data and isinstance(data["claims"], list):
        for c in data["claims"]:
            if isinstance(c, dict):
                for k in ("argument_zalitelja", "obrana_narucitelja", "dkom_obrazlozenje"):
                    if k in c:
                        c[k] = fix_str(c[k])
    for k in ("predmet", "outcome_reason"):
        if k in data:
            data[k] = fix_str(data[k])
    return data


def retry_one(client, model, pdf_path: Path, json_sidecar: Path, cost: CostTracker) -> bool:
    slug = pdf_path.stem
    klasa_hint = slug.replace("-", "/", 2).replace("-", "/", 1)
    # bolji hint iz scraper json-a
    scraper_json = pdf_path.with_suffix(".json")
    if scraper_json.exists():
        try:
            meta = json.loads(scraper_json.read_text(encoding="utf-8"))
            klasa_hint = meta.get("klasa", klasa_hint)
        except Exception:  # noqa: BLE001
            pass

    log.info("Retry %s (klasa: %s)", slug, klasa_hint)
    text = extract_text(pdf_path)
    if not text or len(text) < 500:
        log.warning("  prazan PDF tekst, preskačem")
        return False

    if len(text) > 200_000:
        text = text[:200_000] + "\n\n[TEKST ODSJEČEN]"

    tool = build_tool()
    user_content = (
        f"DKOM odluka (klasa: {klasa_hint}). Izvuci podatke pozivom tool-a.\n\n"
        "=== TEKST ===\n"
        f"{text}"
    )

    msg = client.messages.create(
        model=model,
        max_tokens=8192,
        system=[
            {"type": "text", "text": SYSTEM_PROMPT + LENIENT_PROMPT_ADDITION,
             "cache_control": {"type": "ephemeral"}}
        ],
        tools=[tool],
        tool_choice={"type": "tool", "name": "record_decision"},
        messages=[{"role": "user", "content": user_content}],
    )

    usage = msg.usage
    cost.input_tokens += getattr(usage, "input_tokens", 0)
    cost.output_tokens += getattr(usage, "output_tokens", 0)
    cost.cache_creation_tokens += getattr(usage, "cache_creation_input_tokens", 0) or 0
    cost.cache_read_tokens += getattr(usage, "cache_read_input_tokens", 0) or 0

    result = None
    for block in msg.content:
        if block.type == "tool_use" and block.name == "record_decision":
            result = block.input
            break
    if result is None:
        log.error("  Claude nije pozvao tool")
        return False

    # Sanitize before validation
    result = sanitize_response(dict(result))

    # If claims is still a string (rare), try to parse
    if isinstance(result.get("claims"), str):
        try:
            result["claims"] = json.loads(result["claims"])
        except Exception:  # noqa: BLE001
            log.error("  claims je još string, nemoguće parse-ati")
            return False

    try:
        validated = DkomDecision.model_validate(result)
    except Exception as exc:  # noqa: BLE001
        log.error("  validation fail: %s", str(exc)[:300])
        return False

    json_sidecar.write_text(validated.model_dump_json(indent=2), encoding="utf-8")
    log.info("  ✓ uspjeh, spremljen")
    return True


def main() -> int:
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY nije postavljen")
        return 1
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")

    root = Path("data/02-dkom-odluke")
    extracted = root / "extracted"
    extracted.mkdir(parents=True, exist_ok=True)

    # Find missing
    all_pdfs: dict[str, Path] = {}
    for ydir in (root / "2024", root / "2025", root / "2026"):
        if ydir.exists():
            for pdf in ydir.glob("*.pdf"):
                all_pdfs[pdf.stem] = pdf
    extracted_slugs = {f.stem for f in extracted.glob("*.json") if f.name != "all.jsonl"}
    missing = sorted(set(all_pdfs.keys()) - extracted_slugs)

    log.info("Pronađeno %d failed PDF-ova za retry", len(missing))
    if not missing:
        log.info("Nema failed slučajeva — sve OK!")
        return 0

    client = anthropic.Anthropic(api_key=api_key)
    cost = CostTracker()
    success = 0
    for slug in missing:
        pdf = all_pdfs[slug]
        json_sidecar = extracted / f"{slug}.json"
        if retry_one(client, model, pdf, json_sidecar, cost):
            success += 1

    log.info("=" * 60)
    log.info("Uspjeh: %d / %d", success, len(missing))
    log.info("Trošak: $%.4f", cost.total_usd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
