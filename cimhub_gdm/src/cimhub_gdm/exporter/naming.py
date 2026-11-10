"""GDM names and uuids for exported objects (``EXPORT_MAPPING.md#names``, decision X2).

The name comes from the shared switch (``cimhub_core.names``: CIM ``name``, ``mRID`` or ``uri()``). A GDM name is
free text: nothing is sanitized, and two components may share one (``get_component(cls, name)`` then raises, and
``list_components_by_name`` finds both). The identity is the uuid: a component made from a CIM object takes its
``Identity.identifier``, ``uri()`` (``own``). A part with no CIM object of its own (inline equipment, a per-phase
child, a catalog's n-th variant, a placeholder) takes a uuid5 of its owner's, on its GDM class and suffix
(``part``): infrasys holds one component per uuid, so a part can't reuse its owner's.
"""

from __future__ import annotations

from uuid import UUID, uuid5

from cimhub_core.names import export_name, resolve_name_source


def identifier(obj) -> UUID:
    """The CIM object's Identity.identifier, as ``uri()`` gives it."""
    return UUID(obj.uri())


class Names:
    """The naming switch for one export."""

    def __init__(self, source: str | None = None):
        self.source = resolve_name_source(source)

    def own(self, obj, *, unnamed: str | None = None) -> dict:
        """``name`` and ``uuid`` of the GDM component made from ``obj``. ``unnamed`` is the name when ``obj`` has
        none under name source ``'name'`` (GDM's own default); otherwise an unset name raises."""
        return {"name": self._text(obj, unnamed), "uuid": identifier(obj)}

    def part(self, owner, gdm_class: type, *, suffix: str = "", unnamed: str | None = None) -> dict:
        """``name`` (the owner's + ``suffix``) and ``uuid`` of a ``gdm_class`` part made for ``owner`` with no CIM
        object of its own."""
        return {"name": self._text(owner, unnamed) + suffix,
                "uuid": uuid5(identifier(owner), f"{gdm_class.__name__}{suffix}")}

    def _text(self, obj, unnamed: str | None) -> str:
        if unnamed is not None and self.source == "name" and not (obj.name or "").strip():
            return unnamed
        return export_name(obj, self.source)
