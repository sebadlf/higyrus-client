"""Exception hierarchy for Higyrus API errors."""

from __future__ import annotations

from typing import Any


class HigyrusAPIError(Exception):
    """Error returned by the Higyrus API.

    Raised when a request fails with an error status code or the response
    payload signals a problem. The original ``errors`` list and ``timestamp``
    from the API envelope are preserved for programmatic inspection.

    Attributes:
        status_code: HTTP status code returned by the API.
        errors: List of ``{"title": ..., "detail": ...}`` dicts from the API.
        timestamp: Server-side timestamp string from the error envelope.
    """

    def __init__(
        self,
        status_code: int,
        errors: list[dict[str, Any]] | None = None,
        timestamp: str | None = None,
    ):
        self.status_code = status_code
        self.errors = errors or []
        self.timestamp = timestamp

        if self.errors:
            first = self.errors[0]
            detail = first.get("detail") or first.get("title") or f"HTTP {status_code}"
        else:
            detail = f"HTTP {status_code}"
        super().__init__(detail)


class AuthenticationError(HigyrusAPIError):
    """Raised when authentication fails (missing credentials or HTTP 401)."""


class AuthorizationError(HigyrusAPIError):
    """Raised when the user lacks permissions for the resource (HTTP 403)."""
