from __future__ import annotations

from datetime import date, datetime

from higyrus_client._params import drop_none, format_bool, format_date

# ---------------------------------------------------------------------------
# format_date
# ---------------------------------------------------------------------------


def test_format_date_with_date() -> None:
    assert format_date(date(2026, 4, 23)) == "23/04/2026"


def test_format_date_with_datetime() -> None:
    assert format_date(datetime(2026, 4, 23, 15, 30, 0)) == "23/04/2026"


def test_format_date_zero_pads_day_and_month() -> None:
    assert format_date(date(2026, 1, 5)) == "05/01/2026"


def test_format_date_none_returns_none() -> None:
    assert format_date(None) is None


# ---------------------------------------------------------------------------
# format_bool
# ---------------------------------------------------------------------------


def test_format_bool_true() -> None:
    assert format_bool(True) == "True"


def test_format_bool_false() -> None:
    assert format_bool(False) == "False"


def test_format_bool_none() -> None:
    assert format_bool(None) is None


# ---------------------------------------------------------------------------
# drop_none
# ---------------------------------------------------------------------------


def test_drop_none_removes_only_none_values() -> None:
    assert drop_none({"a": 1, "b": None, "c": "x"}) == {"a": 1, "c": "x"}


def test_drop_none_preserves_false() -> None:
    # False must survive — it's a legitimate API input (e.g. incluirParking).
    assert drop_none({"incluirParking": False}) == {"incluirParking": False}


def test_drop_none_preserves_zero() -> None:
    assert drop_none({"count": 0}) == {"count": 0}


def test_drop_none_preserves_empty_string() -> None:
    assert drop_none({"note": ""}) == {"note": ""}


def test_drop_none_on_empty_dict() -> None:
    assert drop_none({}) == {}


def test_drop_none_returns_new_dict() -> None:
    original = {"a": 1, "b": None}
    result = drop_none(original)
    assert result is not original
    assert original == {"a": 1, "b": None}  # input untouched
