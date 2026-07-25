"""Prometheus metrics endpoint (opt-in)."""

from fastapi import APIRouter, Request, Response, status

from app.api.deps import AppSettings
from app.observability.metrics import metrics_enabled, render_prometheus_metrics

router = APIRouter()


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    include_in_schema=False,
    response_class=Response,
)
async def prometheus_metrics(settings: AppSettings, request: Request) -> Response:
    """Expose Prometheus metrics when enabled via configuration."""
    if not settings.metrics_enabled or not metrics_enabled():
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    payload, content_type = render_prometheus_metrics()
    return Response(content=payload, media_type=content_type)
