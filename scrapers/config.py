"""Scraper configuration from environment variables."""
from __future__ import annotations

import os


def _normalize(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


DATABASE_URL = _normalize(
    os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://pricepantry:pricepantry@localhost:5432/pricepantry",
    )
)

# How many result pages to walk per category/search term.
MAX_PAGES = int(os.environ.get("SCRAPER_MAX_PAGES", "2"))

# Headless is easier to run but more detectable; headful survives bot checks better.
HEADLESS = os.environ.get("SCRAPER_HEADLESS", "true").lower() in {"1", "true", "yes"}
