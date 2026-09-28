"""In-memory refresh session repository for API tests."""

from uuid import UUID

from app.domain.entities.user_refresh_session import UserRefreshSession
from app.domain.interfaces.user_refresh_session_repository import UserRefreshSessionRepository


class InMemoryUserRefreshSessionRepository(UserRefreshSessionRepository):
    """Thread-unsafe in-memory refresh session store."""

    def __init__(self) -> None:
        self._sessions: dict[UUID, UserRefreshSession] = {}
        self._hash_index: dict[str, UUID] = {}

    async def get_by_id(self, entity_id: UUID) -> UserRefreshSession | None:
        return self._sessions.get(entity_id)

    async def get_by_hash(self, refresh_token_id_hash: str) -> UserRefreshSession | None:
        session_id = self._hash_index.get(refresh_token_id_hash)
        return self._sessions.get(session_id) if session_id else None

    async def create_session(
        self,
        user_id: UUID,
        refresh_token_id_hash: str,
    ) -> UserRefreshSession:
        entity = UserRefreshSession(
            user_id=user_id,
            refresh_token_id_hash=refresh_token_id_hash,
        )
        return await self.create(entity)

    async def create(self, entity: UserRefreshSession) -> UserRefreshSession:
        self._sessions[entity.id] = entity
        self._hash_index[entity.refresh_token_id_hash] = entity.id
        return entity

    async def update(self, entity: UserRefreshSession) -> UserRefreshSession:
        old = self._sessions.get(entity.id)
        if old is not None:
            self._hash_index.pop(old.refresh_token_id_hash, None)
        self._sessions[entity.id] = entity
        self._hash_index[entity.refresh_token_id_hash] = entity.id
        return entity

    async def delete(self, entity_id: UUID) -> bool:
        entity = self._sessions.pop(entity_id, None)
        if entity is None:
            return False
        self._hash_index.pop(entity.refresh_token_id_hash, None)
        return True

    async def list_all(self, *, offset: int = 0, limit: int = 100) -> list[UserRefreshSession]:
        sessions = list(self._sessions.values())
        return sessions[offset : offset + limit]

    async def rotate_hash(self, session_id: UUID, refresh_token_id_hash: str) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            msg = "Refresh session not found"
            raise ValueError(msg)
        self._hash_index.pop(session.refresh_token_id_hash, None)
        session.refresh_token_id_hash = refresh_token_id_hash
        session.touch()
        self._hash_index[refresh_token_id_hash] = session_id

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        to_remove = [sid for sid, s in self._sessions.items() if s.user_id == user_id]
        for sid in to_remove:
            await self.delete(sid)
