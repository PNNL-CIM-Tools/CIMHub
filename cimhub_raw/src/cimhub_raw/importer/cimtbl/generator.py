"""RAW Generator -> ``generator.cimtbl``: one ``RegulatingControl`` per plant (bus I), and per record a
``SynchronousMachine`` + ``GeneratingUnit`` (WMOD 0) or a ``PowerElectronicsConnection`` + ``PowerElectronicsUnit``
(WMOD 1, 2, 3), each unit in its bus's ``ControlArea``. A WMOD 3 plant holds a power factor, not a voltage (R3c).
A machine with an implicit step-up transformer (RT + jXT != 0) sits
on an internal ``TopologicalNode`` behind a 2-winding ``PowerTransformer`` (R3b; the core shape
``behind_transformer.cimtbl``, plan C8).

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#generator-r3`` and
``#generator-the-implicit-step-up-transformer-r3b``, ``#generator-renewables-with-a-power-factor-r3c-wmod-2-and-3``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, Row, Table
from cimtopology.core.voltage import base_voltage_mrid

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, lookup, mrid, untranscribed_names
from cimhub_raw.importer.cimtbl.area_interchange import area_mrid, control_area_numbers
from cimhub_raw.importer.cimtbl.derived import generation_p_q, kv_from_per_unit, ohms_from_per_unit, volts_from_per_unit
from cimhub_raw.importer.cimtbl.records import fill_keyed_defaults, listed_off_default, raw_defaults
from cimhub_raw.importer.node_breaker import NodeBreaker

NATIVE_CLASS = schema.GeneratorRecord
#: prefixes requested from the cimtbl-translate table owners (plan C3)
CONTROL_PREFIX = "gc_"
MACHINE_PREFIXES = ("sm_", "gu_", "cagu_")
CONVERTER_PREFIXES = ("pec_", "pecu_", "capu_")

#: STAT -> inService
IN_SERVICE = {1: True, 0: False}
#: WMOD -> is the record a converter-interfaced plant (PowerElectronicsConnection)? (RAW-24)
CONVERTER = {0: False, 1: True, 2: True, 3: True}
#: WMOD codes that raise, with why
UNMAPPED_WMOD = {4: "infeed, fixed Q: no case has one yet"}
#: renewable, Q limits from PG and WPF: WPF listed on the row (R3c-1)
POWER_FACTOR_LIMITS = 2
#: renewable, Q fixed from PG and WPF: a powerFactor plant control (R3c-2)
FIXED_POWER_FACTOR = 3
#: a power-factor plant's fields that a fixed power factor does not use, listed off their defaults (R3c-2)
UNUSED_BY_POWER_FACTOR = ("regulated_voltage_setpoint", "regulated_bus_number", "nreg")
#: bus IDE that regulate voltage, and the swing
REGULATING_BUS_TYPES = (2, 3)
SWING = 3

_OWNER = "ownership is an asset concept (CIM 18 gap)"
_PLANT = "a plant quantity, shared by every machine at bus I (they must agree, else raise)"
FIELDS = {
    "bus_number": Field("structural", note="I: the machine's bus, BaseVoltage, EquipmentContainer (its substation) "
                                           "and ControlArea (the bus's AREA, through ControlAreaGeneratingUnit or "
                                           "ControlAreaPowerElectronicsUnit); the plant key gc_<I>; IDE 2 or 3 "
                                           "enables the plant control, IDE 3 sets referencePriority = 1 on its "
                                           "SynchronousMachines"),
    "gen_id": Field("structural", note="ID: with I the key, mRIDs sm_/gu_/cagu_ or pec_/pecu_/capu_<I>_<ID>, name "
                                       "I_ID; blank: 1 (defaulted)"),
    "p_output": Field("derived", note="PG (MW): p = -PG, load sign convention (generation_p_q, RAW-14); blank: 0 "
                                      "(defaulted)"),
    "q_output": Field("derived", note="QG (Mvar): q = -QG, load sign convention (generation_p_q, RAW-14); blank: 0 "
                                      "(defaulted)"),
    "max_q_output": Field("copied", (("SynchronousMachine", "maxQ", "MVAr"),
                                     ("PowerElectronicsConnection", "maxQ", "MVAr")),
                          note="QT, generator convention as CIM's limit; blank: 9999 (defaulted)"),
    "min_q_output": Field("copied", (("SynchronousMachine", "minQ", "MVAr"),
                                     ("PowerElectronicsConnection", "minQ", "MVAr")),
                          note="QB; blank: -9999 (defaulted)"),
    "regulated_voltage_setpoint": Field("derived", note=f"VS (pu): targetValue = VS x the regulated bus's BASKV, in V "
                                                        f"(volts_from_per_unit); {_PLANT}; blank: 1.0 (defaulted)"),
    "regulated_bus_number": Field("structural", note=f"IREG: the plant control's Terminal bb_<IREG>_T1, or "
                                                     f"bb_<I>_T1 when 0 (RAW-11), or the NREG node's busbar; a "
                                                     f"remote IREG from a swing bus "
                                                     f"raises; {_PLANT}; blank: 0 (defaulted)"),
    "rated_mva": Field("copied", (("SynchronousMachine", "ratedS", "MVA"),
                                  ("PowerElectronicsConnection", "ratedS", "MVA")),
                       note="MBASE, with ratedU = bus I's BASKV: RAW gives no machine kV, and MBASE and ZR are on "
                            "BASKV (E3-1, as R3b-2); blank: SBASE (defaulted)"),
    "zr": Field("derived", note="ZR (pu on MBASE): SynchronousMachine r (ohm) = ZR x BASKV^2 / MBASE "
                                "(ohms_from_per_unit); listed on a PowerElectronicsConnection's row when not 0 "
                                "(R3c-3); blank: 0 (defaulted)"),
    "zx": Field("untranscribed", note="ZX: cim18v17 has no positive-sequence machine reactance (TODO: a profile "
                                      "extension, RAW-23)"),
    "rt": Field("derived", note="RT (pu on MBASE): RT + jXT != 0 is an implicit step-up transformer <machine>_xf, "
                                "the machine on its internal node <machine>_int (R3b-1); end 1 r (ohm) = RT x "
                                "BASKV^2 / MBASE (ohms_from_per_unit); blank: 0 (defaulted)"),
    "xt": Field("derived", note="XT (pu on MBASE): as RT, end 1 x (ohm)"),
    "gtap": Field("derived", note="GTAP: with a step-up, a fixed RatioTapChanger <machine>_xf_tap1 on end 1, neutralU "
                                  "= GTAP x BASKV (R3b-1, R4b-4), none at 1; without one, PSS/E ignores it and it is "
                                  "listed on the machine row when not 1 (R3b-4); blank: 1.0 (defaulted)"),
    "status": Field("mapped", note="STAT: inService = (STAT == 1); blank: 1 (defaulted)"),
    "rmpct": Field("copied", (("SynchronousMachine", "qPercent", None),),
                   note=f"RMPCT, on every SynchronousMachine of the plant; a PowerElectronicsConnection has no "
                        f"qPercent (CIM 18 gap): listed on its row when not 100 (R3c-3); {_PLANT}; blank: 100 "
                        f"(defaulted)"),
    "max_p_output": Field("copied", (("GeneratingUnit", "maxOperatingP", "MW"), ("PowerElectronicsUnit", "maxP", "MW")),
                          note="PT, by WMOD; blank: 9999 (defaulted)"),
    "min_p_output": Field("copied", (("GeneratingUnit", "minOperatingP", "MW"), ("PowerElectronicsUnit", "minP", "MW")),
                          note="PB, by WMOD; blank: -9999 (defaulted)"),
    **{f"o{n}": Field("untranscribed", note=_OWNER) for n in range(1, 5)},
    **{f"f{n}": Field("untranscribed", note=_OWNER) for n in range(1, 5)},
    "wmod": Field("mapped", note="WMOD: the class (RAW-24), 0 conventional a SynchronousMachine + GeneratingUnit, 1 "
                                 "(QT/QB limits), 2 (limits from WPF) and 3 (fixed power factor) renewable a "
                                 "PowerElectronicsConnection + PowerElectronicsUnit; 3 makes the plant control "
                                 "powerFactor (R3c-2); 4 raises until a case has one; blank: 0 (defaulted)"),
    "wpf": Field("mapped", note="WPF: WMOD 2, always listed on the row (no CIM limit follows P, R3c-1); WMOD 3, the "
                                "plant control's targetValue, signed (positive: q has p's sign, R3c-2); unused "
                                "otherwise; blank: 1.0 (defaulted)"),
    "nreg": Field("structural", note=f"NREG: a node of bus IREG; nonzero: the plant control's Terminal is that "
                                     f"node's busbar bb_s<IS>_n<NREG>_T1 (R6, RAW-11); {_PLANT}; blank: 0 "
                                     f"(defaulted)"),
}

_PROVENANCE = """PSS/E RAW Generator -> RegulatingControl per plant (bus I); SynchronousMachine + GeneratingUnit (WMOD 0)
or PowerElectronicsConnection + PowerElectronicsUnit (WMOD 1, 2, 3), each with its ControlArea membership; an implicit
step-up transformer (PowerTransformer, internal TopologicalNode, fixed RatioTapChanger) per machine with RT + jXT.
Source table: Generator (records: {count})
Mapping: cimhub_raw/docs/CIMTBL_MAPPING.md#generator-r3"""


