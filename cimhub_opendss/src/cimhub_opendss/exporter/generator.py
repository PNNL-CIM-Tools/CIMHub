"""SynchronousMachine, and PowerElectronicsWindUnit behind a PowerElectronicsConnection -> OpenDSS ``Generator``
(``EXPORT_MAPPING.md#generator``).

kW and kvar are the machine's output (generation sign: -p, -q), written kW first so that kvar is the engine's at
that kW (S4b-8). A machine whose enabled control regulates the voltage of its own terminal is model 3 (a PV bus):
``Vpu`` = target / ratedU, ``Maxkvar``/``Minkvar`` its q limits. Any other is model 1: DSS has no disabled PV bus,
so a disabled control is not written. CIM has no machine reactance (U13), so ``Xd``,
``Xdp``, ``Xdpp`` and ``H`` come back at the engine's defaults. ``earthing`` false is delta (S4b-5).

A wind turbine behind an inverter is a model 1 Generator at the unit's output (``inverter.inverter_pieces``): DSS has
no inverter wind class, and IEEE 9500 writes its turbines as Generators. The inverter's q limits and ``maxIFault``
have no home on a model 1 Generator, so they are not written. The deck reads back as a SynchronousMachine.

A machine's own ``EnergyConnectionSchedule`` with points (S9) is its ``yearly`` LoadShape: mult = p / the written kW
at each point, as the engine scales kW and kvar by mult. So the points' q must be the written kvar times mult (a
model 3 machine's q is its control's and is not checked); a kW of 0 raises. A wind unit's schedule is not mapped.
"""

from __future__ import annotations

import math

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe
from cimhub_core.getters.control import get_equipment_control
from cimhub_core.getters.der import get_der_output, get_machine_rating
from cimhub_core.getters.in_service import get_in_service
from cimhub_opendss.exporter import loadshape
from cimhub_opendss.exporter.controls import control_enabled
from cimhub_opendss.exporter.injection import device_connection, rated_kv
from cimhub_opendss.exporter.inverter import inverter_pieces
from cimhub_opendss.exporter.naming import Names
from cimhub_core.export_slots import Slot, with_default
from cimhub_opendss.schema import opendss_schema as schema

CIM_CLASSES = (cim.SynchronousMachine,)
#: the inverter unit a Generator stands for; its PowerElectronicsConnection is pvsystem's CIM class
WIND_UNIT = cim.PowerElectronicsWindUnit
NATIVE_CLASS = schema.Generator
NAMESPACE = "Generator"
#: earthing -> the PhaseShuntConnectionKind it stands for (SynchronousMachine has no phaseConnection, S4b-5)
CONNECTION = {True: cim.PhaseShuntConnectionKind.Y, False: cim.PhaseShuntConnectionKind.D}

_NOT_IN_CIM = "untranscribed or raising on import; not in CIM"
SLOTS = {NATIVE_CLASS: with_default(NATIVE_CLASS, {
    "name": Slot("written", "Names, the Generator namespace; a wind unit as inverter_pieces names it"),
    "phases": Slot("written", "the phase conductors; a delta across two is 1"),
    "bus1": Slot("written", "bus_ref of the phase conductors; a wye machine's neutral is node 0"),
    "kv": Slot("written", "ratedU (kV, LL), / sqrt 3 for 1-phase wye (S4b-4 inverted)"),
    "kW": Slot("written", "get_der_output total p (kW, generation sign); a wind unit: its share of the "
                          "connection's p (inverter_pieces)"),
    "kvar": Slot("written", "get_der_output total q (kVAr, generation sign), after kW; a wind unit: its share of q"),
    "pf": Slot("not mapped", "kvar carries q"),
    "model": Slot("written", "3 (ConstantPV) when an enabled control regulates its own terminal's voltage, else 1 "
                             "(ConstantPQ); model 7 comes back as 1"),
    "conn": Slot("written", "earthing true -> wye, false -> delta; unset raises"),
    "Vpu": Slot("written", "model 3: the control's target / ratedU"),
    "maxkvar": Slot("written", "model 3: maxQ (kVAr); unset -> not written"),
    "minkvar": Slot("written", "model 3: minQ (kVAr); unset -> not written"),
    "kVA": Slot("written", "ratedS (kVA); a wind unit: its share of the inverter's ratedS"),
    "MVA": Slot("not mapped", "kVA carries ratedS"),
    **{slot: Slot("unset", "no machine reactance or inertia in cim18v17 (U13); the engine's default")
       for slot in ("Xd", "Xdp", "Xdpp", "H", "D", "XRdp")},
    "enabled": Slot("written", "get_in_service(which='normal'); unset -> not written"),
    "yearly": Slot("written", "the machine's EnergyConnectionSchedule as a LoadShape, mult = p / kW (S9)"),
    "like": Slot("not mapped", "the writer never writes like="),
}, Slot("unset", _NOT_IN_CIM))}
#: how far a point's q may stray from kvar x mult (kVAr, relative to the larger)
Q_REL_TOL = 1e-6


