"""Cron-friendly wrapper that pulls only the newest DKOM decisions.

Designed to run once per day. Defaults are intentionally conservative:
checks only the first 1-2 listing pages, downloads at most 10 new PDFs,
and pauses 5 seconds between downloads so dkom.hr never sees a burst.

Usage:
    poetry run python scripts/daily_dkom.py
    poetry run python scripts/daily_dkom.py --pages 2 --max 5

After downloading, runs the existing index_dkom.py so freshly added PDFs
land in Qdrant the same day.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Lexitor daily DKOM cron task")
    p.add_argument("--pages", type=int, default=1, help="Koliko listing stranica provjeriti (default 1)")
    p.add_argument(
        "--max", type=int, default=10, help="Maksimum novih odluka po pokretanju (default 10)"
    )
    p.add_argument("--delay", type=float, default=5.0, help="Pauza između PDF-ova (s)")
    p.add_argument("--page-delay", type=float, default=10.0, help="Pauza između stranica (s)")
    p.add_argument("--skip-index", action="store_true", help="Preskoči index_dkom.py poziv")
    return p.parse_args()


def run_python(script: str, *cli_args: str) -> int:
    cmd = [sys.executable, str(THIS_DIR / script), *cli_args]
    print(f"\n$ {' '.join(cmd)}", file=sys.stderr)
    return subprocess.call(cmd)


def main() -> int:
    args = parse_args()
    rc = run_python(
        "scrape_dkom.py",
        "--start-page",
        "1",
        "--end-page",
        str(args.pages),
        "--max",
        str(args.max),
        "--delay",
        str(args.delay),
        "--page-delay",
        str(args.page_delay),
        "--verbose",
    )
    if rc != 0:
        print(f"scrape_dkom.py exited {rc} — preskačem indeksiranje.", file=sys.stderr)
        return rc

    if args.skip_index:
        return 0

    rc = run_python("index_dkom.py", "--verbose")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
