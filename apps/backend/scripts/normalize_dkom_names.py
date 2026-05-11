"""Normalizacija imena članova DKOM vijeća u extracted dataset-u.

Problem: LLM ekstrakcija često vrati varijante istih imena (npr. zbog padeža u
PDF-u koji LLM nije savršeno normalizirao u nominativ):
- "Gordana Klišanić" + "Gordan Klišanić" = ista osoba (LLM krivo riješio padež)
- "Marijana Gortan" + "Marijana Gortan Krnić" = ista osoba (LLM izostavio prezime)

Strategija:
1. Explicitne mape (user-defined) — primjenjuju se 100%
2. Fuzzy auto-detection (Levenshtein <2 + prefix match) — sugerira, user potvrđuje
3. Apply: rewrite JSON-e i ponovno generiraj all.jsonl

Usage:
    python scripts/normalize_dkom_names.py --dry-run     # samo prikaži što bi mijenjao
    python scripts/normalize_dkom_names.py --apply       # stvarno mijenja
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Explicitne mape (user-confirmed)
# Format: "varijanta" → "kanonska forma"

EXPLICIT_MAPPINGS: dict[str, str] = {
    # User-potvrđeno 2026-05-11:
    "Gordana Klišanić": "Gordan Klišanić",
    "Marijana Gortan": "Marijana Gortan Krnić",
    "Sanja Badrov": "Sanja Badrov Ranić",
    "Jasnica Loze": "Jasnica Lozo",  # genitivni padež → nominativ
}


def levenshtein(a: str, b: str) -> int:
    """Klasični Levenshtein distance — broj substitucija/insertions/deletions."""
    if len(a) < len(b):
        return levenshtein(b, a)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            insertions = prev[j + 1] + 1
            deletions = curr[j] + 1
            substitutions = prev[j] + (ca != cb)
            curr.append(min(insertions, deletions, substitutions))
        prev = curr
    return prev[-1]


def is_likely_same_person(name_a: str, name_b: str) -> bool:
    """Heuristika: jesu li dvije varijante imena vjerojatno ista osoba?

    Kriteriji:
    1. Levenshtein <= 2 (npr. 'Gordana' vs 'Gordan' — 1 char razlika)
    2. ILI: jedno ime je prefix drugog (npr. 'Marijana Gortan' vs 'Marijana Gortan Krnić')
    3. Prvo slovo prezimena se mora poklapati (sprječava 'Iva Ana' vs 'Iva Maja')
    """
    if name_a == name_b:
        return False
    # Prefix match (jedno je kraće verzija drugog)
    if name_a.startswith(name_b) or name_b.startswith(name_a):
        diff = abs(len(name_a) - len(name_b))
        if diff > 5 and diff < 30:  # razumna razlika u dužini
            return True
    # Levenshtein blizak
    if levenshtein(name_a.lower(), name_b.lower()) <= 2:
        # Provjeri da prezimena počinju isto (zadnja riječ)
        last_a = name_a.split()[-1].lower() if name_a.split() else ""
        last_b = name_b.split()[-1].lower() if name_b.split() else ""
        if last_a[:3] == last_b[:3]:  # prva 3 slova prezimena
            return True
    return False


def collect_all_names(extracted_dir: Path) -> Counter[str]:
    """Skupi sve unique imena članova vijeća iz svih JSON-a."""
    counter: Counter[str] = Counter()
    for jp in extracted_dir.glob("*.json"):
        if jp.name == "all.jsonl":
            continue
        try:
            data = json.loads(jp.read_text(encoding="utf-8"))
            for m in data.get("vijece", []):
                counter[m["ime"]] += 1
        except Exception:  # noqa: BLE001
            continue
    return counter


def suggest_merges(names: Counter[str]) -> list[tuple[str, str, int]]:
    """Predloži parove (varijanta, kanonska, n_pojava_varijante)."""
    suggestions: list[tuple[str, str, int]] = []
    name_list = list(names.keys())
    seen_pairs: set[tuple[str, str]] = set()
    for i, name_a in enumerate(name_list):
        for name_b in name_list[i + 1 :]:
            pair = tuple(sorted([name_a, name_b]))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            if is_likely_same_person(name_a, name_b):
                # Kanonska je ta s više pojava (ili duža)
                if names[name_a] > names[name_b]:
                    canon, variant = name_a, name_b
                elif names[name_b] > names[name_a]:
                    canon, variant = name_b, name_a
                else:
                    # Tie: duža je kanonska (ima više konteksta)
                    canon, variant = (name_a, name_b) if len(name_a) > len(name_b) else (name_b, name_a)
                suggestions.append((variant, canon, names[variant]))
    suggestions.sort(key=lambda x: -x[2])
    return suggestions


def apply_normalization(
    extracted_dir: Path, mappings: dict[str, str], dry_run: bool
) -> tuple[int, int]:
    """Apply mappings na sve JSON-e. Vrati (files_changed, total_replacements)."""
    files_changed = 0
    total_repl = 0
    for jp in sorted(extracted_dir.glob("*.json")):
        if jp.name == "all.jsonl":
            continue
        try:
            data = json.loads(jp.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        changed = False
        for m in data.get("vijece", []):
            orig = m["ime"]
            if orig in mappings:
                m["ime"] = mappings[orig]
                total_repl += 1
                changed = True
        if changed:
            files_changed += 1
            if not dry_run:
                jp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return files_changed, total_repl


def regenerate_aggregate(extracted_dir: Path) -> int:
    """Regeneriraj all.jsonl iz pojedinacnih JSON-a."""
    out = extracted_dir / "all.jsonl"
    n = 0
    with out.open("w", encoding="utf-8") as f:
        for jp in sorted(extracted_dir.glob("*.json")):
            if jp.name == "all.jsonl":
                continue
            try:
                data = json.loads(jp.read_text(encoding="utf-8"))
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
                n += 1
            except Exception:  # noqa: BLE001
                continue
    return n


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/02-dkom-odluke/extracted"))
    parser.add_argument("--dry-run", action="store_true", help="Samo prikaži, nemoj mijenjati")
    parser.add_argument("--apply", action="store_true", help="Apply mappings na fajlove")
    parser.add_argument(
        "--include-suggestions",
        action="store_true",
        help="Uz explicitne, primijeni i auto-suggested merge-eve",
    )
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Pokreni s --dry-run da vidiš što bi se promijenilo, ili --apply da promijeni.")
        return 1

    names = collect_all_names(args.input)
    print(f"Učitano {sum(names.values())} pojava imena, {len(names)} unique.\n")

    # 1. Auto-suggest fuzzy duplicates
    print("=" * 70)
    print("AUTO-DETECTED MOGUĆI DUPLIKATI (fuzzy match)")
    print("=" * 70)
    suggestions = suggest_merges(names)
    if not suggestions:
        print("  (nijedan kandidat za auto-merge)")
    for variant, canon, n in suggestions:
        marker = "✓ već u explicit" if variant in EXPLICIT_MAPPINGS else "?"
        print(f"  {marker}  '{variant}' ({n}×) → '{canon}' ({names[canon]}×)")
    print()

    # 2. Final mappings
    final_mappings = dict(EXPLICIT_MAPPINGS)
    if args.include_suggestions:
        for variant, canon, _ in suggestions:
            if variant not in final_mappings:
                final_mappings[variant] = canon

    print("=" * 70)
    print(f"PRIMJENJIVAT ĆU {len(final_mappings)} MAPPINGS:")
    print("=" * 70)
    for variant, canon in final_mappings.items():
        n = names.get(variant, 0)
        print(f"  '{variant}' ({n}×) → '{canon}'")
    print()

    if args.dry_run:
        print("DRY RUN — nije primijenjeno. Pokreni s --apply da stvarno promijeniš.")
        return 0

    files_changed, total_repl = apply_normalization(args.input, final_mappings, dry_run=False)
    print(f"✓ Promijenjeno {total_repl} pojava u {files_changed} fajlova.")

    n_aggregated = regenerate_aggregate(args.input)
    print(f"✓ Regeneriran all.jsonl ({n_aggregated} odluka).")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
