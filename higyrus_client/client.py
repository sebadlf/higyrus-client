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
- ``HIGYRUS_USER`` — API username (required)
- ``HIGYRUS_PASSWORD`` — API password (required)
- ``HIGYRUS_BASE_URL`` — full base URL up to the ``/api`` prefix,
  e.g. ``https://cliente.aunesa.com/Irmo`` (required)
- ``HIGYRUS_CLIENT_ID`` — tenant / client identifier (optional; sent as
  ``""`` when unset for single-tenant installations)
"""

from __future__ import annotations

import os
import time
from datetime import date, datetime
from typing import Any

import requests as _requests
from dotenv import load_dotenv

from ._params import drop_none, format_bool, format_date
from .exceptions import AuthenticationError, AuthorizationError, HigyrusAPIError
from .models import Movimiento, Posicion, PosicionValuada

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
    if not _user or not _password:
        raise AuthenticationError(
            0,
            [
                {
                    "title": "config",
                    "detail": "HIGYRUS_USER and HIGYRUS_PASSWORD must be set",
                }
            ],
        )
    # HIGYRUS_CLIENT_ID is optional — tenants without multi-tenancy accept
    # an empty string. We send the field verbatim (possibly ``""``) so the
    # server always sees the same shape.

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


# ------------------------------------------------------------------
# Cuentas
# ------------------------------------------------------------------


def get_movimientos(
    id_cuenta: str,
    fecha_desde: date | datetime | str,
    fecha_hasta: date | datetime | str,
    *,
    especie: str | None = None,
    tipo_titulo: str | None = None,
    tipo_titulo_agente: str | None = None,
    movimiento: str | None = None,
) -> list[Movimiento]:
    """Return the movements of an account over a date range.

    Hits ``GET /api/cuentas/{id_cuenta}/movimientos`` — see
    ``documentation/higyrus-docs.pdf`` pp. 26-30. Requires the Higyrus
    permission ``[API] Cuenta - Consulta de movimientos de una cuenta a
    partir de una fecha``.

    Args:
        id_cuenta: Account identifier to query.
        fecha_desde: Start of the date range (inclusive). ``date`` /
            ``datetime`` are formatted as ``dd/mm/yyyy``; strings are
            passed through untouched.
        fecha_hasta: End of the date range (inclusive), same semantics.
        especie: Optional species filter.
        tipo_titulo: Optional security type filter.
        tipo_titulo_agente: Optional agent-side security type filter.
        movimiento: Optional movement type filter.

    Returns:
        A list of :class:`~higyrus_client.models.Movimiento`. Empty list
        when the API returns ``204 No Content``.

    Raises:
        AuthenticationError: ``401`` from the API (token missing/invalid).
        AuthorizationError: ``403`` from the API (caller lacks permission).
        HigyrusAPIError: Any other non-2xx response.
    """
    raw = _get(
        f"/api/cuentas/{id_cuenta}/movimientos",
        fechaDesde=format_date(fecha_desde),
        fechaHasta=format_date(fecha_hasta),
        especie=especie,
        tipoTitulo=tipo_titulo,
        tipoTituloAgente=tipo_titulo_agente,
        movimiento=movimiento,
    )
    if raw is None:
        return []
    assert isinstance(raw, list)
    return [Movimiento.from_api(item) for item in raw]


def get_posicion_valuada(
    id_cuenta: str,
    tipo_cuenta: str,
    nivel: str,
    desde: date | datetime | str,
    hasta: date | datetime | str,
    *,
    lugar: str | None = None,
    estado: str | None = None,
    tipo_titulo: str | None = None,
    extracto: str | None = None,
    ocultar_cerradas: bool | None = None,
    especie: str | None = None,
    concertacion: bool | None = None,
    actualizar: bool | None = None,
) -> list[PosicionValuada]:
    """Return the valued position rows of an account over a date range.

    Hits ``GET /api/cuentas/{id_cuenta}/posicionValuada`` — see
    ``documentation/higyrus-docs.pdf`` pp. 49-52. Requires the Higyrus
    permission ``[API] Consulta de posición valuada``.

    Args:
        id_cuenta: Account identifier.
        tipo_cuenta: Account type (valores a documentar contra sandbox).
        nivel: Aggregation / detail level (valores a documentar contra
            sandbox).
        desde: Start of the date range, ``dd/mm/yyyy`` formatting or
            passthrough string.
        hasta: End of the date range, same semantics.
        lugar: Optional venue filter.
        estado: Optional state filter.
        tipo_titulo: Optional security type filter.
        extracto: Optional statement identifier filter.
        ocultar_cerradas: If provided, serialized as ``"True"``/``"False"``;
            left unset (``None``) the server default applies.
        especie: Optional species filter.
        concertacion: Tri-state flag (``None`` → omitted).
        actualizar: Tri-state flag (``None`` → omitted).

    Returns:
        A list of :class:`~higyrus_client.models.PosicionValuada`. Empty
        list when the API returns ``204 No Content``. The spec documents
        the successful status as ``201``, which is accepted transparently
        by :func:`_request` (it trusts ``resp.ok``).

    Raises:
        AuthenticationError: ``401`` from the API.
        AuthorizationError: ``403`` from the API.
        HigyrusAPIError: Any other non-2xx response.
    """
    raw = _get(
        f"/api/cuentas/{id_cuenta}/posicionValuada",
        tipoCuenta=tipo_cuenta,
        nivel=nivel,
        desde=format_date(desde),
        hasta=format_date(hasta),
        lugar=lugar,
        estado=estado,
        tipoTitulo=tipo_titulo,
        extracto=extracto,
        ocultarCerradas=format_bool(ocultar_cerradas),
        especie=especie,
        concertacion=format_bool(concertacion),
        actualizar=format_bool(actualizar),
    )
    if raw is None:
        return []
    assert isinstance(raw, list)
    return [PosicionValuada.from_api(item) for item in raw]


def get_posiciones(
    id_cuenta: str,
    fecha: date | datetime | str,
    *,
    especie: str | None = None,
    incluir_parking: bool = False,
) -> list[Posicion]:
    """Return the position summary of an account at a given date.

    Hits ``GET /api/cuentas/{id_cuenta}/posiciones`` — see
    ``documentation/higyrus-docs.pdf`` pp. 33-36. Requires the Higyrus
    permission ``[API] Cuenta - Resumen de posiciones``.

    Args:
        id_cuenta: Account identifier to query.
        fecha: Snapshot date. ``date`` / ``datetime`` are formatted as
            ``dd/mm/yyyy``; string values are passed through untouched
            (the API is the source of truth for format validation).
        especie: Optional species filter.
        incluir_parking: Include parking entries under each position
            (default ``False``).

    Returns:
        A list of :class:`~higyrus_client.models.Posicion`. Empty list when
        the API returns ``204 No Content``.

    Raises:
        AuthenticationError: ``401`` from the API (token missing/invalid).
        AuthorizationError: ``403`` from the API (caller lacks permission).
        HigyrusAPIError: Any other non-2xx response.
    """
    raw = _get(
        f"/api/cuentas/{id_cuenta}/posiciones",
        fecha=format_date(fecha),
        especie=especie,
        incluirParking=format_bool(incluir_parking),
    )
    if raw is None:
        return []
    assert isinstance(raw, list)
    return [Posicion.from_api(item) for item in raw]
