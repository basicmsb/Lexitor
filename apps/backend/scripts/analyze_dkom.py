"""Faza B — taksonomija i agregatna statistika DKOM ekstrakcije.

Čita sve JSON fajlove iz `data/02-dkom-odluke/extracted/` (output Faze A) i
proizvodi:

1. Overall stats — count po outcome i godini
2. Vrsta postupka breakdown
3. Claim type frekvencija (top N) + per-type uvazen/odbijen rate
4. Vijeće member voting tendencije (po članu, po trio panelu)
5. Inkonzistentnost detector — isti claim type, suprotni verdikti
6. Citation network — najcitirane prethodne odluke
7. Repeat-offender naručitelji (najviše žalbi)

Output: `data/02-dkom-odluke/analysis/` direktorij + console summary.

Usage:
    python scripts/analyze_dkom.py                 # full analysis
    python scripts/analyze_dkom.py --top 20        # top 20 umjesto 10
"""
from __future__ import annotations

import argparse
import json
import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("analyze_dkom")


def load_decisions(directory: Path) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for jp in sorted(directory.glob("*.json")):
        if jp.name == "all.jsonl":
            continue
        try:
            decisions.append(json.loads(jp.read_text(encoding="utf-8")))
        except Exception as exc:  # noqa: BLE001
            log.warning("Skipping %s: %s", jp.name, exc)
    return decisions


