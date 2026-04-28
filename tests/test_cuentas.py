"""Tests for endpoints under the Cuentas domain."""

from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import MagicMock

import pytest

from higyrus_client.client import (
    get_listado_cuentas,
    get_movimientos,
    get_posicion_valuada,
    get_posiciones,
)
from higyrus_client.exceptions import AuthorizationError, HigyrusAPIError
from higyrus_client.models import Cuenta, Movimiento, Posicion, PosicionValuada
from tests.conftest import build_response


def _movimiento_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "cuenta": "123",
        "fechaDesde": "01/04/2026",
        "fechaHasta": "23/04/2026",
        "fechaConcertacion": "15/04/2026",
        "tipoTitulo": "Accion",
        "tipoTituloAgente": "Accion Local",
        "especie": "YPFD",
        "simboloLocal": "YPFD",
        "lugar": "BYMA",
        "estado": "liquidado",
        # Wire format (verified against sandbox) is "dd/mm/yyyy HH:MM:SS",
        # not ISO 8601. The model stores it verbatim either way.
        "fecha": "15/04/2026 15:30:00",
        "tipoOperacion": "COMPRA",
        "comprobante": "BO-001",
        "informacion": "",
        "subCuenta": "01",
        # cantidad comes as float on the wire (e.g. -21936.48).
        "cantidad": 50.0,
        "tipoEspecie": "ACCION",
        "movimiento": "Compra contado",
        "valuacion": 7500.0,
        "factorizacion": "",
        "concepto": "OP",
        "idMovimientos": [101, 102],
    }
    base.update(overrides)
    return base


def _posicion_valuada_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "cuenta": "123",
        "operador": "op1",
        "unidad": "ARS",
        "lugar": "BYMA",
        "estado": "vigente",
        "uso": "",
        "fecha": "15/04/2026 15:30:00",
        "comprobante": "BO-001",
        "informacion": "",
        # cantidad comes as float on the wire (e.g. -2788.35).
        "cantidad": 100.0,
        "fechaCotizacion": "23/04/2026",
        "precio": 150.0,
        "valuacion": 15000.0,
        "administrador": "admin",
        "cartera": "cart1",
        "mercado": "BYMA",
        "segmento": "CPA",
        "sesion": "PRIN",
        "tipoTitulo": "Accion",
        "monedaCotizacion": "ARS",
        "idMovimiento": "MV-001",
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


