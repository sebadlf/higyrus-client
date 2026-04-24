from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from higyrus_client import client as _client
from higyrus_client.exceptions import (
    AuthenticationError,
    AuthorizationError,
    HigyrusAPIError,
)
from tests.conftest import build_response


def test_login_stores_token_and_returns_it(
    reset_client_state: None,
    mock_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_client, "_token", None)
    mock_session.post.return_value = build_response(
        payload={"username": "test-user", "token": "new-token"},
        status_code=200,
    )

    token = _client.login()

    assert token == "new-token"
    assert _client._token == "new-token"
    mock_session.post.assert_called_once()
    call = mock_session.post.call_args
    assert call.args[0] == "https://api.test/api/login"
    assert call.kwargs["json"] == {
        "clientId": "test-client",
        "username": "test-user",
        "password": "test-pass",
    }


def test_login_missing_credentials_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_client, "_base_url", "https://api.test")
    monkeypatch.setattr(_client, "_client_id", "")
    monkeypatch.setattr(_client, "_user", "")
    monkeypatch.setattr(_client, "_password", "")
    monkeypatch.setattr(_client, "_token", None)

    with pytest.raises(AuthenticationError):
        _client.login()


def test_login_accepts_empty_client_id(
    mock_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Single-tenant installations don't require HIGYRUS_CLIENT_ID. The
    # client must tolerate an empty string and still send the field in
    # the body so the server sees a consistent shape.
    monkeypatch.setattr(_client, "_base_url", "https://api.test")
    monkeypatch.setattr(_client, "_client_id", "")
    monkeypatch.setattr(_client, "_user", "test-user")
    monkeypatch.setattr(_client, "_password", "test-pass")
    monkeypatch.setattr(_client, "_token", None)
    mock_session.post.return_value = build_response(
        payload={"username": "test-user", "token": "new-token"},
        status_code=200,
    )

    token = _client.login()

    assert token == "new-token"
    sent_body = mock_session.post.call_args.kwargs["json"]
    assert sent_body == {
        "clientId": "",
        "username": "test-user",
        "password": "test-pass",
    }


def test_login_missing_base_url_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_client, "_base_url", "")
    monkeypatch.setattr(_client, "_token", None)

    with pytest.raises(AuthenticationError):
        _client.login()


def test_login_without_token_in_body_raises(
    reset_client_state: None,
    mock_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_client, "_token", None)
    mock_session.post.return_value = build_response(
        payload={"username": "test-user"},
        status_code=200,
    )

    with pytest.raises(AuthenticationError):
        _client.login()


def test_login_401_raises_authentication_error(
    reset_client_state: None,
    mock_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_client, "_token", None)
    mock_session.post.return_value = build_response(
        payload={"errors": [{"title": "auth", "detail": "invalid credentials"}]},
        status_code=401,
    )

    with pytest.raises(AuthenticationError) as exc:
        _client.login()

    assert exc.value.status_code == 401
    assert "invalid credentials" in str(exc.value)


def test_request_sends_bearer_header(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(
        payload={"status": "ok"},
        status_code=200,
    )

    result = _client._request("GET", "/api/health")

    assert result == {"status": "ok"}
    call = mock_session.request.call_args
    assert call.args == ("GET", "https://api.test/api/health")
    assert call.kwargs["headers"] == {"Authorization": "Bearer test-token"}


def test_request_403_raises_authorization_error(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(
        payload={"errors": [{"title": "forbidden", "detail": "missing permission"}]},
        status_code=403,
    )

    with pytest.raises(AuthorizationError) as exc:
        _client._request("GET", "/api/cuentas/1")

    assert exc.value.status_code == 403


def test_request_500_raises_base_error(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(
        payload={"errors": [{"title": "internal"}]},
        status_code=500,
    )

    with pytest.raises(HigyrusAPIError) as exc:
        _client._request("GET", "/api/cuentas/1")

    assert exc.value.status_code == 500


def test_request_204_returns_none(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(status_code=204)

    result = _client._request("GET", "/api/cuentas/999")

    assert result is None


def test_get_drops_none_params(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(
        payload={"data": []},
        status_code=200,
    )

    _client._get("/api/cuentas", fechaDesde="2026-01-01", fechaHasta=None)

    call = mock_session.request.call_args
    assert call.kwargs["params"] == {"fechaDesde": "2026-01-01"}
