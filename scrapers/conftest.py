"""Pytest bootstrap for the scrapers package.

The scraper modules import each other as top-level modules (``from base import
...``, ``from db import ...``), so the scrapers directory must be importable.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# Keep the scraper's DB engine pointed at a harmless localhost default during
# unit tests. Nothing in these tests connects to a database, but this avoids
# depending on whatever DATABASE_URL happens to be set in the environment.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://pricepantry:pricepantry@localhost:5432/pricepantry",
)
