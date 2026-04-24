"""Safe-access frozen dataclasses for Higyrus API responses.

All response models inherit from :class:`SafeModel` and are constructed via
:meth:`SafeModel.from_api`, which tolerates partial or missing fields and
substitutes safe defaults per type:

- ``str`` -> ``""``
- ``int`` / ``float`` -> ``0`` / ``0.0``
- ``bool`` -> ``False``
- ``list[X]`` -> ``[]``
- nested ``SafeModel`` -> ``X.from_api(None)`` (empty instance)
- ``X | None`` -> ``None`` when missing (explicit opt-in to nullable)

Extra keys in the payload are ignored; missing keys fall back to defaults.
Chained access like ``posicion.parking[0].diasParking`` never raises — the
worst case is a final ``None`` or a zero-valued primitive.

Field names follow the wire format (camelCase) verbatim so JSON parsing
can stay declarative. This module is exempt from the ``N815`` naming rule
(see ``[tool.ruff.lint.per-file-ignores]`` in ``pyproject.toml``).
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from types import NoneType, UnionType
from typing import Any, Self, Union, cast, get_args, get_origin, get_type_hints


class SafeModel:
    """Base class for Higyrus API response models.

    Subclasses must be frozen dataclasses. Construct instances via
    :meth:`from_api` to tolerate partial or missing fields.
    """

    @classmethod
    def from_api(cls, payload: Any) -> Self:
        """Build an instance from an API payload, with safe defaults."""
        data: dict[str, Any] = payload if isinstance(payload, dict) else {}
        hints = get_type_hints(cls)
        kwargs: dict[str, Any] = {}
        for field in fields(cast(Any, cls)):
            kwargs[field.name] = _coerce(data.get(field.name), hints[field.name])
        return cast(Self, cls(**kwargs))


def _coerce(value: Any, hint: Any) -> Any:
    """Coerce ``value`` to match ``hint``, substituting safe defaults for ``None``."""
    origin = get_origin(hint)
    args = get_args(hint)

    # Optional[T] / T | None: explicit opt-in to nullable — a missing value
    # stays None instead of collapsing to a typed zero.
    if origin is Union or origin is UnionType:
        if value is None:
            return None
        non_none = [a for a in args if a is not NoneType]
        if len(non_none) == 1:
            return _coerce(value, non_none[0])
        return value

    if origin is list:
        if not isinstance(value, list):
            return []
        inner = args[0] if args else Any
        return [_coerce(item, inner) for item in value]

    if isinstance(hint, type) and issubclass(hint, SafeModel):
        return hint.from_api(value)

    if hint is str:
        return value if isinstance(value, str) else ""
    if hint is bool:
        return value if isinstance(value, bool) else False
    if hint is int:
        # bool is a subclass of int in Python — exclude it so bool payloads
        # don't collapse into "cantidad=True".
        if isinstance(value, bool):
            return 0
        return value if isinstance(value, int) else 0
    if hint is float:
        if isinstance(value, bool):
            return 0.0
        if isinstance(value, int | float):
            return float(value)
        return 0.0

    return value


@dataclass(frozen=True, slots=True)
class PosicionValuada(SafeModel):
    """Valued position row returned by ``GET /api/cuentas/{idCuenta}/posicionValuada``.

    See ``documentation/higyrus-docs.pdf`` pp. 49-52. Shape-compatible with
    the multi-account endpoint ``POST /api/cuentas/posicionValuada``.

    Note: the PDF renders some response keys with Spanish accents
    (``información``, ``fechaCotización``, ``valuación``, ``sesión``),
    which is inconsistent with every other endpoint in the spec (where
    keys are ASCII: ``informacion``, ``fechaPrecio``, ``precioUnitario``).
    We treat the accents as a doc/OCR artifact and mirror the rest of the
    API. If the live service actually emits accented keys, add a second
    pass of aliases in ``from_api`` — do not rename these fields.
    """

    cuenta: str
    operador: str
    unidad: str
    lugar: str
    estado: str
    uso: str
    fecha: str
    comprobante: str
    informacion: str
    cantidad: int
    fechaCotizacion: str
    precio: float
    valuacion: float
    administrador: str
    cartera: str
    mercado: str
    segmento: str
    sesion: str


@dataclass(frozen=True, slots=True)
class Parking(SafeModel):
    """Parking entry nested inside a :class:`Posicion`.

    See ``documentation/higyrus-docs.pdf`` pp. 33-36.
    """

    monedaPosicion: str
    diasParking: int
    cantidadLiquidada: int
    observacion: str


@dataclass(frozen=True, slots=True)
class Movimiento(SafeModel):
    """Account movement row returned by ``GET /api/cuentas/{idCuenta}/movimientos``.

    See ``documentation/higyrus-docs.pdf`` pp. 26-30. The ``fecha`` field
    arrives as an ISO 8601 string (e.g. ``"2023-06-28T20:03:18.889Z"``);
    callers can parse it with :meth:`datetime.datetime.fromisoformat` when
    needed. ``idMovimientos`` is the list of internal transaction IDs that
    compose the movement.
    """

    cuenta: str
    fechaDesde: str
    fechaHasta: str
    tipoTitulo: str
    tipoTituloAgente: str
    especie: str
    simboloLocal: str
    lugar: str
    estado: str
    fecha: str
    tipoOperacion: str
    comprobante: str
    informacion: str
    subCuenta: str
    cantidad: int
    tipoEspecie: str
    movimiento: str
    valuacion: float
    factorizacion: str
    concepto: str
    idMovimientos: list[int]


@dataclass(frozen=True, slots=True)
class Posicion(SafeModel):
    """Account position row returned by ``GET /api/cuentas/{idCuenta}/posiciones``.

    See ``documentation/higyrus-docs.pdf`` pp. 33-36. The
    ``disponibleAjustado`` field is only populated for FCI instruments when
    the Higyrus parameter ``irmo.fci.rescate_estadoSolicitudesAdescontar``
    is active; if absent, the safe-access default (``0.0``) is used.
    """

    cuenta: str
    fecha: str
    tipoTitulo: str
    tipoTituloAgente: str
    codigoISIN: str
    especie: str
    nombreEspecie: str
    simboloLocal: str
    lugar: str
    subCuenta: str
    estado: str
    disponibleAjustado: float
    cantidadLiquidada: int
    cantidadPendienteLiquidar: int
    precio: float
    precioUnitario: float
    monedaCotizacion: str
    fechaPrecio: str
    informacion: str
    parking: list[Parking]
