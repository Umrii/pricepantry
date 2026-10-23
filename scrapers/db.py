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
    Index,
    Numeric,
    String,
    UniqueConstraint,
    create_engine,
    func,
    select,
    text,
)
from sqlalchemy.exc import IntegrityError
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
    __table_args__ = (
        UniqueConstraint("store_id", "url", name="uq_product_store_url"),
        # Preferred identity: one row per (store, external_id) when known.
        # Mirrors backend/app/models/product.py and migration 0003.
        Index(
            "uq_products_store_external",
            "store_id",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
    )

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


@dataclass
class PersistSummary:
    """Counts for one persistence pass, for scraper diagnostics."""

    attempted: int = 0   # scraped products handed to persist()
    created: int = 0     # new product rows
    matched: int = 0     # existing product rows updated
    persisted: int = 0   # price observations inserted (successful)
    skipped: int = 0     # products with no valid price → no observation

    def as_line(self) -> str:
        return (
            f"attempted={self.attempted} created={self.created} "
            f"matched={self.matched} persisted={self.persisted} "
            f"skipped={self.skipped}"
        )


def is_valid_price(price: Decimal | None) -> bool:
    """A price is only valid (storable) when it is a positive amount.

    Guards against a failed extraction (``None``) or a bogus ``£0.00`` becoming
    a misleading price observation.
    """
    return price is not None and price > 0


def normalize_url(url: str | None) -> str | None:
    """Deliberate, conservative URL normalisation for fallback matching.

    Trims surrounding whitespace and a single trailing slash so that
    ``.../products/123`` and ``.../products/123/`` are treated as one listing.
    We intentionally do NOT touch scheme/host/query — over-normalising risks
    merging genuinely distinct listings. The retailer ``external_id`` remains
    the preferred identity; URL is only the fallback.
    """
    if not url:
        return url
    u = url.strip()
    if len(u) > 1 and u.endswith("/"):
        u = u[:-1]
    return u


def _find_existing_product(
    db: Session, store: Store, item: ScrapedProduct, url: str | None
) -> Product | None:
    """Locate an existing product by retailer external_id first, then URL.

    Both lookups are scoped to ``store_id`` so identical external IDs or URLs
    from different retailers can never collide.
    """
    product = None
    if item.external_id:
        product = db.scalar(
            select(Product).where(
                Product.store_id == store.id,
                Product.external_id == item.external_id,
            )
        )
    if product is None and url:
        product = db.scalar(
            select(Product).where(Product.store_id == store.id, Product.url == url)
        )
    return product


def _refresh_metadata(product: Product, item: ScrapedProduct, url: str | None) -> None:
    product.name = item.name or product.name
    product.brand = item.brand or product.brand
    product.weight = item.weight or product.weight
    product.category = item.category or product.category
    product.image_url = item.image_url or product.image_url
    product.url = url or product.url


def persist(db: Session, store: Store, items: list[ScrapedProduct]) -> PersistSummary:
    """Upsert products and append a fresh price observation for each valid one.

    Products are matched on the store-native ``external_id`` first (stable
    across URL format changes), then on normalised URL — always scoped to the
    store. Every scrape appends a new price row; history is never overwritten.

    Concurrency: creation goes through a SAVEPOINT. If a competing scraper
    inserts the same identity first, the unique constraint raises
    ``IntegrityError``; the savepoint is rolled back (the outer transaction and
    session stay usable), and we re-query and reuse the winning row so the price
    observation attaches to the correct product and no duplicate is created.

    Logs one diagnostic line per product and returns a :class:`PersistSummary`.
    """
    summary = PersistSummary(attempted=len(items))
    for item in items:
        url = normalize_url(item.url)
        ref = item.external_id or url
        product = _find_existing_product(db, store, item, url)

        if product is None:
            try:
                with db.begin_nested():  # SAVEPOINT
                    product = Product(
                        store_id=store.id,
                        external_id=item.external_id,
                        name=item.name,
                        brand=item.brand,
                        weight=item.weight,
                        category=item.category,
                        image_url=item.image_url,
                        url=url,
                    )
                    db.add(product)
                    db.flush()
                summary.created += 1
                disposition = "created"
            except IntegrityError:
                # A concurrent insert won; reuse the existing row.
                product = _find_existing_product(db, store, item, url)
                if product is None:
                    summary.skipped += 1
                    print(
                        f"[persist] {store.slug} {ref} integrity conflict with no "
                        f"matching row -> skipped"
                    )
                    continue
                _refresh_metadata(product, item, url)
                summary.matched += 1
                disposition = "matched (after conflict)"
        else:
            _refresh_metadata(product, item, url)
            summary.matched += 1
            disposition = "matched"

        if is_valid_price(item.price):
            db.add(
                Price(
                    product_id=product.id,
                    price=item.price,
                    currency="GBP",
                    unit_price=item.unit_price,
                    in_stock=item.in_stock,
                )
            )
            summary.persisted += 1
            print(
                f"[persist] {store.slug} {ref} {disposition} "
                f"price={item.price} -> observation persisted"
            )
        else:
            summary.skipped += 1
            reason = "no price extracted" if item.price is None else "non-positive price"
            print(
                f"[persist] {store.slug} {ref} {disposition} "
                f"-> skipped observation ({reason})"
            )

    try:
        db.commit()
    except Exception as exc:  # pragma: no cover - defensive, exercised in tests
        db.rollback()
        print(f"[persist] DB ERROR committing {store.slug} batch: {exc!r}")
        raise
    return summary
