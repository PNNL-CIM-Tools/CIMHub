"""RAW ``VscDcRecord`` -> ``vsc_dc.cimtbl``: phase-2 stub (.development/RAW_REWRITE_PLAN.md §4.2).

Proposed CIM targets, settled by the slice's spec section: ``DCLineSegment`` and two ``VsConverter``s, with their
AC-side voltage or reactive power control.
"""

from __future__ import annotations

from cimtables.document import Document

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_raw.importer.cimtbl.phase2 import not_mapped_yet

NATIVE_CLASS = schema.VscDcRecord


def map_vsc_dc(native) -> Document:
    """Empty when the case has no ``VscDcRecord``; raises otherwise (phase 2)."""
    return not_mapped_yet(native, NATIVE_CLASS, "vsc_dc")
