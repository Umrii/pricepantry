"""Price records endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.crud import price as crud
from app.db.session import get_db
from app.schemas.price import PriceRead

router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("", response_model=list[PriceRead])
def list_prices(
    db: Session = Depends(get_db),
    product_id: int | None = Query(None, description="Filter by product id"),
    limit: int = Query(500, ge=1, le=2000),
) -> list[PriceRead]:
    return crud.list_prices(db, product_id=product_id, limit=limit)
