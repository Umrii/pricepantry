"""price last_seen_at: support idempotent ingestion

Adds ``prices.last_seen_at`` so a rerun that observes an unchanged price
re-confirms it (bumps last_seen_at) instead of inserting a duplicate row.
Existing rows are backfilled to their ``scraped_at`` so current data keeps a
consistent, non-null value with no history loss.

Revision ID: 0004_price_last_seen
Revises: 0003_product_identity
Create Date: 2026-10-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_price_last_seen"
down_revision: Union[str, None] = "0003_product_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add nullable (no default yet) so existing rows start NULL, backfill every
    # pre-existing row from scraped_at, then enforce NOT NULL and set the
    # server default that future inserts use.
    op.add_column(
        "prices",
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE prices SET last_seen_at = scraped_at")
    op.alter_column(
        "prices",
        "last_seen_at",
        nullable=False,
        server_default=sa.text("now()"),
    )


def downgrade() -> None:
    op.drop_column("prices", "last_seen_at")
