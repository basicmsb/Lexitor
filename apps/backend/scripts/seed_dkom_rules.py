"""Faza C seed — iz DKOM extracted dataset-a generira **rule kandidate**
spremne za implementaciju.

Za svaki claim type, generira sekciju s:
- frekvencijom pojavljivanja (koliko žalbi je imalo ovaj argument)
- uvazen rate (koliko često DKOM uvaži ovakav argument)
- top 5 primjera UVAZENIH argumenata (mali nudge ka detekciji pattern-a)
- top 5 primjera ODBIJENIH argumenata (anti-pattern za false positive prevenciju)
- top 5 citiranih ZJN članaka (gdje god LLM uspio izvući)
- DKOM klase za citation seeding

Output: `data/02-dkom-odluke/rule_seeds.md` — markdown koji programer može
direktno koristiti kao spec za nova pravila.

Tipično workflow:
1. Pokreneš `extract_dkom.py` (Faza A — LLM ekstrakcija)
2. Pokreneš `analyze_dkom.py` (Faza B — agregat statistika)
3. Pokreneš `seed_dkom_rules.py` (Faza C — rule kandidati s primjerima)
4. Za top 10 tipova po frekvenciji, pišeš rule funkcije u
   `src/core/analyzer/don_rules.py` ili extendaš `mock._build_findings`
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

# Mapping kategorije → preporuka za detekciju (regex / RAG / LLM)
RULE_STRATEGY: dict[str, str] = {
    "brand_lock": "**Deterministički regex** — postoji brand lista, pravilo već implementirano (`_detect_brand_mentions`). Eventualno proširenje liste.",
    "kratki_rok": "**Deterministički** — parsing datuma + dni iz `deadline` blokova, usporedba s ZJN čl. 219-220 minimumima.",
    "vague_kriterij": "**Deterministički + LLM** — keyword check (subjektivni izrazi: 'kvaliteta', 'iskustvo' bez mjerljivih jedinica) + LLM judge.",
    "diskrim_uvjeti": "**Deterministički + RAG** — regex za uvjete sposobnosti + RAG retrieval DKOM presedana za usporedbu razmjernosti.",
    "neprecizna_specifikacija": "**LLM judge** — kontradiktornost ili nejasnoća zahtijeva razumijevanje konteksta, ne pattern matching.",
    "neispravna_grupacija": "**LLM judge** — analiza je li grupiranje predmeta nabave u skladu s funkcionalnošću.",
    "kriterij_odabira": "**Deterministički** — provjera težinskih udjela (zbroj = 100%), prisutnost mjerljivih sub-kriterija.",
    "ocjena_ponude": "**Izvan dosega DON checker-a** — ovo je problem post-DON (kako naručitelj ocijenio ponude). Relevantno za žalbe modul.",
    "espd_dokazi": "**Deterministički + LLM** — provjera traženja dokaza koji nisu razmjerni vrijednosti nabave.",
    "jamstvo": "**Deterministički** — iznos jamstva za ozbiljnost ponude (max 1.5% prema čl. 214 ZJN) + rok važnosti.",
    "trosak_postupka": "**Izvan dosega DON checker-a** — pitanje DKOM-a, ne DON-a.",
    "ostalo": "Heterogena kategorija — pregledati slučaj-po-slučaj, dodati nove tipove.",
}


def extract_citations_from_text(text: str) -> list[str]:
    """Pronađi reference na ZJN članke u tekstu (npr. 'članak 207. ZJN')."""
    pattern = r"(?:članka|članak|čl\.?)\s*(\d+)\.?\s*(?:stavka\s*\d+\.?)?\s*(?:ZJN|Zakona\s+o\s+javnoj\s+nabavi|Pravilnika)"
    hits = re.findall(pattern, text, re.IGNORECASE)
    return list(dict.fromkeys(hits))  # unique, order-preserved


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/02-dkom-odluke/extracted"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/02-dkom-odluke/rule_seeds.md"),
    )
    parser.add_argument("--min-cases", type=int, default=3, help="Skip tipove s <N pojava")
    args = parser.parse_args()

    decisions: list[dict[str, Any]] = []
    for jp in sorted(args.input.glob("*.json")):
        if jp.name == "all.jsonl":
            continue
        try:
            decisions.append(json.loads(jp.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            continue

    if not decisions:
        print("Nema ekstrahiranih odluka. Pokreni `extract_dkom.py` prvo.")
        return 1

    # Group claims by type
    type_claims: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for d in decisions:
        for c in d.get("claims", []):
            t = c.get("type")
            if not t:
                continue
            type_claims[t].append({
                "klasa": d["klasa"],
                "predmet": d.get("predmet", ""),
                "narucitelj": d.get("narucitelj_ime", ""),
                "vrsta_postupka": d.get("vrsta_postupka", ""),
                "outcome": d["outcome"],
                "argument": c.get("argument_zalitelja", ""),
                "obrana": c.get("obrana_narucitelja", ""),
                "verdict": c.get("dkom_verdict", ""),
                "obrazlozenje": c.get("dkom_obrazlozenje", ""),
                "violated_article": c.get("violated_article_claimed", ""),
                "datum_odluke": d.get("datum_odluke", ""),
            })

    # Sort types by frequency
    sorted_types = sorted(type_claims.items(), key=lambda x: -len(x[1]))

    lines: list[str] = []
    lines.append(f"# DKOM Rule Seeds — generirano iz {len(decisions)} odluka")
    lines.append("")
    lines.append(
        "Za svaki claim type, najčešće povrede + primjeri za rule implementaciju. "
        "Tipovi sortirani po frekvenciji pojavljivanja."
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    for t, items in sorted_types:
        if len(items) < args.min_cases:
            continue

        uvazen = [x for x in items if x["verdict"] == "uvazen"]
        djelomicno = [x for x in items if x["verdict"] == "djelomicno_uvazen"]
        odbijen = [x for x in items if x["verdict"] == "odbijen"]
        ne_razmatra = [x for x in items if x["verdict"] == "ne_razmatra"]

        razmatrano = len(uvazen) + len(djelomicno) + len(odbijen)
        uvazen_rate = (len(uvazen) + 0.5 * len(djelomicno)) / razmatrano if razmatrano else 0

        # Collect violated articles
        articles: Counter[str] = Counter()
        for x in uvazen + djelomicno:
            if x["violated_article"]:
                # Extract just article numbers
                nums = re.findall(r"\d+", x["violated_article"])
                for n in nums:
                    if 1 <= int(n) <= 500:  # ZJN ima ~470 članaka
                        articles[n] += 1

        lines.append(f"## `{t}` — {len(items)} pojava")
        lines.append("")
        lines.append(f"- **Uvazen rate:** {uvazen_rate * 100:.0f}% ({len(uvazen)} uvazenih, {len(djelomicno)} djelomično, {len(odbijen)} odbijenih, {len(ne_razmatra)} ne-razmatra)")
        lines.append("")
        lines.append(f"- **Strategija detekcije:** {RULE_STRATEGY.get(t, 'TBD')}")
        lines.append("")
        if articles:
            top_arts = ", ".join(f"čl. {a} ({n}×)" for a, n in articles.most_common(5))
            lines.append(f"- **Najčešće citirani članci ZJN:** {top_arts}")
            lines.append("")

        # Primjeri uvazenih (signal za detekciju)
        if uvazen:
            lines.append("### Primjeri UVAZENIH žalbi (signal za detekciju)")
            lines.append("")
            for x in uvazen[:5]:
                lines.append(f"**[{x['klasa']}]** — {x['predmet'][:80]}")
                lines.append(f"- *Naručitelj:* {x['narucitelj']}")
                lines.append(f"- *Argument žalitelja:* {x['argument'][:300]}")
                lines.append(f"- *DKOM:* {x['obrazlozenje'][:300]}")
                if x["violated_article"]:
                    lines.append(f"- *Prekršen:* {x['violated_article']}")
                lines.append("")

        # Primjeri odbijenih (anti-pattern za false positive)
        if odbijen:
            lines.append("### Primjeri ODBIJENIH žalbi (anti-pattern — DKOM kaže ovo NIJE povreda)")
            lines.append("")
            for x in odbijen[:3]:
                lines.append(f"**[{x['klasa']}]** — {x['predmet'][:80]}")
                lines.append(f"- *Argument žalitelja:* {x['argument'][:250]}")
                lines.append(f"- *DKOM zašto NE:* {x['obrazlozenje'][:300]}")
                lines.append("")

        lines.append("---")
        lines.append("")

    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Spremljeno u {args.output}")
    print(f"Procesuirano {len(decisions)} odluka, {sum(len(v) for v in type_claims.values())} claims-ova, {len([t for t,v in sorted_types if len(v) >= args.min_cases])} tipova s ≥{args.min_cases} pojava.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
