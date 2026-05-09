"""Regression tests for the deterministic per-item rules.

Each rule lives in src/core/analyzer/rules.py and returns a list of
findings — possibly empty. We pin the most useful trigger conditions
here so a future tweak can't silently regress the user-facing
behaviour."""

from __future__ import annotations

import pytest

from src.core.analyzer.rules import (
    rule_missing_cijena,
    rule_missing_jm,
    rule_missing_kol,
    rule_missing_opis,
    rule_zero_unit_price,
    run_per_row_rules,
)
from src.models import AnalysisItemStatus, TroskovnikType


# ---------------------------------------------------------------------------
# Missing JM


@pytest.mark.unit
def test_missing_jm_fires_when_kol_present_but_jm_empty() -> None:
    meta = {
        "math_rows": [
            {"row": 5, "kol": 100, "cijena": 50, "jm": ""},
        ]
    }
    findings = rule_missing_jm("Iskop temelja", meta)
    assert len(findings) == 1
    assert findings[0]["kind"] == "missing_jm"
    assert findings[0]["status"] == "warn"


@pytest.mark.unit
def test_missing_jm_no_fire_when_jm_present() -> None:
    meta = {
        "math_rows": [
            {"row": 5, "kol": 100, "cijena": 50, "jm": "m3"},
        ]
    }
    assert rule_missing_jm("Iskop temelja", meta) == []


@pytest.mark.unit
def test_missing_jm_no_fire_when_no_math_values() -> None:
    """A row with only opis text (no kol/cijena) shouldn't fire because
    it might be a header line, not a real math row missing data."""
    meta = {
        "math_rows": [
            {"row": 5, "kol": None, "cijena": None, "jm": "", "position_label": "Stavka"},
        ]
    }
    assert rule_missing_jm("Test", meta) == []


# ---------------------------------------------------------------------------
# Missing kol / cijena


@pytest.mark.unit
def test_missing_kol_fires_when_cijena_present_but_kol_empty() -> None:
    meta = {"math_rows": [{"row": 5, "kol": "", "cijena": 50, "jm": "m3"}]}
    findings = rule_missing_kol("Iskop", meta)
    assert len(findings) == 1
    assert findings[0]["kind"] == "missing_kol"


@pytest.mark.unit
def test_missing_cijena_fires_when_kol_present_but_cijena_empty() -> None:
    meta = {"math_rows": [{"row": 5, "kol": 100, "cijena": None, "jm": "m3"}]}
    findings = rule_missing_cijena("Iskop", meta)
    assert len(findings) == 1
    assert findings[0]["kind"] == "missing_cijena"
    # Default (no type) → WARN
    assert findings[0]["status"] == AnalysisItemStatus.WARN.value


@pytest.mark.unit
def test_missing_cijena_no_fire_for_ponudbeni_troskovnik() -> None:
    """Ponudbeni: prazna jedinična cijena je OČEKIVANA (ponuditelj je
    popunjava). Nije nalaz."""
    meta = {"math_rows": [{"row": 5, "kol": 100, "cijena": None, "jm": "m3"}]}
    findings = rule_missing_cijena("Iskop", meta, TroskovnikType.PONUDBENI)
    assert findings == []


@pytest.mark.unit
def test_missing_cijena_fail_for_procjena_troskovnik() -> None:
    """Procjena: cijena MORA biti popunjena → eskalira u FAIL."""
    meta = {"math_rows": [{"row": 5, "kol": 100, "cijena": None, "jm": "m3"}]}
    findings = rule_missing_cijena("Iskop", meta, TroskovnikType.PROCJENA)
    assert len(findings) == 1
    assert findings[0]["status"] == AnalysisItemStatus.FAIL.value


@pytest.mark.unit
def test_zero_unit_price_no_fire_for_ponudbeni_troskovnik() -> None:
    meta = {"math_rows": [{"row": 5, "kol": 100, "cijena": 0, "jm": "m3"}]}
    findings = rule_zero_unit_price("Iskop", meta, TroskovnikType.PONUDBENI)
    assert findings == []


