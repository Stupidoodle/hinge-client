"""In-memory catalog of Hinge enum labels and the prompt library.

Hinge exposes only enum *IDs* over the network (``GET /config/v3`` returns the
valid id sets); the human labels are not served by any endpoint, so they ship as
bundled static data in ``hinge/data/catalog.json`` and are loaded into memory
here. The prompt library, by contrast, is fetched live (``POST /prompts``) and
held by :class:`~hinge.prompts_manager.HingePromptsManager`.

Nothing here touches a database. Special ordinals: ``-1`` Open to All,
``0`` Prefer Not to Say, ``99999999`` Unknown.
"""

import json
from importlib import resources
from pathlib import Path
from typing import Any

from hinge.prompts_manager import HingePromptsManager

__all__ = ["EnumCatalog", "Catalog"]


class EnumCatalog:
    """Bidirectional ordinal <-> label lookup for Hinge's display enums.

    Backed by the bundled ``catalog.json`` data; no network or database access.
    """

    def __init__(
        self,
        labels: dict[str, dict[int, str]],
        special: dict[int, str] | None = None,
    ) -> None:
        """Build from ``{attribute: {ordinal: label}}`` maps and sentinel values."""
        self._labels = labels
        self._special = special or {}
        self._reverse: dict[str, dict[str, int]] = {
            attr: {label.casefold(): ordinal for ordinal, label in mapping.items()}
            for attr, mapping in labels.items()
        }
        # Valid-id sets default to every known ordinal; refreshable from config/v3.
        self._valid: dict[str, set[int]] = {
            attr: set(mapping) for attr, mapping in labels.items()
        }

    @classmethod
    def load(cls, source: str | Path | dict[str, Any] | None = None) -> EnumCatalog:
        """Load the catalog.

        Args:
            source: ``None`` loads the bundled ``hinge/data/catalog.json``; a path
                loads that JSON file; a dict is used directly (for tests).
        """
        if source is None:
            raw = (resources.files("hinge") / "data" / "catalog.json").read_text("utf-8")
            data = json.loads(raw)
        elif isinstance(source, dict):
            data = source
        else:
            data = json.loads(Path(source).read_text("utf-8"))

        labels = {
            attr: {int(k): v for k, v in mapping.items()}
            for attr, mapping in data["labels"].items()
        }
        special = {int(k): v for k, v in data.get("special", {}).items()}
        return cls(labels, special)

    def attributes(self) -> list[str]:
        """All known attribute names (e.g. ``"religions"``, ``"languages"``)."""
        return list(self._labels)

    def labels(self, attr: str) -> dict[int, str]:
        """Full ordinal->label map for one attribute (copy)."""
        return dict(self._labels.get(attr, {}))

    def label(self, attr: str, ordinal: int) -> str | None:
        """Resolve an ordinal to its label, or a sentinel label, else ``None``."""
        mapping = self._labels.get(attr)
        if mapping is not None and ordinal in mapping:
            return mapping[ordinal]
        return self._special.get(ordinal)

    def ordinal(self, attr: str, label: str) -> int | None:
        """Resolve a label back to its ordinal (case-insensitive), else ``None``."""
        return self._reverse.get(attr, {}).get(label.casefold())

    def is_valid(self, attr: str, ordinal: int) -> bool:
        """Whether ``ordinal`` is a currently-valid value for ``attr``."""
        return ordinal in self._valid.get(attr, set()) or ordinal in self._special

    def set_valid_ids(self, attr: str, ordinals: list[int] | set[int]) -> None:
        """Replace the valid-id set for one attribute (e.g. from ``/config/v3``)."""
        self._valid[attr] = set(ordinals)


class Catalog:
    """Bundles the static :class:`EnumCatalog` with the live prompt library."""

    def __init__(
        self,
        enums: EnumCatalog,
        prompts: HingePromptsManager | None = None,
    ) -> None:
        """Compose an enum catalog with an optional prompts manager."""
        self.enums = enums
        self.prompts = prompts

    @classmethod
    def load(cls, prompts: HingePromptsManager | None = None) -> Catalog:
        """Load the bundled enum catalog; attach a prompts manager if available."""
        return cls(EnumCatalog.load(), prompts)
