"""Stvarna analiza dosljednosti DKOM članova — per-claim-type × per-član
matrica.

Agregat "usvojen rate" (npr. Antolković 62%, Kuhar 40%) miješa različite
tipove povreda — neke su strože, neke meke. Razlika u rate-u može doći iz:
1. Pristrasnosti člana
2. Selection bias (case assignment nije random)
3. Različite vrste predmeta

OVA SKRIPTA radi pravu mjeru dosljednosti:
- Za svaki claim_type, za svaki član vijeća: uvazen rate u tom tipu
- Standardna devijacija po claim_type-u među članovima → veća deviacija = veća
  nedosljednost
- Identificira **outlier-e** — članove čiji rate značajno odstupa od prosjeka

Output: konzolni izvještaj + JSON spremljen.
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/02-dkom-odluke/extracted"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/02-dkom-odluke/analysis/consistency.json"),
    )
    parser.add_argument("--min-cases-member", type=int, default=20)
    parser.add_argument("--min-cases-claim-type", type=int, default=30)
    parser.add_argument("--outlier-threshold-pp", type=int, default=20,
                        help="Outlier ako rate odstupa od prosjeka za N pp")
    args = parser.parse_args()

    decisions: list[dict[str, Any]] = []
    for jp in sorted(args.input.glob("*.json")):
        if jp.name == "all.jsonl":
            continue
        try:
            decisions.append(json.loads(jp.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            continue

    print(f"Učitano {len(decisions)} odluka\n")

    # Per-member, per-claim-type stats
    # struct: stats[member][claim_type] = {"uvazen": n, "odbijen": n, "djelomicno": n}
    stats: dict[str, dict[str, Counter[str]]] = defaultdict(
        lambda: defaultdict(Counter)
    )
    member_totals: Counter[str] = Counter()
    claim_type_totals: Counter[str] = Counter()

    for d in decisions:
        members = [m["ime"] for m in d.get("vijece", [])]
        for c in d.get("claims", []):
            ct = c.get("type")
            v = c.get("dkom_verdict")
            if not ct or not v:
                continue
            for member in members:
                stats[member][ct][v] += 1
                member_totals[member] += 1
            claim_type_totals[ct] += 1

    # Filter to busy members + popular claim types
    busy_members = {m for m, n in member_totals.items() if n >= args.min_cases_member}
    popular_types = {ct for ct, n in claim_type_totals.items() if n >= args.min_cases_claim_type}

    print(f"Aktivnih članova (≥{args.min_cases_member} claims): {len(busy_members)}")
    print(f"Top claim type-ova (≥{args.min_cases_claim_type} pojava): {len(popular_types)}\n")

    # Compute uvazen rate per (member, claim_type)
    # Rate = (uvazen + 0.5 * djelomicno_uvazen) / (uvazen + djelomicno + odbijen)
    # Ignoriramo ne_razmatra jer nema verdikta
    rates: dict[str, dict[str, float | None]] = defaultdict(dict)
    counts: dict[str, dict[str, int]] = defaultdict(dict)
    for member in busy_members:
        for ct in popular_types:
            vd = stats[member][ct]
            uvazen = vd.get("uvazen", 0)
            djel = vd.get("djelomicno_uvazen", 0)
            odbijen = vd.get("odbijen", 0)
            n = uvazen + djel + odbijen
            if n >= 5:  # need at least 5 cases per cell for meaningful rate
                rate = (uvazen + 0.5 * djel) / n
                rates[member][ct] = rate
                counts[member][ct] = n
            else:
                rates[member][ct] = None
                counts[member][ct] = n

    # Per-claim-type: prosjek rate-a + std deviacija + outlier check
    print("=" * 80)
    print("DOSLJEDNOST PO CLAIM TYPE-U")
    print("=" * 80)

    inconsistencies: list[dict[str, Any]] = []

    sorted_types = sorted(popular_types, key=lambda ct: -claim_type_totals[ct])
    for ct in sorted_types:
        ct_rates = [
            (m, rates[m][ct], counts[m][ct])
            for m in busy_members
            if rates[m][ct] is not None
        ]
        if len(ct_rates) < 3:
            continue
        rate_values = [r for _, r, _ in ct_rates]
        mean = statistics.mean(rate_values)
        stdev = statistics.stdev(rate_values) if len(rate_values) > 1 else 0

        # Sort by rate
        ct_rates.sort(key=lambda x: -x[1])

        print(f"\n[{ct}] {claim_type_totals[ct]} ukupnih claim-ova")
        print(f"  Prosjek rate: {mean*100:.0f}%, std dev: {stdev*100:.0f}pp")
        print(f"  Raspon: {ct_rates[-1][1]*100:.0f}% — {ct_rates[0][1]*100:.0f}% ({(ct_rates[0][1]-ct_rates[-1][1])*100:.0f}pp razlika)")
        print(f"  Per član (sortirano od najpopustljivijeg ka najstrožem):")
        for m, r, n in ct_rates:
            deviation = (r - mean) * 100
            marker = ""
            if abs(deviation) >= args.outlier_threshold_pp:
                marker = " ⚠ OUTLIER"
            print(f"    {m:30s} {r*100:5.0f}%  ({n} cases, {deviation:+.0f}pp od prosjeka){marker}")

        # Identify outlier pairs (member1 vs member2 in same claim type)
        outliers_in_type = []
        for i, (m1, r1, n1) in enumerate(ct_rates):
            for m2, r2, n2 in ct_rates[i + 1:]:
                diff = abs(r1 - r2) * 100
                if diff >= 25:  # 25pp razlika = vrijedi prijaviti
                    outliers_in_type.append({
                        "member_high": m1, "rate_high": r1, "n_high": n1,
                        "member_low": m2, "rate_low": r2, "n_low": n2,
                        "diff_pp": diff,
                    })
        if outliers_in_type:
            inconsistencies.extend(
                {**o, "claim_type": ct} for o in outliers_in_type
            )

    # Summary — top inconsistencies
    print("\n\n" + "=" * 80)
    print("TOP INKONZISTENTNOSTI (parovi članova s razlikom ≥25pp u istom claim_type-u)")
    print("=" * 80)

    inconsistencies.sort(key=lambda x: -x["diff_pp"])
    for inc in inconsistencies[:25]:
        print(f"\n  [{inc['claim_type']}] {inc['diff_pp']:.0f}pp razlika:")
        print(f"    {inc['member_high']:30s} {inc['rate_high']*100:.0f}% uvazeno ({inc['n_high']} cases)")
        print(f"    {inc['member_low']:30s} {inc['rate_low']*100:.0f}% uvazeno ({inc['n_low']} cases)")

    # Per-member: cross-type std dev (member-level consistency)
    print("\n\n" + "=" * 80)
    print("PER-ČLAN: KOLIKO SU SAMI U SEBI DOSLJEDNI")
    print("=" * 80)
    print("(std dev rate-a kroz claim_type-ove — visok = član različito presuđuje na različite tipove povreda)")
    print()
    member_stdevs = []
    for member in busy_members:
        rs = [r for r in rates[member].values() if r is not None]
        if len(rs) >= 3:
            mu = statistics.mean(rs)
            sd = statistics.stdev(rs)
            member_stdevs.append((member, mu, sd, len(rs)))
    member_stdevs.sort(key=lambda x: -x[2])
    for member, mu, sd, n in member_stdevs:
        print(f"  {member:30s} prosjek {mu*100:.0f}%, varijacija {sd*100:.0f}pp ({n} type-ova)")

    # Save JSON
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "decisions_total": len(decisions),
        "members_analyzed": sorted(busy_members),
        "claim_types_analyzed": sorted(popular_types),
        "rates_per_member_per_type": {
            m: {ct: rates[m][ct] for ct in popular_types if rates[m][ct] is not None}
            for m in busy_members
        },
        "counts_per_member_per_type": {
            m: {ct: counts[m][ct] for ct in popular_types if counts[m][ct] >= 5}
            for m in busy_members
        },
        "inconsistencies": inconsistencies,
        "member_self_consistency": [
            {"member": m, "mean_rate": mu, "stdev_pp": sd * 100, "n_types": n}
            for m, mu, sd, n in member_stdevs
        ],
    }
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n\nSpremljeno u {args.output}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
