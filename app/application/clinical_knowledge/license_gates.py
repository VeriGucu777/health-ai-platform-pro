"""License and ingestion invariants for clinical knowledge sources."""

from app.domain.clinical_knowledge.enums import (
    AiUsageStatus,
    LICENSE_STATUSES_ALLOWING_INGESTION,
    LicenseStatus,
)
from app.domain.clinical_knowledge.models import ClinicalKnowledgeSource


def validate_source_license_invariants(source: ClinicalKnowledgeSource) -> list[str]:
    """Return human-readable violation messages; empty if OK."""
    issues: list[str] = []

    if source.content_ingestion_allowed:
        if source.license_status not in LICENSE_STATUSES_ALLOWING_INGESTION:
            issues.append(
                f"content_ingestion_allowed=true requires license_status in "
                f"{sorted(LICENSE_STATUSES_ALLOWING_INGESTION)}, got {source.license_status!s}",
            )
        if source.ai_usage_status == AiUsageStatus.PROHIBITED:
            issues.append("content_ingestion_allowed=true with ai_usage_status=prohibited")
        if source.license_status == LicenseStatus.UNKNOWN:
            issues.append("content_ingestion_allowed=true with license_status=unknown")

    if source.license_status == LicenseStatus.UNKNOWN and source.content_ingestion_allowed:
        issues.append("license_status=unknown requires content_ingestion_allowed=false")

    if source.ai_usage_status == AiUsageStatus.PROHIBITED and source.content_ingestion_allowed:
        issues.append("ai_usage_status=prohibited requires content_ingestion_allowed=false")

    return issues
