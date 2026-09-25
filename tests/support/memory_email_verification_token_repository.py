"""In-memory email verification token repository for API tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.domain.entities.email_verification_token import EmailVerificationToken


class InMemoryEmailVerificationTokenRepository:
    """Thread-unsafe in-memory token store."""

    def __init__(self) -> None:
        self._tokens: dict[UUID, EmailVerificationToken] = {}

    async def get_by_id(self, entity_id: UUID) -> EmailVerificationToken | None:
        return self._tokens.get(entity_id)

    async def get_by_token_hash(self, token_hash: str) -> EmailVerificationToken | None:
        return next(
            (token for token in self._tokens.values() if token.token_hash == token_hash),
            None,
        )

    async def create(self, entity: EmailVerificationToken) -> EmailVerificationToken:
        self._tokens[entity.id] = entity
        return entity

    async def update(self, entity: EmailVerificationToken) -> EmailVerificationToken:
        self._tokens[entity.id] = entity
        return entity

    async def delete(self, entity_id: UUID) -> bool:
        return self._tokens.pop(entity_id, None) is not None

    async def supersede_unused_for_user(self, user_id: UUID) -> int:
        now = datetime.now(UTC)
        count = 0
        for token in self._tokens.values():
            if token.user_id != user_id:
                continue
            if token.used_at is not None or token.superseded_at is not None:
                continue
            token.superseded_at = now
            token.touch()
            count += 1
        return count

    async def get_latest_for_user(self, user_id: UUID) -> EmailVerificationToken | None:
        tokens = [token for token in self._tokens.values() if token.user_id == user_id]
        if not tokens:
            return None
        return max(tokens, key=lambda row: row.created_at)

    def all_tokens(self) -> list[EmailVerificationToken]:
        return list(self._tokens.values())
