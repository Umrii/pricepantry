"""Query helpers for price records."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.price import Price


def list_prices(db: Session, *, product_id: int | None = None, limit: int = 500) -> list[Price]:
    query = select(Price).order_by(Price.scraped_at.desc()).limit(limit)
    if product_id is not None:
        query = query.where(Price.product_id == product_id)
    return list(db.scalars(query).all())
