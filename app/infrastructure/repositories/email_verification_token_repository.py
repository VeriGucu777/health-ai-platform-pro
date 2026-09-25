"""SQLAlchemy email verification token repository."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.email_verification_token import EmailVerificationToken
from app.domain.interfaces.email_verification_token_repository import (
    EmailVerificationTokenRepository as EmailVerificationTokenRepositoryPort,
)
from app.infrastructure.database.models.email_verification_token import EmailVerificationTokenModel
from app.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyEmailVerificationTokenRepository(
    SQLAlchemyRepository[EmailVerificationTokenModel, EmailVerificationToken],
    EmailVerificationTokenRepositoryPort,
):
    """PostgreSQL-backed verification token store."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EmailVerificationTokenModel)

    async def get_by_token_hash(self, token_hash: str) -> EmailVerificationToken | None:
        stmt = select(EmailVerificationTokenModel).where(
            EmailVerificationTokenModel.token_hash == token_hash,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def supersede_unused_for_user(self, user_id: UUID) -> int:
        now = datetime.now(UTC)
        stmt = (
            update(EmailVerificationTokenModel)
            .where(
                EmailVerificationTokenModel.user_id == user_id,
                EmailVerificationTokenModel.used_at.is_(None),
                EmailVerificationTokenModel.superseded_at.is_(None),
            )
            .values(superseded_at=now)
            .returning(EmailVerificationTokenModel.id)
        )
        result = await self._session.execute(stmt)
        return len(result.scalars().all())

    async def get_latest_for_user(self, user_id: UUID) -> EmailVerificationToken | None:
        stmt = (
            select(EmailVerificationTokenModel)
            .where(EmailVerificationTokenModel.user_id == user_id)
            .order_by(EmailVerificationTokenModel.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    def _to_entity(self, model: EmailVerificationTokenModel) -> EmailVerificationToken:
        return EmailVerificationToken(
            id=model.id,
            user_id=model.user_id,
            token_hash=model.token_hash,
            expires_at=model.expires_at,
            used_at=model.used_at,
            superseded_at=model.superseded_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: EmailVerificationToken) -> EmailVerificationTokenModel:
        return EmailVerificationTokenModel(
            id=entity.id,
            user_id=entity.user_id,
            token_hash=entity.token_hash,
            expires_at=entity.expires_at,
            used_at=entity.used_at,
            superseded_at=entity.superseded_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
