"""RAW ``ImpedanceCorrectionRecord`` -> ``impedance_correction.cimtbl``: phase-2 stub (.development/RAW_REWRITE_PLAN.md §4.2).

Proposed CIM targets, settled by the slice's spec section: ``TapChangerTable`` + ``TapChangerTablePoint`` (r, x
correction per ratio or angle step), linked from the transformer's ``RatioTapChanger``/``PhaseTapChanger``.
"""

from __future__ import annotations

from cimtables.document import Document

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_raw.importer.cimtbl.phase2 import not_mapped_yet

NATIVE_CLASS = schema.ImpedanceCorrectionRecord


def map_impedance_correction(native) -> Document:
    """Empty when the case has no ``ImpedanceCorrectionRecord``; raises otherwise (phase 2)."""
    return not_mapped_yet(native, NATIVE_CLASS, "impedance_correction")