def overall_stats(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    outcomes = Counter(d["outcome"] for d in decisions)
    years = Counter(
        (d.get("datum_odluke") or "")[:4] for d in decisions if d.get("datum_odluke")
    )
    vrste = Counter(d["vrsta_postupka"] for d in decisions)
    return {
        "total": len(decisions),
        "by_outcome": dict(outcomes.most_common()),
        "by_year": dict(sorted(years.items())),
        "by_vrsta": dict(vrste.most_common()),
    }


def claim_type_stats(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-claim-type: koliko puta se pojavio, uvazen/odbijen rate, primjeri."""
    type_counter: Counter[str] = Counter()
    type_verdicts: dict[str, Counter[str]] = defaultdict(Counter)
    type_examples: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    # (klasa, verdict, argument_zalitelja[:120])

    for d in decisions:
        klasa = d.get("klasa", "?")
        for c in d.get("claims", []):
            t = c.get("type", "ostalo")
            v = c.get("dkom_verdict", "ne_razmatra")
            arg = (c.get("argument_zalitelja") or "")[:120]
            type_counter[t] += 1
            type_verdicts[t][v] += 1
            if len(type_examples[t]) < 5:  # do 5 primjera per type
                type_examples[t].append((klasa, v, arg))

    result = {}
    for t, n in type_counter.most_common():
        verdicts = dict(type_verdicts[t])
        uvazen = verdicts.get("uvazen", 0) + verdicts.get("djelomicno_uvazen", 0) * 0.5
        razmatran = sum(v for k, v in verdicts.items() if k != "ne_razmatra")
        rate = uvazen / razmatran if razmatran > 0 else None
        result[t] = {
            "total": n,
            "verdicts": verdicts,
            "uvazen_rate": rate,
            "examples": type_examples[t],
        }
    return result


def member_stats(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    """Za svakog člana vijeća: koliko odluka, raspodjela ishoda."""
    member_cases: Counter[str] = Counter()
    member_outcomes: dict[str, Counter[str]] = defaultdict(Counter)
    member_claim_types: dict[str, Counter[str]] = defaultdict(Counter)

    for d in decisions:
        outcome = d["outcome"]
        for m in d.get("vijece", []):
            name = m["ime"]
            member_cases[name] += 1
            member_outcomes[name][outcome] += 1
            for c in d.get("claims", []):
                v = c.get("dkom_verdict", "ne_razmatra")
                t = c.get("type", "ostalo")
                if v == "uvazen":
                    member_claim_types[name][f"{t}:uvazen"] += 1
                elif v == "odbijen":
                    member_claim_types[name][f"{t}:odbijen"] += 1

    result = {}
    for name, n in member_cases.most_common():
        outs = dict(member_outcomes[name])
        uvazen_count = outs.get("usvojena", 0) + outs.get("djelomicno_usvojena", 0) * 0.5
        razmatran = n - outs.get("odbacena", 0) - outs.get("obustavljen", 0)
        rate = uvazen_count / razmatran if razmatran > 0 else None
        result[name] = {
            "total_cases": n,
            "outcomes": outs,
            "usvojen_rate": rate,
        }
    return result


def panel_stats(decisions: list[dict[str, Any]], min_cases: int = 3) -> dict[str, Any]:
    """Trio panel statistika — koliko puta su isti 3 člana sjedili zajedno
    i kako su odlučili."""
    panel_cases: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for d in decisions:
        members = tuple(sorted(m["ime"] for m in d.get("vijece", [])))
        if len(members) >= 2:
            panel_cases[members].append(d)

    result = {}
    for trio, cases in sorted(panel_cases.items(), key=lambda x: -len(x[1])):
        if len(cases) < min_cases:
            continue
        outs = Counter(c["outcome"] for c in cases)
        uvazen = outs.get("usvojena", 0) + outs.get("djelomicno_usvojena", 0) * 0.5
        razmatran = sum(v for k, v in outs.items() if k not in ("odbacena", "obustavljen"))
        rate = uvazen / razmatran if razmatran > 0 else None
        result[" + ".join(trio)] = {
            "total_cases": len(cases),
            "outcomes": dict(outs),
            "usvojen_rate": rate,
        }
    return result


def inconsistency_detector(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pronađi slučajeve gdje isti claim type ima suprotne verdikte
    (uvazen vs odbijen). Indikator nedosljedne prakse."""
    # Group by claim type → list of (klasa, verdict, argument)
    by_type: dict[str, list[tuple[str, str, str, list[str]]]] = defaultdict(list)
    for d in decisions:
        klasa = d.get("klasa", "?")
        members = [m["ime"] for m in d.get("vijece", [])]
        for c in d.get("claims", []):
            t = c.get("type")
            v = c.get("dkom_verdict")
            arg = (c.get("argument_zalitelja") or "")[:200]
            if t and v in ("uvazen", "odbijen"):
                by_type[t].append((klasa, v, arg, members))

    result = []
    for t, items in by_type.items():
        uvazen_items = [x for x in items if x[1] == "uvazen"]
        odbijen_items = [x for x in items if x[1] == "odbijen"]
        if uvazen_items and odbijen_items:
            result.append({
                "type": t,
                "uvazen_count": len(uvazen_items),
                "odbijen_count": len(odbijen_items),
                "uvazen_rate": len(uvazen_items) / (len(uvazen_items) + len(odbijen_items)),
                "uvazen_examples": [
                    {"klasa": x[0], "argument": x[2], "vijece": x[3]} for x in uvazen_items[:3]
                ],
                "odbijen_examples": [
                    {"klasa": x[0], "argument": x[2], "vijece": x[3]} for x in odbijen_items[:3]
                ],
            })
    result.sort(key=lambda x: -(x["uvazen_count"] + x["odbijen_count"]))
    return result


def citation_network(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    cite_counter: Counter[str] = Counter()
    cite_sources: dict[str, list[str]] = defaultdict(list)
    for d in decisions:
        for cited in d.get("citirane_prethodne_odluke", []):
            cite_counter[cited] += 1
            cite_sources[cited].append(d["klasa"])
    top = {}
    for klasa, n in cite_counter.most_common(20):
        top[klasa] = {
            "cited_by_count": n,
            "cited_by": cite_sources[klasa][:5],
        }
    return top


def repeat_offenders(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    nar_counter: Counter[str] = Counter()
    nar_outcomes: dict[str, Counter[str]] = defaultdict(Counter)
    for d in decisions:
        n = d.get("narucitelj_ime")
        if not n:
            continue
        nar_counter[n] += 1
        nar_outcomes[n][d["outcome"]] += 1
    result = {}
    for name, count in nar_counter.most_common(15):
        result[name] = {
            "total_cases": count,
            "outcomes": dict(nar_outcomes[name]),
        }
    return result


def print_summary(analysis: dict[str, Any], top: int) -> None:
    print()
    print("=" * 70)
    print("DKOM ANALIZA — agregatna statistika")
    print("=" * 70)
    o = analysis["overall"]
    print(f"\nUkupno odluka: {o['total']}")
    print(f"\nPo ishodu:")
    for k, v in o["by_outcome"].items():
        pct = v / o["total"] * 100
        print(f"  {k:25s} {v:5d}  ({pct:.1f}%)")
    print(f"\nPo godini:")
    for k, v in o["by_year"].items():
        print(f"  {k:25s} {v:5d}")
    print(f"\nPo vrsti postupka:")
    for k, v in o["by_vrsta"].items():
        print(f"  {k:25s} {v:5d}")

    print(f"\n{'=' * 70}\nClaim type frekvencija (top {top}):")
    for t, info in list(analysis["claim_types"].items())[:top]:
        rate_str = f"{info['uvazen_rate']*100:.0f}%" if info["uvazen_rate"] is not None else "-"
        print(f"\n  [{t}]  {info['total']} pojava, uvazen rate: {rate_str}")
        print(f"    verdicts: {info['verdicts']}")
        for klasa, v, arg in info["examples"][:2]:
            print(f"    • {klasa} [{v}]: {arg[:100]}")

    print(f"\n{'=' * 70}\nNajaktivniji članovi vijeća (top {top}):")
    for name, info in list(analysis["members"].items())[:top]:
        rate = f"{info['usvojen_rate']*100:.0f}%" if info["usvojen_rate"] is not None else "-"
        print(f"  {name:35s} {info['total_cases']:4d} cases  (usvojen rate: {rate})")
        print(f"    outcomes: {info['outcomes']}")

    print(f"\n{'=' * 70}\nNajčešći trio paneli (≥3 cases):")
    for trio, info in list(analysis["panels"].items())[:top]:
        rate = f"{info['usvojen_rate']*100:.0f}%" if info["usvojen_rate"] is not None else "-"
        print(f"\n  {trio}")
        print(f"    {info['total_cases']} cases, usvojen rate: {rate}, ishodi: {info['outcomes']}")

    print(f"\n{'=' * 70}\nInkonzistentnost (isti claim type, suprotni verdikti):")
    for entry in analysis["inconsistencies"][:top]:
        print(f"\n  [{entry['type']}]  uvazenih: {entry['uvazen_count']}, odbijenih: {entry['odbijen_count']}")
        print(f"    uvazen rate: {entry['uvazen_rate']*100:.0f}%")
        if entry["uvazen_examples"]:
            ex = entry["uvazen_examples"][0]
            print(f"    UVAZEN  primjer: {ex['klasa']}: {ex['argument'][:120]}")
        if entry["odbijen_examples"]:
            ex = entry["odbijen_examples"][0]
            print(f"    ODBIJEN primjer: {ex['klasa']}: {ex['argument'][:120]}")

    print(f"\n{'=' * 70}\nCitation network — najcitiranije prethodne odluke (top 10):")
    for klasa, info in list(analysis["citations"].items())[:10]:
        print(f"  {klasa}  citirano {info['cited_by_count']}× (od strane: {', '.join(info['cited_by'][:3])})")

    print(f"\n{'=' * 70}\nRepeat offender naručitelji (top 10):")
    for nar, info in list(analysis["repeat_offenders"].items())[:10]:
        print(f"  {nar:50s} {info['total_cases']:4d}  {info['outcomes']}")

    print()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=15, help="Top N stavki u svakoj kategoriji")
    parser.add_argument("--input", type=Path, default=Path("data/02-dkom-odluke/extracted"))
    parser.add_argument("--output", type=Path, default=Path("data/02-dkom-odluke/analysis"))
    args = parser.parse_args()

    decisions = load_decisions(args.input)
    log.info("Učitano %d ekstrahiranih odluka", len(decisions))
    if not decisions:
        log.error("Nema odluka — pokreni prvo `extract_dkom.py`")
        return 1

    analysis = {
        "overall": overall_stats(decisions),
        "claim_types": claim_type_stats(decisions),
        "members": member_stats(decisions),
        "panels": panel_stats(decisions),
        "inconsistencies": inconsistency_detector(decisions),
        "citations": citation_network(decisions),
        "repeat_offenders": repeat_offenders(decisions),
    }

    args.output.mkdir(parents=True, exist_ok=True)
    output_file = args.output / "summary.json"
    output_file.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.info("Spremljeno u %s", output_file)

    print_summary(analysis, args.top)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
