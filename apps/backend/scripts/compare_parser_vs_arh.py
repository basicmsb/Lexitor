"""Batch tool za usporedbu original parser-a (canonical_xlsx) protiv
_ARH ground truth parser-a (arh_xlsx).

Svrha: identificirati gdje original parser pogrešno klasificira ili
mapira stavke u odnosu na "prijevod" (Marko-ovu ručno korigiranu _ARH
verziju). Iz diff-a izvode se nova pravila za canonical_xlsx parser.

Pravila parovanja (po Marko-ovoj direktivi):
  - Original = bez _ARHIGON sufiksa (npr. "Troškovnik GO.xlsx")
  - Ground truth = isti naziv s _ARHIGON_R0x sufiksom — uzima se najveći R0x
  - Ako u mapi postoji samo .arhigonfile / .arhigon (XML BoQ), parsiramo ga
    samostalno bez para

Output:
  - Pisani izvještaj (markdown) sa diff statistikama po paru
  - Agregat: koje vrste razlika se pojavljuju najčešće → top kandidati za
    parser fixeve

Pokretanje:
  cd apps/backend
  ./.venv/Scripts/python.exe scripts/compare_parser_vs_arh.py \\
    --root "C:/Dropbox/Arhigon WEB/_TVRTKE - Unos podataka/_R_" \\
    --out reports/parser_comparison_2026-05-09.md
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Allow running without poetry/venv setup (script directly invoked)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.document_parser.arh_xlsx import parse_arh_xlsx  # noqa: E402
from src.document_parser.base import ParsedDocument  # noqa: E402
from src.document_parser.canonical_xlsx import parse_canonical_xlsx  # noqa: E402

# Sufiksi koji označavaju _ARH ground truth varijantu (case-insensitive).
# Redoslijed je bitan — duži prije kraćeg da ne odsiječemo prerano.
_ARH_SUFFIX_PATTERNS = [
    re.compile(r"_ARHIGON_R(?P<rev>\d+)$", re.IGNORECASE),
    re.compile(r"_ARHIGON$", re.IGNORECASE),
    re.compile(r"_za[ _]Arhigon$", re.IGNORECASE),
    re.compile(r"_Arhigon$", re.IGNORECASE),
    re.compile(r"_ARH$", re.IGNORECASE),
    re.compile(r"_corrected$", re.IGNORECASE),
]


def _classify_xlsx(name: str) -> tuple[str, int] | None:
    """Vraća (base_name, rev) ako je _ARH varijanta, inače None.
    rev je broj iz _R0x (-1 = bez R, 0 = R0, 1 = R01, …)"""
    if not name.lower().endswith(".xlsx"):
        return None
    stem = name[: -len(".xlsx")]
    for pat in _ARH_SUFFIX_PATTERNS:
        m = pat.search(stem)
        if m:
            base = stem[: m.start()]
            try:
                rev = int(m.group("rev"))
            except (IndexError, ValueError):
                rev = -1  # nema R sufiks
            return base, rev
    return None


@dataclass
class Pair:
    """Par (original.xlsx, ground_truth.xlsx) — ground_truth je najveći R0x."""
    folder: Path
    original: Path | None
    arh: Path | None
    arh_rev: int  # 0 ako je samo _ARHIGON.xlsx bez R sufiksa, -1 ako nema _ARH

    @property
    def has_pair(self) -> bool:
        return self.original is not None and self.arh is not None


def _fuzzy_pick_original(arh_base: str, originals: list[Path]) -> Path | None:
    """Iz liste originala (xlsx bez _ARH sufiksa) vrati onaj čiji se naziv
    najbolje preklapa s `arh_base`. Heuristika: najduži zajednički prefiks
    + cutoff. Pokriva slučajeve kad je _ARH base proširen sufiksima:
        original: 'GD03-…-v19.xlsx'
        arh:      'GD03-…-v19_IS_za_slanje_ARHIGON_R02.xlsx'
    """
    import difflib
    if not originals:
        return None
    arh_lower = arh_base.lower()
    # Prvo: točno podudaranje
    for o in originals:
        if o.stem.lower() == arh_lower:
            return o
    # Drugo: arh_base je ekstenzija original-a (tj. original.lower() je prefix)
    for o in originals:
        if arh_lower.startswith(o.stem.lower()):
            return o
    # Treće: original je ekstenzija arh_base-a
    for o in originals:
        if o.stem.lower().startswith(arh_lower):
            return o
    # Četvrto: difflib SequenceMatcher
    best = difflib.get_close_matches(
        arh_lower, [o.stem.lower() for o in originals], n=1, cutoff=0.6,
    )
    if best:
        for o in originals:
            if o.stem.lower() == best[0]:
                return o
    return None


def find_pairs(root: Path) -> list[Pair]:
    """Walka root rekurzivno. Za svaku mapu:
    - Klasificira xlsx fajlove na _ARH varijante i obične originale
    - Za svaku _ARH varijantu nađe najsličniji original u istoj mapi
    - Bira najveći R0x kao ground truth
    Vraća listu parova."""
    pairs: list[Pair] = []
    for folder in [root, *[p for p in root.rglob("*") if p.is_dir()]]:
        arhs: dict[str, dict[str, Any]] = {}  # base → {fp, rev}
        originals: list[Path] = []
        for fp in folder.iterdir():
            if not fp.is_file() or fp.name.startswith("~$"):
                continue
            if not fp.name.lower().endswith(".xlsx"):
                continue
            classified = _classify_xlsx(fp.name)
            if classified:
                base, rev = classified
                slot = arhs.setdefault(base, {"fp": None, "rev": -2})
                if rev > slot["rev"]:
                    slot["fp"] = fp
                    slot["rev"] = rev
            else:
                originals.append(fp)

        # Spari _ARH s najsličnijim originalom
        used_orig: set[Path] = set()
        for base, slot in arhs.items():
            arh_fp = slot["fp"]
            available = [o for o in originals if o not in used_orig]
            orig = _fuzzy_pick_original(base, available)
            if orig is not None:
                used_orig.add(orig)
            pairs.append(Pair(
                folder=folder,
                original=orig,
                arh=arh_fp,
                arh_rev=slot["rev"],
            ))
        # Originali bez para — preskačemo (bez ground truth nema usporedbe)
    return pairs


def _process_pair_worker(orig_path: str, arh_path: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Worker za ProcessPoolExecutor — mora biti top-level radi pickle.
    Vraća (orig_summary, arh_summary) kao plain dictove (Counter je picklable).
    Pravi diff radi u main procesu da se ParsedDocument ne mora pickleati."""
    orig_doc = parse_canonical_xlsx(Path(orig_path))
    arh_doc = parse_arh_xlsx(Path(arh_path))
    return _parsed_summary_picklable(orig_doc), _parsed_summary_picklable(arh_doc)


