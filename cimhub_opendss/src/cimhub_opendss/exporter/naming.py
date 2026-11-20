"""DSS names for exported objects (``EXPORT_MAPPING.md#names``, decision E1).

The text comes from the shared switch (``cimhub_core.names``: CIM ``name``, ``mRID`` or ``uri()``), sanitized for
DSS. Two objects that land on one name in one DSS namespace raise, because DSS would silently merge them.
"""

from __future__ import annotations

from cimhub_core.names import export_name, resolve_name_source
from cimhub_opendss.dss_writer import dss_safe_name

BUS_NAMESPACE = "bus"


class Names:
    """Every name written to one deck, per DSS namespace (a DSS class, or ``bus``), compared lowercased as DSS
    compares them."""

    def __init__(self, source: str | None = None):
        self.source = resolve_name_source(source)
        self._taken: dict[tuple[str, str], tuple[str, str]] = {}  # (namespace, lowered) -> (mRID, suffix)

    def name(self, obj, namespace: str, *, suffix: str = "") -> str:
        """``obj``'s DSS name in ``namespace``; ``suffix`` (``_a``) names one of several DSS objects made from it."""
        return self._claim(dss_safe_name(export_name(obj, self.source) + suffix), obj, namespace, suffix)

    def fixed(self, name: str, obj, namespace: str) -> str:
        """A name DSS dictates (the circuit's ``Vsource.source``), claimed for ``obj``."""
        return self._claim(name, obj, namespace, "")

    def bus(self, node, *, suffix: str = "") -> str:
        """A ConnectivityNode's bus name, or with ``suffix`` a bus the deck adds for another object (a multi-circuit
        group's ends, ``<group>_1``). ``.`` is DSS's node delimiter, so it is sanitized too."""
        name = dss_safe_name(export_name(node, self.source) + suffix).replace(".", "_")
        return self._claim(name, node, BUS_NAMESPACE, suffix)

    def _claim(self, name: str, obj, namespace: str, suffix: str) -> str:
        key, owner = (namespace, name.lower()), (obj.mRID, suffix)
        taken = self._taken.setdefault(key, owner)
        if taken != owner:
            raise ValueError(f"{type(obj).__name__} {obj.mRID!r} and {taken[0]!r} are both named {name!r} in DSS "
                             f"{namespace} (name source {self.source!r})")
        return name
