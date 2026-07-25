"""Health check endpoints — used by load balancers and monitoring."""

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from app.api.deps import AppSettings
from app.api.schemas.health import HealthResponse, ReadinessResponse
from app.application.services.system_health_service import SystemHealthService
from app.observability.metrics import record_db_health_check

router = APIRouter()


def _health_service(request: Request) -> SystemHealthService:
    return request.app.state.system_health_service


@router.get("/health", summary="Health check", response_model=HealthResponse)
async def health_check(request: Request, settings: AppSettings) -> HealthResponse:
    """Return service liveness metadata while the process is running."""
    service = _health_service(request)
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        uptime_seconds=service.uptime_seconds,
    )


@router.get("/ready", summary="Readiness check", response_model=ReadinessResponse)
async def readiness_check(request: Request) -> JSONResponse:
    """Return readiness based on required dependencies such as PostgreSQL."""
    service = _health_service(request)
    result = await service.check_readiness()
    if settings := getattr(request.app.state, "settings", None):
        if settings.metrics_enabled and settings.health_check_db_enabled:
            record_db_health_check(success=result.checks.get("database") == "ok")

    response = ReadinessResponse(status=result.status, checks=result.checks)
    status_code = status.HTTP_200_OK if result.is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=response.model_dump())
