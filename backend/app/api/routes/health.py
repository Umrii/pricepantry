"""Liveness / readiness endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    """Return ok if the API is up and the database is reachable."""
    db_ok = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # pragma: no cover - defensive
        db_ok = "unavailable"
    return {"status": "ok", "database": db_ok}
