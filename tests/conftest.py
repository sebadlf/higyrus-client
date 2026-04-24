from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from higyrus_client import client as _client


@pytest.fixture
def reset_client_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset module-level auth state and inject dummy credentials."""
    monkeypatch.setattr(_client, "_token", "test-token")
    monkeypatch.setattr(_client, "_token_ts", time.time())
    monkeypatch.setattr(_client, "_client_id", "test-client")
    monkeypatch.setattr(_client, "_user", "test-user")
    monkeypatch.setattr(_client, "_password", "test-pass")
    monkeypatch.setattr(_client, "_base_url", "https://api.test")


@pytest.fixture
def mock_session(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replace the requests session with a MagicMock."""
    mock = MagicMock()
    monkeypatch.setattr(_client, "_session", mock)
    return mock


def build_response(
    payload: dict[str, Any] | list[Any] | None = None,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
) -> MagicMock:
    """Build a MagicMock response with json(), status_code, headers and ok."""
    response = MagicMock()
    response.status_code = status_code
    response.ok = 200 <= status_code < 300
    response.json.return_value = payload if payload is not None else {}
    response.content = b"" if payload is None and status_code == 204 else b"{}"
    response.headers = headers or {}
    response.raise_for_status.return_value = None
    return response
