"""Compare live sandbox payloads against our dataclass schemas.

Uses the internal ``_get`` helper to fetch raw JSON (bypassing
``from_api``), then diffs each sample payload against the corresponding
dataclass fields. Prints:

- wire keys missing from the model (likely new fields to add)
- model keys missing from the wire (may be conditional, not a problem)
- type mismatches between wire value and declared annotation
- a sample of a few rows so we can eyeball semantics

Reads credentials and ``HIGYRUS_TEST_ACCOUNT_ID`` / ``_TIPO_CUENTA`` /
``_NIVEL`` from ``.env``.
"""

from __future__ import annotations

import json
import os
from dataclasses import fields
from datetime import date, timedelta
from types import NoneType, UnionType
from typing import Any, Union, get_args, get_origin

from dotenv import load_dotenv

from higyrus_client import client as _client
from higyrus_client._params import format_bool, format_date
from higyrus_client.models import Movimiento, Posicion, PosicionValuada, SafeModel

load_dotenv()

ACCOUNT = os.getenv("HIGYRUS_TEST_ACCOUNT_ID")
TIPO_CUENTA = os.getenv("HIGYRUS_TEST_TIPO_CUENTA")
NIVEL = os.getenv("HIGYRUS_TEST_NIVEL")


def _python_kinds_for(hint: Any) -> tuple[type, ...]:
    """Flatten an annotation into the concrete Python types we expect at runtime."""
    origin = get_origin(hint)
    args = get_args(hint)
    if origin is Union or origin is UnionType:
        kinds: list[type] = []
        for a in args:
            kinds.extend(_python_kinds_for(a))
        return tuple(kinds)
    if origin is list:
        return (list,)
    if hint is str:
        return (str,)
    if hint is bool:
        return (bool,)
    if hint is int:
        return (int,)
    if hint is float:
        return (int, float)  # JSON numbers may come as int for whole values
    if hint is NoneType:
        return (type(None),)
    if isinstance(hint, type) and issubclass(hint, SafeModel):
        return (dict,)
    return (object,)


def diff_schema(name: str, sample: dict[str, Any], model_cls: type[SafeModel]) -> None:
    model_fields = {f.name: f for f in fields(model_cls)}  # type: ignore[arg-type]
    wire_keys = set(sample.keys())
    model_keys = set(model_fields)

    wire_only = wire_keys - model_keys
    model_only = model_keys - wire_keys

    print(f"\n=== {name} ({model_cls.__name__}) ===")
    print(f"  wire keys: {len(wire_keys)}  |  model keys: {len(model_keys)}")
    if wire_only:
        print(f"  !! wire keys NOT in model (ADD THESE): {sorted(wire_only)}")
        for k in sorted(wire_only):
            v = sample[k]
            print(f"       {k!r} -> {type(v).__name__}: {v!r:.80}")
    if model_only:
        print(f"  ?? model keys NOT in this sample (may be conditional): {sorted(model_only)}")

    # Type mismatches on shared keys.
    import typing

    hints = typing.get_type_hints(model_cls)
    mismatches: list[str] = []
    for k in wire_keys & model_keys:
        v = sample[k]
        expected = _python_kinds_for(hints[k])
        if v is None:
            # Accept None even if the annotation isn't Optional — SafeModel
            # will substitute the default.
            continue
        if not isinstance(v, expected):
            mismatches.append(
                f"       {k!r}: wire={type(v).__name__}={v!r:.60}, expected={expected}"
            )
    if mismatches:
        print("  !! type mismatches:")
        for line in mismatches:
            print(line)


def sample_first(raw: Any) -> dict[str, Any] | None:
    if isinstance(raw, list) and raw:
        first = raw[0]
        if isinstance(first, dict):
            return first
    elif isinstance(raw, dict):
        return raw
    return None


def fetch_posiciones() -> list[dict[str, Any]] | None:
    if not ACCOUNT:
        print("-- skipped posiciones: HIGYRUS_TEST_ACCOUNT_ID missing")
        return None
    raw = _client._get(
        f"/api/cuentas/{ACCOUNT}/posiciones",
        fecha=format_date(date.today()),
        incluirParking=format_bool(True),
    )
    assert isinstance(raw, list)
    return raw


def fetch_movimientos() -> list[dict[str, Any]] | None:
    if not ACCOUNT:
        print("-- skipped movimientos: HIGYRUS_TEST_ACCOUNT_ID missing")
        return None
    today = date.today()
    desde = today - timedelta(days=30)
    raw = _client._get(
        f"/api/cuentas/{ACCOUNT}/movimientos",
        fechaDesde=format_date(desde),
        fechaHasta=format_date(today),
    )
    assert isinstance(raw, list)
    return raw


def fetch_posicion_valuada() -> list[dict[str, Any]] | None:
    if not (ACCOUNT and TIPO_CUENTA and NIVEL):
        print("-- skipped posicionValuada: missing ACCOUNT / TIPO_CUENTA / NIVEL")
        return None
    today = date.today()
    desde = today.replace(day=1)
    raw = _client._get(
        f"/api/cuentas/{ACCOUNT}/posicionValuada",
        tipoCuenta=TIPO_CUENTA,
        nivel=NIVEL,
        desde=format_date(desde),
        hasta=format_date(today),
    )
    assert isinstance(raw, list)
    return raw


def main() -> None:
    for name, fetcher, model in [
        ("/api/cuentas/{idCuenta}/posiciones", fetch_posiciones, Posicion),
        ("/api/cuentas/{idCuenta}/movimientos", fetch_movimientos, Movimiento),
        ("/api/cuentas/{idCuenta}/posicionValuada", fetch_posicion_valuada, PosicionValuada),
    ]:
        try:
            raw = fetcher()
        except Exception as err:
            print(f"\n!! {name} failed: {type(err).__name__}: {err}")
            continue
        if raw is None:
            continue
        sample = sample_first(raw)
        if sample is None:
            print(f"\n-- {name}: no rows in response")
            continue
        diff_schema(name, sample, model)
        print("  sample row (truncated):")
        print("    " + json.dumps(sample, ensure_ascii=False, default=str)[:500])


if __name__ == "__main__":
    main()
