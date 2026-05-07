"""Scraper for DKOM (dkom.hr) decisions and accompanying metadata.

Usage (from apps/backend/):
    poetry run python scripts/scrape_dkom.py --year 2026 --max 50

Output:
    data/02-dkom-odluke/{year}/{klasa-safe}.pdf
    data/02-dkom-odluke/{year}/{klasa-safe}.json   (metadata)
    data/02-dkom-odluke/index.csv                  (append-only audit log)

The script reads the public listing at https://www.dkom.hr/javna-objava-odluka/10
which is server-rendered HTML with a single table containing all decisions.
Each row layout:

    klasa | naručitelj | žalitelj | predmet | vrsta | datum (DD.MM.YYYY.) |
    status | <a href="...pdf">datum odluke</a>
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

LISTING_URL = "https://www.dkom.hr/javna-objava-odluka/10"
DEFAULT_OUTPUT = Path("data/02-dkom-odluke")
USER_AGENT = "Lexitor/0.0.1 (DKOM scraper for legal compliance research)"
DATE_FORMATS = ("%d.%m.%Y.", "%d.%m.%Y", "%Y-%m-%d")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DKOM odluke scraper")
    p.add_argument("--year", type=int, help="Filtriraj odluke iz zadane godine")
    p.add_argument("--max", type=int, default=None, help="Maksimalan broj odluka za skinuti")
    p.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output direktorij (default: data/02-dkom-odluke)",
    )
    p.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Razmak između download-a u sekundama (default 1.0)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Samo prikaži pronađene odluke bez skidanja PDF-ova",
    )
    p.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout (sec)")
    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args()


def slugify_klasa(klasa: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9-]+", "-", klasa).strip("-")
    return cleaned or "unknown"


def parse_date(text: str) -> datetime | None:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text.strip(), fmt)
        except ValueError:
            continue
    return None


def extract_rows(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    rows: list[dict[str, Any]] = []
    for tr in soup.select("table tr"):
        cells = tr.find_all("td")
        if len(cells) < 8:
            continue
        klasa = cells[0].get_text(strip=True)
        narucitelj = cells[1].get_text(" ", strip=True)
        zalitelj = cells[2].get_text(" ", strip=True)
        predmet = cells[3].get_text(" ", strip=True)
        vrsta = cells[4].get_text(strip=True)
        zaprimljeno_text = cells[5].get_text(strip=True)
        status = cells[6].get_text(" ", strip=True)
        pdf_anchor = cells[7].find("a")
        pdf_url = pdf_anchor.get("href") if pdf_anchor else None
        odluka_text = pdf_anchor.get_text(strip=True) if pdf_anchor else ""

        if not klasa or not pdf_url:
            continue

        zaprimljeno = parse_date(zaprimljeno_text)
        odluka_dt = parse_date(odluka_text)
        rows.append(
            {
                "klasa": klasa,
                "narucitelj": narucitelj,
                "zalitelj": zalitelj,
                "predmet": predmet,
                "vrsta": vrsta,
                "zaprimljeno": zaprimljeno.date().isoformat() if zaprimljeno else zaprimljeno_text,
                "status": status,
                "odluka_datum": odluka_dt.date().isoformat() if odluka_dt else odluka_text,
                "pdf_url": pdf_url,
            }
        )
    return rows


def determine_year(row: dict[str, Any]) -> str:
    for key in ("odluka_datum", "zaprimljeno"):
        value = row.get(key) or ""
        if len(value) >= 4 and value[:4].isdigit():
            return value[:4]
    match = re.search(r"/(\d{2})-", row.get("klasa", ""))
    if match:
        suffix = int(match.group(1))
        century = 2000 if suffix < 50 else 1900
        return str(century + suffix)
    return "unknown"


def filter_rows(rows: list[dict[str, Any]], *, year: int | None) -> list[dict[str, Any]]:
    if year is None:
        return rows
    return [row for row in rows if determine_year(row) == str(year)]


def write_metadata(target: Path, row: dict[str, Any]) -> None:
    target.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")


def append_index(index_path: Path, row: dict[str, Any]) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not index_path.exists()
    with index_path.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        if is_new:
            writer.writerow(
                [
                    "scraped_at",
                    "klasa",
                    "year",
                    "narucitelj",
                    "predmet",
                    "vrsta",
                    "odluka_datum",
                    "pdf_url",
                    "local_path",
                ]
            )
        writer.writerow(
            [
                datetime.utcnow().isoformat(timespec="seconds") + "Z",
                row["klasa"],
                row.get("year", ""),
                row["narucitelj"],
                row["predmet"],
                row["vrsta"],
                row["odluka_datum"],
                row["pdf_url"],
                row.get("local_path", ""),
            ]
        )


def main() -> int:
    args = parse_args()
    output_root = args.output.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    index_path = output_root / "index.csv"

    print(f"Fetching {LISTING_URL}", file=sys.stderr)
    with httpx.Client(
        timeout=args.timeout, follow_redirects=True, headers={"User-Agent": USER_AGENT}
    ) as client:
        listing = client.get(LISTING_URL)
        listing.raise_for_status()
        rows = extract_rows(listing.text)

    print(f"  Found {len(rows)} decisions in listing.", file=sys.stderr)
    rows = filter_rows(rows, year=args.year)
    if args.year is not None:
        print(f"  After year filter ({args.year}): {len(rows)} decisions.", file=sys.stderr)

    if args.max is not None:
        rows = rows[: args.max]
        print(f"  Limited to first {len(rows)} decisions.", file=sys.stderr)

    if args.dry_run:
        for row in rows:
            print(f"  {row['klasa']:32s}  {row['odluka_datum']:12s}  {row['predmet'][:80]}")
        return 0

    downloaded = 0
    skipped = 0
    failed = 0

    with httpx.Client(
        timeout=args.timeout, follow_redirects=True, headers={"User-Agent": USER_AGENT}
    ) as client:
        for index, row in enumerate(rows):
            year = determine_year(row)
            slug = slugify_klasa(row["klasa"])
            target_dir = output_root / year
            target_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = target_dir / f"{slug}.pdf"
            meta_path = target_dir / f"{slug}.json"

            if pdf_path.exists():
                skipped += 1
                if args.verbose:
                    print(f"  [{index + 1}/{len(rows)}] SKIP {row['klasa']} (already on disk)")
                continue

            try:
                response = client.get(row["pdf_url"])
                response.raise_for_status()
            except httpx.HTTPError as exc:
                failed += 1
                print(f"  [{index + 1}/{len(rows)}] FAIL {row['klasa']}: {exc}", file=sys.stderr)
                continue

            pdf_path.write_bytes(response.content)
            row_with_meta = {
                **row,
                "year": year,
                "local_path": str(pdf_path.relative_to(output_root.parent)),
                "downloaded_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "size_bytes": len(response.content),
            }
            write_metadata(meta_path, row_with_meta)
            append_index(index_path, row_with_meta)
            downloaded += 1
            if args.verbose:
                print(
                    f"  [{index + 1}/{len(rows)}] OK   {row['klasa']} → "
                    f"{pdf_path.relative_to(output_root)}"
                )
            time.sleep(args.delay)

    print(
        f"\nDone. downloaded={downloaded} skipped={skipped} failed={failed}",
        file=sys.stderr,
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
