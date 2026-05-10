"""Generic Narodne novine scraper za bilo koji zakon ili pravilnik.

Parsira HTML s narodne-novine.nn.hr u JSONL listu članaka — istu strukturu
koju koristi `index_zjn.py` (može se koristiti generički index_legislation.py
ili reusati index_zjn.py s drugim --root).

Usage (pojedinačno):
    poetry run python scripts/scrape_legislation.py \\
        --url https://narodne-novine.nn.hr/clanci/sluzbeni/2017_07_65_1534.html \\
        --name "Pravilnik o dokumentaciji o nabavi" \\
        --reference "NN 65/2017" \\
        --output data/01-zakoni/pravilnici/dokumentacija-65-17

Usage (batch — svi zakoni odjednom):
    poetry run python scripts/scrape_legislation.py --batch
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

USER_AGENT = "Lexitor/0.0.1 (legal-compliance research, contact: marko.basic@arhigon.com)"
ARTICLE_HEADER_RE = re.compile(r"^Članak\s+(\d+)\.?$")

# --- Batch konfiguracija — sve relevantne zakone odjednom ----------------
# Iz https://sredisnjanabava.gov.hr/.../544 (autoritativna lista) + ZOO
BATCH_LEGISLATION = [
    # ZJN izmjene (NN 120/16 je već skupljen kroz scrape_zjn.py)
    {
        "url": "https://narodne-novine.nn.hr/clanci/sluzbeni/2022_10_114_1740.html",
        "name": "Zakon o izmjenama i dopunama Zakona o javnoj nabavi",
        "reference": "NN 114/2022",
        "subdir": "zjn-izmjene-114-22",
    },
    # Pravilnici o javnoj nabavi
    {
        "url": "https://narodne-novine.nn.hr/clanci/sluzbeni/2017_07_65_1534.html",
        "name": "Pravilnik o dokumentaciji o nabavi te ponudi",
        "reference": "NN 65/2017",
        "subdir": "pravilnik-dokumentacija-65-17",
    },
    {
        "url": "https://narodne-novine.nn.hr/clanci/sluzbeni/2020_07_75_1451.html",
        "name": "Pravilnik o izmjenama i dopunama Pravilnika o dokumentaciji o nabavi",
        "reference": "NN 75/2020",
        "subdir": "pravilnik-dokumentacija-izmjene-75-20",
    },
    {
        "url": "https://narodne-novine.nn.hr/clanci/sluzbeni/2017_07_65_1535.html",
        "name": "Pravilnik o nadzoru nad provedbom Zakona o javnoj nabavi",
        "reference": "NN 65/2017",
        "subdir": "pravilnik-nadzor-65-17",
    },
    {
        "url": "https://narodne-novine.nn.hr/clanci/sluzbeni/2017_07_65_1533.html",
        "name": "Pravilnik o izobrazbi u području javne nabave",
        "reference": "NN 65/2017",
        "subdir": "pravilnik-izobrazba-65-17",
    },
    {
        "url": "https://narodne-novine.nn.hr/clanci/sluzbeni/2017_10_101_2338.html",
        "name": "Pravilnik o elektroničkoj žalbi u javnoj nabavi",
        "reference": "NN 101/2017",
        "subdir": "pravilnik-elektronicka-zalba-101-17",
    },
    {
        "url": "https://narodne-novine.nn.hr/clanci/sluzbeni/2023_02_19_325.html",
        "name": "Pravilnik o izmjenama i dopunama Pravilnika o elektroničkoj žalbi",
        "reference": "NN 19/2023",
        "subdir": "pravilnik-elektronicka-zalba-izmjene-19-23",
    },
    {
        "url": "https://narodne-novine.nn.hr/clanci/sluzbeni/2017_10_101_2339.html",
        "name": "Pravilnik o planu nabave, registru ugovora, prethodnom savjetovanju",
        "reference": "NN 101/2017",
        "subdir": "pravilnik-plan-nabave-101-17",
    },
    {
        "url": "https://narodne-novine.nn.hr/clanci/sluzbeni/2020_12_144_2775.html",
        "name": "Pravilnik o izmjenama i dopunama Pravilnika o planu nabave (1)",
        "reference": "NN 144/2020",
        "subdir": "pravilnik-plan-nabave-izmjene-144-20",
    },
    {
        "url": "https://narodne-novine.nn.hr/clanci/sluzbeni/2023_03_30_518.html",
        "name": "Pravilnik o izmjenama Pravilnika o planu nabave (2)",
        "reference": "NN 30/2023",
        "subdir": "pravilnik-plan-nabave-izmjene-30-23",
    },
    # Zakon o DKOM-u
    {
        "url": "http://narodne-novine.nn.hr/clanci/sluzbeni/2013_02_18_293.html",
        "name": "Zakon o Državnoj komisiji za kontrolu postupaka javne nabave",
        "reference": "NN 18/2013",
        "subdir": "zakon-dkom-18-13",
    },
    {
        "url": "http://narodne-novine.nn.hr/clanci/sluzbeni/2013_10_127_2759.html",
        "name": "Zakon o izmjenama i dopunama Zakona o DKOM (1)",
        "reference": "NN 127/2013",
        "subdir": "zakon-dkom-izmjene-127-13",
    },
    {
        "url": "http://narodne-novine.nn.hr/clanci/sluzbeni/2014_06_74_1393.html",
        "name": "Zakon o izmjenama Zakona o DKOM (2)",
        "reference": "NN 74/2014",
        "subdir": "zakon-dkom-izmjene-74-14",
    },
    {
        "url": "https://narodne-novine.nn.hr/clanci/sluzbeni/2019_10_98_1966.html",
        "name": "Zakon o izmjenama Zakona o DKOM (3)",
        "reference": "NN 98/2019",
        "subdir": "zakon-dkom-izmjene-98-19",
    },
    {
        "url": "https://narodne-novine.nn.hr/clanci/sluzbeni/2021_04_41_812.html",
        "name": "Zakon o izmjenama i dopunama Zakona o DKOM (4)",
        "reference": "NN 41/2021",
        "subdir": "zakon-dkom-izmjene-41-21",
    },
    # Sustav državne uprave (kontekst)
    {
        "url": "https://narodne-novine.nn.hr/clanci/sluzbeni/2019_07_66_1290.html",
        "name": "Zakon o sustavu državne uprave",
        "reference": "NN 66/2019",
        "subdir": "zakon-drzavna-uprava-66-19",
    },
    {
        "url": "https://narodne-novine.nn.hr/clanci/sluzbeni/2020_07_85_1593.html",
        "name": "Zakon o ustrojstvu i djelokrugu tijela državne uprave",
        "reference": "NN 85/2020",
        "subdir": "zakon-ustrojstvo-85-20",
    },
    {
        "url": "https://narodne-novine.nn.hr/clanci/sluzbeni/2024_05_57_982.html",
        "name": "Zakon o izmjenama Zakona o ustrojstvu",
        "reference": "NN 57/2024",
        "subdir": "zakon-ustrojstvo-izmjene-57-24",
    },
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generic NN legislativa scraper")
    p.add_argument("--url", help="URL HTML-a na narodne-novine.nn.hr")
    p.add_argument("--name", help="Ime zakona / pravilnika")
    p.add_argument("--reference", help="NN broj (npr. 'NN 120/2016')")
    p.add_argument("--output", type=Path, help="Output direktorij")
    p.add_argument("--batch", action="store_true",
                   help="Pokreni sve zakone iz BATCH_LEGISLATION konfige")
    p.add_argument(
        "--batch-root", type=Path, default=Path("data/01-zakoni"),
        help="Root direktorij za batch (default: data/01-zakoni)",
    )
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument("--force", action="store_true", help="Re-fetch HTML čak i ako postoji")
    p.add_argument("--delay", type=float, default=2.0,
                   help="Razmak između HTTP poziva u batch modu (sec)")
    return p.parse_args()


def download_html(url: str, target: Path, *, timeout: float, force: bool) -> str:
    if target.exists() and not force:
        return target.read_text(encoding="utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"  Fetching {url}", flush=True)
    response = httpx.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
        follow_redirects=True,
    )
    response.raise_for_status()
    target.write_text(response.text, encoding="utf-8")
    return response.text


def parse_articles(html: str) -> list[dict[str, Any]]:
    """Walk the body, splitting on each 'Članak N.' marker. Identično
    parse_zjn.py logici — Narodne novine HTML format je dosljedan."""
    soup = BeautifulSoup(html, "lxml")
    body = soup.find("body") or soup

    paragraphs: list[tuple[str, str]] = []
    for el in body.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6"]):
        text = el.get_text(" ", strip=True)
        if text:
            paragraphs.append((el.name, text))

    articles: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    current_glava: str | None = None
    current_dio: str | None = None

    for _kind, text in paragraphs:
        m = ARTICLE_HEADER_RE.match(text)
        if m is not None:
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
            upper = text.upper()
            if upper.startswith("DIO "):
                current_dio = text
            elif upper.startswith("GLAVA "):
                current_glava = text
            continue
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


def write_outputs(
    articles: list[dict[str, Any]],
    *,
    root: Path,
    name: str,
    reference: str,
    url: str,
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    jsonl_path = root / "articles.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as fh:
        for art in articles:
            fh.write(json.dumps(art, ensure_ascii=False) + "\n")
    metadata = {
        "title": name,
        "reference": reference,
        "url": url,
        "scraped_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "article_count": len(articles),
    }
    (root / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def scrape_one(
    url: str,
    name: str,
    reference: str,
    output: Path,
    *,
    timeout: float,
    force: bool,
) -> int:
    """Skidaj jedan zakon. Vraća broj parsiranih članaka."""
    html_filename = url.rstrip("/").rsplit("/", 1)[-1]
    html_path = output / html_filename
    try:
        html = download_html(url, html_path, timeout=timeout, force=force)
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL fetch: {exc}", flush=True)
        return 0
    articles = parse_articles(html)
    if not articles:
        print(f"  WARN: 0 članaka pronađeno (HTML format drugačiji?)", flush=True)
        return 0
    write_outputs(
        articles,
        root=output,
        name=name,
        reference=reference,
        url=url,
    )
    return len(articles)


def main() -> int:
    args = parse_args()

    if args.batch:
        batch_root = args.batch_root.resolve()
        total = 0
        for i, item in enumerate(BATCH_LEGISLATION, 1):
            output = batch_root / item["subdir"]
            print(
                f"[{i}/{len(BATCH_LEGISLATION)}] {item['name']} ({item['reference']})",
                flush=True,
            )
            n = scrape_one(
                item["url"],
                item["name"],
                item["reference"],
                output,
                timeout=args.timeout,
                force=args.force,
            )
            print(f"  {n} članaka", flush=True)
            total += n
            if i < len(BATCH_LEGISLATION):
                import time
                time.sleep(args.delay)
        print(f"\nDone. Total {total} članaka iz {len(BATCH_LEGISLATION)} zakona.")
        return 0

    if not (args.url and args.name and args.reference and args.output):
        print("Single mode treba: --url --name --reference --output", file=sys.stderr)
        return 2
    n = scrape_one(
        args.url,
        args.name,
        args.reference,
        args.output.resolve(),
        timeout=args.timeout,
        force=args.force,
    )
    print(f"Done. {n} članaka.")
    return 0 if n > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
