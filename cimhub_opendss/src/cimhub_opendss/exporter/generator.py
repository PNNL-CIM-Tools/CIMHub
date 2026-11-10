"""SynchronousMachine -> OpenDSS ``Generator`` (``EXPORT_MAPPING.md#generator``).

kW and kvar are the machine's output (generation sign: -p, -q), written kW first so that kvar is the engine's at
that kW (S4b-8). A machine whose enabled control regulates the voltage of its own terminal is model 3 (a PV bus):
``Vpu`` = target / ratedU, ``Maxkvar``/``Minkvar`` its q limits. Any other is model 1: DSS has no disabled PV bus,
so a disabled control is not written. CIM has no machine reactance (U13), so ``Xd``,
``Xdp``, ``Xdpp`` and ``H`` come back at the engine's defaults. ``earthing`` false is delta (S4b-5).
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe
from cimhub_core.getters.control import get_equipment_control
from cimhub_core.getters.der import get_der_output, get_machine_rating
from cimhub_core.getters.in_service import get_in_service
from cimhub_opendss.exporter.controls import control_enabled
from cimhub_opendss.exporter.injection import device_connection, rated_kv
from cimhub_opendss.exporter.naming import Names
from cimhub_core.export_slots import Slot, with_default
from cimhub_opendss.schema import opendss_schema as schema

CIM_CLASSES = (cim.SynchronousMachine,)
NATIVE_CLASS = schema.Generator
NAMESPACE = "Generator"
#: earthing -> the PhaseShuntConnectionKind it stands for (SynchronousMachine has no phaseConnection, S4b-5)
CONNECTION = {True: cim.PhaseShuntConnectionKind.Y, False: cim.PhaseShuntConnectionKind.D}

_NOT_IN_CIM = "untranscribed or raising on import; not in CIM"
SLOTS = {NATIVE_CLASS: with_default(NATIVE_CLASS, {
    "name": Slot("written", "Names, the Generator namespace"),
    "phases": Slot("written", "the phase conductors; a delta across two is 1"),
    "bus1": Slot("written", "bus_ref of the phase conductors; a wye machine's neutral is node 0"),
    "kv": Slot("written", "ratedU (kV, LL), / sqrt 3 for 1-phase wye (S4b-4 inverted)"),
    "kW": Slot("written", "get_der_output total p (kW, generation sign)"),
    "kvar": Slot("written", "get_der_output total q (kVAr, generation sign), after kW"),
    "pf": Slot("not mapped", "kvar carries q"),
    "model": Slot("written", "3 (ConstantPV) when an enabled control regulates its own terminal's voltage, else 1 "
                             "(ConstantPQ); model 7 comes back as 1"),
    "conn": Slot("written", "earthing true -> wye, false -> delta; unset raises"),
    "Vpu": Slot("written", "model 3: the control's target / ratedU"),
    "maxkvar": Slot("written", "model 3: maxQ (kVAr); unset -> not written"),
    "minkvar": Slot("written", "model 3: minQ (kVAr); unset -> not written"),
    "kVA": Slot("written", "ratedS (kVA)"),
    "MVA": Slot("not mapped", "kVA carries ratedS"),
    **{slot: Slot("unset", "no machine reactance or inertia in cim18v17 (U13); the engine's default")
       for slot in ("Xd", "Xdp", "Xdpp", "H", "D", "XRdp")},
    "enabled": Slot("written", "get_in_service(which='normal'); unset -> not written"),
    "like": Slot("not mapped", "the writer never writes like="),
}, Slot("unset", _NOT_IN_CIM))}


def export(context) -> list[schema.Generator]:
    """One Generator per SynchronousMachine."""
    return [_generator(machine, context.names) for machine in context.objects(*CIM_CLASSES)]


def regulates_itself(machine: cim.SynchronousMachine) -> bool:
    """The machine has a control of its own terminal, which only the Generator writes (model 3)."""
    control = machine.RegulatingControl
    return control is not None and control.Terminal in machine.Terminals


def _generator(machine: cim.SynchronousMachine, names: Names) -> schema.Generator:
    if machine.earthing not in CONNECTION:
        raise ValueError(f"{describe(machine)}: earthing {machine.earthing}; it is the Generator's conn (S4b-5)")
    rating = get_machine_rating(machine, "kVA", "kVAr", sign="generation", voltage_unit="kV")
    output = get_der_output(machine, "kW", "kVAr", sign="generation")
    placed = device_connection(machine, output.phases, CONNECTION[machine.earthing], machine.earthing, names)
    slots = dict(name=names.name(machine, NAMESPACE), bus1=placed.bus1, phases=placed.phases, conn=placed.conn,
                 kv=rated_kv(rating.rated_u, output.phases, placed.conn), kW=output.total.p, kvar=output.total.q,
                 kVA=rating.rated_s, model="ConstantPQ", enabled=get_in_service(machine, which="normal"))
    if machine.RegulatingControl is not None:
        slots.update(_pv_bus(machine, rating))
    return NATIVE_CLASS(**slots)


def _pv_bus(machine: cim.SynchronousMachine, rating) -> dict:
    """Model 3's slots, or none when the control is disabled; a control the Generator cannot carry raises."""
    if not regulates_itself(machine):
        raise ValueError(f"{describe(machine)}: its control monitors another terminal; a Generator regulates its own")
    equipment = get_equipment_control(machine, unit="kV")
    settings = equipment.control
    if settings.mode is not cim.RegulatingControlModeKind.voltage:
        raise ValueError(f"{describe(machine)}: a {settings.mode.value} control; a Generator regulates voltage")
    unmapped = [name for name, value in (("targetDeadband", settings.deadband),
                                         ("minAllowedTargetValue", settings.min_allowed),
                                         ("maxAllowedTargetValue", settings.max_allowed),
                                         ("reverseTargetValue", settings.reverse_target)) if value not in (None, 0)]
    if unmapped:
        raise ValueError(f"{describe(machine)}: {unmapped} have no Generator slot")
    if control_enabled(machine.RegulatingControl, settings.enabled, equipment.control_enabled) is not True:
        return {}
    return dict(model="ConstantPV", Vpu=settings.target / rating.rated_u, maxkvar=rating.max_q, minkvar=rating.min_q)
