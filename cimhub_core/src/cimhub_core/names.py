"""Export naming: which CIM attribute an exporter writes a native name from (``name``, ``mRID`` or ``uri()``).

Import never sanitizes: a native identifier is quoted into the ``.cimtbl`` as written (invariant I8).
"""

from __future__ import annotations

import os


# ---------------------------------------------------------------------------
# Export naming: one switch shared by every exporter (DSS_REWRITE_PLAN.md E1)
# ---------------------------------------------------------------------------

#: What an exported native name is written from: the CIM ``name``, the ``mRID``, or ``uri()`` (the stable UUID; a
#: fixed length, which GridLAB-D's name-reference limit needs).
NAME_SOURCES = ("name", "mrid", "uri")
NAME_SOURCE_ENV = "CIMHUB_NAME_SOURCE"
DEFAULT_NAME_SOURCE = "mrid"


def resolve_name_source(source: str | None = None) -> str:
    """The exporter's ``name_source`` argument, else ``$CIMHUB_NAME_SOURCE``, else ``'mrid'`` (unique by
    construction: the importers compile it from the native name). Any other value raises."""
    if source is None:
        source = os.environ.get(NAME_SOURCE_ENV) or DEFAULT_NAME_SOURCE
    if source not in NAME_SOURCES:
        raise ValueError(f"name source must be one of {list(NAME_SOURCES)}, not {source!r}")
    return source


def export_name(obj, source: str) -> str:
    """The text ``obj`` is exported under: its ``name``, ``mRID`` or ``uri()``. Unset or blank raises. The spoke
    sanitizes the result with its own format's rule."""
    if source == "name":
        text = obj.name
    elif source == "mrid":
        text = obj.mRID
    elif source == "uri":
        text = obj.uri()
    else:
        raise ValueError(f"name source must be one of {list(NAME_SOURCES)}, not {source!r}")
    if text is None or not str(text).strip():
        raise ValueError(f"{type(obj).__name__} {obj.mRID!r}: has no {source} to export it under")
    return str(text)
