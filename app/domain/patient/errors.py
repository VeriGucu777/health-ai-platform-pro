"""Patient domain errors that are not mapped to public HTTP responses by default."""


class PatientHardDeleteForbiddenError(Exception):
    """Raised when code attempts to hard-delete a patient row."""

    def __init__(self, message: str = "Patient hard delete is not supported") -> None:
        super().__init__(message)
