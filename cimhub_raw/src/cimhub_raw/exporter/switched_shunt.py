"""LinearShuntCompensators under one RegulatingControl -> Switched shunt (``EXPORT_MAPPING.md#switched-shunt``).

Each shunt is one block (Ni steps of Bi), as the importer writes a bank, and the shunts naming one control are one
record. MODSW, VSWHI/VSWLO and SWREG invert the importer's ``CONTROL_MODE``, ``volts_from_per_unit`` and
``reactive_band`` (R2, R2b).
"""

from __future__ import annotations

import logging
import re

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.export_slots import Slot
from cimhub_core.getters import describe, required_qty
from cimhub_core.getters.base_voltage import get_base_voltage
from cimhub_core.getters.control import get_regulating_control
from cimhub_core.getters.in_service import get_in_service
from cimhub_raw.exporter import branch
from cimhub_raw.exporter.bus import raw_bus
from cimhub_raw.exporter.identity import terminal_buses
from cimhub_raw.exporter.shunt_admittance import bus_base_admittance
from cimhub_raw.importer.cimtbl.derived import band_fractions, mva_from_per_unit, per_unit_from_kv, rating_from_ka
from cimhub_raw.importer.cimtbl.switched_shunt import BLOCKS, FACTS, PLANT, PREFIX

NATIVE_CLASS = schema.SwitchedShuntRecord
CIM_CLASSES = (cim.LinearShuntCompensator,)  # with fixed_shunt; line shunts with branch
LOCKED, DISCRETE, CONTINUOUS = 0, 1, 2
MACHINES = (cim.SynchronousMachine, cim.PowerElectronicsConnection)  # MODSW 3: a plant's
FACTS_DEVICES = (cim.StaticSynchronousCompensator,)  # MODSW 6

_BLOCK = Slot("written", "Ni / Bi: block i, maximumSections and get_shunt_admittance b per section (pu on the bus "
                         "base) x SBASE; in the swsh_<I>_b<i> order, else reactors first, each by mRID")
_BAND = ("from get_regulating_control target +- deadband / 2: voltage in kV over the regulated bus's BASKV; MODSW 3 "
         "and 6 as fractions of the machine's minQ..maxQ or the FACTS device's -SHMX..SHMX (band_fractions); blank "
         "for a disabled control with no target")
SLOTS = {NATIVE_CLASS: {
    "bus_number": Slot("written", "I: the blocks' busNumber (a v34 switched shunt's key)"),
    "modsw": Slot("written", "MODSW from the control: voltage 0 locked, 1 discrete, 2 continuous; reactivePower 3 on "
                             "a machine (or disabled elsewhere), 6 on a FACTS device"),
    "adjm": Slot("unset", "ADJM: the switching-order method has no CIM home"),
    "status": Slot("rule", "ST: 0 when the blocks' inService is false, else 1"),
    "vswhi": Slot("written", "VSWHI: the band's top " + _BAND),
    "vswlo": Slot("written", "VSWLO: the band's bottom " + _BAND),
    "swreg": Slot("written", "SWREG: the busNumber of the control's terminal, its own bus included (E2-2); blank "
                             "for MODSW 6"),
    "rmpct": Slot("unset", "RMPCT: a shunt's participation share has no CIM home (CIM 18 gap)"),
    "rmidnt": Slot("written", "RMIDNT: MODSW 6: the name of the FACTS device at the control's terminal"),
    "binit": Slot("written", "BINIT: the sum over the blocks of get_shunt_admittance b of the sections in service "
                             "(pu on the bus base) x SBASE"),
    **{f"{kind}{block}": _BLOCK for block in range(1, BLOCKS + 1) for kind in ("n", "b")},
    "nreg": Slot("unset", "NREG: a node of a node-breaker block, written by E5"),
}}

_log = logging.getLogger(__name__)


def export(context) -> list[schema.SwitchedShuntRecord]:
    """One Switched shunt per RegulatingControl of shunts, by bus."""
    line_shunts = branch.line_shunts(context)
    banks: dict[cim.RegulatingControl, list] = {}
    for shunt in context.objects(cim.LinearShuntCompensator):
        if shunt.RegulatingControl is not None and shunt not in line_shunts:
            banks.setdefault(shunt.RegulatingControl, []).append(shunt)
    records, holder = [], {}
    for control, blocks in banks.items():
        record = _record(control, blocks, context)
        if record.bus_number in holder:
            raise ValueError(f"bus {record.bus_number}: {describe(holder[record.bus_number])} and {describe(control)} "
                             "both control switched shunts; a v34 switched shunt's key is its bus")
        holder[record.bus_number] = control
        records.append(record)
    return sorted(records, key=lambda record: record.bus_number)


