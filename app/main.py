"""FastAPI application factory and lifespan management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.router import create_api_router
from app.application.services.system_health_service import SystemHealthService
from app.core.config import Settings, get_settings
from app.core.logging import get_logger, setup_logging
from app.infrastructure.database.session import dispose_engine, get_engine
from app.middleware.auth_rate_limit import AuthRateLimiter
from app.middleware.exception_handlers import register_exception_handlers
from app.middleware.logging import RequestLoggingMiddleware
from app.observability.metrics import configure_metrics

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown hooks."""
    settings: Settings = app.state.settings
    from app.core.pilot_runtime import validate_pilot_runtime_settings

    validate_pilot_runtime_settings(settings)
    get_engine(settings)
    if settings.rag_enabled:
        kind = (settings.embedding_provider or "").strip().lower()
        if kind == "local" or settings.is_production or settings.environment == "staging":
            from app.infrastructure.embeddings.embedding_factory import get_embedding_provider

            app.state.embedding_provider = get_embedding_provider(settings)
            logger.info(
                "Clinical retrieval embedding provider ready (%s, dim=%s)",
                app.state.embedding_provider.model_name,
                app.state.embedding_provider.dimensions,
            )
    else:
        logger.info(
            "RAG_ENABLED=false — skipping embedding provider startup preload (pilot/low-memory mode)",
        )
    logger.info(
        "Starting %s v%s [%s]",
        settings.app_name,
        settings.app_version,
        settings.environment,
    )
    yield
    await dispose_engine()
    logger.info("Shutting down %s", settings.app_name)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    from app.core.jwt_settings import validate_settings_security

    app_settings = settings or get_settings()
    if settings is not None:
        validate_settings_security(app_settings)
    setup_logging(app_settings)
    configure_metrics(app_settings.metrics_enabled)

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        description="AI-powered Healthcare Platform API",
        docs_url="/docs" if app_settings.is_development else None,
        redoc_url="/redoc" if app_settings.is_development else None,
        openapi_url="/openapi.json" if app_settings.is_development else None,
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    app.state.auth_rate_limiter = AuthRateLimiter.from_settings(app_settings)
    app.state.system_health_service = SystemHealthService(
        app_settings,
        started_at=datetime.now(UTC),
    )

    # CORS — configured for React web and React Native clients
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(RequestLoggingMiddleware)
    register_exception_handlers(app)
    app.include_router(create_api_router(app_settings.api_v1_prefix))

    @app.get("/", tags=["Root"], include_in_schema=False, response_model=None)
    async def root() -> RedirectResponse | JSONResponse:
        if app_settings.is_development:
            return RedirectResponse(url="/docs")
        return JSONResponse(
            content={
                "service": app_settings.app_name,
                "version": app_settings.app_version,
                "environment": app_settings.environment,
                "health": f"{app_settings.api_v1_prefix}/health",
                "ready": f"{app_settings.api_v1_prefix}/ready",
            },
        )

    return app


app = create_app()
