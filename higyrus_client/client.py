"""REST client for the Higyrus API.

Thin wrapper over the HTTP endpoints of the Higyrus API. State is held at
module level (token, session, credentials) and the token is refreshed
automatically a little before the 24 h server-side expiry.

Auth flow:
- ``POST /api/login`` with JSON ``{"clientId", "username", "password"}``
  returns ``{"username", "token"}``.
- The token is then sent as ``Authorization: Bearer <token>`` on every
  subsequent request (OAuth 2.0 style).

Environment variables (loaded from ``.env`` via ``python-dotenv``):
- ``HIGYRUS_CLIENT_ID`` — tenant / client identifier (required)
- ``HIGYRUS_USER`` — API username (required)
- ``HIGYRUS_PASSWORD`` — API password (required)
- ``HIGYRUS_BASE_URL`` — full base URL up to the ``/api`` prefix,
  e.g. ``https://cliente.aunesa.com/Irmo`` (required)
"""

from __future__ import annotations

import os
import time
from typing import Any

import requests as _requests
from dotenv import load_dotenv

from ._params import drop_none
from .exceptions import AuthenticationError, AuthorizationError, HigyrusAPIError

load_dotenv()

# -- Module-level state --
_base_url: str = os.getenv("HIGYRUS_BASE_URL", "").rstrip("/")
_client_id: str = os.getenv("HIGYRUS_CLIENT_ID", "")
_user: str = os.getenv("HIGYRUS_USER", "")
_password: str = os.getenv("HIGYRUS_PASSWORD", "")
_token: str | None = None
_token_ts: float = 0.0
_TOKEN_TTL = 23 * 60 * 60  # refresh 1 h before the 24 h expiry
_session = _requests.Session()
_REQUEST_TIMEOUT = 30.0


# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------


def _ensure_token() -> None:
    """Log in if there is no cached token or it is older than ``_TOKEN_TTL``."""
    if _token and (time.time() - _token_ts) < _TOKEN_TTL:
        return
    login()


def login() -> str:
    """Authenticate against ``POST /api/login`` and cache the resulting token.

    Returns:
        The newly issued token string, also stored in module state.

    Raises:
        AuthenticationError: If credentials/base URL are missing, if the API
            rejects the credentials, or if the response body lacks a ``token``.
    """
    global _token, _token_ts
    if not _base_url:
        raise AuthenticationError(
            0, [{"title": "config", "detail": "HIGYRUS_BASE_URL must be set"}]
        )
    if not _client_id or not _user or not _password:
        raise AuthenticationError(
            0,
            [
                {
                    "title": "config",
                    "detail": "HIGYRUS_CLIENT_ID, HIGYRUS_USER and HIGYRUS_PASSWORD must be set",
                }
            ],
        )

    resp = _session.post(
        f"{_base_url}/api/login",
        json={"clientId": _client_id, "username": _user, "password": _password},
        timeout=_REQUEST_TIMEOUT,
    )
    if resp.status_code == 401:
        _raise_for_response(resp)

    resp.raise_for_status()
    data: dict[str, Any] = resp.json()
    token = data.get("token")
    if not token:
        raise AuthenticationError(
            resp.status_code, [{"title": "auth", "detail": "No token in login response"}]
        )

    _token = token
    _token_ts = time.time()
    return token


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _raise_for_response(resp: _requests.Response) -> None:
    """Translate a non-2xx response into the matching Higyrus exception."""
    try:
        payload: dict[str, Any] = resp.json()
    except ValueError:
        payload = {}

    errors = payload.get("errors") if isinstance(payload, dict) else None
    timestamp = payload.get("timestamp") if isinstance(payload, dict) else None

    exc_cls: type[HigyrusAPIError]
    if resp.status_code == 401:
        exc_cls = AuthenticationError
    elif resp.status_code == 403:
        exc_cls = AuthorizationError
    else:
        exc_cls = HigyrusAPIError

    raise exc_cls(resp.status_code, errors, timestamp)


def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any] | None:
    """Execute an authenticated HTTP request and decode the JSON payload.

    The token is ensured/refreshed and sent via ``Authorization: Bearer``.

    Returns:
        Parsed JSON on 2xx. ``None`` when the API replies with ``204 No Content``.

    Raises:
        HigyrusAPIError: For any non-2xx response, with the error body parsed
            into ``errors`` / ``timestamp`` when available.
    """
    _ensure_token()
    assert _token is not None

    url = f"{_base_url}{path}"
    resp = _session.request(
        method,
        url,
        params=drop_none(params) if params else None,
        json=json_body,
        headers={"Authorization": f"Bearer {_token}"},
        timeout=_REQUEST_TIMEOUT,
    )

    if not resp.ok:
        _raise_for_response(resp)

    if resp.status_code == 204 or not resp.content:
        return None

    return resp.json()


def _get(path: str, **params: Any) -> dict[str, Any] | list[Any] | None:
    """GET ``path`` with query ``params`` (``None`` values are dropped)."""
    return _request("GET", path, params=params)


def _post(
    path: str, *, json_body: dict[str, Any] | None = None, **params: Any
) -> dict[str, Any] | list[Any] | None:
    """POST to ``path`` with JSON body and/or query ``params``."""
    return _request("POST", path, params=params, json_body=json_body)


def _patch(
    path: str, *, json_body: dict[str, Any] | None = None, **params: Any
) -> dict[str, Any] | list[Any] | None:
    """PATCH ``path`` with JSON body and/or query ``params``."""
    return _request("PATCH", path, params=params, json_body=json_body)


# ------------------------------------------------------------------
# Health  (no auth required)
# ------------------------------------------------------------------


def get_health() -> dict[str, Any]:
    """Return the server status. Hits ``GET /api/health``.

    Does not require authentication.
    """
    url = f"{_base_url}/api/health"
    resp = _session.get(url, timeout=_REQUEST_TIMEOUT)
    if not resp.ok:
        _raise_for_response(resp)
    return resp.json()
