"""RAW Switched shunt -> ``switched_shunt.cimtbl``: one ``LinearShuntCompensator`` per block (Ni steps of Bi), as the
banks are wired and switched, all under one ``RegulatingControl``: of voltage on a busbar terminal (MODSW 0..2), or of
the reactive power of a plant's machine or a FACTS shunt on its own terminal (MODSW 3, 6; R2b).

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#switched-shunt``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, Row, Table
from cimtopology.core.voltage import base_voltage_mrid

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, fill_defaults, lookup, mrid, untranscribed_names
from cimhub_raw.importer.cimtbl import facts_device, generator
from cimhub_raw.importer.cimtbl.derived import block_sections, per_unit_from_mva, reactive_band, volts_from_per_unit
from cimhub_raw.importer.cimtbl.records import fill_keyed_defaults, listed_off_default, raw_defaults
from cimhub_raw.importer.node_breaker import NodeBreaker

NATIVE_CLASS = schema.SwitchedShuntRecord
PREFIX = "swsh_"  # requested from the cimtbl-translate table owners (plan C3)
CONTROL_PREFIX = "cc_"
BLOCKS = 8
BLOCK_SLOTS = tuple(f"{kind}{block}" for block in range(1, BLOCKS + 1) for kind in ("n", "b"))

#: STATUS -> inService
IN_SERVICE = {1: True, 0: False}
#: MODSW -> (mode, enabled, discrete); a locked shunt keeps its control, disabled, so its blocks stay grouped
CONTROL_MODE = {0: ("voltage", False, None), 1: ("voltage", True, True), 2: ("voltage", True, False),
                3: ("reactivePower", True, True), 6: ("reactivePower", True, True)}
#: MODSW codes that raise, with why
UNMAPPED_MODES = {4: "VSC converter reactive power: no case has one yet", 5: "another switched shunt's admittance: "
                  "no case has one yet"}
#: MODSW 3: the plant's machine; MODSW 6: the FACTS device named by RMIDNT
PLANT, FACTS = 3, 6

_BLOCK = "Ni / Bi: block i, a LinearShuntCompensator swsh_<I>_b<i> with maximumSections = Ni and bPerSection (pu " \
         "system) = Bi / SBASE (per_unit_from_mva), up to the first Ni or Bi of 0 (RAW's end of blocks); a block " \
         "after it raises; never defaulted"
FIELDS = {
    "bus_number": Field("structural", note="I: the key (a v34 switched shunt has no ID); every block's bus, nomU (kV) "
                                           "= its BASKV, BaseVoltage and EquipmentContainer (its substation)"),
    "modsw": Field("mapped", note="MODSW: 0 locked (control enabled = false), 1 voltage discrete, 2 voltage "
                                  "continuous, 3 plant and 6 FACTS shunt reactivePower discrete (R2b); 4 and 5 raise "
                                  "(no case); blank: 1 (defaulted)"),
    "adjm": Field("untranscribed", note="ADJM: the switching-order method has no CIM home; the block order is kept "
                                        "by _b<i>"),
    "status": Field("mapped", note="STATUS: inService = (STATUS == 1) on every block; blank: 1 (defaulted)"),
    "vswhi": Field("derived", note="VSWHI (pu): MODSW 0..2: targetValue = (VSWHI + VSWLO) / 2 and targetDeadband "
                                   "= VSWHI - VSWLO, x the regulated bus's BASKV, in V (volts_from_per_unit); MODSW "
                                   "3, 6: pu of the device's Q range, in VAr (reactive_band; R2b-1, R2b-2), listed "
                                   "when there is no machine at SWREG; blank: 1.0 (defaulted)"),
    "vswlo": Field("derived", note="VSWLO (pu): as VSWHI"),
    "swreg": Field("structural", note="SWREG: the regulated bus; the control's Terminal = bb_<SWREG>_T1, or "
                                      "bb_<I>_T1 when 0 (RAW-11); MODSW 3: the plant's bus, Terminal = its machine's "
                                      "<machine>_T1 (several machines raise; none: the control disabled on "
                                      "bb_<SWREG>_T1, R2b-1); MODSW 6: unused; blank: 0 (defaulted)"),
    "rmpct": Field("untranscribed", note="RMPCT: CIM has no participation share for a shunt (CIM 18 gap)"),
    "rmidnt": Field("structural", note="RMIDNT: MODSW 6: the FACTS device, Terminal fd_<RMIDNT>_T1 (R2b-2); only "
                                       "MODSW 4 (raises) uses it otherwise"),
    "binit": Field("derived", note="BINIT (Mvar at 1 pu): split into each block's sections in RAW's switching "
                                   "order (block_sections); beyond the blocks' total raises; blank: 0 (defaulted)"),
    **{slot: Field("structural", note=_BLOCK) for slot in BLOCK_SLOTS},
    "nreg": Field("structural", note="NREG: a node of bus SWREG; nonzero: the control's Terminal is that node's "
                                     "busbar bb_s<IS>_n<NREG>_T1 (R6, RAW-11); blank: 0 (defaulted)"),
}

_PROVENANCE = """PSS/E RAW Switched shunt -> LinearShuntCompensator per block, RegulatingControl.
Source table: Switched shunt (records: {count})
Mapping: cimhub_raw/docs/CIMTBL_MAPPING.md#switched-shunt"""


