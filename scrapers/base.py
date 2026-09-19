"""Abstract scraper interface.

Phase 2 adds Asda / Sainsbury's / Morrisons by subclassing ``AbstractScraper``
and implementing the three methods below — the orchestration in ``run.py`` stays
unchanged.

        AbstractScraper
              |
    -----------------------------------
    |         |          |            |
  Tesco     Asda     Sainsbury    Morrisons
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from db import ScrapedProduct


class AbstractScraper(ABC):
    #: URL-friendly identifier, e.g. "tesco".
    slug: str = ""
    #: Human-readable store name.
    store_name: str = ""
    #: Store homepage.
    website_url: str = ""

    @abstractmethod
    def scrape_categories(self) -> list[str]:
        """Return the list of category / search terms this run will cover."""

    @abstractmethod
    def scrape_products(self, category: str) -> list[ScrapedProduct]:
        """Scrape all products for a single category (across its pages)."""

    @abstractmethod
    def scrape_price(self, raw: dict) -> Decimal | None:
        """Extract a normalized price from a raw product record."""

    def run(self) -> list[ScrapedProduct]:
        """Scrape every category and return a de-duplicated product list."""
        seen: set[str] = set()
        results: list[ScrapedProduct] = []
        for category in self.scrape_categories():
            for product in self.scrape_products(category):
                if product.url in seen:
                    continue
                seen.add(product.url)
                results.append(product)
        return results
