"""Fetch the canonical ZJN (Zakon o javnoj nabavi, NN 120/2016) HTML
and parse it into individual article documents for indexing.

Usage (from apps/backend/):
    poetry run python scripts/scrape_zjn.py
    poetry run python scripts/scrape_zjn.py --output data/01-zakoni/zjn

Output:
    data/01-zakoni/zjn/zjn-2016.html              (raw HTML)
    data/01-zakoni/zjn/articles.jsonl              (parsed articles)
    data/01-zakoni/zjn/metadata.json               (versioning)

We deliberately keep this fully offline-friendly: one HTTP request, the
Narodne novine URL is a single resource, no rate-limit concerns.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ZJN_URL = "https://narodne-novine.nn.hr/clanci/sluzbeni/2016_12_120_2607.html"
ZJN_NN_REFERENCE = "NN 120/2016"
ZJN_TITLE = "Zakon o javnoj nabavi"
USER_AGENT = "Lexitor/0.0.1 (legal-compliance research, contact: marko.basic@arhigon.com)"

DEFAULT_OUTPUT = Path("data/01-zakoni/zjn")

ARTICLE_HEADER_RE = re.compile(r"^Članak\s+(\d+)\.?$")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ZJN scraper (NN 120/2016)")
    p.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output direktorij (default: data/01-zakoni/zjn)",
    )
    p.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout (sec)")
    p.add_argument("--force", action="store_true", help="Pre-skinu HTML čak i ako već postoji")
    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args()


def download_html(target: Path, *, timeout: float, force: bool) -> str:
    if target.exists() and not force:
        return target.read_text(encoding="utf-8")

    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"Fetching {ZJN_URL}", file=sys.stderr)
    response = httpx.get(
        ZJN_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
        follow_redirects=True,
    )
    response.raise_for_status()
    target.write_text(response.text, encoding="utf-8")
    return response.text


def parse_articles(html: str) -> list[dict[str, Any]]:
    """Walk the body, splitting on each "Članak N." marker.

    The Narodne novine HTML is mostly flat <p>-soup with "Članak N." sitting
    in its own paragraph immediately above the article body. We collect
    every paragraph between two markers.
    """
    soup = BeautifulSoup(html, "lxml")
    body = soup.find("body") or soup

    paragraphs: list[tuple[str, str]] = []  # (kind, text)
    for el in body.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6"]):
        text = el.get_text(" ", strip=True)
        if not text:
            continue
        kind = el.name
        paragraphs.append((kind, text))

    articles: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    current_glava: str | None = None
    current_dio: str | None = None

    for _kind, text in paragraphs:
        m = ARTICLE_HEADER_RE.match(text)
        if m is not None:
            # finalise previous
            if current is not None:
                articles.append(_finalise_article(current))
            current = {
                "number": int(m.group(1)),
                "header": text,
                "lines": [],
                "dio": current_dio,
                "glava": current_glava,
            }
            continue

        if current is None:
            # Pre-article structural markers — keep latest dio/glava
            upper = text.upper()
            if upper.startswith("DIO "):
                current_dio = text
            elif upper.startswith("GLAVA "):
                current_glava = text
            continue

        # Inside an article
        upper = text.upper()
        if upper.startswith("DIO "):
            current_dio = text
            continue
        if upper.startswith("GLAVA "):
            current_glava = text
            continue
        current["lines"].append(text)

    if current is not None:
        articles.append(_finalise_article(current))

    return articles


def _finalise_article(raw: dict[str, Any]) -> dict[str, Any]:
    body = "\n\n".join(raw["lines"]).strip()
    title_line = raw["lines"][0].strip() if raw["lines"] else ""
    return {
        "number": raw["number"],
        "header": raw["header"],
        "title": title_line if len(title_line) < 220 else "",
        "dio": raw["dio"],
        "glava": raw["glava"],
        "text": body,
    }


def write_outputs(articles: list[dict[str, Any]], *, root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    jsonl_path = root / "articles.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as fh:
        for art in articles:
            fh.write(json.dumps(art, ensure_ascii=False) + "\n")

    metadata = {
        "title": ZJN_TITLE,
        "reference": ZJN_NN_REFERENCE,
        "url": ZJN_URL,
        "scraped_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "article_count": len(articles),
    }
    (root / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> int:
    args = parse_args()
    root = args.output.resolve()
    html_path = root / "zjn-2016.html"
    html = download_html(html_path, timeout=args.timeout, force=args.force)
    articles = parse_articles(html)
    if not articles:
        print("Nije pronađen niti jedan članak — provjeri parser ili HTML strukturu.", file=sys.stderr)
        return 1
    write_outputs(articles, root=root)
    print(
        f"Done. {len(articles)} članaka spremljeno u {root.relative_to(root.parent.parent.parent)}",
        file=sys.stderr,
    )
    if args.verbose:
        sample = articles[:3]
        for art in sample:
            print(f"  Članak {art['number']}.: {art['title'][:80] or art['text'][:80]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
