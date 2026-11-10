"""RAW ``MultiTerminalDCRecord`` -> ``multi_terminal_dc.cimtbl``: phase-2 stub (.development/RAW_REWRITE_PLAN.md §4.2).

Proposed CIM targets, settled by the slice's spec section: ``DCConverterUnit``s, ``CsConverter``s,
``DCBusbar``/``DCNode``s and ``DCLineSegment``s of one DC grid.
"""

from __future__ import annotations

from cimtables.document import Document

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_raw.importer.cimtbl.phase2 import not_mapped_yet

NATIVE_CLASS = schema.MultiTerminalDCRecord


def map_multi_terminal_dc(native) -> Document:
    """Empty when the case has no ``MultiTerminalDCRecord``; raises otherwise (phase 2)."""
    return not_mapped_yet(native, NATIVE_CLASS, "multi_terminal_dc")
