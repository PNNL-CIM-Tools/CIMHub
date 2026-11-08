"""RAW ``FactsDeviceRecord`` -> ``facts_device.cimtbl``: phase-2 stub (.development/RAW_REWRITE_PLAN.md §4.2).

Proposed CIM targets, settled by the slice's spec section: ``StaticVarCompensator`` (shunt part) and
``SeriesCompensator`` (series part); UPFC/IPFC forms have no CIM 18 class (a gap to log).
"""

from __future__ import annotations

from cimtables.document import Document

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_raw.importer.cimtbl.phase2 import not_mapped_yet

NATIVE_CLASS = schema.FactsDeviceRecord


def map_facts_device(native) -> Document:
    """Empty when the case has no ``FactsDeviceRecord``; raises otherwise (phase 2)."""
    return not_mapped_yet(native, NATIVE_CLASS, "facts_device")
