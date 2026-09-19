"""Database layer for the scraper.

These ORM models intentionally mirror ``backend/app/models`` so the scraper can
write into the same schema (created & migrated by the backend's Alembic).
Tables are NOT created here — the backend owns migrations. In Phase 2 this
should be extracted into a shared package to remove the duplication.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    create_engine,
    func,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

from config import DATABASE_URL


class Base(DeclarativeBase):
    pass


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    website_url: Mapped[str | None] = mapped_column(String(500))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("store_id", "url", name="uq_product_store_url"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"))
    external_id: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(500))
    brand: Mapped[str | None] = mapped_column(String(200))
    weight: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[str | None] = mapped_column(String(200))
    image_url: Mapped[str | None] = mapped_column(String(1000))
    url: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Price(Base):
    __tablename__ = "prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="GBP")
    unit_price: Mapped[str | None] = mapped_column(String(100))
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True)


@dataclass
class ScrapedProduct:
    """A normalized product record produced by a scraper."""

    name: str
    url: str
    price: Decimal | None
    brand: str | None = None
    weight: str | None = None
    category: str | None = None
    image_url: str | None = None
    external_id: str | None = None
    unit_price: str | None = None
    in_stock: bool = True


def get_or_create_store(db: Session, slug: str, name: str, website_url: str) -> Store:
    store = db.scalar(select(Store).where(Store.slug == slug))
    if store is None:
        store = Store(slug=slug, name=name, website_url=website_url)
        db.add(store)
        db.flush()
    return store


def persist(db: Session, store: Store, items: list[ScrapedProduct]) -> tuple[int, int]:
    """Upsert products (by URL) and insert a fresh price row for each.

    Returns (new_products, price_rows_inserted).
    """
    new_products = 0
    price_rows = 0
    for item in items:
        # Prefer matching on the store-native external_id (stable across URL
        # format changes, e.g. /groceries/ vs /shop/); fall back to URL.
        product = None
        if item.external_id:
            product = db.scalar(
                select(Product).where(
                    Product.store_id == store.id,
                    Product.external_id == item.external_id,
                )
            )
        if product is None:
            product = db.scalar(
                select(Product).where(
                    Product.store_id == store.id, Product.url == item.url
                )
            )
        if product is None:
            product = Product(
                store_id=store.id,
                external_id=item.external_id,
                name=item.name,
                brand=item.brand,
                weight=item.weight,
                category=item.category,
                image_url=item.image_url,
                url=item.url,
            )
            db.add(product)
            db.flush()
            new_products += 1
        else:
            # Refresh mutable metadata that may have changed.
            product.name = item.name or product.name
            product.brand = item.brand or product.brand
            product.weight = item.weight or product.weight
            product.category = item.category or product.category
            product.image_url = item.image_url or product.image_url
            product.url = item.url or product.url

        if item.price is not None:
            db.add(
                Price(
                    product_id=product.id,
                    price=item.price,
                    currency="GBP",
                    unit_price=item.unit_price,
                    in_stock=item.in_stock,
                )
            )
            price_rows += 1

    db.commit()
    return new_products, price_rows
