from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from higyrus_client.models import Parking, Posicion, SafeModel, _coerce

# ---------------------------------------------------------------------------
# Helper models for focused unit testing of SafeModel / _coerce
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Leaf(SafeModel):
    name: str
    count: int


@dataclass(frozen=True, slots=True)
class _Parent(SafeModel):
    label: str
    flag: bool
    amount: float
    child: _Leaf
    children: list[_Leaf]
    optional_note: str | None


# ---------------------------------------------------------------------------
# _coerce scalar paths
# ---------------------------------------------------------------------------


def test_coerce_str_default_on_none() -> None:
    assert _coerce(None, str) == ""


def test_coerce_str_passes_through() -> None:
    assert _coerce("hello", str) == "hello"


def test_coerce_str_rejects_non_str() -> None:
    assert _coerce(123, str) == ""


def test_coerce_int_default_on_none() -> None:
    assert _coerce(None, int) == 0


def test_coerce_int_rejects_bool() -> None:
    # bool is a subclass of int in Python — ensure we don't misclassify.
    assert _coerce(True, int) == 0


def test_coerce_float_widens_int() -> None:
    assert _coerce(5, float) == 5.0


def test_coerce_float_rejects_str() -> None:
    assert _coerce("3.14", float) == 0.0


def test_coerce_bool_default_on_none() -> None:
    assert _coerce(None, bool) is False


def test_coerce_bool_rejects_int() -> None:
    assert _coerce(1, bool) is False


# ---------------------------------------------------------------------------
# _coerce container paths
# ---------------------------------------------------------------------------


def test_coerce_list_none_becomes_empty() -> None:
    assert _coerce(None, list[int]) == []


def test_coerce_list_non_list_becomes_empty() -> None:
    assert _coerce("not a list", list[int]) == []


def test_coerce_list_coerces_each_item() -> None:
    assert _coerce([1, None, "x", 3], list[int]) == [1, 0, 0, 3]


# ---------------------------------------------------------------------------
# SafeModel.from_api — behaviour
# ---------------------------------------------------------------------------


def test_from_api_full_payload() -> None:
    leaf = _Leaf.from_api({"name": "a", "count": 7})
    assert leaf.name == "a"
    assert leaf.count == 7


def test_from_api_none_payload_returns_empty_instance() -> None:
    leaf = _Leaf.from_api(None)
    assert leaf.name == ""
    assert leaf.count == 0


def test_from_api_missing_keys_fill_defaults() -> None:
    leaf = _Leaf.from_api({"name": "only"})
    assert leaf.name == "only"
    assert leaf.count == 0


def test_from_api_none_values_fill_defaults() -> None:
    leaf = _Leaf.from_api({"name": None, "count": None})
    assert leaf.name == ""
    assert leaf.count == 0


def test_from_api_extra_keys_are_ignored() -> None:
    leaf = _Leaf.from_api({"name": "a", "count": 1, "extra": "ignored", "other": 99})
    assert leaf.name == "a"
    assert leaf.count == 1


def test_from_api_nested_model_populated() -> None:
    parent = _Parent.from_api(
        {
            "label": "p",
            "flag": True,
            "amount": 2.5,
            "child": {"name": "c", "count": 3},
            "children": [{"name": "x", "count": 1}, {"name": "y", "count": 2}],
            "optional_note": "present",
        }
    )
    assert parent.child.name == "c"
    assert parent.child.count == 3
    assert [c.name for c in parent.children] == ["x", "y"]
    assert parent.optional_note == "present"


def test_from_api_nested_model_absent_becomes_empty() -> None:
    parent = _Parent.from_api({"label": "p"})
    # Chaining stays safe even without any nested payload.
    assert parent.child.name == ""
    assert parent.child.count == 0
    assert parent.children == []


def test_from_api_optional_field_preserves_none() -> None:
    parent = _Parent.from_api({"label": "p"})
    assert parent.optional_note is None


def test_from_api_optional_field_coerces_when_present() -> None:
    parent = _Parent.from_api({"label": "p", "optional_note": "note"})
    assert parent.optional_note == "note"


# ---------------------------------------------------------------------------
# Pilot models: Posicion + Parking (see documentation/higyrus-docs.pdf, p. 33-36)
# ---------------------------------------------------------------------------


def _full_posicion_payload() -> dict[str, Any]:
    return {
        "cuenta": "123",
        "fecha": "23/04/2026",
        "tipoTitulo": "Accion",
        "tipoTituloAgente": "Accion Local",
        "codigoISIN": "ARXXXXXX",
        "especie": "YPFD",
        "nombreEspecie": "YPF",
        "simboloLocal": "YPFD",
        "lugar": "BYMA",
        "subCuenta": "01",
        "estado": "vigente",
        "disponibleAjustado": 1500.75,
        "cantidadLiquidada": 100,
        "cantidadPendienteLiquidar": 20,
        "precio": 15000.5,
        "precioUnitario": 150.0,
        "monedaCotizacion": "ARS",
        "fechaPrecio": "22/04/2026",
        "informacion": "cartera",
        "parking": [
            {
                "monedaPosicion": "USD",
                "diasParking": 5,
                "cantidadLiquidada": 50,
                "observacion": "ok",
            }
        ],
    }


def test_posicion_full_payload() -> None:
    pos = Posicion.from_api(_full_posicion_payload())
    assert pos.cuenta == "123"
    assert pos.disponibleAjustado == 1500.75
    assert len(pos.parking) == 1
    assert pos.parking[0].diasParking == 5


def test_posicion_partial_payload_fci_without_disponible_ajustado() -> None:
    # Replicates the documented behaviour: disponibleAjustado absent for
    # non-FCI or when the Higyrus parameter is disabled.
    payload = _full_posicion_payload()
    del payload["disponibleAjustado"]
    pos = Posicion.from_api(payload)
    assert pos.disponibleAjustado == 0.0


def test_posicion_empty_payload_chaining_stays_safe() -> None:
    pos = Posicion.from_api(None)
    assert pos.cuenta == ""
    assert pos.precio == 0.0
    assert pos.parking == []


def test_posicion_parking_absent_becomes_empty_list() -> None:
    payload = _full_posicion_payload()
    del payload["parking"]
    pos = Posicion.from_api(payload)
    assert pos.parking == []


def test_parking_from_api_tolerates_missing_fields() -> None:
    parking = Parking.from_api({"monedaPosicion": "USD"})
    assert parking.monedaPosicion == "USD"
    assert parking.diasParking == 0
    assert parking.cantidadLiquidada == 0
    assert parking.observacion == ""
