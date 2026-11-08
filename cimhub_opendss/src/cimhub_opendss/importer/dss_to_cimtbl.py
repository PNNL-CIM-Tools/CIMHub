"""OpenDSS deck -> ``.cimtbl`` documents -> cim18v17: the orchestrator.

``MAPPING_ORDER`` is the master's ``Import`` order (DSS_REWRITE_PLAN.md section 2): catalogs before the instances
that use them. Each slice adds its mappers here. A DSS class no mapper reads is listed by count on the master's
comment (DSS-11), so nothing disappears silently.

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md#master``.
"""

from __future__ import annotations

import textwrap

from cimtables.document import Document, DocumentSet, Import

from cimhub_core.base import CimtblImporter
from cimhub_core.cimtbl import CIM_PROFILE
from cimhub_opendss.importer.cimtbl import linecode

#: ``(native class, mapper)`` in ``Import`` order.
MAPPING_ORDER = (
    (linecode.NATIVE_CLASS, linecode.map_linecode),
)

#: The master's ``Authority`` unless the caller names another (plan D7).
AUTHORITY = "https://github.com/PNNL-CIM-Tools/CIMHub"


def map_master(native, parts: list[Document], *, name: str, authority: str = AUTHORITY) -> Document:
    """The master document: settings, then one ``Import`` per non-empty part, in ``MAPPING_ORDER``."""
    mapped = {native_class for native_class, _ in MAPPING_ORDER}
    counts = sorted((cls.__name__, native.count(cls)) for cls in native.graph if cls not in mapped)
    comment = f"OpenDSS deck {name}\nMapping: cimhub_opendss/docs/CIMTBL_MAPPING.md#master"
    if counts:
        comment += "\n" + textwrap.fill("not mapped: " + ", ".join(f"{cls_name} {count}" for cls_name, count in counts),
                                       width=116, break_long_words=False)
    return Document(name=name, statements=[Import(part.name) for part in parts], profile=CIM_PROFILE,
                    authority=authority, model=name, comment=comment)


class DssImporter(CimtblImporter):
    """A DSS model to ``.cimtbl`` documents: the master plus one document per mapped DSS class.

    ``name`` is the master's ``Model`` and file stem (the deck's name, e.g. ``IEEE13_CDPSM``).
    """

    def __init__(self, name: str, *, authority: str = AUTHORITY):
        self.name = name
        self.authority = authority

    def to_cimtbl(self, model) -> DocumentSet:
        parts = [part for part in (mapper(model) for _, mapper in MAPPING_ORDER) if part.statements]
        return DocumentSet(master=map_master(model, parts, name=self.name, authority=self.authority), parts=parts)


def dss_to_cim(model, *, name: str, authority: str = AUTHORITY, network=None, artifact_dir=None):
    """A DSS model (``DssReader(path).read_all()``) as a cim18v17 network, built from its written artifacts."""
    return DssImporter(name, authority=authority).to_cim(model, network=network, artifact_dir=artifact_dir)
