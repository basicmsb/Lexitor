"""Auto-detekcija pod-tipa DON dokumenta iz filename-a.

EOJN razdvaja DON-set u dvije kategorije:
1. Glavni DON dokumenti (Upute, Kriteriji, Općg podaci, Kriteriji ponude)
2. EOJN Dokumenti (Tehničke specifikacije, Troškovnik, Ugovor, Prilozi)

Plus, često postoji i projektantska dokumentacija (Tehnički opis, Glavni
projekt) priložena kao informativni materijal — to NIJE DON sam po sebi,
nego projektni dokument koji projektant priprema. Pravila tipa
`diskrim_uvjeti` (godine iskustva, Hrvatska komora, …) NE smiju se
primjenjivati na te projektantske dokumente — projektant je sam tu naveo
da je član komore, što je informacija o autoru, ne kriterij za ponuditelje.
"""
from __future__ import annotations

from enum import Enum


class DocumentSubtype(str, Enum):
    """Pod-tipovi DON dokumenta — koriste EOJN nazive iz strukture nabave.
    None / unknown = sva pravila se aplikuju."""

    UPUTE_PONUDITELJIMA = "upute_ponuditeljima"
    KRITERIJI_SUBJEKTA = "kriteriji_subjekta"  # kvalitativni odabir
    KRITERIJI_PONUDE = "kriteriji_ponude"  # ENP kriteriji
    OPCI_PODACI = "opci_podaci"
    TEHNICKE_SPECIFIKACIJE = "tehnicke_specifikacije"  # uključuje i Tehnički opis, Glavni projekt itd.
    TROSKOVNIK = "troskovnik"
    UGOVOR = "ugovor"
    OSTALO = "ostalo"


# EOJN nazivi za UI prikaz
SUBTYPE_LABELS: dict[str, str] = {
    DocumentSubtype.UPUTE_PONUDITELJIMA.value: "Upute za ponuditelje",
    DocumentSubtype.KRITERIJI_SUBJEKTA.value: "Kriteriji za kvalitativni odabir gospodarskog subjekta",
    DocumentSubtype.KRITERIJI_PONUDE.value: "Kriteriji za odabir ponude",
    DocumentSubtype.OPCI_PODACI.value: "Opći podaci o postupku nabave",
    DocumentSubtype.TEHNICKE_SPECIFIKACIJE.value: "Tehničke specifikacije",
    DocumentSubtype.TROSKOVNIK.value: "Troškovnik",
    DocumentSubtype.UGOVOR.value: "Prijedlog ugovora",
    DocumentSubtype.OSTALO.value: "Drugi dokument / izjava",
}


def detect_subtype_from_filename(filename: str) -> str | None:
    """Heuristika koja iz imena datoteke pogađa pod-tip.

    Vraća DocumentSubtype.value ili None ako se ne može detektirati.
    """
    if not filename:
        return None
    lower = filename.lower()
    # Skinuti ekstenziju za parsing
    lower = lower.rsplit(".", 1)[0]

    # Tehničke specifikacije — EOJN tu klasificira i projektantsku dokumentaciju
    # (Tehnički opis, Glavni projekt, Tablice tehničkih karakteristika) JEDNAKO
    # kao i DON tehničke specifikacije. Iste rule-ovi se primjenjuju.
    if any(
        kw in lower
        for kw in (
            "tehničke specifikacije",
            "tehnicke specifikacije",
            "tehnička specifikacija",
            "tehnicka specifikacija",
            "specifikacij",
            "glavni projekt",
            "gp_",
            "gp-",
            "tehnički opis",
            "tehnicki opis",
            "natječaj",
            "natjecaj",
            "tablice tehnič",
            "tablice tehnic",
            "izvedbeni projekt",
            "projektna dokumentacij",
        )
    ):
        return DocumentSubtype.TEHNICKE_SPECIFIKACIJE.value

    # Troškovnik
    if any(
        kw in lower
        for kw in (
            "troškovni",
            "troskovni",
            "ponudbeni list",
            "ponudbenilist",
            "troskovnik",
        )
    ):
        return DocumentSubtype.TROSKOVNIK.value

    # Upute za ponuditelje
    if "upute" in lower and "ponud" in lower:
        return DocumentSubtype.UPUTE_PONUDITELJIMA.value

    # Kriteriji — razlikovati subjekta (kvalitativni) od ponude (ENP)
    if "kriterij" in lower:
        if any(kw in lower for kw in ("kvalitativ", "subjekt", "gospodarsk")):
            return DocumentSubtype.KRITERIJI_SUBJEKTA.value
        if any(kw in lower for kw in ("ponud", "enp", "ekonomsk")):
            return DocumentSubtype.KRITERIJI_PONUDE.value
        return DocumentSubtype.KRITERIJI_SUBJEKTA.value  # default

    # Opći podaci
    if any(kw in lower for kw in ("opći podaci", "opci podaci", "opc. podaci", "općenito")):
        return DocumentSubtype.OPCI_PODACI.value

    # Ugovor
    if "ugovor" in lower:
        return DocumentSubtype.UGOVOR.value

    # Odgovori na pitanja, izjave, prilozi
    if any(
        kw in lower
        for kw in (
            "odgovor",
            "izjava",
            "prilog",
            "obrazac",
            "dodatak",
        )
    ):
        return DocumentSubtype.OSTALO.value

    return None
