"""Store schemas."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StoreBase(BaseModel):
    name: str
    slug: str
    website_url: str | None = None
    logo_url: str | None = None


class StoreRead(StoreBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
