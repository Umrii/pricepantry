"""Price schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PriceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    price: Decimal
    currency: str
    unit_price: str | None = None
    in_stock: bool
    # When this price was first observed, and most recently re-confirmed (UTC).
    scraped_at: datetime
    last_seen_at: datetime | None = None
