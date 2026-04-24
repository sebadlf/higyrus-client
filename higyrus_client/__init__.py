"""Python client for the Higyrus API.

Re-exports the REST client surface as a flat namespace, so callers can do::

    import higyrus_client as higyrus

    higyrus.login()
    status = higyrus.get_health()

See the README and the in-module docstrings for usage details.
"""

from .client import (
    get_health,
    get_movimientos,
    get_posiciones,
    login,
)
from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    HigyrusAPIError,
)
from .models import (
    Movimiento,
    Parking,
    Posicion,
    SafeModel,
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
    "get_movimientos",
    "get_posiciones",
    # Models
    "Movimiento",
    "Parking",
    "Posicion",
    "SafeModel",
]
