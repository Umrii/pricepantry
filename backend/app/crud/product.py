"""Query helpers for products and their prices.

Latest-price selection is deterministic and done database-side: list and search
pages fetch only the single latest *valid* price per product (one extra query,
no N+1, no full history loaded), while the detail view loads a bounded,
chronologically-ordered slice of history for the chart.
"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.price import Price
from app.models.product import Product
from app.schemas.product import ProductDetail, ProductRead

# A price observation only counts as the "latest valid price" when it is a
# positive amount; a failed/invalid scrape can never have persisted a <= 0 row
# (see scraper validation), but we also guard on read.
_VALID_PRICE = Price.price > 0

# Deterministic "newest first" ordering, with id breaking identical-timestamp ties.
_LATEST_ORDER = (Price.scraped_at.desc(), Price.id.desc())

# Default and maximum number of historical observations returned for the chart.
DEFAULT_HISTORY_LIMIT = 90
MAX_HISTORY_LIMIT = 1000


def _base_query():
    """Products with their store eager-loaded (prices are fetched separately)."""
    return (
        select(Product)
        .options(joinedload(Product.store))
        .order_by(Product.name.asc())
    )


def latest_prices_for(db: Session, product_ids: list[int]) -> dict[int, Price]:
    """Return {product_id: latest valid Price} for the given products.

    Uses a single windowed query so a listing page does not load full price
    history. ``row_number()`` over ``(scraped_at DESC, id DESC)`` picks exactly
    one deterministic row per product.
    """
    if not product_ids:
        return {}
    rn = func.row_number().over(
        partition_by=Price.product_id, order_by=_LATEST_ORDER
    ).label("rn")
    ranked = (
        select(Price.id.label("price_id"), rn)
        .where(Price.product_id.in_(product_ids), _VALID_PRICE)
        .subquery()
    )
    latest_ids = select(ranked.c.price_id).where(ranked.c.rn == 1)
    rows = db.scalars(select(Price).where(Price.id.in_(latest_ids))).all()
    return {p.product_id: p for p in rows}


def list_products(
    db: Session, *, page: int, page_size: int, category: str | None = None
) -> tuple[list[ProductRead], int]:
    query = _base_query()
    count_query = select(func.count(Product.id))
    if category:
        query = query.where(Product.category == category)
        count_query = count_query.where(Product.category == category)

    total = db.scalar(count_query) or 0
    products = list(
        db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    )
    latest = latest_prices_for(db, [p.id for p in products])
    return [to_read(p, latest.get(p.id)) for p in products], total


def search_products(
    db: Session, *, q: str, page: int, page_size: int
) -> tuple[list[ProductRead], int]:
    pattern = f"%{q}%"
    condition = or_(Product.name.ilike(pattern), Product.brand.ilike(pattern))

    query = _base_query().where(condition)
    total = db.scalar(select(func.count(Product.id)).where(condition)) or 0
    products = list(
        db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    )
    latest = latest_prices_for(db, [p.id for p in products])
    return [to_read(p, latest.get(p.id)) for p in products], total


def get_product(
    db: Session, product_id: int, *, history_limit: int = DEFAULT_HISTORY_LIMIT
) -> ProductDetail | None:
    product = db.scalars(
        select(Product).options(joinedload(Product.store)).where(Product.id == product_id)
    ).one_or_none()
    if product is None:
        return None

    limit = max(1, min(history_limit, MAX_HISTORY_LIMIT))
    history = list(
        db.scalars(
            select(Price)
            .where(Price.product_id == product_id, _VALID_PRICE)
            .order_by(*_LATEST_ORDER)
            .limit(limit)
        ).all()
    )
    return to_detail(product, history)


# --------------------------------------------------------------------------- #
# Serialization helpers — turn ORM objects into API schemas.
# --------------------------------------------------------------------------- #
def to_read(product: Product, latest: Price | None) -> ProductRead:
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
        # "Last observed" = when the current price was last confirmed, which for
        # an unchanged price is more recent than when it first changed.
        price_updated_at=latest.last_seen_at if latest else None,
    )


def to_detail(product: Product, history: list[Price]) -> ProductDetail:
    # history is newest-first; element 0 is the latest valid observation.
    latest = history[0] if history else None
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
        price_updated_at=latest.last_seen_at if latest else None,
        price_history=history,
    )
