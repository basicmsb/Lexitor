"""Regression tests for the analyzer's deterministic brand-mention check.

Brand detection (`_detect_brand_mentions`) flags rows where a manufacturer
name or "tipa kao …" phrase appears WITHOUT the legally-required "ili
jednakovrijedan/no/na/…" disclaimer. Croatian inflection is fiddly
(fleeting 'a': "jednakovrijedan" m. vs "jednakovrijedno" n.) so we pin
each form here."""

from __future__ import annotations

import pytest

from src.core.analyzer.mock import _build_findings, _detect_brand_mentions
from src.document_parser.base import ParsedItem


# ---------------------------------------------------------------------------
# Negative cases — proper disclaimer present, no flag


@pytest.mark.unit
@pytest.mark.parametrize(
    "text",
    [
        # Neuter form "jednakovrijedno" (literal ZJN wording)
        "Geotekstil tipa kao Sika 300 PP ili jednakovrijedno",
        # Masculine "jednakovrijedan" (with fleeting 'a')
        "tipa kao Sika geotekstil 300 PP ili jednakovrijedan. Obračun po m2",
        # Feminine "jednakovrijedna"
        "Sklopka tipa kao Schneider ili jednakovrijedna",
        # Genitive plural "jednakovrijednih"
        "Lampe tipa kao Helios ili jednakovrijednih",
        # Adverbial "jednakovrijedno" near brand
        "Daikin klima 5kW ili jednakovrijedno rješenje",
        # Different grammatical case "jednakovrijednu"
        "Knauf ploča ili jednakovrijednu",
    ],
)
def test_brand_with_equivalent_clause_passes(text: str) -> None:
    """Brand named, but with the 'ili jednakovrijedan/no/na/…' clause —
    no finding should fire."""
    assert _detect_brand_mentions(text) is None


# ---------------------------------------------------------------------------
# Positive cases — brand without disclaimer, must flag


@pytest.mark.unit
def test_brand_without_disclaimer_flags() -> None:
    text = "Geotekstil Sika 300 PP, debljine d=2mm"
    finding = _detect_brand_mentions(text)
    assert finding is not None
    explanation, suggestion = finding
    assert "Sika" in explanation
    assert "ili jednakovrijedno" in suggestion.lower() or "jednakovrijed" in suggestion.lower()


@pytest.mark.unit
def test_phrase_tipa_kao_without_disclaimer_flags() -> None:
    text = "Sklopka tipa kao Schneider EasyPact, 3-polna"
    finding = _detect_brand_mentions(text)
    assert finding is not None


@pytest.mark.unit
def test_no_brand_no_flag() -> None:
    text = "Iskop temelja u kategoriji III, ručno, m3"
    assert _detect_brand_mentions(text) is None


# ---------------------------------------------------------------------------
# Edge cases


@pytest.mark.unit
def test_disclaimer_far_from_brand_still_passes() -> None:
    """ZJN doesn't require physical proximity — the disclaimer can appear
    several sentences after the brand name, as long as it's in the same
    item description. We accept any 'ili jednakovrijed*' anywhere in
    the text."""
    text = (
        "Geotekstil Sika 300 PP, postava preko podloge u sloju d=20cm. "
        "Materijal mora biti UV stabilan i otporan na vlagu. "
        "Dopušten je i ekvivalent — ili jednakovrijedno."
    )
    assert _detect_brand_mentions(text) is None


@pytest.mark.unit
def test_empty_text_no_flag() -> None:
    assert _detect_brand_mentions("") is None
    assert _detect_brand_mentions(None) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# DON kindovi — brand_lock se mora aktivirati i za DON blokove,
# ne samo za troškovničke stavke (regresija nakon 2026-05-10).


@pytest.mark.unit
@pytest.mark.parametrize(
    "kind",
    ["paragraph", "requirement", "criterion", "list", "table"],
)
def test_brand_lock_fires_on_don_kinds(kind: str) -> None:
    """DON blokovi (paragraph/requirement/criterion/list/table) moraju
    pokrenuti brand_lock ako spominju marku bez „ili jednakovrijedno”."""
    item = ParsedItem(
        position=0,
        text="Ponuditelj mora dostaviti hidroizolaciju Sika 300 PP.",
        metadata={"kind": kind},
    )
    findings = _build_findings(item)
    brand_findings = [f for f in findings if f.get("kind") == "brand_lock"]
    assert len(brand_findings) == 1, f"brand_lock not fired for DON kind={kind}"
    assert "Sika" in brand_findings[0]["explanation"]


@pytest.mark.unit
def test_brand_lock_skips_section_header_and_deadline() -> None:
    """Naslov i deadline blokovi se preskaču — naslov nije specifikacija,
    a rokovi gotovo nikad ne spominju marku."""
    for kind in ("section_header", "deadline"):
        item = ParsedItem(
            position=0,
            text="Sika 300 — krajnji rok 15.06.2026.",
            metadata={"kind": kind},
        )
        findings = _build_findings(item)
        assert not [f for f in findings if f.get("kind") == "brand_lock"]


@pytest.mark.unit
def test_don_brand_with_disclaimer_passes() -> None:
    """DON requirement s legalnim disclaimerom — bez nalaza."""
    item = ParsedItem(
        position=0,
        text="Hidroizolacija tipa kao Sika 300 PP ili jednakovrijedna.",
        metadata={"kind": "requirement"},
    )
    findings = _build_findings(item)
    assert not [f for f in findings if f.get("kind") == "brand_lock"]
