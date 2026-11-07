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
