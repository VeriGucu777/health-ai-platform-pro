"""Async SQLAlchemy engine and session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_bound_settings: Settings | None = None


def get_engine(settings: Settings | None = None) -> AsyncEngine:
    """Return the async engine singleton, bound to the given settings."""
    global _engine, _bound_settings
    settings = settings or get_settings()

    if _engine is None or _bound_settings != settings:
        if _engine is not None:
            raise RuntimeError(
                "Database engine already initialized with different settings. "
                "Call reset_database_engine() before rebinding."
            )
        _engine = create_async_engine(
            str(settings.database_url),
            echo=settings.database_echo,
            pool_pre_ping=True,
        )
        _bound_settings = settings

    return _engine


def get_session_factory(settings: Settings | None = None) -> async_sessionmaker[AsyncSession]:
    """Return the async session factory singleton."""
    global _session_factory
    settings = settings or get_settings()

    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(settings),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _session_factory


async def dispose_engine() -> None:
    """Dispose the engine and reset session factory — call on app shutdown."""
    global _engine, _session_factory, _bound_settings
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
    _bound_settings = None


def reset_database_engine() -> None:
    """Reset engine references without async dispose — for tests only."""
    global _engine, _session_factory, _bound_settings
    _engine = None
    _session_factory = None
    _bound_settings = None


async def get_db_session(settings: Settings | None = None) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session — used as a FastAPI dependency."""
    session_factory = get_session_factory(settings)
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
