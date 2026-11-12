"""The earth a line's impedance is computed over: its WireConfiguration's EarthResistivity (skill `export-getters`).

A geometry is only an impedance once an earth model and a resistivity are chosen (Carson, Deri). cim18v17 holds
them on ``EarthResistivity``, shared by the configurations computed over one earth. ``rho`` is typed Resistance in
the profile, so it is read in ohm and stands for ohm-m (a resistivity has no CIMUnit there).
"""

from __future__ import annotations

from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty


class EarthData(NamedTuple):
    model: cim.EarthModelKind | None
    rho: float | None  # ohm-m
    earth_return_gmr: float | None  # m


def get_earth_resistivity(configuration: cim.WireConfiguration) -> EarthData | None:
    """The configuration's earth: model, resistivity (ohm-m) and Carson earth-return GMR (m); None when it names
    no EarthResistivity."""
    earth = configuration.EarthResistivity
    if earth is None:
        return None
    return EarthData(earth.earthModelType, get_qty(earth, "rho", "ohm"), get_qty(earth, "earthReturnGMR", "m"))
