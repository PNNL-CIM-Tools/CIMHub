"""SeriesCompensator -> OpenDSS series ``Reactor`` (``EXPORT_MAPPING.md#reactor``).

``R`` and ``X`` are r and x per phase (ohm). A DSS Reactor has no mutual coupling, so r0 and x0, when set, must
equal them (the importer writes them so). Ratings are a line's (``line.ratings``).
"""

from __future__ import annotations

import math

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe
from cimhub_core.getters.in_service import get_in_service
from cimhub_core.getters.series_compensator import get_series_compensator
from cimhub_core.getters.terminals import get_conductor_phases
from cimhub_opendss.exporter.line import ratings, terminal_buses
from cimhub_opendss.exporter.naming import Names
from cimhub_core.export_slots import Slot, with_default
from cimhub_opendss.schema import opendss_schema as schema

CIM_CLASSES = (cim.SeriesCompensator,)
NATIVE_CLASS = schema.Reactor
NAMESPACE = "Reactor"

SLOTS = {NATIVE_CLASS: with_default(NATIVE_CLASS, {
    "name": Slot("written", "Names, the Reactor namespace"),
    "bus1": Slot("written", "terminal_buses (line.py): the first terminal on the phase conductors"),
    "bus2": Slot("written", "terminal_buses: the second terminal"),
    "phases": Slot("written", "the phase conductors"),
    "R": Slot("written", "get_series_compensator r (ohm)"),
    "X": Slot("written", "get_series_compensator x (ohm)"),
    "normamps": Slot("written", "get_current_limits normal (A); unset -> not written"),
    "emergamps": Slot("written", "get_current_limits emergency (A); unset -> not written"),
    "enabled": Slot("written", "get_in_service(which='normal'); unset -> not written"),
    **{slot: Slot("not mapped", "R and X carry the impedance; r0/x0 other than r/x raise")
       for slot in ("kvar", "Rmatrix", "Xmatrix", "Z1", "Z2", "Z0", "Z", "LmH", "Rp", "Parallel")},
    "like": Slot("not mapped", "the writer never writes like="),
}, Slot("unset", "untranscribed or raising on import; not in CIM"))}


def export(context) -> list[schema.Reactor]:
    """One Reactor per SeriesCompensator."""
    return [_reactor(compensator, context.names) for compensator in context.objects(*CIM_CLASSES)]


def _reactor(compensator: cim.SeriesCompensator, names: Names) -> schema.Reactor:
    data = get_series_compensator(compensator)
    coupled = [name for name, zero, positive in (("r0", data.r0, data.r), ("x0", data.x0, data.x))
               if zero is not None and not math.isclose(zero, positive)]
    if coupled:
        raise ValueError(f"{describe(compensator)}: {coupled} differ from r/x; a DSS Reactor has no mutual coupling")
    if data.varistor_present:
        raise ValueError(f"{describe(compensator)}: a varistor; a DSS Reactor has none")
    conductors = tuple(phase for phase in get_conductor_phases(compensator) if phase is not cim.SinglePhaseKind.N)
    bus1, bus2 = terminal_buses(compensator, conductors, names)
    return NATIVE_CLASS(name=names.name(compensator, NAMESPACE), bus1=bus1, bus2=bus2, phases=len(conductors),
                        R=data.r, X=data.x, **ratings(compensator), enabled=get_in_service(compensator, which="normal"))
