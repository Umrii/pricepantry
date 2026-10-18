"""Product search endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.crud import product as crud
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.product import ProductRead

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=Page[ProductRead])
def search(
    db: Session = Depends(get_db),
    q: str = Query(..., min_length=1, description="Search term (name or brand)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[ProductRead]:
    items, total = crud.search_products(db, q=q, page=page, page_size=page_size)
    return Page.create(items, total=total, page=page, page_size=page_size)
