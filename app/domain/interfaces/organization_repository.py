"""Organization repository port."""

from app.domain.organization.entities import Organization
from app.domain.interfaces.repository import Repository


class OrganizationRepository(Repository[Organization]):
    """Contract for organization persistence."""
