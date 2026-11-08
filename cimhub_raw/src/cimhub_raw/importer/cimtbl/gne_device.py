"""RAW ``GneDeviceRecord`` -> ``gne_device.cimtbl``: phase-2 stub (.development/RAW_REWRITE_PLAN.md §4.2).

Proposed CIM targets, settled by the slice's spec section: none known: a GNE device is a user-written model. Likely
untranscribed as a whole, with its name listed.
"""

from __future__ import annotations

from cimtables.document import Document

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_raw.importer.cimtbl.phase2 import not_mapped_yet

NATIVE_CLASS = schema.GneDeviceRecord


def map_gne_device(native) -> Document:
    """Empty when the case has no ``GneDeviceRecord``; raises otherwise (phase 2)."""
    return not_mapped_yet(native, NATIVE_CLASS, "gne_device")
