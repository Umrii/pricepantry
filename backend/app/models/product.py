"""Product model — a single store's catalogue listing.

Cross-store product matching (Phase 6) will link these rows together via a
separate layer, so no schema change is needed here.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = (
        # A given URL uniquely identifies a listing within a store.
        UniqueConstraint("store_id", "url", name="uq_product_store_url"),
        # The retailer's own product id is the preferred identity: enforce one
        # row per (store, external_id) when the external_id is known. Partial so
        # that rows without an external_id (URL-only) are unconstrained here.
        Index(
            "uq_products_store_external",
            "store_id",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Store-native identifier (e.g. Tesco product id), when available.
    external_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)

    name: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    brand: Mapped[str | None] = mapped_column(String(200), index=True, nullable=True)
    weight: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str | None] = mapped_column(String(200), index=True, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)

    store: Mapped["Store"] = relationship(back_populates="products")  # noqa: F821
    prices: Mapped[list["Price"]] = relationship(  # noqa: F821
        back_populates="product",
        cascade="all, delete-orphan",
        # Newest first, with id as a deterministic tiebreak for identical
        # timestamps so ``prices[0]`` is always the single latest observation.
        order_by="Price.scraped_at.desc(), Price.id.desc()",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Product {self.name!r}>"