def export(context) -> list:
    """One Generator per SynchronousMachine (its yearly LoadShape first when new), then one per
    PowerElectronicsWindUnit."""
    records = []
    for machine in context.objects(*CIM_CLASSES):
        generator = _generator(machine, context.names)
        found = loadshape.device_schedule(context, machine, 1)
        if found is not None:
            generator.yearly, shapes = loadshape.device_yearly(context, found, _multipliers(machine, generator, found))
            records += shapes
        records.append(generator)
    for connection in context.objects(cim.PowerElectronicsConnection):
        pieces = inverter_pieces(connection, WIND_UNIT, NAMESPACE, context.names)
        if pieces and loadshape.device_schedule(context, connection, len(pieces)) is not None:
            raise ValueError(f"{describe(connection)}: a schedule on a wind unit is not mapped")
        records += [_wind_generator(piece) for piece in pieces]
    return records


def _multipliers(machine, generator: schema.Generator, found) -> list[float]:
    """mult = p / kW at each point; q must follow kvar x mult, unless the machine regulates its own voltage."""
    if found.p is None:
        raise ValueError(f"{describe(found.schedule)}: no p; a Generator's shape scales its kW")
    if generator.kW == 0:
        raise ValueError(f"{describe(found.schedule)}: the machine's kW is 0; a Generator's shape scales its kW")
    mult = [p / generator.kW for p in found.p]
    if found.q is not None and generator.model != "ConstantPV":
        for number, (value, q) in enumerate(zip(mult, found.q), start=1):
            if not math.isclose(q, generator.kvar * value, rel_tol=Q_REL_TOL, abs_tol=Q_REL_TOL):
                raise ValueError(f"{describe(found.schedule)}: point {number} has q {q} kVAr, not kvar "
                                 f"{generator.kvar} x mult {value}; the engine scales kvar with kW")
    return mult


def regulates_itself(machine: cim.SynchronousMachine) -> bool:
    """The machine has a control of its own terminal, which only the Generator writes (model 3)."""
    control = machine.RegulatingControl
    return control is not None and control.Terminal in machine.Terminals


def _generator(machine: cim.SynchronousMachine, names: Names) -> schema.Generator:
    rating = get_machine_rating(machine, "kVA", "kVAr", sign="generation", voltage_unit="kV")
    if rating.earthing not in CONNECTION:
        raise ValueError(f"{describe(machine)}: earthing {rating.earthing}; it is the Generator's conn (S4b-5)")
    output = get_der_output(machine, "kW", "kVAr", sign="generation")
    placed = device_connection(machine, output.phases, CONNECTION[rating.earthing], rating.earthing, names)
    slots = dict(name=names.name(machine, NAMESPACE), bus1=placed.bus1, phases=placed.phases, conn=placed.conn,
                 kv=rated_kv(rating.rated_u, output.phases, placed.conn), kW=output.total.p, kvar=output.total.q,
                 kVA=rating.rated_s, model="ConstantPQ", enabled=get_in_service(machine, which="normal"))
    if machine.RegulatingControl is not None:
        slots.update(_pv_bus(machine, rating))
    return NATIVE_CLASS(**slots)


def _wind_generator(piece) -> schema.Generator:
    """Model 1 at the unit's output, on the inverter's bus, voltage and kVA share."""
    placed = {slot: piece.slots[slot] for slot in ("bus1", "phases", "conn", "kv", "kVA", "enabled")}
    return NATIVE_CLASS(name=piece.name, kW=piece.p, kvar=piece.q, model="ConstantPQ", **placed)


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
                                         ("reverseTargetValue", settings.reverse_target),
                                         ("reverseTargetDeadband", settings.reverse_deadband)) if value not in (None, 0)]
    if unmapped:
        raise ValueError(f"{describe(machine)}: {unmapped} have no Generator slot")
    if control_enabled(machine.RegulatingControl, settings.enabled, equipment.control_enabled) is not True:
        return {}
    return dict(model="ConstantPV", Vpu=settings.target / rating.rated_u, maxkvar=rating.max_q, minkvar=rating.min_q)
