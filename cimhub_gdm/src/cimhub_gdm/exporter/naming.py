"""GDM names for exported objects (``EXPORT_MAPPING.md#names``, decision X2).

The text comes from the shared switch (``cimhub_core.names``: CIM ``name``, ``mRID`` or ``uri()``). A GDM name is
free text, so nothing is sanitized. Two objects that land on one name in one GDM class raise, because
``DistributionSystem.get_component(cls, name)`` would find only one of them.
"""

from __future__ import annotations

from cimhub_core.names import export_name, resolve_name_source


class Names:
    """Every name written to one system, per GDM class."""

    def __init__(self, source: str | None = None):
        self.source = resolve_name_source(source)
        self._taken: dict[tuple[str, str], tuple[str, str]] = {}  # (GDM class, name) -> (mRID, suffix)

    def name(self, obj, gdm_class: type, *, suffix: str = "") -> str:
        """``obj``'s name in ``gdm_class``; ``suffix`` (``_A``) names one of several GDM objects made from it."""
        name = export_name(obj, self.source) + suffix
        key, owner = (gdm_class.__name__, name), (obj.mRID, suffix)
        taken = self._taken.setdefault(key, owner)
        if taken != owner:
            raise ValueError(f"{type(obj).__name__} {obj.mRID!r} and {taken[0]!r} are both named {name!r} in GDM "
                             f"{gdm_class.__name__} (name source {self.source!r})")
        return name
