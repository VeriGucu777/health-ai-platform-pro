"""Map patient access policy decisions to application exceptions."""

from app.core.exceptions import AppException, ForbiddenError, NotFoundError
from app.domain.patient_access.result import PatientAccessDecision


def raise_for_patient_access_decision(decision: PatientAccessDecision) -> None:
    """Raise a typed HTTP-oriented exception when access is denied."""
    if decision.allowed:
        return

    message = "Patient not found"
    status = decision.suggested_http_status or 404
    if status == 403:
        raise ForbiddenError(message)
    if status == 404:
        raise NotFoundError(message)
    raise AppException(message, status_code=status)
