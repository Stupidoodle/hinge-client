"""hinge-client — typed async client for the Hinge API."""

from importlib.metadata import PackageNotFoundError, version

from hinge.client import HingeClient
from hinge.core.catalog import Catalog, EnumCatalog
from hinge.core.logging import configure_logging, logger
from hinge.error import HingeAuthError, HingeEmail2FAError

try:
    __version__ = version("hinge-client")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0+unknown"

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
