"""Top-level API router — aggregates versioned sub-routers."""

from fastapi import APIRouter

from app.api.v1.router import create_api_v1_router


def create_api_router(api_v1_prefix: str = "/api/v1") -> APIRouter:
    """Build the root API router with all versioned sub-routers."""
    router = APIRouter()
    router.include_router(create_api_v1_router(api_v1_prefix))
    return router
