"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Normalize DATABASE_URL to postgresql+asyncpg:// for the async runtime."""
    if url.startswith("postgres://"):
        return f"postgresql+asyncpg://{url[len('postgres://'):]}"
    if url.startswith("postgresql://"):
        return f"postgresql+asyncpg://{url[len('postgresql://'):]}"
    return url


class Settings(BaseSettings):
    """Central configuration — single source of truth for all env vars."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="Health AI Platform Pro", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        alias="ENVIRONMENT",
    )
    debug: bool = Field(default=False, alias="DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8001, alias="PORT")
    uvicorn_workers: int = Field(default=1, alias="UVICORN_WORKERS")

    # Database
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/health_ai_platform",
        alias="DATABASE_URL",
    )
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")

    # JWT
    jwt_secret_key: str = Field(default="change-me", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=30,
        alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7,
        alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS",
    )

    # CORS
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        alias="CORS_ORIGINS",
    )

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: Literal["text", "json"] = Field(default="text", alias="LOG_FORMAT")

    # Observability
    metrics_enabled: bool = Field(default=False, alias="METRICS_ENABLED")
    slow_request_threshold_ms: int = Field(default=1000, alias="SLOW_REQUEST_THRESHOLD_MS")
    health_check_db_enabled: bool = Field(default=True, alias="HEALTH_CHECK_DB_ENABLED")
    health_check_db_timeout_seconds: float = Field(
        default=2.0,
        alias="HEALTH_CHECK_DB_TIMEOUT_SECONDS",
    )

    # Authentication rate limiting
    auth_rate_limit_enabled: bool = Field(default=True, alias="AUTH_RATE_LIMIT_ENABLED")
    auth_login_rate_limit: int = Field(default=10, alias="AUTH_LOGIN_RATE_LIMIT")
    auth_login_rate_window_seconds: int = Field(default=60, alias="AUTH_LOGIN_RATE_WINDOW_SECONDS")
    auth_refresh_rate_limit: int = Field(default=20, alias="AUTH_REFRESH_RATE_LIMIT")
    auth_refresh_rate_window_seconds: int = Field(
        default=60,
        alias="AUTH_REFRESH_RATE_WINDOW_SECONDS",
    )
    auth_register_rate_limit: int = Field(default=5, alias="AUTH_REGISTER_RATE_LIMIT")
    auth_register_rate_window_seconds: int = Field(
        default=60,
        alias="AUTH_REGISTER_RATE_WINDOW_SECONDS",
    )

    # Rate limiting backend
    auth_rate_limit_backend: Literal["memory", "redis"] = Field(
        default="memory",
        alias="AUTH_RATE_LIMIT_BACKEND",
    )
    redis_url: str | None = Field(default=None, alias="REDIS_URL")

    # Clinical retrieval / RAG (embedding + pgvector search)
    rag_enabled: bool = Field(default=True, alias="RAG_ENABLED")

    # Clinical retrieval embeddings (local/self-hosted by default in production)
    embedding_provider: str = Field(default="", alias="EMBEDDING_PROVIDER")
    local_embedding_model: str = Field(
        default="health-ai-platform/clinical-retrieval-multilingual-v1",
        alias="LOCAL_EMBEDDING_MODEL",
    )
    embedding_version: str = Field(default="3", alias="EMBEDDING_VERSION")
    clinical_retrieval_vector_dimension: int = Field(
        default=384,
        alias="CLINICAL_RETRIEVAL_VECTOR_DIMENSION",
    )
    fake_embedding_dimensions: int = Field(
        default=64,
        alias="FAKE_EMBEDDING_DIMENSIONS",
    )

    # Clinical narrative LLM (v1 — external opt-in; no local LLM in v1)
    clinical_narrative_provider: str = Field(default="", alias="CLINICAL_NARRATIVE_PROVIDER")
    clinical_narrative_default_language: str = Field(
        default="tr",
        alias="CLINICAL_NARRATIVE_DEFAULT_LANGUAGE",
    )
    clinical_narrative_max_output_tokens: int = Field(
        default=1024,
        alias="CLINICAL_NARRATIVE_MAX_OUTPUT_TOKENS",
    )
    clinical_narrative_timeout_seconds: float = Field(
        default=30.0,
        alias="CLINICAL_NARRATIVE_TIMEOUT_SECONDS",
    )
    clinical_narrative_max_retries: int = Field(default=1, alias="CLINICAL_NARRATIVE_MAX_RETRIES")
    clinical_narrative_external_base_url: str = Field(
        default="",
        alias="CLINICAL_NARRATIVE_EXTERNAL_BASE_URL",
    )
    clinical_narrative_external_api_key: str = Field(
        default="",
        alias="CLINICAL_NARRATIVE_EXTERNAL_API_KEY",
    )
    clinical_narrative_external_model: str = Field(
        default="",
        alias="CLINICAL_NARRATIVE_EXTERNAL_MODEL",
    )
    clinical_narrative_rate_limit_enabled: bool = Field(
        default=True,
        alias="CLINICAL_NARRATIVE_RATE_LIMIT_ENABLED",
    )
    clinical_narrative_rate_limit: int = Field(default=10, alias="CLINICAL_NARRATIVE_RATE_LIMIT")
    clinical_narrative_rate_window_seconds: int = Field(
        default=60,
        alias="CLINICAL_NARRATIVE_RATE_WINDOW_SECONDS",
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url_field(cls, value: str) -> str:
        if isinstance(value, str):
            return normalize_database_url(value)
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def database_url_sync(self) -> str:
        """Sync driver URL for Alembic migrations (asyncpg → psycopg)."""
        return str(self.database_url).replace("+asyncpg", "+psycopg")


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — import via dependency injection in routes."""
    settings = Settings()
    from app.core.jwt_settings import validate_settings_security

    validate_settings_security(settings)
    return settings
