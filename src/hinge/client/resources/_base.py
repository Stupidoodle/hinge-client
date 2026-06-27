"""Base class shared by all Hinge API resource namespaces."""

from hinge.client._core import HingeClient


class BaseResource:
    """Common base for resource namespaces composed onto :class:`HingeClient`.

    Each resource holds a reference to its owning client and reaches the
    shared transport, headers, and session state through ``self._client``.
    """

    def __init__(self, client: HingeClient) -> None:
        """Bind the resource to its owning client.

        Args:
            client: The :class:`HingeClient` that owns this resource.

        """
        self._client = client
