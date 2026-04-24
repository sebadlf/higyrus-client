"""Python client for the Higyrus API.

Re-exports the REST client surface as a flat namespace, so callers can do::

    import higyrus_client as higyrus

    higyrus.login()
    status = higyrus.get_health()

See the README and the in-module docstrings for usage details.
"""

from .client import (
    get_health,
    login,
)
from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    HigyrusAPIError,
)
from .models import (
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
    # Models
    "Parking",
    "Posicion",
    "SafeModel",
]