def shunt_blocks(record) -> list[tuple[int, float]]:
    """``(Ni, Bi)`` up to the first Ni or Bi of 0 or blank, RAW's end of blocks. A block after it raises."""
    pairs = [(getattr(record, f"n{block}"), getattr(record, f"b{block}")) for block in range(1, BLOCKS + 1)]
    blocks = []
    for steps, step in pairs:
        if not steps or not step:
            break
        blocks.append((steps, step))
    if any(steps or step for steps, step in pairs[len(blocks) + 1:]):
        raise ValueError(f"switched shunt {record.ID}: a block after the first zero Ni or Bi (block "
                         f"{len(blocks) + 1}): {pairs}")
    if not blocks:
        raise ValueError(f"switched shunt {record.ID}: no blocks (N1, B1 = {pairs[0]})")
    return blocks


def regulated_nodes(native) -> list[tuple[int, int, str]]:
    """``(regulated bus, NREG, record id)`` of every switched shunt whose control regulates a node (R6)."""
    return [(shunt.swreg or shunt.bus_number, shunt.nreg, f"switched shunt {shunt.ID}")
            for shunt in native.list_by_class(NATIVE_CLASS) if shunt.nreg]


def _reactive_control(shunt, plants: dict[int, list], facts: dict[str, object], node_breaker: NodeBreaker,
                      record_id: str) -> tuple[bool, float | None, float | None, str, str | None]:
    """``(enabled, targetValue, targetDeadband, Terminal, listed)`` of a reactive-power control (MODSW 3, 6; R2b)."""
    if shunt.modsw == FACTS:
        device = facts.get(shunt.rmidnt)
        if device is None:
            raise ValueError(f"{record_id}: RMIDNT {shunt.rmidnt!r} names no FACTS device")
        if device.jbus:
            raise NotImplementedError(f"{record_id}: FACTS device {device.name} has a series element; its shunt range "
                                      "is reduced by the bridge transfer (no case)")
        target, deadband = reactive_band(shunt.vswlo, shunt.vswhi, -device.shmx, device.shmx)
        return True, target, deadband, f"{mrid(facts_device.PREFIX, device.name)}_T1", None
    regulated = shunt.swreg or shunt.bus_number
    machines = plants.get(regulated, [])
    if len(machines) > 1:
        raise NotImplementedError(f"{record_id}: the plant at bus {regulated} has {len(machines)} machines; one "
                                  "terminal measures one machine (no case)")
    if not machines:
        listed = listed_off_default(shunt, ("vswhi", "vswlo"), raw_defaults(NATIVE_CLASS))
        return False, None, None, node_breaker.regulated_terminal(regulated, shunt.nreg, record_id), listed
    machine = machines[0]
    target, deadband = reactive_band(shunt.vswlo, shunt.vswhi, machine.min_q_output, machine.max_q_output)
    return True, target, deadband, f"{generator.machine_mrid(machine)}_T1", None


def _plants(native) -> dict[int, list]:
    """Every generator by its bus, its blanks filled: the plants MODSW 3 controls."""
    defaults = raw_defaults(generator.NATIVE_CLASS)
    plants: dict[int, list] = {}
    for record in native.list_by_class(generator.NATIVE_CLASS):
        machine, _ = fill_keyed_defaults(generator.FIELDS, record, defaults)
        plants.setdefault(machine.bus_number, []).append(machine)
    return plants


