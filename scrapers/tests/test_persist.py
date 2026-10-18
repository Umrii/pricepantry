"""Tests for persistence, price validation and scraper diagnostics.

Uses an in-memory SQLite database and the scraper's own ORM models — no live
Tesco requests and no real Postgres.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import db as scraper_db
from db import Base, Price, Product, ScrapedProduct, is_valid_price, persist


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, future=True)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


def _store(db):
    return scraper_db.get_or_create_store(db, "tesco", "Tesco", "https://tesco.com")


def _item(ext="100", price="2.75", **kw):
    return ScrapedProduct(
        name=kw.get("name", "Arla Big Milk 2L"),
        url=kw.get("url", f"https://www.tesco.com/shop/en-GB/products/{ext}"),
        price=None if price is None else Decimal(price),
        external_id=ext,
        category="Milk",
        unit_price=kw.get("unit_price", "£1.38/litre"),
    )


# --------------------------------------------------------------------------- #
# Price validation
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "value, valid",
    [(Decimal("2.75"), True), (Decimal("0.01"), True),
     (None, False), (Decimal("0.00"), False), (Decimal("-1.00"), False)],
)
def test_is_valid_price(value, valid):
    assert is_valid_price(value) is valid


# --------------------------------------------------------------------------- #
# persist()
# --------------------------------------------------------------------------- #
def test_valid_price_creates_product_and_observation(session):
    store = _store(session)
    summary = persist(session, store, [_item(price="2.75")])
    assert (summary.attempted, summary.created, summary.persisted, summary.skipped) == (
        1, 1, 1, 0,
    )
    assert session.scalar(select(func.count(Price.id))) == 1


def test_missing_price_skips_observation_but_keeps_product(session):
    store = _store(session)
    summary = persist(session, store, [_item(price=None)])
    assert summary.created == 1 and summary.persisted == 0 and summary.skipped == 1
    assert session.scalar(select(func.count(Product.id))) == 1
    assert session.scalar(select(func.count(Price.id))) == 0  # no misleading row


def test_non_positive_price_skipped(session):
    store = _store(session)
    summary = persist(session, store, [_item(price="0.00")])
    assert summary.persisted == 0 and summary.skipped == 1
    assert session.scalar(select(func.count(Price.id))) == 0


def test_rescrape_matches_by_external_id_and_appends_history(session):
    store = _store(session)
    persist(session, store, [_item(ext="287971983", price="2.75")])
    # Same external_id, different URL format + new price -> matched, history appended.
    summary = persist(
        session, store,
        [_item(ext="287971983", price="2.80",
               url="https://www.tesco.com/groceries/en-GB/products/287971983")],
    )
    assert summary.created == 0 and summary.matched == 1 and summary.persisted == 1
    assert session.scalar(select(func.count(Product.id))) == 1      # not duplicated
    assert session.scalar(select(func.count(Price.id))) == 2        # history preserved


def test_logging_reports_context_for_skip(session, capsys):
    store = _store(session)
    persist(session, store, [_item(ext="999", price=None)])
    out = capsys.readouterr().out
    assert "tesco" in out and "999" in out and "skipped" in out and "no price" in out
