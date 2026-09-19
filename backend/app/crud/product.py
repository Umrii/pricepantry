"""Query helpers for products and their prices."""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.price import Price
from app.models.product import Product
from app.schemas.product import ProductDetail, ProductRead


def _base_query():
    """Products with their store eager-loaded and prices for latest-price derivation."""
    return (
        select(Product)
        .options(joinedload(Product.store), selectinload(Product.prices))
        .order_by(Product.name.asc())
    )


def list_products(
    db: Session, *, page: int, page_size: int, category: str | None = None
) -> tuple[list[Product], int]:
    query = _base_query()
    count_query = select(func.count(Product.id))

    if category:
        query = query.where(Product.category == category)
        count_query = count_query.where(Product.category == category)

    total = db.scalar(count_query) or 0
    items = (
        db.scalars(query.offset((page - 1) * page_size).limit(page_size)).unique().all()
    )
    return list(items), total


def search_products(
    db: Session, *, q: str, page: int, page_size: int
) -> tuple[list[Product], int]:
    pattern = f"%{q}%"
    condition = or_(Product.name.ilike(pattern), Product.brand.ilike(pattern))

    query = _base_query().where(condition)
    total = db.scalar(select(func.count(Product.id)).where(condition)) or 0
    items = (
        db.scalars(query.offset((page - 1) * page_size).limit(page_size)).unique().all()
    )
    return list(items), total


def get_product(db: Session, product_id: int) -> Product | None:
    query = (
        select(Product)
        .options(joinedload(Product.store), selectinload(Product.prices))
        .where(Product.id == product_id)
    )
    return db.scalars(query).unique().one_or_none()


# --------------------------------------------------------------------------- #
# Serialization helpers — turn ORM objects into API schemas.
# --------------------------------------------------------------------------- #
def _latest_price(product: Product) -> Price | None:
    # Product.prices is ordered by scraped_at desc at the relationship level.
    return product.prices[0] if product.prices else None


def to_read(product: Product) -> ProductRead:
    latest = _latest_price(product)
    return ProductRead(
        id=product.id,
        store_id=product.store_id,
        external_id=product.external_id,
        name=product.name,
        brand=product.brand,
        weight=product.weight,
        category=product.category,
        image_url=product.image_url,
        url=product.url,
        store=product.store,
        latest_price=latest.price if latest else None,
        currency=latest.currency if latest else None,
    )


def to_detail(product: Product) -> ProductDetail:
    latest = _latest_price(product)
    return ProductDetail(
        id=product.id,
        store_id=product.store_id,
        external_id=product.external_id,
        name=product.name,
        brand=product.brand,
        weight=product.weight,
        category=product.category,
        image_url=product.image_url,
        url=product.url,
        store=product.store,
        latest_price=latest.price if latest else None,
        currency=latest.currency if latest else None,
        price_history=list(product.prices),
    )
