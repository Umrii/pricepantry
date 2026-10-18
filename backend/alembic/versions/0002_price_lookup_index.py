"""price lookup index: composite (product_id, scraped_at, id)

Replaces the single-column index on ``prices.product_id`` with a composite that
serves the per-product latest-price lookup and bounded history reads
(``WHERE product_id = ? ORDER BY scraped_at DESC, id DESC``). Index-only change;
no data is touched.

Revision ID: 0002_price_index
Revises: 0001_initial
Create Date: 2026-10-18
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_price_index"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_prices_product_scraped", "prices", ["product_id", "scraped_at", "id"]
    )
    # The composite index has product_id as its leading column, so the old
    # single-column index is redundant.
    op.drop_index("ix_prices_product_id", table_name="prices")


def downgrade() -> None:
    op.create_index("ix_prices_product_id", "prices", ["product_id"])
    op.drop_index("ix_prices_product_scraped", table_name="prices")