def test_get_movimientos_preserves_wire_datetime_string(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    # The wire `fecha` field is "dd/mm/yyyy HH:MM:SS" (verified against
    # sandbox) — the model stores it verbatim. We do not reformat or
    # parse it into a datetime.
    mock_session.request.return_value = build_response(
        payload=[_movimiento_payload(fecha="25/03/2026 00:00:00")],
        status_code=200,
    )

    result = get_movimientos("X", date(2026, 4, 1), date(2026, 4, 23))

    assert result[0].fecha == "25/03/2026 00:00:00"


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
# get_posicion_valuada
# ---------------------------------------------------------------------------


def test_get_posicion_valuada_happy_path(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(
        payload=[_posicion_valuada_payload(), _posicion_valuada_payload(cuenta="456")],
        status_code=200,
    )

    result = get_posicion_valuada(
        "123",
        tipo_cuenta="COMITENTE",
        nivel="DETALLE",
        desde=date(2026, 4, 1),
        hasta=date(2026, 4, 23),
    )

    assert len(result) == 2
    assert all(isinstance(p, PosicionValuada) for p in result)
    assert result[0].valuacion == 15000.0
    assert result[1].cuenta == "456"


def test_get_posicion_valuada_accepts_201_status(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    # The PDF lists success as HTTP 201 on a GET (doc inconsistency).
    # _request trusts resp.ok, so any 2xx is accepted transparently.
    mock_session.request.return_value = build_response(
        payload=[_posicion_valuada_payload()],
        status_code=201,
    )

    result = get_posicion_valuada(
        "X",
        "COMITENTE",
        "DETALLE",
        date(2026, 4, 1),
        date(2026, 4, 23),
    )

    assert len(result) == 1


def test_get_posicion_valuada_204_returns_empty_list(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(status_code=204)

    result = get_posicion_valuada(
        "X",
        "COMITENTE",
        "DETALLE",
        date(2026, 4, 1),
        date(2026, 4, 23),
    )

    assert result == []


def test_get_posicion_valuada_url_and_minimal_params(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(payload=[], status_code=200)

    get_posicion_valuada(
        "ABC-9",
        tipo_cuenta="COMITENTE",
        nivel="DETALLE",
        desde=date(2026, 1, 5),
        hasta=date(2026, 4, 23),
    )

    call = mock_session.request.call_args
    assert call.args == ("GET", "https://api.test/api/cuentas/ABC-9/posicionValuada")
    # Optional params not passed → dropped entirely; no default bools sent.
    assert call.kwargs["params"] == {
        "tipoCuenta": "COMITENTE",
        "nivel": "DETALLE",
        "desde": "05/01/2026",
        "hasta": "23/04/2026",
    }


def test_get_posicion_valuada_translates_all_optional_kwargs(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(payload=[], status_code=200)

    get_posicion_valuada(
        "X",
        "COMITENTE",
        "DETALLE",
        date(2026, 4, 1),
        date(2026, 4, 23),
        lugar="BYMA",
        estado="vigente",
        tipo_titulo="Accion",
        extracto="EXT-1",
        ocultar_cerradas=True,
        especie="YPFD",
        concertacion=False,
        actualizar=True,
    )

    params = mock_session.request.call_args.kwargs["params"]
    assert params["lugar"] == "BYMA"
    assert params["estado"] == "vigente"
    assert params["tipoTitulo"] == "Accion"
    assert params["extracto"] == "EXT-1"
    assert params["ocultarCerradas"] == "True"
    assert params["especie"] == "YPFD"
    assert params["concertacion"] == "False"
    assert params["actualizar"] == "True"


def test_get_posicion_valuada_bool_none_is_dropped(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    # Tri-state bools: None must not be sent (server default applies).
    # Distinguishes from False, which explicitly forces the flag off.
    mock_session.request.return_value = build_response(payload=[], status_code=200)

    get_posicion_valuada(
        "X",
        "COMITENTE",
        "DETALLE",
        date(2026, 4, 1),
        date(2026, 4, 23),
        ocultar_cerradas=False,
    )

    params = mock_session.request.call_args.kwargs["params"]
    assert params["ocultarCerradas"] == "False"
    assert "concertacion" not in params
    assert "actualizar" not in params


def test_get_posicion_valuada_partial_payload_uses_safe_defaults(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    # Missing optional fields → SafeModel defaults, no crash on chaining.
    payload = _posicion_valuada_payload()
    for key in ("administrador", "cartera", "mercado", "segmento", "sesion"):
        del payload[key]
    mock_session.request.return_value = build_response(payload=[payload], status_code=200)

    result = get_posicion_valuada(
        "X",
        "COMITENTE",
        "DETALLE",
        date(2026, 4, 1),
        date(2026, 4, 23),
    )

    assert result[0].administrador == ""
    assert result[0].cartera == ""
    assert result[0].valuacion == 15000.0  # still present


def test_get_posicion_valuada_403_raises_authorization_error(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(
        payload={"errors": [{"title": "forbidden", "detail": "missing permission"}]},
        status_code=403,
    )

    with pytest.raises(AuthorizationError):
        get_posicion_valuada(
            "X",
            "COMITENTE",
            "DETALLE",
            date(2026, 4, 1),
            date(2026, 4, 23),
        )


def test_get_posicion_valuada_400_raises_base_error(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(
        payload={"errors": [{"title": "bad_request", "detail": "nivel inválido"}]},
        status_code=400,
    )

    with pytest.raises(HigyrusAPIError) as exc:
        get_posicion_valuada(
            "X",
            "COMITENTE",
            "DETALLE",
            date(2026, 4, 1),
            date(2026, 4, 23),
        )

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


# ---------------------------------------------------------------------------
# get_listado_cuentas
# ---------------------------------------------------------------------------


def _cuenta_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "123",
        "tipo": "comitente",
        "cartera": "C1",
        "categoria": "minorista",
        "clase": "individuo",
        "fechaAlta": "01/03/2026",
        "denominacion": "PEREZ JUAN",
        "alias": "JP",
        "titular": "PEREZ JUAN",
        "tipoTitular": "fisica",
        "estado": "alta",
        "nota": "",
        "disposicionesGenerales": {
            "vigenciaDesde": "01/03/2026",
            "vigenciaHasta": "01/03/2027",
            "condicionesGenerales": "OK",
            "autorizacionGeneral": "Si",
            "fondosDisponibles": "Propios",
            "cuentaFCI": "No",
            "derivacionBYMA": "No",
            "instruccionesFondos": "Cuenta bancaria",
            "tipoCliente": "Minorista",
            "horizonteInversion": "Largo",
            "perfilInversion": "Conservador",
            "actividadEsperada": "Inversion",
            "operatoria": "Plena",
            "vinculacionAgente": "Cliente",
            "derivacionMAV": "No",
        },
        "domicilios": [
            {
                "uso": "real",
                "pais": "ARG",
                "provincia": "Santa Fe",
                "codigoPostal": "S2000",
                "ciudad": "Rosario",
                "direccion": "Paraguay 777",
            }
        ],
        "personasRelacionadas": [
            {
                "tipoRelacion": "titular",
                "persona": "PEREZ JUAN",
                "tipoId": "DNI",
                "id": "12345678",
                "orden": "1",
                "desde": "01/03/2026",
                "hasta": "",
                "realizarSeguimiento": "Si",
                "limitaAccesoCuenta": "No",
                "participacionFondeo": "100",
                "descripcion": "",
                "limitaOperacion": "No",
                "limitaExtraccion": "No",
            }
        ],
        "mediosComunicacion": [
            {
                "tipo": "email",
                "medio": "juan@example.com",
                "vigenciaDesde": "01/03/2026",
                "vigenciaHasta": "",
                "uso": "principal",
                "principal": "Si",
                "notas": "",
            }
        ],
        "cuentasBancarias": [
            {
                "cbu": "0170123456789012345678",
                "banco": "Frances",
                "moneda": "ARS",
                "vigenteDesde": "01/03/2026",
                "vigenteHasta": "",
            }
        ],
        "administrador": {
            "agente": {"codigo": "A01", "denominacion": "Aunesa"},
            "operador": {
                "nombre": "operador1",
                "nombreReal": "Operador Uno",
                "idExterno": "OP-1",
            },
            "sucursal": {"codigo": "S01", "denominacion": "Rosario"},
        },
    }
    base.update(overrides)
    return base


def test_get_listado_cuentas_happy_path(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(
        payload=[_cuenta_payload(), _cuenta_payload(id="456")],
        status_code=200,
    )

    result = get_listado_cuentas()

    assert len(result) == 2
    assert all(isinstance(c, Cuenta) for c in result)
    assert result[0].id == "123"
    assert result[1].id == "456"
    assert result[0].domicilios[0].direccion == "Paraguay 777"
    assert result[0].administrador.agente.denominacion == "Aunesa"
    assert result[0].cuentasBancarias[0].cbu == "0170123456789012345678"


def test_get_listado_cuentas_204_returns_empty_list(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(status_code=204)

    assert get_listado_cuentas() == []


def test_get_listado_cuentas_url_and_no_filters(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(payload=[], status_code=200)

    get_listado_cuentas()

    call = mock_session.request.call_args
    assert call.args == ("GET", "https://api.test/api/cuentas/listadoCuentas")
    # Sin filtros, todos los params son None y deben caer por drop_none.
    assert call.kwargs["params"] == {}


def test_get_listado_cuentas_translates_snake_to_camel(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(payload=[], status_code=200)

    get_listado_cuentas(
        tipo_cuenta="comitente",
        estado="alta",
        fecha_desde=date(2026, 1, 1),
        fecha_hasta=date(2026, 4, 23),
    )

    params = mock_session.request.call_args.kwargs["params"]
    assert params == {
        "tipoCuenta": "comitente",
        "estado": "alta",
        "fechaDesde": "01/01/2026",
        "fechaHasta": "23/04/2026",
    }


def test_get_listado_cuentas_id_cuenta_passed_as_list_for_repeated_param(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    # ``requests`` serializes list values as repeated query params:
    # ?idCuenta=111&idCuenta=123. Verified by passing the list straight
    # through without flattening.
    mock_session.request.return_value = build_response(payload=[], status_code=200)

    get_listado_cuentas(id_cuenta=["111", "123", "1234"])

    params = mock_session.request.call_args.kwargs["params"]
    assert params == {"idCuenta": ["111", "123", "1234"]}


def test_get_listado_cuentas_partial_payload_uses_safe_defaults(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    # Si faltan los nested objetos / listas, SafeModel cae a defaults
    # vacios — encadenar atributos no debe romper.
    payload = _cuenta_payload()
    del payload["disposicionesGenerales"]
    del payload["domicilios"]
    del payload["administrador"]
    mock_session.request.return_value = build_response(payload=[payload], status_code=200)

    result = get_listado_cuentas()

    assert result[0].disposicionesGenerales.tipoCliente == ""
    assert result[0].domicilios == []
    assert result[0].administrador.agente.codigo == ""
    assert result[0].administrador.operador.nombre == ""


def test_get_listado_cuentas_403_raises_authorization_error(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(
        payload={"errors": [{"title": "forbidden", "detail": "missing permission"}]},
        status_code=403,
    )

    with pytest.raises(AuthorizationError):
        get_listado_cuentas()


def test_get_listado_cuentas_400_raises_base_error(
    reset_client_state: None,
    mock_session: MagicMock,
) -> None:
    mock_session.request.return_value = build_response(
        payload={"errors": [{"title": "bad_request", "detail": "estado invalido"}]},
        status_code=400,
    )

    with pytest.raises(HigyrusAPIError) as exc:
        get_listado_cuentas(estado="ZZZ")

    assert exc.value.status_code == 400
