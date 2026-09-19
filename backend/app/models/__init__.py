"""Import all models so they register on ``Base.metadata`` (used by Alembic)."""
from app.models.price import Price
from app.models.product import Product
from app.models.store import Store

__all__ = ["Store", "Product", "Price"]