def machine_mrid(generator) -> str:
    """The machine's mRID: ``sm_<I>_<ID>`` (WMOD 0) or ``pec_<I>_<ID>`` (WMOD 1, 2, 3); a switched shunt's plant control
    measures its terminal (R2b-1)."""
    converter = lookup(CONVERTER, generator.wmod, slot="wmod", record_id=generator.ID)
    return mrid((CONVERTER_PREFIXES if converter else MACHINE_PREFIXES)[0], generator.ID)


def has_step_up(generator) -> bool:
    """RT + jXT != 0: the record carries an implicit step-up transformer (R3b)."""
    return bool(generator.rt or generator.xt)


class StepUpRows:
    """The implicit step-up transformers (R3b-1): an internal node, a 2-winding transformer and, off GTAP 1, a fixed
    tap, per machine. RAW gives no terminal kV, so both ends keep bus I's base (R3b-2)."""

    def __init__(self):
        self.nodes, self.transformers, self.ends, self.taps = [], [], [], []

    def add(self, machine: str, generator, kv: float, container: str) -> str:
        """The rows of ``machine``'s step-up; returns its internal node, the machine's bus."""
        name, bus = generator.ID, generator.bus_number
        transformer, internal, base = f"{machine}_xf", f"{machine}_int", base_voltage_mrid(kv)
        mva = generator.rated_mva
        self.nodes.append(Row([internal, f"{name} terminal", base, container]))
        self.transformers.append(Row([transformer, f"{name} step-up", "true", container]))
        self.ends += [
            Row([f"{transformer}_1", f"{name}_1", str(bus), "1", cell(kv), cell(mva),
                 cell(ohms_from_per_unit(generator.rt, kv, mva)), cell(ohms_from_per_unit(generator.xt, kv, mva)),
                 base, transformer]),
            Row([f"{transformer}_2", f"{name}_2", internal, "2", cell(kv), cell(mva), None, None, base, transformer]),
        ]
        if generator.gtap != 1.0:
            self.taps.append(Row([f"{transformer}_tap1", f"{name}_1", "1", "1", "1",
                                  cell(kv_from_per_unit(generator.gtap, kv)), "1", "false", "false",
                                  f"{transformer}_1"]))
        return internal

    def tables(self) -> list[Table]:
        if not self.transformers:
            return []
        tables = [
            Table("TopologicalNode", [Column("mRID"), Column("name"), Column("BaseVoltage"),
                                      Column("ConnectivityNodeContainer")], self.nodes,
                  comment="each step-up machine's internal node (behind_transformer, plan C8): no RAW bus; bus I's "
                          "base, since RAW gives no terminal kV (R3b-2)"),
            Table("PowerTransformer", [Column("mRID"), Column("name"), Column("inService"),
                                       Column("EquipmentContainer")], self.transformers,
                  comment="each implicit step-up transformer (RT + jXT != 0, R3b-1); always in service"),
            Table("PowerTransformerEnd", [Column("mRID"), Column("name"), Column("bus"), Column("endNumber"),
                                          Column("ratedU", "kV"), Column("ratedS", "MVA"), Column("r", "ohm"),
                                          Column("x", "ohm"), Column("BaseVoltage"), Column("PowerTransformer")],
                  self.ends, comment="end 1 at bus I, end 2 at the internal node, both ratedU = BASKV and ratedS = "
                                     "MBASE; r, x = RT, XT x BASKV^2 / MBASE on end 1"),
        ]
        if self.taps:
            tables.append(Table(
                "RatioTapChanger", [Column("mRID"), Column("name"), Column("lowStep"), Column("highStep"),
                                    Column("neutralStep"), Column("neutralU", "kV"), Column("step"),
                                    Column("ltcFlag"), Column("controlEnabled"), Column("TransformerEnd")],
                self.taps, comment="GTAP != 1: a fixed tap at the high-voltage bus, neutralU = GTAP x BASKV (R4b-4)"))
        return tables


