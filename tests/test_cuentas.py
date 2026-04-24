"""Tests for endpoints under the Cuentas domain."""

from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import MagicMock

import pytest

from higyrus_client.client import get_movimientos, get_posiciones
from higyrus_client.exceptions import AuthorizationError, HigyrusAPIError
from higyrus_client.models import Movimiento, Posicion
from tests.conftest import build_response


def _movimiento_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "cuenta": "123",
        "fechaDesde": "01/04/2026",
        "fechaHasta": "23/04/2026",
        "tipoTitulo": "Accion",
        "tipoTituloAgente": "Accion Local",
        "especie": "YPFD",
        "simboloLocal": "YPFD",
        "lugar": "BYMA",
        "estado": "liquidado",
        "fecha": "2026-04-15T15:30:00.000Z",
        "tipoOperacion": "COMPRA",
        "comprobante": "BO-001",
        "informacion": "",
        "subCuenta": "01",
        "cantidad": 50,
        "tipoEspecie": "ACCION",
        "movimiento": "Compra contado",
        "valuacion": 7500.0,
        "factorizacion": "",
        "concepto": "OP",
        "idMovimientos": [101, 102],
    }
    base.update(overrides)
    return base


def _posicion_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "cuenta": "123",
        "fecha": "23/04/2026",
        "tipoTitulo": "Accion",
        "tipoTituloAgente": "Accion Local",
        "codigoISIN": "ARXXXX",
        "especie": "YPFD",
        "nombreEspecie": "YPF",
        "simboloLocal": "YPFD",
        "lugar": "BYMA",
        "subCuenta": "01",
        "estado": "vigente",
        "disponibleAjustado": 1500.0,
        "cantidadLiquidada": 100,
        "cantidadPendienteLiquidar": 0,
        "precio": 150.0,
        "precioUnitario": 150.0,
        "monedaCotizacion": "ARS",
        "fechaPrecio": "23/04/2026",
        "informacion": "",
        "parking": [],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# get_movimientos
# ---------------------------------------------------------------------------


