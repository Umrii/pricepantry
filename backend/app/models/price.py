"""Price model — a time-series of price observations.

Every scrape inserts a *new* row rather than updating an existing one, which is
exactly what Phase 3 (historical pricing) needs.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Price(Base):
    __tablename__ = "prices"
    __table_args__ = (
        # Serves the per-product latest-price lookup and bounded history reads
        # (WHERE product_id = ? ORDER BY scraped_at DESC, id DESC). A plain
        # btree is scanned backwards for the DESC order. Supersedes the old
        # single-column index on product_id.
        Index("ix_prices_product_scraped", "product_id", "scraped_at", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )

    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="GBP", nullable=False)
    # e.g. "£0.65/100g" — a normalized unit price string when the store provides it.
    unit_price: Mapped[str | None] = mapped_column(String(100), nullable=True)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    product: Mapped["Product"] = relationship(back_populates="prices")  # noqa: F821

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Price {self.price} {self.currency} @ {self.scraped_at:%Y-%m-%d}>"
