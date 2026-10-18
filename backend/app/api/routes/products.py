"""Product listing and detail endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.crud import product as crud
from app.crud.product import DEFAULT_HISTORY_LIMIT, MAX_HISTORY_LIMIT
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.product import ProductDetail, ProductRead

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=Page[ProductRead])
def list_products(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = Query(None, description="Filter by category"),
) -> Page[ProductRead]:
    items, total = crud.list_products(
        db, page=page, page_size=page_size, category=category
    )
    return Page.create(items, total=total, page=page, page_size=page_size)


@router.get("/{product_id}", response_model=ProductDetail)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    history_limit: int = Query(
        DEFAULT_HISTORY_LIMIT,
        ge=1,
        le=MAX_HISTORY_LIMIT,
        description="Max number of historical price observations returned",
    ),
) -> ProductDetail:
    product = crud.get_product(db, product_id, history_limit=history_limit)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