def _parsed_summary_picklable(parsed: ParsedDocument) -> dict[str, Any]:
    """Identičan _parsed_summary ali bez Counter-a (dict-only za pickle)."""
    sheets: dict[str, dict[str, Any]] = {}
    for it in parsed.items:
        meta = it.metadata or {}
        sheet = meta.get("sheet", "?")
        kind = meta.get("kind", "?")
        s = sheets.setdefault(sheet, {"by_kind": {}, "stavke_rb": [], "items": 0})
        s["by_kind"][kind] = s["by_kind"].get(kind, 0) + 1
        s["items"] += 1
        if kind == "stavka":
            rb = meta.get("rb") or ""
            if rb:
                s["stavke_rb"].append(rb)
    return sheets


def _parsed_summary(parsed: ParsedDocument) -> dict[str, Any]:
    """Sažeti rezime parsed dokumenta po sheetu."""
    sheets: dict[str, dict[str, Any]] = {}
    for it in parsed.items:
        meta = it.metadata or {}
        sheet = meta.get("sheet", "?")
        kind = meta.get("kind", "?")
        s = sheets.setdefault(sheet, {"by_kind": Counter(), "stavke_rb": [], "items": 0})
        s["by_kind"][kind] += 1
        s["items"] += 1
        if kind == "stavka":
            rb = meta.get("rb") or ""
            if rb:
                s["stavke_rb"].append(rb)
    return sheets


def _diff_pair(orig_doc: ParsedDocument, arh_doc: ParsedDocument) -> dict[str, Any]:
    """Diff izvještaj između parsed_original i parsed_arh (in-process putanja)."""
    return _diff_summaries(_parsed_summary(orig_doc), _parsed_summary(arh_doc))


