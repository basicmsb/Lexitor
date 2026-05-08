"""Regression tests for the analyzer's deterministic brand-mention check.

Brand detection (`_detect_brand_mentions`) flags rows where a manufacturer
name or "tipa kao …" phrase appears WITHOUT the legally-required "ili
jednakovrijedan/no/na/…" disclaimer. Croatian inflection is fiddly
(fleeting 'a': "jednakovrijedan" m. vs "jednakovrijedno" n.) so we pin
each form here."""

from __future__ import annotations

import pytest

from src.core.analyzer.mock import _detect_brand_mentions


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
