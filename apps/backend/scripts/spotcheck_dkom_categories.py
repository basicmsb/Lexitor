"""Manualni spot-check LLM kategorizacije DKOM claim-type-ova.

Prikazuje 50 random claims-ova jedan po jedan u terminalu:
- LLM-ova klasifikacija (npr. 'neprecizna_specifikacija')
- Argument žalitelja (LLM-ov sažetak)
- DKOM obrazloženje (LLM-ov sažetak)
- Opcionalno: cijeli tekst odluke u PDF-u (preko `open <pdf>`)

Korisnik tipka:
- y = točna kategorija
- n = pogrešna kategorija (treba pitati koja je prava)
- ? = ne mogu odlučiti
- q = quit

Output: `data/02-dkom-odluke/analysis/spotcheck_results.json` —
agregat koji pokazuje accuracy per claim_type.

Usage:
    python scripts/spotcheck_dkom_categories.py
    python scripts/spotcheck_dkom_categories.py --n 30
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

CLAIM_TYPES = [
    "brand_lock", "kratki_rok", "vague_kriterij", "diskrim_uvjeti",
    "neprecizna_specifikacija", "neispravna_grupacija", "kriterij_odabira",
    "ocjena_ponude", "espd_dokazi", "jamstvo", "trosak_postupka", "ostalo",
]


def load_all_claims(extracted_dir: Path) -> list[dict[str, Any]]:
    """Skupi sve claims-ove iz svih odluka u flat listu."""
    flat = []
    for jp in sorted(extracted_dir.glob("*.json")):
        if jp.name == "all.jsonl":
            continue
        try:
            data = json.loads(jp.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        klasa = data.get("klasa", "?")
        predmet = data.get("predmet", "")
        for c in data.get("claims", []):
            flat.append({
                "klasa": klasa,
                "predmet": predmet,
                "claim": c,
                "json_file": jp.name,
            })
    return flat


def print_claim(idx: int, total: int, entry: dict[str, Any]) -> None:
    c = entry["claim"]
    print()
    print("=" * 75)
    print(f"[{idx}/{total}]  {entry['klasa']}")
    print(f"Predmet: {entry['predmet'][:80]}")
    print("=" * 75)
    print(f"\n📋 LLM kategorija: \033[1;33m{c.get('type', '?')}\033[0m")
    print(f"📜 Verdict: {c.get('dkom_verdict', '?')}")
    if c.get("violated_article_claimed"):
        print(f"📖 Članak: {c['violated_article_claimed']}")
    print(f"\n💬 ARGUMENT ŽALITELJA:")
    print(f"   {c.get('argument_zalitelja', '?')[:500]}")
    if c.get("obrana_narucitelja"):
        print(f"\n🛡 OBRANA NARUČITELJA:")
        print(f"   {c['obrana_narucitelja'][:300]}")
    print(f"\n⚖ DKOM OBRAZLOŽENJE:")
    print(f"   {c.get('dkom_obrazlozenje', '?')[:400]}")
    print()


def prompt_user() -> tuple[str, str | None]:
    """Vrati (action, correct_category_if_wrong).
    action: 'y' / 'n' / '?' / 'q' / 's' (skip)
    """
    print("\033[1;36m")
    print("   [y] točno   [n] pogrešno   [?] ne znam   [s] skip   [q] quit")
    print("\033[0m", end="")
    ans = input("   ➜ ").strip().lower()
    if ans == "n":
        print(f"   Tipovi: {', '.join(CLAIM_TYPES)}")
        correct = input("   Prava kategorija: ").strip().lower()
        if correct in CLAIM_TYPES:
            return "n", correct
        elif correct:
            return "n", "ostalo"  # ako ne navede valjano, ostavi "ostalo"
        return "n", None
    return ans, None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=50, help="Koliko slučajeva")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/02-dkom-odluke/extracted"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/02-dkom-odluke/analysis/spotcheck_results.json"),
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    claims = load_all_claims(args.input)
    print(f"Učitano {len(claims)} claims-ova ukupno.")
    sample = random.sample(claims, min(args.n, len(claims)))
    print(f"Random sample: {len(sample)} claims-ova\n")

    results: list[dict[str, Any]] = []
    for i, entry in enumerate(sample, 1):
        print_claim(i, len(sample), entry)
        action, correct = prompt_user()
        if action == "q":
            print("Prekidam.")
            break
        results.append({
            "klasa": entry["klasa"],
            "json_file": entry["json_file"],
            "llm_category": entry["claim"].get("type"),
            "verdict": action,
            "correct_category": correct,
        })

    # Aggregate
    by_action: Counter[str] = Counter(r["verdict"] for r in results)
    print("\n" + "=" * 75)
    print("REZULTAT SPOT-CHECK-A")
    print("=" * 75)
    print(f"Procesuirano: {len(results)} / {len(sample)} sample-a")
    print(f"  Točno (y):    {by_action.get('y', 0)}")
    print(f"  Pogrešno (n): {by_action.get('n', 0)}")
    print(f"  Nesigurno (?):{by_action.get('?', 0)}")
    print(f"  Skip (s):     {by_action.get('s', 0)}")

    decided = by_action.get("y", 0) + by_action.get("n", 0)
    if decided > 0:
        accuracy = by_action.get("y", 0) / decided
        print(f"\nAccuracy (točno / decided): {accuracy*100:.0f}%")

    # Per-category accuracy
    cat_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"y": 0, "n": 0})
    for r in results:
        cat = r["llm_category"]
        if cat and r["verdict"] in ("y", "n"):
            cat_stats[cat][r["verdict"]] += 1
    print("\nPer-kategorija accuracy:")
    for cat in sorted(cat_stats, key=lambda c: -(cat_stats[c]["y"] + cat_stats[c]["n"])):
        s = cat_stats[cat]
        total = s["y"] + s["n"]
        acc = s["y"] / total * 100 if total else 0
        print(f"  {cat:30s}  {s['y']:2d} točno / {s['n']:2d} pogrešno  ({acc:.0f}% acc)")

    # Most-misclassified
    miscls: Counter[tuple[str, str]] = Counter()
    for r in results:
        if r["verdict"] == "n" and r["correct_category"]:
            miscls[(r["llm_category"], r["correct_category"])] += 1
    if miscls:
        print("\nNajčešći miss-mapping-i (LLM rekao → trebao reći):")
        for (llm, correct), n in miscls.most_common(10):
            print(f"  {llm} → {correct}  ({n}×)")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({
            "sample_size": len(sample),
            "processed": len(results),
            "actions": dict(by_action),
            "accuracy": (by_action.get("y", 0) / decided) if decided else None,
            "per_category": {cat: dict(s) for cat, s in cat_stats.items()},
            "miscls": [
                {"llm_said": k[0], "correct": k[1], "count": n}
                for k, n in miscls.most_common()
            ],
            "raw_results": results,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nSpremljeno u {args.output}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
