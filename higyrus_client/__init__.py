"""Python client for the Higyrus API.

Re-exports the REST client surface as a flat namespace, so callers can do::

    import higyrus_client as higyrus

    higyrus.login()
    status = higyrus.get_health()

See the README and the in-module docstrings for usage details.
"""

from .client import (
    get_health,
    get_listado_cuentas,
    get_movimientos,
    get_posicion_valuada,
    get_posiciones,
    login,
)
from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    HigyrusAPIError,
)
from .models import (
    Administrador,
    Agente,
    Cuenta,
    CuentaBancaria,
    DisposicionesGenerales,
    Domicilio,
    MedioComunicacion,
    Movimiento,
    Operador,
    Parking,
    PersonaRelacionada,
    Posicion,
    PosicionValuada,
    SafeModel,
    Sucursal,
)

__all__ = [
    # Exceptions
    "AuthenticationError",
    "AuthorizationError",
    "HigyrusAPIError",
    # Auth / health
    "get_health",
    "login",
    # Cuentas
    "get_listado_cuentas",
    "get_movimientos",
    "get_posicion_valuada",
    "get_posiciones",
    # Models
    "Administrador",
    "Agente",
    "Cuenta",
    "CuentaBancaria",
    "DisposicionesGenerales",
    "Domicilio",
    "MedioComunicacion",
    "Movimiento",
    "Operador",
    "Parking",
    "PersonaRelacionada",
    "Posicion",
    "PosicionValuada",
    "SafeModel",
    "Sucursal",
]
