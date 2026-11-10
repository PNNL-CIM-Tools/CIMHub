"""Sanitize raw native strings for use as CIM names, lookup keys, and bus IDs.

Native source formats (OpenDSS, GridLAB-D, ...) name equipment, catalog entries, and
nodes with free-form utility strings. Those strings flow into CIM
``IdentifiedObject.name`` -- which is the object's identity, every ``find_by_name``
lookup key, and the exported bus/device identifier -- so a character that is legal
in the source but not downstream corrupts the whole chain:

- ``.`` is the OpenDSS node delimiter, so a bus named ``7674067.786_551037.964``
  parses as bus ``7674067`` node ``786_551037`` and raises an integer-conversion
  error.
- ``<>&"'`` break the CIM XML the model is serialized to (a raw ``<`` in a name
  such as ``Cable_1P_1C_2GA_AL-<NULL>`` makes the file unparseable).

So a raw string must become a clean token at the one point it enters the CIM
model. ``_`` is chosen over ``-`` only because it reads as a
single identifier; either is OpenDSS- and XML-safe.
"""

from __future__ import annotations

import os
import re

_UNSAFE_CIM_NAME_RE = re.compile(r'[\s.<>&"\'\[\]{}(),=~|]+')


def clean_cim_name(raw, default: str = "UNKNOWN") -> str:
    """Return *raw* sanitized for use as a CIM name, lookup key, and DSS bus.

    Must be applied identically wherever a native string becomes a CIM name or a
    lookup key, or a sanitized definition stops matching an unsanitized reference.
    Idempotent.
    """
    if raw is None:
        return default
    text = str(raw).strip()
    if not text:
        return default
    return _UNSAFE_CIM_NAME_RE.sub('_', text)


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
