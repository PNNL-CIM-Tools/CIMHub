"""A shunt's admittance in pu on its bus's base, as RAW states every shunt (``EXPORT_MAPPING.md#which-shunt-is-which``).

RAW's GL, BL, Bi and a line shunt's G + jB are at 1 pu of the bus's BASKV. ``get_shunt_admittance``'s pu is on the
shunt's ``nomU``, so the two must agree: the importer writes ``nomU`` = BASKV, and a shunt rated off its bus voltage
raises until a consumer needs one.
"""

from __future__ import annotations

import math

from cimtables.graph_write import get_qty

from cimhub_core.getters import describe
from cimhub_core.getters.base_voltage import get_base_voltage
from cimhub_core.getters.shunt import ShuntAdmittance, get_shunt_admittance

REL_TOL = 1e-9


def bus_base_admittance(shunt, sections: str, base_power) -> ShuntAdmittance:
    """g and b of the shunt's ``sections`` in pu on its BaseVoltage and ``base_power``. A ``nomU`` other than the
    BaseVoltage raises."""
    rated_kv = get_qty(shunt, "nomU", "kV")
    base_kv = get_base_voltage(shunt, "kV", form="LL")
    if rated_kv is None or not math.isclose(rated_kv, base_kv, rel_tol=REL_TOL):
        raise ValueError(f"{describe(shunt)}: nomU {rated_kv} kV is not its BaseVoltage {base_kv} kV; RAW states a "
                         "shunt at 1 pu of its bus voltage")
    return get_shunt_admittance(shunt, "pu", sections=sections, base_power=base_power)
