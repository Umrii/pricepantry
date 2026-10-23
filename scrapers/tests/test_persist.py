"""Tests for persistence, price validation and scraper diagnostics.

Uses an in-memory SQLite database and the scraper's own ORM models — no live
Tesco requests and no real Postgres.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import db as scraper_db
from db import Base, Price, Product, ScrapedProduct, is_valid_price, persist


def _item_no_ext(url: str, price: str = "1.00", name: str = "No-ID Milk"):
    return ScrapedProduct(
        name=name, url=url, price=Decimal(price), external_id=None, category="Milk"
    )


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


# --------------------------------------------------------------------------- #
# Product identity & matching
# --------------------------------------------------------------------------- #
def test_match_by_external_id_across_url_change(session):
    store = _store(session)
    persist(session, store, [_item(
        ext="500", price="1.00",
        url="https://www.tesco.com/groceries/en-GB/products/500")])
    persist(session, store, [_item(
        ext="500", price="1.10",
        url="https://www.tesco.com/shop/en-GB/products/500")])
    assert session.scalar(select(func.count(Product.id))) == 1   # matched by ext id
    assert session.scalar(select(func.count(Price.id))) == 2     # history preserved
    assert session.scalar(select(Product.url)).endswith("/shop/en-GB/products/500")


def test_url_fallback_when_external_id_missing(session):
    store = _store(session)
    u = "https://www.tesco.com/shop/en-GB/products/700"
    persist(session, store, [_item_no_ext(u, "1.00")])
    persist(session, store, [_item_no_ext(u, "1.20")])   # same url -> matched
    assert session.scalar(select(func.count(Product.id))) == 1
    assert session.scalar(select(func.count(Price.id))) == 2


def test_url_trailing_slash_normalised_to_same_product(session):
    store = _store(session)
    base = "https://www.tesco.com/shop/en-GB/products/710"
    persist(session, store, [_item_no_ext(base, "1.00")])
    persist(session, store, [_item_no_ext(base + "/", "1.10")])  # trailing slash
    assert session.scalar(select(func.count(Product.id))) == 1


def test_missing_external_id_distinct_urls_are_separate(session):
    store = _store(session)
    persist(session, store, [
        _item_no_ext("https://www.tesco.com/shop/en-GB/products/701", "1.00"),
        _item_no_ext("https://www.tesco.com/shop/en-GB/products/702", "2.00"),
    ])
    assert session.scalar(select(func.count(Product.id))) == 2


def test_same_external_id_different_retailers_not_merged(session):
    tesco = scraper_db.get_or_create_store(session, "tesco", "Tesco", "https://tesco.com")
    asda = scraper_db.get_or_create_store(session, "asda", "Asda", "https://asda.com")
    persist(session, tesco, [_item(ext="900", price="1.00", url="https://tesco.com/p/900")])
    persist(session, asda, [_item(ext="900", price="2.00", url="https://asda.com/p/900")])
    rows = session.scalars(select(Product).where(Product.external_id == "900")).all()
    assert len(rows) == 2
    assert {r.store_id for r in rows} == {tesco.id, asda.id}


# --------------------------------------------------------------------------- #
# Database integrity & concurrency
# --------------------------------------------------------------------------- #
def test_unique_index_blocks_duplicate_external_id(session):
    store = _store(session)
    session.add(Product(store_id=store.id, external_id="950", name="A",
                        url="https://tesco.com/p/950-a"))
    session.flush()
    session.add(Product(store_id=store.id, external_id="950", name="B",
                        url="https://tesco.com/p/950-b"))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_null_external_ids_do_not_collide(session):
    # The partial/standard unique index must allow many URL-only rows.
    store = _store(session)
    session.add(Product(store_id=store.id, external_id=None, name="X",
                        url="https://tesco.com/p/x"))
    session.add(Product(store_id=store.id, external_id=None, name="Y",
                        url="https://tesco.com/p/y"))
    session.flush()  # must not raise
    assert session.scalar(select(func.count(Product.id))) == 2


def test_concurrent_create_recovers_via_requery(session, monkeypatch):
    store = _store(session)
    # A competing scraper already inserted this product.
    session.add(Product(store_id=store.id, external_id="960", name="Existing",
                        url="https://www.tesco.com/shop/en-GB/products/960"))
    session.commit()

    real = scraper_db._find_existing_product
    calls = {"n": 0}

    def flaky(db, store_, item, url):
        calls["n"] += 1
        if calls["n"] == 1:
            return None  # simulate the check-missed race window
        return real(db, store_, item, url)

    monkeypatch.setattr(scraper_db, "_find_existing_product", flaky)

    summary = persist(session, store, [_item(
        ext="960", price="1.50",
        url="https://www.tesco.com/shop/en-GB/products/960")])

    assert session.scalar(select(func.count(Product.id))) == 1   # no duplicate
    assert (summary.created, summary.matched, summary.persisted) == (0, 1, 1)
    assert session.scalar(select(func.count(Price.id))) == 1     # price kept


# --------------------------------------------------------------------------- #
# Idempotent ingestion — unchanged prices are re-confirmed, not duplicated
# --------------------------------------------------------------------------- #
def test_unchanged_price_is_idempotent(session):
    store = _store(session)
    s1 = persist(session, store, [_item(ext="800", price="2.75")])
    s2 = persist(session, store, [_item(ext="800", price="2.75")])  # rerun, same price
    assert session.scalar(select(func.count(Product.id))) == 1
    assert session.scalar(select(func.count(Price.id))) == 1        # NOT duplicated
    assert (s1.persisted, s1.unchanged) == (1, 0)
    assert (s2.persisted, s2.unchanged) == (0, 1)


def test_price_change_creates_new_observation(session):
    store = _store(session)
    persist(session, store, [_item(ext="801", price="2.75")])
    persist(session, store, [_item(ext="801", price="2.80")])      # genuine change
    persist(session, store, [_item(ext="801", price="2.75")])      # changed back
    assert session.scalar(select(func.count(Price.id))) == 3       # all changes kept


def test_unchanged_price_bumps_last_seen_at(session):
    store = _store(session)
    prod = Product(store_id=store.id, external_id="802", name="Milk",
                   url="https://www.tesco.com/shop/en-GB/products/802")
    session.add(prod)
    session.flush()
    # Naive datetime: SQLite's now() (used by persist) returns naive values, so
    # the baseline must be naive too for an apples-to-apples comparison. On
    # Postgres both sides are tz-aware; the ordering assertion holds either way.
    old = datetime(2026, 1, 1)
    session.add(Price(product_id=prod.id, price=Decimal("2.75"), currency="GBP",
                      in_stock=True, scraped_at=old, last_seen_at=old))
    session.commit()

    persist(session, store, [_item(ext="802", price="2.75")])
    rows = session.scalars(select(Price)).all()
    assert len(rows) == 1                       # no new row
    assert rows[0].last_seen_at > old           # re-confirmed
    assert rows[0].scraped_at == old            # original change time preserved
