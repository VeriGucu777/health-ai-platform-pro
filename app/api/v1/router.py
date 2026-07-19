"""API v1 router — mounts all v1 endpoint modules."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, patients


def create_api_v1_router(prefix: str = "/api/v1") -> APIRouter:
    """Build the v1 API router with a configurable prefix."""
    api_v1_router = APIRouter(prefix=prefix)
    api_v1_router.include_router(health.router, tags=["Health"])
    api_v1_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
    api_v1_router.include_router(patients.router, prefix="/patients", tags=["Patients"])
    return api_v1_router
