"""RAW Switched shunt -> ``switched_shunt.cimtbl``: one ``LinearShuntCompensator`` per block (Ni steps of Bi), as the
banks are wired and switched, all under one ``RegulatingControl`` on a busbar terminal.

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#switched-shunt``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, Row, Table
from cimtopology.core.voltage import base_voltage_mrid

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, lookup, mrid, untranscribed_names
from cimhub_raw.importer.cimtbl.bus import busbar_mrid
from cimhub_raw.importer.cimtbl.derived import block_sections, per_unit_from_mva, volts_from_per_unit
from cimhub_raw.importer.cimtbl.records import fill_keyed_defaults, raw_defaults

NATIVE_CLASS = schema.SwitchedShuntRecord
PREFIX = "swsh_"  # requested from the cimtbl-translate table owners (plan C3)
CONTROL_PREFIX = "cc_"
BLOCKS = 8
BLOCK_SLOTS = tuple(f"{kind}{block}" for block in range(1, BLOCKS + 1) for kind in ("n", "b"))

#: STATUS -> inService
IN_SERVICE = {1: True, 0: False}
#: MODSW -> (enabled, discrete); a locked shunt keeps its control, disabled, so its blocks stay grouped
CONTROL_MODE = {0: (False, None), 1: (True, True), 2: (True, False)}
#: MODSW codes that raise, with why
UNMAPPED_MODES = {3: "plant reactive power: no case has one yet", 5: "another switched shunt's admittance: no case "
                  "has one yet", 4: "VSC converter reactive power: phase 2 (VSC DC)", 6: "FACTS shunt reactive power: "
                  "phase 2 (FACTS)"}

_BLOCK = "Ni / Bi: block i, a LinearShuntCompensator swsh_<I>_b<i> with maximumSections = Ni and bPerSection (pu " \
         "system) = Bi / SBASE (per_unit_from_mva), up to the first Ni or Bi of 0 (RAW's end of blocks); a block " \
         "after it raises; never defaulted"
FIELDS = {
    "bus_number": Field("structural", note="I: the key (a v34 switched shunt has no ID); every block's bus, nomU (kV) "
                                           "= its BASKV, BaseVoltage and EquipmentContainer (its substation)"),
    "modsw": Field("mapped", note="MODSW: 0 locked (control enabled = false), 1 voltage discrete, 2 voltage "
                                  "continuous; 3 and 5 raise (no case), 4 and 6 raise (phase 2); blank: 1 (defaulted)"),
    "adjm": Field("untranscribed", note="ADJM: the switching-order method has no CIM home; the block order is kept "
                                        "by _b<i>"),
    "status": Field("mapped", note="STATUS: inService = (STATUS == 1) on every block; blank: 1 (defaulted)"),
    "vswhi": Field("derived", note="VSWHI (pu): targetValue = (VSWHI + VSWLO) / 2 and targetDeadband = VSWHI - "
                                   "VSWLO, x the regulated bus's BASKV, in V (volts_from_per_unit); blank: 1.0 "
                                   "(defaulted)"),
    "vswlo": Field("derived", note="VSWLO (pu): as VSWHI"),
    "swreg": Field("structural", note="SWREG: the regulated bus; the control's Terminal = bb_<SWREG>_T1, or "
                                      "bb_<I>_T1 when 0 (RAW-11); blank: 0 (defaulted)"),
    "rmpct": Field("untranscribed", note="RMPCT: CIM has no participation share for a shunt (CIM 18 gap)"),
    "rmidnt": Field("untranscribed", note="RMIDNT: only MODSW 4 and 6 use it, which raise"),
    "binit": Field("derived", note="BINIT (Mvar at 1 pu): split into each block's sections in RAW's switching "
                                   "order (block_sections); beyond the blocks' total raises; blank: 0 (defaulted)"),
    **{slot: Field("structural", note=_BLOCK) for slot in BLOCK_SLOTS},
    "nreg": Field("structural", note="NREG: a node of bus SWREG; nonzero raises until R6 (node-breaker); blank: 0 "
                                     "(defaulted)"),
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


def map_switched_shunt(native, substations_by_bus: dict[int, str], base_kv_of: dict[int, float],
                       base_mva: float) -> Document:
    defaults = {slot: value for slot, value in raw_defaults(NATIVE_CLASS).items() if slot not in BLOCK_SLOTS}
    records = sorted(native.list_by_class(NATIVE_CLASS), key=lambda shunt: shunt.bus_number)
    control_rows, block_rows = [], []
    for record in records:
        shunt, defaulted = fill_keyed_defaults(FIELDS, record, defaults)
        record_id = f"switched shunt {shunt.ID}"
        if shunt.modsw in UNMAPPED_MODES:
            raise NotImplementedError(f"{record_id}: MODSW {shunt.modsw} ({UNMAPPED_MODES[shunt.modsw]})")
        enabled, discrete = lookup(CONTROL_MODE, shunt.modsw, slot="modsw", record_id=record_id)
        if shunt.nreg:
            raise NotImplementedError(f"{record_id}: NREG {shunt.nreg} names a node in a substation (R6)")
        bus = shunt.bus_number
        regulated = shunt.swreg or bus
        if regulated not in base_kv_of:
            raise ValueError(f"{record_id}: SWREG {regulated} is no bus")
        control = mrid(CONTROL_PREFIX, shunt.ID)
        regulated_kv = base_kv_of[regulated]
        control_rows.append(Row([
            control, shunt.ID, "voltage", cell(discrete), cell(enabled),
            cell(volts_from_per_unit((shunt.vswhi + shunt.vswlo) / 2, regulated_kv)),
            cell(volts_from_per_unit(shunt.vswhi - shunt.vswlo, regulated_kv)),
            f"{busbar_mrid(regulated)}_T1"], comment=defaulted))

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
                                                                "targetValue and targetDeadband in V"]))),
            Table("LinearShuntCompensator",
                  [Column("mRID"), Column("name"), Column("bus"), Column("bPerSection", "pu system"),
                   Column("nomU", "kV"), Column("maximumSections"), Column("sections"), Column("inService"),
                   Column("controlEnabled"), Column("RegulatingControl"), Column("BaseVoltage"),
                   Column("EquipmentContainer")],
                  block_rows, comment="one per block: Ni sections of Bi; sections split from BINIT (block_sections)"),
        ]
    return Document(name="switched_shunt", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(records)))
