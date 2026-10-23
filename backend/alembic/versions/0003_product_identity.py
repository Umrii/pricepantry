"""product identity: dedupe + partial unique index on (store_id, external_id)

Why: the schema previously enforced uniqueness only on (store_id, url), so the
same retailer product reachable via two URL formats (e.g. /groceries/ vs /shop/)
could exist as two rows. This migration:

  1. Consolidates rows that share the same non-null (store_id, external_id) —
     the retailer's own product identity — by reassigning every price
     observation to the lowest-id canonical row (NO price history is lost),
     then removing the now-empty duplicate rows.
  2. Adds a PARTIAL unique index so repeated/concurrent scrapes can no longer
     create duplicates for an identified product. Partial (external_id IS NOT
     NULL) so URL-only rows remain unconstrained here; (store_id, url) still
     covers those via the existing unique constraint.

Safety: the merge only touches rows that are provably the same product (equal
store_id + external_id). All price rows are reassigned, so history is preserved.
The consolidation is data-dependent and is not reversed by downgrade (the index
is dropped, but duplicates are not recreated).

Revision ID: 0003_product_identity
Revises: 0002_price_index
Create Date: 2026-10-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_product_identity"
down_revision: Union[str, None] = "0002_price_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CANON_CTE = """
WITH canon AS (
    SELECT store_id, external_id, MIN(id) AS keep_id
    FROM products
    WHERE external_id IS NOT NULL
    GROUP BY store_id, external_id
    HAVING COUNT(*) > 1
)
"""


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Reassign price observations from duplicate products to the canonical
    #    (lowest-id) product for each (store_id, external_id) group.
    conn.execute(sa.text(
        _CANON_CTE + """
        , dupes AS (
            SELECT p.id AS dup_id, c.keep_id
            FROM products p
            JOIN canon c
              ON p.store_id = c.store_id AND p.external_id = c.external_id
            WHERE p.id <> c.keep_id
        )
        UPDATE prices
        SET product_id = dupes.keep_id
        FROM dupes
        WHERE prices.product_id = dupes.dup_id
        """
    ))

    # 2. Remove the now price-less duplicate product rows.
    conn.execute(sa.text(
        _CANON_CTE + """
        DELETE FROM products p
        USING canon c
        WHERE p.store_id = c.store_id
          AND p.external_id = c.external_id
          AND p.id <> c.keep_id
        """
    ))

    # 3. Enforce retailer product identity going forward.
    op.create_index(
        "uq_products_store_external",
        "products",
        ["store_id", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_products_store_external", table_name="products")
    # Data consolidation is intentionally not reversed.
