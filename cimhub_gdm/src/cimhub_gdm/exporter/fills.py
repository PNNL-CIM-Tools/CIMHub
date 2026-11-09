"""Required GDM fields CIM cannot hold, and the neutral value written for each (EXPORT_PLAN.md decision X4, §3.1).

A fill is written only where GDM requires the field and CIM has no home for it. Never in place of a getter's
``None`` for a value CIM can hold: that raises, or follows the slot's written rule. Every use is counted through
``ExportContext.fill``, and ``warn`` logs one WARNING per export naming each filled field and its count.
"""

from __future__ import annotations

import logging
from collections import Counter

import numpy as np
from gdm.quantities import CapacitancePULength, ReactancePULength, ResistancePULength
from gdm.systems.distribution.common import TimeCurrentCurve
from gdm.systems.distribution.controllers import DistributionRecloserController
from infrasys.quantities import Distance, Time

log = logging.getLogger(__name__)

#: A switch, fuse or recloser has no length in CIM. GDM enforces length > 0; with zero matrices it scales nothing.
SWITCH_LENGTH = Distance(1, "meter")

#: A switch controller's operating delay and lock have no CIM home: no delay, not locked.
SWITCH_CONTROLLER_DELAY = Time(0, "second")
SWITCH_CONTROLLER_LOCKED = False

#: A fuse's clearing delay beyond its curve has no CIM home (no FuseCharacteristicCurve in cim18v17).
FUSE_DELAY = Time(0, "second")

#: ZIP fractions (p: Z, I, P; q: Z, I, P) of a load CIM gives as voltage exponents. GDM requires the fractions, and
#: an exponent load ignores them (ditto writes Model=4); constant power is what the importer's own atoms write.
ZIP_UNDER_EXPONENTS = (0.0, 0.0, 1.0, 0.0, 0.0, 1.0)

#: Fields whose fill is placeholder protection, named in the WARNING (decision X5).
PROTECTION_FIELDS = ("MatrixImpedanceFuseEquipment.tcc_curve", "MatrixImpedanceRecloser.controller")


def switch_matrices(size: int) -> dict:
    """``r_matrix`` and ``x_matrix`` of 1 ohm/km on the diagonal, ``c_matrix`` zero, ``size`` × ``size``.

    A CIM switch is ideal, but a zero matrix is singular: OpenDSS (through ditto) cannot invert it. This is OpenDSS's
    own switch impedance (``Switch=yes``: r1 = x1 = 1 per unit length, no mutual), 1 milliohm across the 1 m fill.
    """
    diagonal = np.eye(size)
    return {"r_matrix": ResistancePULength(diagonal, "ohm / kilometer"),
            "x_matrix": ReactancePULength(diagonal, "ohm / kilometer"),
            "c_matrix": CapacitancePULength(np.zeros((size, size)), "farad / kilometer")}


def fuse_curve(name: str) -> TimeCurrentCurve:
    """GDM's own example curve, named ``name``: the numbers are GDM's, not scaled to the fuse's rating (X5)."""
    return TimeCurrentCurve.example().model_copy(update={"name": name})


def recloser_controller(name: str) -> DistributionRecloserController:
    """GDM's own example controller and its equipment, both named ``name`` (not the example's vendor model) (X5)."""
    example = DistributionRecloserController.example()
    equipment = example.equipment.model_copy(update={"name": name})
    return example.model_copy(update={"name": name, "equipment": equipment})


def warn(filled: Counter) -> None:
    """One WARNING naming every filled field and how often it was filled."""
    if not filled:
        return
    fields = [f"{field} x{count}" for field, count in sorted(filled.items())]
    protection = [field for field in PROTECTION_FIELDS if field in filled]
    note = (f"; {', '.join(protection)} are placeholder protection (GDM's example values, not scaled to the "
            "device's rating)") if protection else ""
    log.warning("GDM export filled %d required fields CIM cannot hold with neutral values (EXPORT_PLAN.md §3.1)%s:"
                "\n  %s", sum(filled.values()), note, "\n  ".join(fields))
