"""Latest-price selection + freshness + bounded history (in-memory SQLite)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.price import Price
from app.models.product import Product
from app.models.store import Store

T0 = datetime(2026, 10, 18, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def db_client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestingSession = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    Base.metadata.create_all(engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestingSession, TestClient(app)
    app.dependency_overrides.clear()


def _store(db: Session) -> Store:
    s = Store(name="Tesco", slug="tesco", website_url="https://tesco.com")
    db.add(s)
    db.flush()
    return s


def _product(db: Session, store: Store, name: str, ext: str) -> Product:
    p = Product(
        store_id=store.id, external_id=ext, name=name, category="Milk",
        url=f"https://tesco.com/p/{ext}",
    )
    db.add(p)
    db.flush()
    return p


def _price(
    db: Session, product: Product, amount: str, scraped_at: datetime,
    last_seen_at: datetime | None = None,
) -> Price:
    pr = Price(
        product_id=product.id, price=Decimal(amount), currency="GBP",
        in_stock=True, scraped_at=scraped_at,
        last_seen_at=last_seen_at or scraped_at,
    )
    db.add(pr)
    db.flush()
    return pr


def test_latest_is_most_recent_even_when_inserted_out_of_order(db_client):
    TestingSession, client = db_client
    db = TestingSession()
    store = _store(db)
    p = _product(db, store, "Milk 2L", "100")
    # Insert newest first, then older ones — selection must not depend on order.
    _price(db, p, "2.00", T0 + timedelta(hours=2))   # latest
    _price(db, p, "1.80", T0)
    _price(db, p, "1.90", T0 + timedelta(hours=1))
    db.commit()
    db.close()

    body = client.get(f"/products/{p.id}").json()
    assert body["latest_price"] == "2.00"
    assert body["price_updated_at"].startswith("2026-10-18T12:00:00")
    # History newest-first, all three observations, chronologically consistent.
    assert [h["price"] for h in body["price_history"]] == ["2.00", "1.90", "1.80"]


def test_price_updated_at_reflects_last_seen_not_change_time(db_client):
    # An unchanged price re-confirmed later: price_updated_at should be the
    # last_seen_at (last confirmation), not scraped_at (when it first changed).
    TestingSession, client = db_client
    db = TestingSession()
    store = _store(db)
    p = _product(db, store, "Milk 2L", "150")
    _price(db, p, "1.80", T0, last_seen_at=T0 + timedelta(hours=6))
    db.commit()
    db.close()

    body = client.get(f"/products/{p.id}").json()
    assert body["latest_price"] == "1.80"
    assert body["price_updated_at"].startswith("2026-10-18T16:00:00")   # last_seen
    assert body["price_history"][0]["scraped_at"].startswith("2026-10-18T10:00:00")


def test_identical_timestamps_broken_by_id(db_client):
    TestingSession, client = db_client
    db = TestingSession()
    store = _store(db)
    p = _product(db, store, "Eggs", "200")
    _price(db, p, "2.50", T0)   # lower id
    _price(db, p, "2.70", T0)   # higher id, same timestamp -> this is "latest"
    db.commit()
    db.close()

    body = client.get(f"/products/{p.id}").json()
    assert body["latest_price"] == "2.70"


def test_zero_price_cannot_replace_valid_latest(db_client):
    TestingSession, client = db_client
    db = TestingSession()
    store = _store(db)
    p = _product(db, store, "Bread", "300")
    _price(db, p, "1.40", T0)                       # valid
    _price(db, p, "0.00", T0 + timedelta(hours=1))  # invalid, newer
    db.commit()
    db.close()

    body = client.get(f"/products/{p.id}").json()
    assert body["latest_price"] == "1.40"            # not the £0.00
    # Invalid rows are excluded from history too.
    assert all(Decimal(h["price"]) > 0 for h in body["price_history"])


def test_product_without_valid_price_is_unavailable(db_client):
    TestingSession, client = db_client
    db = TestingSession()
    store = _store(db)
    p = _product(db, store, "Mystery", "400")   # no price rows at all
    db.commit()
    db.close()

    body = client.get(f"/products/{p.id}").json()
    assert body["latest_price"] is None
    assert body["price_updated_at"] is None
    assert body["price_history"] == []


def test_list_endpoint_reports_latest_and_timestamp(db_client):
    TestingSession, client = db_client
    db = TestingSession()
    store = _store(db)
    p = _product(db, store, "Milk 2L", "100")
    _price(db, p, "1.80", T0)
    _price(db, p, "2.00", T0 + timedelta(hours=2))
    db.commit()
    db.close()

    body = client.get("/products").json()
    item = next(i for i in body["items"] if i["id"] == p.id)
    assert item["latest_price"] == "2.00"
    assert item["price_updated_at"].startswith("2026-10-18T12:00:00")


def test_history_limit_bounds_results(db_client):
    TestingSession, client = db_client
    db = TestingSession()
    store = _store(db)
    p = _product(db, store, "Milk 2L", "100")
    for i in range(5):
        _price(db, p, f"1.{50 + i}", T0 + timedelta(hours=i))
    db.commit()
    db.close()

    body = client.get(f"/products/{p.id}", params={"history_limit": 2}).json()
    assert len(body["price_history"]) == 2            # bounded
    assert body["price_history"][0]["price"] == "1.54"  # still the latest two
    assert body["price_history"][1]["price"] == "1.53"
