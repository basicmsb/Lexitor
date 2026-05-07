"""Map original ↔ _ARH-R0x ↔ .arhigon triplets across the troskovnik tree.

Read-only — does not modify or upload anything. Output is a sorted list of
"good triplets" we can use as test fixtures for the new XLSX parser.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Dropbox\Arhigon WEB\_TVRTKE - Unos podataka\_R_")

# Patterns to strip when computing the base key for grouping.
# Order matters — strip the more specific suffix first.
STRIP_PATTERNS = [
    re.compile(r"_ARH[_-]R\d+(?:_\d{4}-\d{2}-\d{2})?$", re.IGNORECASE),
    re.compile(r"_ARH(?:_\d{4}-\d{2}-\d{2})?$", re.IGNORECASE),
    re.compile(r"_R\d+(?:_\d{4}-\d{2}-\d{2})?$", re.IGNORECASE),
    re.compile(r"_\d{4}-\d{2}-\d{2}$"),
    re.compile(r"\s+$"),
]

ARH_VERSION_RE = re.compile(r"_ARH[_-]R(\d+)", re.IGNORECASE)
ARH_NO_VERSION_RE = re.compile(r"_ARH(?![_-]R)", re.IGNORECASE)


@dataclass
class FileInfo:
    path: Path
    kind: str  # "original" | "arh" | "arhigon"
    version: int  # 0 = no R-version, otherwise R-number
    size: int
    company: str
    base_key: str = ""


def normalise_base(stem: str) -> str:
    s = stem
    while True:
        new = s
        for rx in STRIP_PATTERNS:
            new = rx.sub("", new)
        if new == s:
            break
        s = new
    return s.strip(" ._-")


def classify(path: Path) -> FileInfo | None:
    name = path.name
    suffix = path.suffix.lower()
    if suffix not in (".xlsx", ".xls", ".arhigon"):
        return None

    stem = path.stem
    has_arh = bool(ARH_VERSION_RE.search(stem) or ARH_NO_VERSION_RE.search(stem))

    if suffix == ".arhigon":
        kind = "arhigon"
    elif has_arh:
        kind = "arh"
    else:
        kind = "original"

    m = ARH_VERSION_RE.search(stem)
    version = int(m.group(1)) if m else 0

    try:
        rel = path.relative_to(ROOT)
        company = rel.parts[0] if rel.parts else ""
    except ValueError:
        company = ""

    base = normalise_base(stem)
    return FileInfo(
        path=path,
        kind=kind,
        version=version,
        size=path.stat().st_size,
        company=company,
        base_key=base,
    )


@dataclass
class Triplet:
    company: str
    base: str
    original: list[FileInfo] = field(default_factory=list)
    arh: list[FileInfo] = field(default_factory=list)
    arhigon: list[FileInfo] = field(default_factory=list)

    @property
    def has_all_three(self) -> bool:
        return bool(self.original and self.arh and self.arhigon)

    @property
    def has_pair(self) -> bool:
        return bool(self.original and self.arh)

    @property
    def latest_arh(self) -> FileInfo | None:
        if not self.arh:
            return None
        return max(self.arh, key=lambda f: (f.version, f.size))

    @property
    def latest_arhigon(self) -> FileInfo | None:
        if not self.arhigon:
            return None
        return max(self.arhigon, key=lambda f: f.path.stat().st_mtime)

    @property
    def best_original(self) -> FileInfo | None:
        if not self.original:
            return None
        return max(self.original, key=lambda f: f.size)

    @property
    def complexity_score(self) -> int:
        """Heuristic — bigger originals are usually more interesting."""
        orig = self.best_original
        return orig.size if orig is not None else 0


def main() -> None:
    print(f"Scanning {ROOT}…", file=sys.stderr)

    by_company: dict[tuple[str, str], Triplet] = {}
    counts = {"original": 0, "arh": 0, "arhigon": 0}

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        info = classify(path)
        if info is None:
            continue
        counts[info.kind] += 1
        key = (info.company, info.base_key)
        if key not in by_company:
            by_company[key] = Triplet(company=info.company, base=info.base_key)
        bucket = by_company[key]
        if info.kind == "original":
            bucket.original.append(info)
        elif info.kind == "arh":
            bucket.arh.append(info)
        else:
            bucket.arhigon.append(info)

    triplets = list(by_company.values())

    print()
    print("====== AGGREGATE ======")
    print(f"  total: {sum(counts.values())}")
    print(f"    original (xlsx, no _ARH): {counts['original']}")
    print(f"    ARH xlsx (any _ARH variant): {counts['arh']}")
    print(f"    .arhigon files: {counts['arhigon']}")
    print(f"  unique base groups: {len(triplets)}")

    full = [t for t in triplets if t.has_all_three]
    pair = [t for t in triplets if t.has_pair and not t.has_all_three]
    arh_only = [t for t in triplets if t.arh and not t.original]
    orig_only = [t for t in triplets if t.original and not t.arh and not t.arhigon]

    print(f"\n  groups with original + ARH + .arhigon: {len(full)}")
    print(f"  groups with original + ARH (no .arhigon): {len(pair)}")
    print(f"  groups with ARH only (no original tracked): {len(arh_only)}")
    print(f"  groups with original only: {len(orig_only)}")

    full.sort(key=lambda t: t.complexity_score, reverse=True)
    print("\n====== TOP 15 FULL TRIPLETS (by original size) ======")
    for t in full[:15]:
        orig = t.best_original
        arh = t.latest_arh
        arhig = t.latest_arhigon
        print(
            f"  [{orig.size//1024:>5} KB] {t.company} :: {t.base[:60]}\n"
            f"     orig: {orig.path.relative_to(ROOT)}\n"
            f"     ARH:  {arh.path.relative_to(ROOT)}  (R{arh.version})\n"
            f"     .arh: {arhig.path.relative_to(ROOT)}"
        )

    pair.sort(key=lambda t: t.complexity_score, reverse=True)
    print("\n====== TOP 10 ORIGINAL+ARH (no .arhigon) ======")
    for t in pair[:10]:
        orig = t.best_original
        arh = t.latest_arh
        print(
            f"  [{orig.size//1024:>5} KB] {t.company} :: {t.base[:60]}\n"
            f"     orig: {orig.path.relative_to(ROOT)}\n"
            f"     ARH:  {arh.path.relative_to(ROOT)}  (R{arh.version})"
        )

    arh_versions = [len(t.arh) for t in triplets if t.arh]
    if arh_versions:
        from collections import Counter

        dist = Counter(arh_versions)
        print("\n====== ARH VERSIONS PER GROUP ======")
        for k in sorted(dist):
            print(f"  {k} versions: {dist[k]} groups")


if __name__ == "__main__":
    main()
