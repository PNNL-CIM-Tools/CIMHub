"""The earth a line's impedance is computed over: its WireConfiguration's EarthResistivity, or the network's one for
a line with a direct WireSpacing (skill `export-getters`).

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
    return None if earth is None else _earth_data(earth)


def get_network_earth(network) -> EarthData:
    """The earth of a line with a direct WireSpacing: the network's one EarthResistivity, since cim18v17 associates
    one only with a WireConfiguration or a PerLengthImpedance, not with an ACLineSegment or a WireSpacing. None or
    several raise."""
    earths = list(network.graph.get(cim.EarthResistivity, {}).values())
    if len(earths) != 1:
        raise ValueError(f"a line with a direct WireSpacing takes the network's one EarthResistivity (cim18v17 "
                         f"associates none with an ACLineSegment or a WireSpacing); the network has {len(earths)}")
    return _earth_data(earths[0])


def _earth_data(earth: cim.EarthResistivity) -> EarthData:
    return EarthData(earth.earthModelType, get_qty(earth, "rho", "ohm"), get_qty(earth, "earthReturnGMR", "m"))
