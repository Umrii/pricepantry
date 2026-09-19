"""Product schemas."""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.schemas.price import PriceRead
from app.schemas.store import StoreRead


class ProductBase(BaseModel):
    name: str
    brand: str | None = None
    weight: str | None = None
    category: str | None = None
    image_url: str | None = None
    url: str


class ProductRead(ProductBase):
    """List representation — includes the store and the latest price."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    external_id: str | None = None
    store: StoreRead
    latest_price: Decimal | None = None
    currency: str | None = None


class ProductDetail(ProductRead):
    """Detail representation — adds the full price history."""

    price_history: list[PriceRead] = []
