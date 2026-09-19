"""Smoke tests for the API against a temporary SQLite database.

These verify wiring (routes, schemas, CRUD) without needing Postgres.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.price import Price
from app.models.product import Product
from app.models.store import Store


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)

    # Seed one store + product + price.
    db = TestingSession()
    store = Store(name="Tesco", slug="tesco", website_url="https://tesco.com")
    db.add(store)
    db.flush()
    product = Product(
        store_id=store.id,
        name="Tesco Semi Skimmed Milk 2.272L",
        brand="Tesco",
        weight="2.272L",
        category="Milk",
        url="https://tesco.com/p/1",
    )
    db.add(product)
    db.flush()
    db.add(Price(product_id=product.id, price=Decimal("1.65"), currency="GBP", in_stock=True))
    db.commit()
    db.close()

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_products(client):
    r = client.get("/products")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["name"].startswith("Tesco Semi Skimmed Milk")
    assert item["latest_price"] == "1.65"
    assert item["store"]["slug"] == "tesco"


def test_search(client):
    r = client.get("/search", params={"q": "milk"})
    assert r.status_code == 200
    assert r.json()["total"] == 1

    r = client.get("/search", params={"q": "zzzz"})
    assert r.json()["total"] == 0


def test_product_detail_and_history(client):
    r = client.get("/products/1")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == 1
    assert len(body["price_history"]) == 1

    assert client.get("/products/999").status_code == 404


def test_prices_endpoint(client):
    r = client.get("/prices", params={"product_id": 1})
    assert r.status_code == 200
    assert len(r.json()) == 1
