"""Global exception handlers registered on the FastAPI app."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.schemas.common import ErrorResponse
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.core.request_context import get_request_id

logger = get_logger(__name__)


def _request_id_from(request: Request) -> str | None:
    return getattr(request.state, "request_id", None) or get_request_id()


def _error_response(
    *,
    message: str,
    status_code: int,
    request: Request,
    details: dict | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            success=False,
            message=message,
            details=details,
            request_id=_request_id_from(request),
        ).model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach application exception handlers to the FastAPI instance."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        request_id = _request_id_from(request)
        if exc.status_code >= 500:
            logger.error(
                "Application error (%s): %s [%s]",
                exc.status_code,
                exc.message,
                request_id,
            )
        elif exc.status_code in {401, 403, 429}:
            logger.warning(
                "Application error (%s): %s [%s]",
                exc.status_code,
                exc.message,
                request_id,
            )
        else:
            logger.info(
                "Application error (%s): %s [%s]",
                exc.status_code,
                exc.message,
                request_id,
            )
        return _error_response(
            message=exc.message,
            status_code=exc.status_code,
            request=request,
            details=exc.details or None,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = _request_id_from(request)
        logger.exception("Unhandled exception [%s]: %s", request_id, exc)
        return _error_response(
            message="Internal server error",
            status_code=500,
            request=request,
        )