@pytest.mark.unit
def test_run_per_row_rules_respects_ponudbeni_type() -> None:
    """run_per_row_rules prosljeđuje troskovnik_type pravilima koja ovise
    o njemu. Ponudbeni: missing_cijena + zero_unit_price ne fire-aju."""
    meta = {"math_rows": [{"row": 5, "kol": 100, "cijena": None, "jm": "m3"}]}
    findings = run_per_row_rules(
        "Iskop temelja u zemlji III ktg",
        meta,
        TroskovnikType.PONUDBENI,
    )
    kinds = {f["kind"] for f in findings}
    assert "missing_cijena" not in kinds
    assert "zero_unit_price" not in kinds


# ---------------------------------------------------------------------------
# Missing opis


@pytest.mark.unit
def test_missing_opis_fires_when_no_text_or_position_label() -> None:
    meta = {
        "math_rows": [
            {"row": 5, "kol": 100, "cijena": 50, "jm": "m3", "position_label": ""},
        ]
    }
    findings = rule_missing_opis("", meta)
    assert len(findings) == 1
    assert findings[0]["status"] == "fail"


@pytest.mark.unit
def test_missing_opis_no_fire_when_position_label_present() -> None:
    meta = {
        "math_rows": [
            {"row": 5, "kol": 100, "cijena": 50, "jm": "m3", "position_label": "Beton C25/30"},
        ]
    }
    assert rule_missing_opis("", meta) == []


@pytest.mark.unit
def test_missing_opis_no_fire_when_text_present() -> None:
    meta = {"math_rows": [{"row": 5, "kol": 100, "cijena": 50, "jm": "m3"}]}
    assert rule_missing_opis("Iskop temelja u zemlji III ktg", meta) == []


# ---------------------------------------------------------------------------
# Zero unit price


@pytest.mark.unit
def test_zero_unit_price_fires_when_kol_positive_but_cijena_zero() -> None:
    meta = {"math_rows": [{"row": 5, "kol": 100, "cijena": 0, "jm": "m3"}]}
    findings = rule_zero_unit_price("Iskop", meta)
    assert len(findings) == 1
    assert findings[0]["kind"] == "zero_unit_price"


@pytest.mark.unit
def test_zero_unit_price_no_fire_when_cijena_nonzero() -> None:
    meta = {"math_rows": [{"row": 5, "kol": 100, "cijena": 50, "jm": "m3"}]}
    assert rule_zero_unit_price("Iskop", meta) == []


# ---------------------------------------------------------------------------
# run_per_row_rules — integration


@pytest.mark.unit
def test_run_per_row_rules_aggregates_multiple_findings() -> None:
    """A stavka can trigger multiple rules at once — they should all
    be returned in the findings list."""
    meta = {
        "math_rows": [
            {"row": 5, "kol": 100, "cijena": 0, "jm": ""},  # missing_jm + zero_unit_price
        ]
    }
    findings = run_per_row_rules("Iskop", meta)
    kinds = {f["kind"] for f in findings}
    assert "missing_jm" in kinds
    assert "zero_unit_price" in kinds


@pytest.mark.unit
def test_run_per_row_rules_no_fire_on_clean_item() -> None:
    meta = {
        "math_rows": [
            {"row": 5, "kol": 100, "cijena": 50, "jm": "m3", "iznos": 5000},
        ]
    }
    findings = run_per_row_rules(
        "Strojni iskop temelja u zemlji III ktg s utovarom u ručna kolica",
        meta,
    )
    assert findings == []


@pytest.mark.unit
def test_run_per_row_rules_handles_empty_metadata() -> None:
    """Should not crash on items with no metadata or empty math_rows.
    Long-enough text avoids the vague_opis trigger."""
    long_ok_text = "Strojni iskop temelja u zemlji III ktg"
    assert run_per_row_rules(long_ok_text, None) == []
    assert run_per_row_rules(long_ok_text, {}) == []
    assert run_per_row_rules(long_ok_text, {"math_rows": []}) == []