def _check_record(generator, record_id: str) -> None:
    """The forms R3 does not map raise."""
    if generator.wmod in UNMAPPED_WMOD:
        raise NotImplementedError(f"{record_id}: WMOD {generator.wmod} ({UNMAPPED_WMOD[generator.wmod]})")


def _listed(generator, converter: bool, defaults: dict) -> str | None:
    """What a machine's or connection's row lists: GTAP without a step-up (R3b-4); on a connection, ZR and RMPCT
    off their defaults (R3c-3), and WMOD 2's WPF always, so the exporter tells WMOD 2 from 1 (R3c-1)."""
    slots = ("zr", "rmpct") if converter else ()
    if not has_step_up(generator):
        slots += ("gtap",)
    listed = listed_off_default(generator, slots, defaults)
    if generator.wmod != POWER_FACTOR_LIMITS:
        return listed
    wpf = f"wpf={cell(generator.wpf)}"
    return f"{listed}, {wpf}" if listed else f"untranscribed: {wpf}"


def _is_power_factor_plant(members, plant_id: str) -> bool:
    """A WMOD 3 plant holds its one connection's power factor (R3c-2); WMOD 3 beside another record raises."""
    fixed = [generator.ID for generator, _ in members if generator.wmod == FIXED_POWER_FACTOR]
    if fixed and len(members) > 1:
        raise NotImplementedError(f"{plant_id}: WMOD 3 {fixed} shares the plant with other records; one control "
                                  "holds either a voltage or one connection's power factor (no case has one yet)")
    return bool(fixed)


