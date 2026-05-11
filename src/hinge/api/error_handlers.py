"""Exception handlers for Hinge API routes."""

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from hinge.core.logging_config import logger as log
from hinge.error import HingeAuthError, HingeSessionExpiredError


def register_hinge_error_handlers(app: FastAPI) -> None:
    """Register exception handlers for Hinge-specific errors.

    Args:
        app: The FastAPI application instance.

    """

    @app.exception_handler(HingeSessionExpiredError)
    async def _hinge_session_expired(
        _request: Request,
        exc: HingeSessionExpiredError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "error": str(exc),
                "auth_state": "unauthenticated",
            },
        )

    @app.exception_handler(HingeAuthError)
    async def _hinge_auth_error(
        _request: Request,
        exc: HingeAuthError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "error": str(exc),
                "auth_state": "unauthenticated",
            },
        )

    @app.exception_handler(httpx.HTTPStatusError)
    async def _httpx_status_error(
        request: Request,
        exc: httpx.HTTPStatusError,
    ) -> JSONResponse:
        # Only intercept Hinge-related requests (under /api/v1/hinge/)
        if not request.url.path.startswith("/api/v1/hinge"):
            # Re-raise for non-Hinge routes to use their own handlers
            raise exc

        status = exc.response.status_code
        upstream_url = str(exc.request.url) if exc.request else "unknown"
        body_text = exc.response.text[:200] if exc.response else ""
        log.error(
            "hinge_upstream_error",
            status=status,
            url=upstream_url,
            body=body_text,
            path=request.url.path,
        )
        # Do NOT treat 401 from data endpoints as session death.
        # Only /likelimit (via check_session_health) is authoritative.
        return JSONResponse(
            status_code=502,
            content={
                "success": False,
                "error": f"Hinge upstream error: {status}",
                "upstream_url": upstream_url,
                "detail": body_text,
            },
        )
