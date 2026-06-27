"""hinge-client — typed async client for the Hinge API."""

from hinge.client import HingeClient
from hinge.core.catalog import Catalog, EnumCatalog
from hinge.core.logging import configure_logging, logger
from hinge.error import HingeAuthError, HingeEmail2FAError

__version__ = "0.1.0"

__all__ = [
    "HingeClient",
    "Catalog",
    "EnumCatalog",
    "HingeAuthError",
    "HingeEmail2FAError",
    "configure_logging",
    "logger",
    "__version__",
]