def _plant_key(generator) -> tuple[int, int, float, float]:
    """(regulated bus, NREG, VS, RMPCT): what every record of one plant must share."""
    return generator.regulated_bus_number or generator.bus_number, generator.nreg, \
        generator.regulated_voltage_setpoint, generator.rmpct


def regulated_nodes(native) -> list[tuple[int, int, str]]:
    """``(regulated bus, NREG, record id)`` of every generator whose control regulates a node (R6)."""
    return [(generator.regulated_bus_number or generator.bus_number, generator.nreg, f"generator {generator.ID}")
            for generator in native.list_by_class(NATIVE_CLASS) if generator.nreg]


def _plants(records, defaults: dict) -> dict[int, list[tuple[object, str | None]]]:
    """bus I -> its records, filled and checked, with their ``defaulted`` comments; a plant that disagrees raises."""
    plants: dict[int, list[tuple[object, str | None]]] = {}
    for record in records:
        generator, defaulted = fill_keyed_defaults(FIELDS, record, defaults)
        _check_record(generator, f"generator {generator.ID}")
        members = plants.setdefault(generator.bus_number, [])
        if members and _plant_key(members[0][0]) != _plant_key(generator):
            raise ValueError(f"plant {generator.bus_number}: generators {members[0][0].ID} and {generator.ID} "
                             f"disagree on (IREG, NREG, VS, RMPCT): {_plant_key(members[0][0])} vs "
                             f"{_plant_key(generator)}; PSS/E treats them as plant quantities")
        members.append((generator, defaulted))
    return plants