def _diff_summaries(orig_summary: dict[str, Any], arh_summary: dict[str, Any]) -> dict[str, Any]:
    """Diff izvještaj iz već-summarized dict-ova (worker putanja)."""
    # Konvertiraj `by_kind` u Counter ako stigne kao plain dict
    for sheet_data in (*orig_summary.values(), *arh_summary.values()):
        if not isinstance(sheet_data["by_kind"], Counter):
            sheet_data["by_kind"] = Counter(sheet_data["by_kind"])

    # Zajednički sheetovi (po normaliziranom imenu)
    all_sheets = set(orig_summary) | set(arh_summary)
    diffs: list[dict[str, Any]] = []
    totals = {"stavka": [0, 0], "opci_uvjeti": [0, 0], "section_header": [0, 0]}

    for sheet in sorted(all_sheets):
        o = orig_summary.get(sheet)
        a = arh_summary.get(sheet)
        if o is None and a is not None:
            diffs.append({"sheet": sheet, "type": "missing_in_original",
                          "arh_kinds": dict(a["by_kind"])})
            continue
        if a is None and o is not None:
            # _ARH često skipa naslovne / opci sheetove → očekivano
            diffs.append({"sheet": sheet, "type": "missing_in_arh",
                          "orig_kinds": dict(o["by_kind"]), "expected": True})
            continue
        for kind in ("stavka", "opci_uvjeti", "section_header"):
            o_count = o["by_kind"].get(kind, 0) if o else 0
            a_count = a["by_kind"].get(kind, 0) if a else 0
            if kind in totals:
                totals[kind][0] += o_count
                totals[kind][1] += a_count
            if o_count != a_count:
                diffs.append({
                    "sheet": sheet,
                    "type": f"{kind}_count_mismatch",
                    "orig": o_count, "arh": a_count, "delta": o_count - a_count,
                })
        # rb pairing usporedba (samo kada oba imaju stavke)
        if o and a and o["stavke_rb"] and a["stavke_rb"]:
            orig_rbs = set(o["stavke_rb"])
            arh_rbs = set(a["stavke_rb"])
            missing = arh_rbs - orig_rbs
            extra = orig_rbs - arh_rbs
            if missing:
                diffs.append({"sheet": sheet, "type": "rb_missing_in_original",
                              "rbs": sorted(missing)[:10]})
            if extra:
                diffs.append({"sheet": sheet, "type": "rb_extra_in_original",
                              "rbs": sorted(extra)[:10]})
    return {"sheets": diffs, "totals": totals}


