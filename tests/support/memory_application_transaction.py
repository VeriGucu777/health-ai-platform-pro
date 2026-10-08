"""In-memory application transaction tracker for unit tests."""

from app.application.clinical_encounter.transaction import ApplicationTransaction


class TrackingApplicationTransaction:
    """Records commit/rollback calls without a database."""

    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True