def _record(control, blocks: list, context) -> schema.SwitchedShuntRecord:
    buses = {terminal_buses(block, context) for block in blocks}
    if len(buses) != 1:
        raise ValueError(f"{describe(control)}: controls shunts on buses {sorted(buses)}; a switched shunt is on one")
    [(bus,)] = buses
    blocks = _ordered(blocks, bus)
    if len(blocks) > BLOCKS:
        raise ValueError(f"{describe(control)}: controls {len(blocks)} shunts; a switched shunt has {BLOCKS} blocks")
    base_power = context.network.base_power
    base_mva = base_power.to("MVA")
    steps, binit = {}, 0.0
    for index, block in enumerate(blocks, start=1):
        full = bus_base_admittance(block, "maximum", base_power)
        if full.g:
            raise ValueError(f"{describe(block)}: gPerSection is set; a switched shunt block has no G")
        if full.sections < 1:
            raise ValueError(f"{describe(block)}: maximumSections {full.sections}; a block has at least one step")
        steps[f"n{index}"] = full.sections
        steps[f"b{index}"] = mva_from_per_unit(full.b / full.sections, base_mva)
        binit += mva_from_per_unit(bus_base_admittance(block, "actual", base_power).b, base_mva)
    modsw = _control_mode(control, blocks)
    vswlo, vswhi = _band(control, modsw, context)
    device = control.Terminal.ConductingEquipment
    return schema.SwitchedShuntRecord(
        bus_number=bus, modsw=modsw, status=1 if _in_service(blocks) else 0, vswhi=vswhi, vswlo=vswlo,
        swreg=None if modsw == FACTS else context.bus_numbers[raw_bus(control.Terminal.TopologicalNode, context)],
        rmidnt=device.name if modsw == FACTS else None, binit=binit, **steps)


def _ordered(blocks: list, bus: int) -> list:
    """The blocks in the swsh_<I>_b<k> order; otherwise reactors first, then capacitors, each by mRID (logged)."""
    pattern = re.compile(rf"{re.escape(PREFIX)}{bus}_b(\d+)")
    if all(pattern.fullmatch(block.mRID) for block in blocks):
        return sorted(blocks, key=lambda block: int(pattern.fullmatch(block.mRID).group(1)))
    _log.info("bus %d: switched shunt blocks without swsh_%d_b<k> mRIDs are ordered reactors first", bus, bus)
    return sorted(blocks, key=lambda block: (required_qty(block, "bPerSection", "S") >= 0, block.mRID))


def _in_service(blocks: list) -> bool:
    states = {get_in_service(block, which="actual") is not False for block in blocks}
    if len(states) != 1:
        raise ValueError(f"{describe(blocks[0].RegulatingControl)}: its blocks are in and out of service; a switched "
                         "shunt has one status")
    return states.pop()


def _control_mode(control, blocks: list) -> int:
    """MODSW from the control's mode, its enabled flags and the equipment at its terminal."""
    block_flags = {block.controlEnabled for block in blocks}
    if len(block_flags) != 1:
        raise ValueError(f"{describe(control)}: its blocks' controlEnabled disagree")
    locked = control.enabled is False or block_flags == {False}
    device = control.Terminal.ConductingEquipment
    if control.mode is cim.RegulatingControlModeKind.voltage:
        if locked:
            return LOCKED
        return CONTINUOUS if control.discrete is False else DISCRETE
    if control.mode is cim.RegulatingControlModeKind.reactivePower:
        if isinstance(device, FACTS_DEVICES):
            return FACTS
        if isinstance(device, MACHINES) or locked:
            return PLANT
        raise ValueError(f"{describe(control)}: reactive power of {describe(device)}; MODSW 3 regulates a plant's "
                         "machine and 6 a FACTS device")
    raise ValueError(f"{describe(control)}: mode {control.mode}; a switched shunt regulates voltage or reactive power")


def _band(control, modsw: int, context) -> tuple[float | None, float | None]:
    """``(VSWLO, VSWHI)``; blank for a disabled control with no target (R2b-1's no-plant case)."""
    if control.targetValue is None and control.enabled is False:
        return None, None
    device = control.Terminal.ConductingEquipment
    if modsw in (LOCKED, DISCRETE, CONTINUOUS):
        settings = get_regulating_control(control, "kV")
        half = (settings.deadband or 0.0) / 2
        base_kv = get_base_voltage(control.Terminal.TopologicalNode, "kV", form="LL")
        return per_unit_from_kv(settings.target - half, base_kv), per_unit_from_kv(settings.target + half, base_kv)
    settings = get_regulating_control(control, "MVAr")
    if modsw == FACTS:
        shmx = rating_from_ka(required_qty(device, "ratedI", "kA"), get_base_voltage(device, "kV", form="LL"))
        q_min, q_max = -shmx, shmx
    else:
        if not isinstance(device, MACHINES):
            raise ValueError(f"{describe(control)}: a reactive-power target on {describe(device)}, not a machine")
        q_min, q_max = get_qty(device, "minQ", "MVAr"), get_qty(device, "maxQ", "MVAr")
        if q_min is None or q_max is None:
            raise ValueError(f"{describe(device)}: minQ and maxQ are needed for the band of {describe(control)}")
    return band_fractions(settings.target, settings.deadband or 0.0, q_min, q_max)
