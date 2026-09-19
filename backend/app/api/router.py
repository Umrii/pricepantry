"""Aggregate all API routers under one object."""
from fastapi import APIRouter

from app.api.routes import health, prices, products, search

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(products.router)
api_router.include_router(search.router)
api_router.include_router(prices.router)