def _facts_devices(native) -> dict[str, object]:
    """Every FACTS device by its NAME, its blanks filled: the shunts MODSW 6 controls."""
    defaults = raw_defaults(facts_device.NATIVE_CLASS)
    return {record.name: fill_defaults(facts_device.FIELDS, record, defaults)[0]
            for record in native.list_by_class(facts_device.NATIVE_CLASS)}


def map_switched_shunt(native, substations_by_bus: dict[int, str], base_kv_of: dict[int, float],
                       node_breaker: NodeBreaker, base_mva: float) -> Document:
    defaults = {slot: value for slot, value in raw_defaults(NATIVE_CLASS).items() if slot not in BLOCK_SLOTS}
    records = sorted(native.list_by_class(NATIVE_CLASS), key=lambda shunt: shunt.bus_number)
    plants, facts = _plants(native), _facts_devices(native)
    control_rows, block_rows = [], []
    for record in records:
        shunt, defaulted = fill_keyed_defaults(FIELDS, record, defaults)
        record_id = f"switched shunt {shunt.ID}"
        if shunt.modsw in UNMAPPED_MODES:
            raise NotImplementedError(f"{record_id}: MODSW {shunt.modsw} ({UNMAPPED_MODES[shunt.modsw]})")
        mode, enabled, discrete = lookup(CONTROL_MODE, shunt.modsw, slot="modsw", record_id=record_id)
        bus = shunt.bus_number
        regulated = shunt.swreg or bus
        if regulated not in base_kv_of:
            raise ValueError(f"{record_id}: SWREG {regulated} is no bus")
        control = mrid(CONTROL_PREFIX, shunt.ID)
        if mode == "voltage":
            regulated_kv = base_kv_of[regulated]
            target = volts_from_per_unit((shunt.vswhi + shunt.vswlo) / 2, regulated_kv)
            deadband = volts_from_per_unit(shunt.vswhi - shunt.vswlo, regulated_kv)
            terminal, listed = node_breaker.regulated_terminal(regulated, shunt.nreg, record_id), None
        else:
            enabled, target, deadband, terminal, listed = _reactive_control(shunt, plants, facts, node_breaker,
                                                                            record_id)
        control_rows.append(Row([control, shunt.ID, mode, cell(discrete), cell(enabled), cell(target), cell(deadband),
                                 terminal], comment="; ".join(filter(None, [defaulted, listed])) or None))

        blocks = shunt_blocks(shunt)
        in_service = cell(lookup(IN_SERVICE, shunt.status, slot="status", record_id=record_id))
        for block, ((steps, step), sections) in enumerate(zip(blocks, block_sections(shunt.binit, blocks, record_id)),
                                                          start=1):
            block_rows.append(Row([
                mrid(PREFIX, f"{shunt.ID}_b{block}"), f"{shunt.ID}_b{block}", str(bus),
                cell(per_unit_from_mva(step, base_mva)), cell(base_kv_of[bus]), str(steps), cell(sections), in_service,
                cell(enabled), control, base_voltage_mrid(base_kv_of[bus]), substations_by_bus[bus]]))

    statements = []
    if records:
        statements = [
            Table("RegulatingControl",
                  [Column("mRID"), Column("name"), Column("mode"), Column("discrete"), Column("enabled"),
                   Column("targetValue"), Column("targetDeadband"), Column("Terminal")],
                  control_rows, comment="\n".join(filter(None, [untranscribed_names(FIELDS),
                                                                "targetValue and targetDeadband in V (voltage) or VAr "
                                                                "(reactivePower)"]))),
            Table("LinearShuntCompensator",
                  [Column("mRID"), Column("name"), Column("bus"), Column("bPerSection", "pu system"),
                   Column("nomU", "kV"), Column("maximumSections"), Column("sections"), Column("inService"),
                   Column("controlEnabled"), Column("RegulatingControl"), Column("BaseVoltage"),
                   Column("EquipmentContainer")],
                  block_rows, comment="one per block: Ni sections of Bi; sections split from BINIT (block_sections)"),
        ]
    return Document(name="switched_shunt", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(records)))