def test_get_movimientos_happy_path(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(
        payload=[_movimiento_payload(), _movimiento_payload(tipoOperacion="VENTA")],
        status_code=200,
    )

    result = get_movimientos("123", date(2026, 4, 1), date(2026, 4, 23))

    assert len(result) == 2
    assert all(isinstance(m, Movimiento) for m in result)
    assert result[0].tipoOperacion == "COMPRA"
    assert result[1].tipoOperacion == "VENTA"
    assert result[0].idMovimientos == [101, 102]


def test_get_movimientos_204_returns_empty_list(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(status_code=204)

    assert get_movimientos("123", date(2026, 4, 1), date(2026, 4, 23)) == []


def test_get_movimientos_url_and_default_params(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(payload=[], status_code=200)

    get_movimientos("ABC-9", date(2026, 1, 5), date(2026, 4, 23))

    call = mock_session.request.call_args
    assert call.args == ("GET", "https://api.test/api/cuentas/ABC-9/movimientos")
    # Optional kwargs default to None and must be dropped entirely.
    assert call.kwargs["params"] == {
        "fechaDesde": "05/01/2026",
        "fechaHasta": "23/04/2026",
    }


def test_get_movimientos_translates_snake_to_camel(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(payload=[], status_code=200)

    get_movimientos(
        "X",
        date(2026, 4, 1),
        date(2026, 4, 23),
        especie="YPFD",
        tipo_titulo="Accion",
        tipo_titulo_agente="Accion Local",
        movimiento="Compra contado",
    )

    params = mock_session.request.call_args.kwargs["params"]
    assert params["especie"] == "YPFD"
    assert params["tipoTitulo"] == "Accion"
    assert params["tipoTituloAgente"] == "Accion Local"
    assert params["movimiento"] == "Compra contado"


def test_get_movimientos_accepts_string_fechas(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(payload=[], status_code=200)

    get_movimientos("X", "01/04/2026", "23/04/2026")

    params = mock_session.request.call_args.kwargs["params"]
    assert params["fechaDesde"] == "01/04/2026"
    assert params["fechaHasta"] == "23/04/2026"


def test_get_movimientos_preserves_iso_datetime_string(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    # The response `fecha` field arrives as ISO 8601 — the model stores it
    # verbatim; we do not reformat.
    mock_session.request.return_value = build_response(
        payload=[_movimiento_payload(fecha="2026-04-15T15:30:00.123Z")],
        status_code=200,
    )

    result = get_movimientos("X", date(2026, 4, 1), date(2026, 4, 23))

    assert result[0].fecha == "2026-04-15T15:30:00.123Z"


def test_get_movimientos_tolerates_empty_id_movimientos(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    payload = _movimiento_payload()
    del payload["idMovimientos"]
    mock_session.request.return_value = build_response(payload=[payload], status_code=200)

    result = get_movimientos("X", date(2026, 4, 1), date(2026, 4, 23))

    # Missing list → [] via SafeModel defaults.
    assert result[0].idMovimientos == []


def test_get_movimientos_403_raises_authorization_error(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(
        payload={"errors": [{"title": "forbidden", "detail": "missing permission"}]},
        status_code=403,
    )

    with pytest.raises(AuthorizationError):
        get_movimientos("X", date(2026, 4, 1), date(2026, 4, 23))


def test_get_movimientos_400_raises_base_error(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(
        payload={"errors": [{"title": "bad_request", "detail": "fecha fuera de rango"}]},
        status_code=400,
    )

    with pytest.raises(HigyrusAPIError) as exc:
        get_movimientos("X", date(2026, 4, 1), date(2026, 4, 23))

    assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# get_posiciones
# ---------------------------------------------------------------------------


def test_get_posiciones_happy_path(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(
        payload=[_posicion_payload(), _posicion_payload(especie="ALUA")],
        status_code=200,
    )

    result = get_posiciones("123", date(2026, 4, 23))

    assert len(result) == 2
    assert all(isinstance(p, Posicion) for p in result)
    assert result[0].cuenta == "123"
    assert result[1].especie == "ALUA"


def test_get_posiciones_204_returns_empty_list(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(status_code=204)

    assert get_posiciones("123", date(2026, 4, 23)) == []


def test_get_posiciones_url_and_default_params(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(payload=[], status_code=200)

    get_posiciones("ABC-9", date(2026, 1, 5))

    call = mock_session.request.call_args
    assert call.args == ("GET", "https://api.test/api/cuentas/ABC-9/posiciones")
    # especie is None and should be dropped; incluirParking defaults to
    # False and is still sent explicitly as "False".
    assert call.kwargs["params"] == {"fecha": "05/01/2026", "incluirParking": "False"}


def test_get_posiciones_passes_especie(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(payload=[], status_code=200)

    get_posiciones("X", date(2026, 4, 23), especie="YPFD")

    params = mock_session.request.call_args.kwargs["params"]
    assert params["especie"] == "YPFD"


def test_get_posiciones_incluir_parking_true_serializes_as_capitalized(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(payload=[], status_code=200)

    get_posiciones("X", date(2026, 4, 23), incluir_parking=True)

    params = mock_session.request.call_args.kwargs["params"]
    assert params["incluirParking"] == "True"


def test_get_posiciones_accepts_string_fecha(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(payload=[], status_code=200)

    get_posiciones("X", "23/04/2026")

    params = mock_session.request.call_args.kwargs["params"]
    assert params["fecha"] == "23/04/2026"


def test_get_posiciones_parses_parking_entries(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    payload = _posicion_payload(
        parking=[
            {
                "monedaPosicion": "USD",
                "diasParking": 5,
                "cantidadLiquidada": 50,
                "observacion": "ok",
            }
        ]
    )
    mock_session.request.return_value = build_response(payload=[payload], status_code=200)

    result = get_posiciones("X", date(2026, 4, 23), incluir_parking=True)

    assert result[0].parking[0].diasParking == 5
    assert result[0].parking[0].monedaPosicion == "USD"


def test_get_posiciones_without_disponible_ajustado_defaults_to_zero(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    # Reproduces the documented behaviour: disponibleAjustado is absent
    # for non-FCI instruments or when the Higyrus parameter is disabled.
    payload = _posicion_payload()
    del payload["disponibleAjustado"]
    mock_session.request.return_value = build_response(payload=[payload], status_code=200)

    result = get_posiciones("X", date(2026, 4, 23))

    assert result[0].disponibleAjustado == 0.0


def test_get_posiciones_403_raises_authorization_error(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(
        payload={"errors": [{"title": "forbidden", "detail": "missing permission"}]},
        status_code=403,
    )

    with pytest.raises(AuthorizationError):
        get_posiciones("X", date(2026, 4, 23))


def test_get_posiciones_400_raises_base_error(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(
        payload={"errors": [{"title": "bad_request", "detail": "missing fecha"}]},
        status_code=400,
    )

    with pytest.raises(HigyrusAPIError) as exc:
        get_posiciones("X", date(2026, 4, 23))

    assert exc.value.status_code == 400
