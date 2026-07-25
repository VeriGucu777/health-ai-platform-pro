"""Health and readiness API schemas."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Process liveness and identity metadata."""

    status: str
    service: str
    version: str
    environment: str
    uptime_seconds: int = Field(ge=0)


class ReadinessResponse(BaseModel):
    """Dependency readiness status."""

    status: str
    checks: dict[str, str] = Field(default_factory=dict)
