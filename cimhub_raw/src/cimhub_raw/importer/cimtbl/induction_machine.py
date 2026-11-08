"""RAW ``InductionMachineRecord`` -> ``induction_machine.cimtbl``: phase-2 stub (.development/RAW_REWRITE_PLAN.md §4.2).

Proposed CIM targets, settled by the slice's spec section: ``AsynchronousMachine`` (nameplate, the equivalent
circuit in pu on its base).
"""

from __future__ import annotations

from cimtables.document import Document

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_raw.importer.cimtbl.phase2 import not_mapped_yet

NATIVE_CLASS = schema.InductionMachineRecord


def map_induction_machine(native) -> Document:
    """Empty when the case has no ``InductionMachineRecord``; raises otherwise (phase 2)."""
    return not_mapped_yet(native, NATIVE_CLASS, "induction_machine")