def _format_pair_report(pair: Pair, diff: dict[str, Any] | None,
                        error: str | None) -> str:
    rel = pair.folder.name
    orig = pair.original.name if pair.original else "—"
    arh = pair.arh.name if pair.arh else "—"
    out = [f"### {rel}", f"  - original: `{orig}`",
           f"  - ground truth (_ARH R{pair.arh_rev}): `{arh}`"]
    if error:
        out.append(f"  - **ERROR**: {error}")
        return "\n".join(out)
    if diff is None:
        out.append("  - skipped (no pair)")
        return "\n".join(out)
    t = diff["totals"]
    out.append(
        f"  - totals: stavka {t['stavka'][0]} vs {t['stavka'][1]} (Δ {t['stavka'][0]-t['stavka'][1]:+d}), "
        f"opci_uvjeti {t['opci_uvjeti'][0]} vs {t['opci_uvjeti'][1]}, "
        f"section_header {t['section_header'][0]} vs {t['section_header'][1]}"
    )
    if diff["sheets"]:
        out.append("  - razlike:")
        for d in diff["sheets"][:25]:
            out.append(f"    - `{d.get('sheet','?')}`: {d['type']} "
                       f"{ {k:v for k,v in d.items() if k not in ('sheet','type')} }")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=0,
                        help="Process samo prvih N parova (0 = sve)")
    parser.add_argument("--max-mb", type=float, default=20.0,
                        help="Preskoči parove gdje je bilo koji fajl veći od X MB (default 20)")
    parser.add_argument("--timeout", type=float, default=60.0,
                        help="Sekundi po paru prije nego abort (default 60)")
    parser.add_argument("--since-months", type=int, default=0,
                        help="Filtriraj parove gdje je _ARH stariji od X mjeseci (0 = sve)")
    args = parser.parse_args()

    if not args.root.exists():
        print(f"Root path ne postoji: {args.root}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)

    print(f"Skeniram {args.root}…", flush=True)
    pairs = find_pairs(args.root)
    print(f"Pronađeno {len(pairs)} mapa s troškovnicima", flush=True)
    paired = [p for p in pairs if p.has_pair]
    only_orig = [p for p in pairs if p.original and not p.arh]
    only_arh = [p for p in pairs if p.arh and not p.original]
    print(f"  s parom: {len(paired)}", flush=True)
    print(f"  samo original: {len(only_orig)}", flush=True)
    print(f"  samo _ARH: {len(only_arh)}", flush=True)

    work = paired
    if args.since_months > 0:
        import time
        cutoff = time.time() - args.since_months * 30 * 24 * 3600
        before = len(work)
        work = [p for p in work if p.arh and p.arh.stat().st_mtime >= cutoff]
        print(
            f"  filter --since-months {args.since_months}: "
            f"{before} → {len(work)} (skip {before-len(work)} starijih)",
            flush=True,
        )
    if args.limit:
        work = work[: args.limit]

    sections: list[str] = []
    diff_kind_totals: Counter = Counter()
    errors = 0
    skipped = 0
    timeouts = 0
    max_bytes = int(args.max_mb * 1024 * 1024)

    # Inkrementalno pisanje — append nakon svakog para
    args.out.write_text(
        f"# Parser comparison report (in progress…)\n\n"
        f"- root: `{args.root}`\n"
        f"- max-mb: {args.max_mb}, timeout: {args.timeout}s/par\n\n",
        encoding="utf-8",
    )

    # ProcessPoolExecutor s 1 workerom — workeri u zasebnom procesu
    # tako da timeout zaista može abandonirati zaglavljen parser.
    executor = ProcessPoolExecutor(max_workers=1)

    try:
        for i, pair in enumerate(work, 1):
            sz_orig = pair.original.stat().st_size if pair.original else 0
            sz_arh = pair.arh.stat().st_size if pair.arh else 0
            sz_max_mb = max(sz_orig, sz_arh) / (1024 * 1024)
            print(
                f"[{i}/{len(work)}] {pair.folder.name} "
                f"(orig={sz_orig/(1024*1024):.1f}MB, arh={sz_arh/(1024*1024):.1f}MB)",
                flush=True,
            )
            if sz_orig > max_bytes or sz_arh > max_bytes:
                print(f"  SKIP: file too large ({sz_max_mb:.1f}MB > {args.max_mb}MB)", flush=True)
                sections.append(
                    f"### {pair.folder.name}\n"
                    f"  - SKIPPED: file too large ({sz_max_mb:.1f}MB > {args.max_mb}MB)\n"
                )
                skipped += 1
                with args.out.open("a", encoding="utf-8") as fh:
                    fh.write(sections[-1] + "\n")
                continue

            diff = None
            error = None
            future = executor.submit(
                _process_pair_worker, str(pair.original), str(pair.arh)
            )
            try:
                orig_summary, arh_summary = future.result(timeout=args.timeout)
                diff = _diff_summaries(orig_summary, arh_summary)
                for d in diff["sheets"]:
                    diff_kind_totals[d["type"]] += 1
            except FuturesTimeoutError:
                error = f"TIMEOUT after {args.timeout}s — abandoning worker"
                print(f"  {error}", flush=True)
                timeouts += 1
                # Worker je zaglavljen — restartam pool da oslobodim resurse
                executor.shutdown(wait=False, cancel_futures=True)
                executor = ProcessPoolExecutor(max_workers=1)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                print(f"  ERROR: {error}", flush=True)
                errors += 1

            sections.append(_format_pair_report(pair, diff, error))
            with args.out.open("a", encoding="utf-8") as fh:
                fh.write(sections[-1] + "\n")
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    # Završni izvještaj — prepiši cijeli fajl s headerom + svim sekcijama
    header = [
        f"# Parser comparison report",
        f"",
        f"- root: `{args.root}`",
        f"- pairs total: {len(pairs)} (s parom: {len(paired)}, samo original: {len(only_orig)}, samo _ARH: {len(only_arh)})",
        f"- processed: {len(work)} (errors: {errors}, skipped >{args.max_mb}MB: {skipped}, timeouts >{args.timeout}s: {timeouts})",
        f"",
        f"## Top diff kinds (ukupno across all pairs)",
        f"",
    ]
    for kind, n in diff_kind_totals.most_common(20):
        header.append(f"- `{kind}`: {n}")
    header.append("")
    header.append("## Po paru")
    header.append("")

    args.out.write_text("\n".join(header + sections), encoding="utf-8")
    print(f"\nIzvještaj: {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
