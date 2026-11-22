"""SeriesCompensator -> GLM ``series_reactor`` (``EXPORT_MAPPING.md#x28-series-reactors``).

``phase_X_impedance`` is r + jx on each of the compensator's phases (ohm). GridLAB-D's reactor has no coupling between
phases (``series_reactor.cpp:105``), so r0 and x0, when set, must equal r and x (as the DSS exporter's rule), and a
varistor raises. Ratings are a link's (``line.ratings``). The importer's S7 inverted.
"""

from __future__ import annotations

import math

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.export_slots import Slot, with_default
from cimhub_core.getters import describe
from cimhub_core.getters.series_compensator import get_series_compensator
from cimhub_core.getters.terminals import get_conductor_phases, get_terminal_nodes
from cimhub_gridlabd.exporter.buses import letters
from cimhub_gridlabd.exporter.line import ratings
from cimhub_gridlabd.exporter.units import glm_unit
from cimhub_gridlabd.schema import gridlabd as schema

CIM_CLASSES = (cim.SeriesCompensator,)
NATIVE_CLASS = schema.SeriesReactor

SLOTS = {NATIVE_CLASS: with_default(NATIVE_CLASS, {
    "name": Slot("written", "Names (X1)"),
    "phases": Slot("written", "the compensator's A, B, C"),
    "from_node": Slot("written", "terminal 1's bus"), "to": Slot("written", "terminal 2's bus"),
    **{f"phase_{letter}_impedance": Slot("written", "get_series_compensator r + jx (ohm), on each of its phases; "
                                                    "r0/x0 other than r/x raise") for letter in "ABC"},
    **{f"phase_{letter}_{part}": Slot("not mapped", "the impedance's parts; phase_X_impedance is written")
       for letter in "ABC" for part in ("resistance", "reactance")},
    **{f"continuous_rating_{letter}": Slot("written", "get_current_limits normal") for letter in "ABC"},
    **{f"emergency_rating_{letter}": Slot("written", "get_current_limits emergency") for letter in "ABC"},
}, Slot("unset", "not in CIM; GridLAB-D's default"))}


def export(context) -> list[schema.SeriesReactor]:
    return [_reactor(compensator, context) for compensator in context.objects(*CIM_CLASSES)]


def _reactor(compensator: cim.SeriesCompensator, context) -> schema.SeriesReactor:
    data = get_series_compensator(compensator, glm_unit(NATIVE_CLASS, "phase_A_impedance"))
    coupled = [name for name, zero, positive in (("r0", data.r0, data.r), ("x0", data.x0, data.x))
               if zero is not None and not math.isclose(zero, positive)]
    if coupled:
        raise ValueError(f"{describe(compensator)}: {coupled} differ from r/x; GridLAB-D's series_reactor has no "
                         "coupling between phases")
    if data.varistor_present:
        raise ValueError(f"{describe(compensator)}: a varistor; GridLAB-D's series_reactor has none")
    phase_letters = letters(get_conductor_phases(compensator))
    first, second = get_terminal_nodes(compensator)
    impedance = schema.Complex(real=data.r, imag=data.x)
    return NATIVE_CLASS(name=context.names.name(compensator), phases=phase_letters,
                        from_node=context.buses[first].name, to=context.buses[second].name,
                        **{f"phase_{letter}_impedance": impedance for letter in phase_letters},
                        **ratings(compensator, phase_letters, NATIVE_CLASS))