def map_generator(native, substations_by_bus: dict[int, str], base_kv_of: dict[int, float],
                  bus_area: dict[int, int], bus_type: dict[int, int], node_breaker: NodeBreaker,
                  base_mva: float) -> Document:
    records = sorted(native.list_by_class(NATIVE_CLASS), key=lambda generator: (generator.bus_number,
                                                                               str(generator.gen_id)))
    if not records:
        return Document(name="generator", statements=[], profile=CIM_PROFILE)
    control_areas = control_area_numbers(native)
    defaults = {**raw_defaults(NATIVE_CLASS), "rated_mva": base_mva}
    plants = _plants(records, defaults)
    step_ups = StepUpRows()

    control_rows, terminal_updates, unit_rows, machine_area_rows, machine_rows = [], [], [], [], []
    converter_rows, converter_unit_rows, converter_area_rows = [], [], []
    for bus, members in plants.items():
        plant_id = f"plant {bus}"
        regulated, node, setpoint, _ = _plant_key(members[0][0])
        if regulated not in base_kv_of:
            raise ValueError(f"{plant_id}: IREG {regulated} is no bus")
        swing = bus_type[bus] == SWING
        if swing and regulated != bus:
            raise ValueError(f"{plant_id}: a swing bus regulates remote bus {regulated} (PSS/E would regulate bus "
                             f"{bus} instead)")
        if swing and all(lookup(CONVERTER, generator.wmod, slot="wmod", record_id=generator.ID)
                         for generator, _ in members):
            raise ValueError(f"{plant_id}: a swing bus with no SynchronousMachine (only converter records), so no "
                             "referencePriority")
        if bus_area[bus] not in control_areas:
            raise ValueError(f"{plant_id}: AREA {bus_area[bus]} has no area-interchange record (no ControlArea "
                             f"{area_mrid(bus_area[bus])})")
        control = mrid(CONTROL_PREFIX, bus)
        enabled = cell(bus_type[bus] in REGULATING_BUS_TYPES)
        if _is_power_factor_plant(members, plant_id):
            generator = members[0][0]
            control_rows.append(Row([control, str(bus), "powerFactor", "false", enabled, cell(generator.wpf), None],
                                    comment=listed_off_default(generator, UNUSED_BY_POWER_FACTOR, defaults)))
            terminal_updates.append(Row([control, f"{machine_mrid(generator)}_T1"]))
        else:
            control_rows.append(Row([control, str(bus), "voltage", "false", enabled,
                                     cell(volts_from_per_unit(setpoint, base_kv_of[regulated])),
                                     node_breaker.regulated_terminal(regulated, node, plant_id)]))

        kv, container, area = base_kv_of[bus], substations_by_bus[bus], area_mrid(bus_area[bus])
        for generator, defaulted in members:
            record_id = generator.ID
            converter = lookup(CONVERTER, generator.wmod, slot="wmod", record_id=record_id)
            comment = "; ".join(note for note in (defaulted, _listed(generator, converter, defaults)) if note) or None
            p, q = generation_p_q(generator)
            in_service = cell(lookup(IN_SERVICE, generator.status, slot="status", record_id=record_id))
            limits = [cell(generator.max_q_output), cell(generator.min_q_output), cell(generator.rated_mva), cell(kv)]
            if converter:
                connection, unit, membership = (mrid(prefix, record_id) for prefix in CONVERTER_PREFIXES)
                node = step_ups.add(connection, generator, kv, container) if has_step_up(generator) else str(bus)
                converter_rows.append(Row([connection, record_id, node, cell(p), cell(q), *limits, in_service,
                                           enabled, control, base_voltage_mrid(kv), container], comment=comment))
                converter_unit_rows.append(Row([unit, record_id, cell(generator.max_p_output),
                                                cell(generator.min_p_output), connection, container]))
                converter_area_rows.append(Row([membership, record_id, area, unit]))
            else:
                machine, unit, membership = (mrid(prefix, record_id) for prefix in MACHINE_PREFIXES)
                node = step_ups.add(machine, generator, kv, container) if has_step_up(generator) else str(bus)
                unit_rows.append(Row([unit, record_id, cell(generator.max_p_output), cell(generator.min_p_output),
                                      container]))
                machine_area_rows.append(Row([membership, record_id, area, unit]))
                machine_rows.append(Row([
                    machine, record_id, node, cell(p), cell(q), *limits,
                    cell(ohms_from_per_unit(generator.zr, kv, generator.rated_mva)), cell(generator.rmpct),
                    cell(1 if swing else None), in_service, enabled, control, unit, base_voltage_mrid(kv),
                    container], comment=comment))

    untranscribed = untranscribed_names(FIELDS)
    statements = [Table("RegulatingControl",
                        [Column(name) for name in ("mRID", "name", "mode", "discrete", "enabled", "targetValue",
                                                   "Terminal")],
                        control_rows, comment="one per plant (bus I); targetValue in V (voltage) or a power "
                                              "factor (powerFactor, a WMOD 3 plant)")]
    statements += step_ups.tables()  # the internal nodes before the machines that sit on them
    if machine_rows:
        statements += [
            Table("GeneratingUnit", [Column("mRID"), Column("name"), Column("maxOperatingP", "MW"),
                                     Column("minOperatingP", "MW"), Column("EquipmentContainer")], unit_rows),
            Table("ControlAreaGeneratingUnit", [Column("mRID"), Column("name"), Column("ControlArea"),
                                                Column("GeneratingUnit")], machine_area_rows),
            Table("SynchronousMachine",
                  [Column("mRID"), Column("name"), Column("bus"), Column("p", "MW"), Column("q", "MVAr"),
                   Column("maxQ", "MVAr"), Column("minQ", "MVAr"), Column("ratedS", "MVA"), Column("ratedU", "kV"),
                   Column("r", "ohm"),
                   Column("qPercent"), Column("referencePriority"), Column("inService"), Column("controlEnabled"),
                   Column("RegulatingControl"), Column("GeneratingUnit"), Column("BaseVoltage"),
                   Column("EquipmentContainer")],
                  machine_rows, comment=f"WMOD 0\n{untranscribed}"),
        ]
    if converter_rows:
        statements += [
            Table("PowerElectronicsConnection",
                  [Column("mRID"), Column("name"), Column("bus"), Column("p", "MW"), Column("q", "MVAr"),
                   Column("maxQ", "MVAr"), Column("minQ", "MVAr"), Column("ratedS", "MVA"), Column("ratedU", "kV"),
                   Column("inService"),
                   Column("controlEnabled"), Column("RegulatingControl"), Column("BaseVoltage"),
                   Column("EquipmentContainer")],
                  converter_rows, comment=f"WMOD 1, 2, 3; listed when not the default: zr, rmpct (no qPercent); "
                                          f"WMOD 2's wpf always\n{untranscribed}"),
            Table("PowerElectronicsUnit", [Column("mRID"), Column("name"), Column("maxP", "MW"),
                                           Column("minP", "MW"), Column("PowerElectronicsConnection"),
                                           Column("EquipmentContainer")], converter_unit_rows),
            Table("ControlAreaPowerElectronicsUnit", [Column("mRID"), Column("name"), Column("ControlArea"),
                                                      Column("PowerElectronicsUnit")], converter_area_rows),
        ]
    if terminal_updates:
        statements.append(Table("RegulatingControl", [Column("mRID"), Column("Terminal")], terminal_updates,
                                update=True, comment="a powerFactor control on its connection's own terminal, "
                                                     "which binds after the control (R3c-2)"))
    return Document(name="generator", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(records)))
