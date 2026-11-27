"""EnergySource -> OpenDSS ``Vsource`` (``EXPORT_MAPPING.md#vsource``).

A 3-phase source's impedance is written as the ohms group (R1 X1 R0 X0), the importer's copied form. A 1-phase
source's is written as the short-circuit group (MVAsc3 MVAsc1 x1r1 x0r0), by the exact inverse of the importer's
``thevenin_from_short_circuit``: on one phase the engine forces Z0 = Z1 when given ohms, so only this group keeps
its single impedance (2 Z1 + Z0) / 3 (engine-checked, atom ``single_phase``).
"""

from __future__ import annotations

import math

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe
from cimhub_core.getters.in_service import get_in_service
from cimhub_core.getters.source import get_source
from cimhub_core.getters.terminals import get_terminal_nodes
from cimhub_opendss.exporter.buses import bus_ref
from cimhub_core.export_slots import Slot
from cimhub_opendss.schema import opendss_schema as schema

CIM_CLASSES = (cim.EnergySource,)
NATIVE_CLASS = schema.Vsource

_GROUP = "not written: the ohms or the MVAsc group carries the same impedance"
_NOT_IN_CIM = "not in CIM (untranscribed on import)"

VSOURCE_SLOTS = {
    "name": Slot("written", "Names; the circuit's source is always `source`"),
    "bus1": Slot("written", "bus_ref(get_terminal_nodes, get_source.phases)"),
    "basekv": Slot("written", "get_source.nominal_u (kV)"),
    "pu": Slot("written", "get_source.magnitude_pu"),
    "angle": Slot("rule", "get_source.angle (deg); unset -> 0, the reference angle"),
    "phases": Slot("written", "the phase conductors: 3 or 1, any other count raises"),
    "R1": Slot("written", "3-phase: get_source.impedance.r (ohm); r, x, r0, x0 unset raises (DSS takes one group)"),
    "X1": Slot("written", "3-phase: get_source.impedance.x (ohm)"),
    "R0": Slot("written", "3-phase: get_source.impedance.r0 (ohm)"),
    "X0": Slot("written", "3-phase: get_source.impedance.x0 (ohm)"),
    "MVAsc3": Slot("written", "1-phase: kV^2 / abs(Z1) (short_circuit_from_thevenin)"),
    "MVAsc1": Slot("written", "1-phase: 3 kV^2 / abs(2 Z1 + Z0)"),
    "x1r1": Slot("written", "1-phase: x / r; r = 0 raises"),
    "x0r0": Slot("written", "1-phase: x0 / r0; r0 = 0 raises"),
    "enabled": Slot("written", "get_in_service(which='normal'); unset -> not written"),
    "Isc3": Slot("not mapped", _GROUP), "Isc1": Slot("not mapped", _GROUP),
    "Z1": Slot("not mapped", _GROUP), "Z0": Slot("not mapped", _GROUP),
    "Z2": Slot("not mapped", "r2/x2 set and different from r/x raises: the Z2 group is not mapped (nor imported)"),
    "puZ1": Slot("not mapped", _GROUP), "puZ0": Slot("not mapped", _GROUP), "puZ2": Slot("not mapped", _GROUP),
    "baseMVA": Slot("not mapped", _GROUP),
    "frequency": Slot("unset", "Options.defaultbasefreq is the deck's"),
    "basefreq": Slot("unset", "Options.defaultbasefreq is the deck's"),
    "ScanType": Slot("unset", _NOT_IN_CIM), "Sequence": Slot("unset", _NOT_IN_CIM),
    "spectrum": Slot("unset", _NOT_IN_CIM), "Yearly": Slot("unset", _NOT_IN_CIM),
    "Daily": Slot("unset", _NOT_IN_CIM), "Duty": Slot("unset", _NOT_IN_CIM),
    "Model": Slot("unset", _NOT_IN_CIM), "puZideal": Slot("unset", _NOT_IN_CIM),
    "bus2": Slot("not mapped", "an EnergySource has one terminal"),
    "like": Slot("not mapped", "the writer never writes like="),
}

SLOTS = {NATIVE_CLASS: VSOURCE_SLOTS}

_REL_TOL = 1e-6
_ABS_TOL = 1e-9  # ohm: rel_tol alone never matches a 0 (IEEE123's R1) against float noise


def export(context) -> list[schema.Vsource]:
    """One Vsource per EnergySource."""
    return [_vsource(source, context) for source in context.objects(*CIM_CLASSES)]


def _vsource(source: cim.EnergySource, context) -> schema.Vsource:
    """The circuit's source is named ``source`` (``context.circuit_source``)."""
    values = get_source(source, angle_unit="deg", voltage_unit="kV", impedance_unit="ohm")
    impedance = values.impedance
    unset = [name for name in ("r", "x", "r0", "x0") if getattr(impedance, name) is None]
    if unset:
        raise ValueError(f"{describe(source)}: {', '.join(unset)} unset; DSS takes R1 X1 R0 X0 as one group")
    for negative, positive in (("r2", "r"), ("x2", "x")):
        value = getattr(impedance, negative)
        if value is not None and not math.isclose(value, getattr(impedance, positive), rel_tol=_REL_TOL,
                                                  abs_tol=_ABS_TOL):
            raise ValueError(f"{describe(source)}: {negative} differs from {positive}; DSS's Z2 group is not mapped")
    if len(values.phases) not in (1, 3):
        raise ValueError(f"{describe(source)}: {len(values.phases)} phases; a Vsource is 1- or 3-phase")
    [node] = get_terminal_nodes(source)
    names = context.names
    name = names.fixed("source", source, "Vsource") if source is context.circuit_source else \
        names.name(source, "Vsource")
    if len(values.phases) == 3:
        group = {"R1": impedance.r, "X1": impedance.x, "R0": impedance.r0, "X0": impedance.x0}
    else:
        group = dict(zip(("MVAsc3", "MVAsc1", "x1r1", "x0r0"),
                         short_circuit_from_thevenin(source, values.nominal_u, *impedance[:4])))
    return NATIVE_CLASS(
        name=name,
        bus1=bus_ref(node, values.phases, names),
        phases=len(values.phases),
        basekv=values.nominal_u,
        pu=values.magnitude_pu,
        angle=0.0 if values.angle is None else values.angle,  # unset: the reference angle
        enabled=get_in_service(source, which="normal"),
        **group,
    )


def short_circuit_from_thevenin(source, kv: float, r1: float, x1: float, r0: float,
                                x0: float) -> tuple[float, float, float, float]:
    """``(MVAsc3, MVAsc1, x1r1, x0r0)``: the exact inverse of the importer's ``thevenin_from_short_circuit``,
    |Z1| = kV^2 / MVAsc3 and |2 Z1 + Z0| = 3 kV^2 / MVAsc1 (``VSource.pas`` ``RecalcElementData``). A zero r or r0
    has no X/R ratio and raises."""
    if r1 == 0 or r0 == 0:
        raise ValueError(f"{describe(source)}: r or r0 is 0, so a 1-phase source has no X/R ratio for DSS")
    return kv ** 2 / math.hypot(r1, x1), 3 * kv ** 2 / math.hypot(2 * r1 + r0, 2 * x1 + x0), x1 / r1, x0 / r0
