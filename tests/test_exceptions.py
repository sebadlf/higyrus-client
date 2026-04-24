from __future__ import annotations

import pytest

from higyrus_client.exceptions import (
    AuthenticationError,
    AuthorizationError,
    HigyrusAPIError,
)


def test_higyrus_api_error_uses_first_error_detail() -> None:
    err = HigyrusAPIError(
        400,
        errors=[{"title": "bad_request", "detail": "missing param"}],
        timestamp="2026-04-23T20:00:00Z",
    )
    assert str(err) == "missing param"
    assert err.status_code == 400
    assert err.errors == [{"title": "bad_request", "detail": "missing param"}]
    assert err.timestamp == "2026-04-23T20:00:00Z"


def test_higyrus_api_error_falls_back_to_title() -> None:
    err = HigyrusAPIError(400, errors=[{"title": "bad_request"}])
    assert str(err) == "bad_request"


def test_higyrus_api_error_falls_back_to_status() -> None:
    err = HigyrusAPIError(500)
    assert str(err) == "HTTP 500"


def test_authentication_and_authorization_errors_are_subclasses() -> None:
    auth_err = AuthenticationError(401)
    forbidden = AuthorizationError(403)
    assert isinstance(auth_err, HigyrusAPIError)
    assert isinstance(forbidden, HigyrusAPIError)
    with pytest.raises(AuthenticationError):
        raise auth_err
    with pytest.raises(AuthorizationError):
        raise forbidden
