"""Live smoke check for the Higyrus API client.

Runs every public endpoint implemented so far against a real tenant:

1. ``GET /api/health`` (no auth)
2. ``POST /api/login`` (validates credentials and caches the token)
3. ``GET /api/cuentas/{idCuenta}/posiciones``
4. ``GET /api/cuentas/{idCuenta}/movimientos``
5. ``GET /api/cuentas/{idCuenta}/posicionValuada``

Each check is independent — if one fails (e.g. permission missing, bad
config) the others still run. Use this to verify open doc questions
against the live API:

- Does ``/posiciones`` accept ``dd/mm/yyyy`` for the ``fecha`` param?
- Does ``/posicionValuada`` return 200 or 201 on success?
- Does ``/posicionValuada`` emit JSON keys with or without accents?

Required env vars (the client itself reads these from ``.env``):

- ``HIGYRUS_CLIENT_ID``
- ``HIGYRUS_USER``
- ``HIGYRUS_PASSWORD``
- ``HIGYRUS_BASE_URL``

Optional env vars to enable the per-account checks:

- ``HIGYRUS_TEST_ACCOUNT_ID`` — without it, steps 3-5 are skipped.
- ``HIGYRUS_TEST_TIPO_CUENTA`` + ``HIGYRUS_TEST_NIVEL`` — both required
  together to enable step 5 (posicionValuada); without them step 5 is
  skipped but 3 and 4 still run.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

from dotenv import load_dotenv

import higyrus_client as higyrus
from higyrus_client.exceptions import HigyrusAPIError

load_dotenv()

TEST_ACCOUNT = os.getenv("HIGYRUS_TEST_ACCOUNT_ID")
TEST_TIPO_CUENTA = os.getenv("HIGYRUS_TEST_TIPO_CUENTA")
TEST_NIVEL = os.getenv("HIGYRUS_TEST_NIVEL")

# Movements look-back window and positions snapshot offset.
_MOVEMENTS_LOOKBACK_DAYS = 30


def check_health() -> None:
    print("\n== GET /api/health ==")
    try:
        status = higyrus.get_health()
    except HigyrusAPIError as err:
        print(f"  !! get_health: {type(err).__name__}: {err}")
        return
    print(f"  ok: {status}")


def check_login() -> None:
    print("\n== POST /api/login ==")
    try:
        higyrus.login()
    except HigyrusAPIError as err:
        print(f"  !! login: {type(err).__name__}: {err}")
        return
    print("  ok: token cached for 24 h")


def check_posiciones() -> None:
    print("\n== GET /api/cuentas/{idCuenta}/posiciones ==")
    if not TEST_ACCOUNT:
        print("  -- skipped: set HIGYRUS_TEST_ACCOUNT_ID to enable")
        return

    today = date.today()
    try:
        posiciones = higyrus.get_posiciones(
            TEST_ACCOUNT,
            fecha=today,
            incluir_parking=True,
        )
    except HigyrusAPIError as err:
        print(f"  !! get_posiciones: {type(err).__name__}: {err}")
        return

    print(f"  {len(posiciones)} posiciones on {today}")
    for pos in posiciones[:5]:
        print(
            f"    {pos.especie:<12} "
            f"cant={pos.cantidadLiquidada:>10}  "
            f"precio={pos.precio:>12}  "
            f"disp={pos.disponibleAjustado}"
        )


def check_movimientos() -> None:
    print("\n== GET /api/cuentas/{idCuenta}/movimientos ==")
    if not TEST_ACCOUNT:
        print("  -- skipped: set HIGYRUS_TEST_ACCOUNT_ID to enable")
        return

    today = date.today()
    desde = today - timedelta(days=_MOVEMENTS_LOOKBACK_DAYS)
    try:
        movimientos = higyrus.get_movimientos(
            TEST_ACCOUNT,
            fecha_desde=desde,
            fecha_hasta=today,
        )
    except HigyrusAPIError as err:
        print(f"  !! get_movimientos: {type(err).__name__}: {err}")
        return

    print(f"  {len(movimientos)} movimientos between {desde} and {today}")
    for mov in movimientos[:5]:
        fecha = mov.fecha[:10] if mov.fecha else ""
        print(
            f"    {fecha} "
            f"{mov.tipoOperacion:<8} "
            f"{mov.especie:<12} "
            f"cant={mov.cantidad:>10}  "
            f"val={mov.valuacion}"
        )


def check_posicion_valuada() -> None:
    print("\n== GET /api/cuentas/{idCuenta}/posicionValuada ==")
    if not TEST_ACCOUNT:
        print("  -- skipped: set HIGYRUS_TEST_ACCOUNT_ID to enable")
        return
    if not TEST_TIPO_CUENTA or not TEST_NIVEL:
        print("  -- skipped: set HIGYRUS_TEST_TIPO_CUENTA and HIGYRUS_TEST_NIVEL to enable")
        return

    today = date.today()
    desde = today.replace(day=1)
    try:
        valuada = higyrus.get_posicion_valuada(
            TEST_ACCOUNT,
            tipo_cuenta=TEST_TIPO_CUENTA,
            nivel=TEST_NIVEL,
            desde=desde,
            hasta=today,
        )
    except HigyrusAPIError as err:
        print(f"  !! get_posicion_valuada: {type(err).__name__}: {err}")
        return

    print(f"  {len(valuada)} posiciones valuadas between {desde} and {today}")
    for row in valuada[:5]:
        print(
            f"    mercado={row.mercado:<8}  "
            f"cant={row.cantidad:>10}  "
            f"precio={row.precio:>12}  "
            f"val={row.valuacion}"
        )


def main() -> None:
    check_health()
    check_login()
    check_posiciones()
    check_movimientos()
    check_posicion_valuada()


if __name__ == "__main__":
    main()
