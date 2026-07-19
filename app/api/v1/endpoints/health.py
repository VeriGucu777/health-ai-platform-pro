"""Health check endpoints — used by load balancers and monitoring."""

from fastapi import APIRouter

from app.api.deps import AppSettings

router = APIRouter()


@router.get("/health", summary="Health check")
async def health_check(settings: AppSettings) -> dict[str, str]:
    """Return service health status."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/ready", summary="Readiness check")
async def readiness_check() -> dict[str, str]:
    """Return readiness status — extend with DB connectivity checks later."""
    return {"status": "ready"}
