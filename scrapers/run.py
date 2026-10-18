"""Scraper entrypoint: scrape Tesco and persist into Postgres.

Usage:
    python -m run                 # scrape and write to the database
    python -m run --dry-run       # scrape and print, no DB writes
    python -m run --categories milk bread
"""
from __future__ import annotations

import argparse
import sys

import config
from db import SessionLocal, get_or_create_store, persist
from tesco.scraper import TescoScraper


def main() -> int:
    parser = argparse.ArgumentParser(description="Price Pantry scraper")
    parser.add_argument("--dry-run", action="store_true", help="do not write to DB")
    parser.add_argument("--categories", nargs="*", help="override search terms")
    parser.add_argument("--max-pages", type=int, default=config.MAX_PAGES)
    parser.add_argument("--headful", action="store_true", help="run a visible browser")
    args = parser.parse_args()

    scraper = TescoScraper(
        max_pages=args.max_pages,
        headless=not args.headful and config.HEADLESS,
        categories=args.categories,
    )

    print(
        f"[run] scraping {scraper.store_name} — "
        f"categories={scraper.scrape_categories()} max_pages={scraper.max_pages} "
        f"headless={scraper.headless}"
    )
    products = scraper.run()
    print(f"[run] scraped {len(products)} unique products")

    if not products:
        print(
            "[run] No products scraped. Tesco may have blocked the request, or the "
            "selectors changed. Try --headful, or adjust selectors in "
            "tesco/scraper.py. The app still runs on seed/previous data."
        )
        return 1

    if args.dry_run:
        for pr in products[:20]:
            print(f"  - {pr.name} | {pr.price} | {pr.url}")
        print("[run] dry-run: nothing written to the database.")
        return 0

    db = SessionLocal()
    try:
        store = get_or_create_store(
            db, scraper.slug, scraper.store_name, scraper.website_url
        )
        summary = persist(db, store, products)
        print(f"[run] persisted summary: {summary.as_line()}")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
