"""RAW Generator -> ``generator.cimtbl``: one ``RegulatingControl`` per plant (bus I), and per record a
``SynchronousMachine`` + ``GeneratingUnit`` (WMOD 0) or a ``PowerElectronicsConnection`` + ``PowerElectronicsUnit``
(WMOD 1), each unit in its bus's ``ControlArea``.

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#generator-r3``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, Row, Table
from cimtopology.core.voltage import base_voltage_mrid

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, lookup, mrid, untranscribed_names
from cimhub_raw.importer.cimtbl.area_interchange import area_mrid, control_area_numbers
from cimhub_raw.importer.cimtbl.bus import busbar_mrid
from cimhub_raw.importer.cimtbl.derived import generation_p_q, ohms_from_per_unit, volts_from_per_unit
from cimhub_raw.importer.cimtbl.records import fill_keyed_defaults, raw_defaults

NATIVE_CLASS = schema.GeneratorRecord
#: prefixes requested from the cimtbl-translate table owners (plan C3)
CONTROL_PREFIX = "gc_"
MACHINE_PREFIXES = ("sm_", "gu_", "cagu_")
CONVERTER_PREFIXES = ("pec_", "pecu_", "capu_")

#: STAT -> inService
IN_SERVICE = {1: True, 0: False}
#: WMOD -> is the record a converter-interfaced plant (PowerElectronicsConnection)? (RAW-24)
CONVERTER = {0: False, 1: True}
#: WMOD codes that raise, with why
UNMAPPED_WMOD = {2: "renewable, Q limits from WPF: no case has one yet",
                 3: "renewable, fixed Q from WPF: no case has one yet", 4: "infeed, fixed Q: no case has one yet"}
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
                                                     f"bb_<I>_T1 when 0 (RAW-11); a remote IREG from a swing bus "
                                                     f"raises; {_PLANT}; blank: 0 (defaulted)"),
    "rated_mva": Field("copied", (("SynchronousMachine", "ratedS", "MVA"),
                                  ("PowerElectronicsConnection", "ratedS", "MVA")),
                       note="MBASE; blank: SBASE (defaulted)"),
    "zr": Field("derived", note="ZR (pu on MBASE): SynchronousMachine r (ohm) = ZR x BASKV^2 / MBASE "
                                "(ohms_from_per_unit); untranscribed on a PowerElectronicsConnection; blank: 0 "
                                "(defaulted)"),
    "zx": Field("untranscribed", note="ZX: cim18v17 has no positive-sequence machine reactance (TODO: a profile "
                                      "extension, RAW-23)"),
    "rt": Field("structural", note="RT: the implicit step-up transformer; nonzero raises until a case has one "
                                   "(RAW-25); blank: 0 (defaulted)"),
    "xt": Field("structural", note="XT: as RT"),
    "gtap": Field("untranscribed", note="GTAP: used only when RT + jXT is nonzero, which raises"),
    "status": Field("mapped", note="STAT: inService = (STAT == 1); blank: 1 (defaulted)"),
    "rmpct": Field("copied", (("SynchronousMachine", "qPercent", None),),
                   note=f"RMPCT, on every SynchronousMachine of the plant; a PowerElectronicsConnection has no "
                        f"qPercent (CIM 18 gap); {_PLANT}; blank: 100 (defaulted)"),
    "max_p_output": Field("copied", (("GeneratingUnit", "maxOperatingP", "MW"), ("PowerElectronicsUnit", "maxP", "MW")),
                          note="PT, by WMOD; blank: 9999 (defaulted)"),
    "min_p_output": Field("copied", (("GeneratingUnit", "minOperatingP", "MW"), ("PowerElectronicsUnit", "minP", "MW")),
                          note="PB, by WMOD; blank: -9999 (defaulted)"),
    **{f"o{n}": Field("untranscribed", note=_OWNER) for n in range(1, 5)},
    **{f"f{n}": Field("untranscribed", note=_OWNER) for n in range(1, 5)},
    "wmod": Field("mapped", note="WMOD: the class (RAW-24), 0 conventional a SynchronousMachine + GeneratingUnit, 1 "
                                 "renewable with QT/QB limits a PowerElectronicsConnection + PowerElectronicsUnit; 2, "
                                 "3 and 4 raise until a case has one; blank: 0 (defaulted)"),
    "wpf": Field("untranscribed", note="WPF: used only by WMOD 2 and 3, which raise"),
    "nreg": Field("structural", note="NREG: a node of bus IREG; nonzero raises until R6 (node-breaker); blank: 0 "
                                     "(defaulted)"),
}

_PROVENANCE = """PSS/E RAW Generator -> RegulatingControl per plant (bus I); SynchronousMachine + GeneratingUnit (WMOD 0)
or PowerElectronicsConnection + PowerElectronicsUnit (WMOD 1), each with its ControlArea membership.
Source table: Generator (records: {count})
Mapping: cimhub_raw/docs/CIMTBL_MAPPING.md#generator-r3"""


def _check_record(generator, record_id: str) -> None:
    """The forms R3 does not map raise."""
    if generator.wmod in UNMAPPED_WMOD:
        raise NotImplementedError(f"{record_id}: WMOD {generator.wmod} ({UNMAPPED_WMOD[generator.wmod]})")
    if generator.rt or generator.xt:
        raise NotImplementedError(f"{record_id}: RT + jXT = {generator.rt} + j{generator.xt}, an implicit step-up "
                                  "transformer (RAW-25: no case has one yet)")
    if generator.nreg:
        raise NotImplementedError(f"{record_id}: NREG {generator.nreg} names a node in a substation (R6)")


def _plant_key(generator) -> tuple[int, float, float]:
    """(regulated bus, VS, RMPCT): what every record of one plant must share."""
    return generator.regulated_bus_number or generator.bus_number, generator.regulated_voltage_setpoint, \
        generator.rmpct


def _plants(records, defaults: dict) -> dict[int, list[tuple[object, str | None]]]:
    """bus I -> its records, filled and checked, with their ``defaulted`` comments; a plant that disagrees raises."""
    plants: dict[int, list[tuple[object, str | None]]] = {}
    for record in records:
        generator, defaulted = fill_keyed_defaults(FIELDS, record, defaults)
        _check_record(generator, f"generator {generator.ID}")
        members = plants.setdefault(generator.bus_number, [])
        if members and _plant_key(members[0][0]) != _plant_key(generator):
            raise ValueError(f"plant {generator.bus_number}: generators {members[0][0].ID} and {generator.ID} "
                             f"disagree on (IREG, VS, RMPCT): {_plant_key(members[0][0])} vs "
                             f"{_plant_key(generator)}; PSS/E treats them as plant quantities")
        members.append((generator, defaulted))
    return plants


def map_generator(native, substations_by_bus: dict[int, str], base_kv_of: dict[int, float],
                  bus_area: dict[int, int], bus_type: dict[int, int], base_mva: float) -> Document:
    records = sorted(native.list_by_class(NATIVE_CLASS), key=lambda generator: (generator.bus_number,
                                                                               str(generator.gen_id)))
    if not records:
        return Document(name="generator", statements=[], profile=CIM_PROFILE)
    control_areas = control_area_numbers(native)
    plants = _plants(records, {**raw_defaults(NATIVE_CLASS), "rated_mva": base_mva})

    control_rows, unit_rows, machine_area_rows, machine_rows = [], [], [], []
    converter_rows, converter_unit_rows, converter_area_rows = [], [], []
    for bus, members in plants.items():
        plant_id = f"plant {bus}"
        regulated, setpoint, _ = _plant_key(members[0][0])
        if regulated not in base_kv_of:
            raise ValueError(f"{plant_id}: IREG {regulated} is no bus")
        swing = bus_type[bus] == SWING
        if swing and regulated != bus:
            raise ValueError(f"{plant_id}: a swing bus regulates remote bus {regulated} (PSS/E would regulate bus "
                             f"{bus} instead)")
        if swing and all(lookup(CONVERTER, generator.wmod, slot="wmod", record_id=generator.ID)
                         for generator, _ in members):
            raise ValueError(f"{plant_id}: a swing bus with no SynchronousMachine (only WMOD 1 records), so no "
                             "referencePriority")
        if bus_area[bus] not in control_areas:
            raise ValueError(f"{plant_id}: AREA {bus_area[bus]} has no area-interchange record (no ControlArea "
                             f"{area_mrid(bus_area[bus])})")
        control = mrid(CONTROL_PREFIX, bus)
        enabled = cell(bus_type[bus] in REGULATING_BUS_TYPES)
        control_rows.append(Row([control, str(bus), "voltage", "false", enabled,
                                 cell(volts_from_per_unit(setpoint, base_kv_of[regulated])),
                                 f"{busbar_mrid(regulated)}_T1"]))

        kv, container, area = base_kv_of[bus], substations_by_bus[bus], area_mrid(bus_area[bus])
        for generator, defaulted in members:
            record_id = generator.ID
            p, q = generation_p_q(generator)
            in_service = cell(lookup(IN_SERVICE, generator.status, slot="status", record_id=record_id))
            limits = [cell(generator.max_q_output), cell(generator.min_q_output), cell(generator.rated_mva)]
            if lookup(CONVERTER, generator.wmod, slot="wmod", record_id=record_id):
                connection, unit, membership = (mrid(prefix, record_id) for prefix in CONVERTER_PREFIXES)
                converter_rows.append(Row([connection, record_id, str(bus), cell(p), cell(q), *limits, in_service,
                                           enabled, control, base_voltage_mrid(kv), container], comment=defaulted))
                converter_unit_rows.append(Row([unit, record_id, cell(generator.max_p_output),
                                                cell(generator.min_p_output), connection, container]))
                converter_area_rows.append(Row([membership, record_id, area, unit]))
            else:
                machine, unit, membership = (mrid(prefix, record_id) for prefix in MACHINE_PREFIXES)
                unit_rows.append(Row([unit, record_id, cell(generator.max_p_output), cell(generator.min_p_output),
                                      container]))
                machine_area_rows.append(Row([membership, record_id, area, unit]))
                machine_rows.append(Row([
                    machine, record_id, str(bus), cell(p), cell(q), *limits,
                    cell(ohms_from_per_unit(generator.zr, kv, generator.rated_mva)), cell(generator.rmpct),
                    cell(1 if swing else None), in_service, enabled, control, unit, base_voltage_mrid(kv),
                    container], comment=defaulted))

    untranscribed = untranscribed_names(FIELDS)
    statements = [Table("RegulatingControl",
                        [Column(name) for name in ("mRID", "name", "mode", "discrete", "enabled", "targetValue",
                                                   "Terminal")],
                        control_rows, comment="one per plant (bus I); targetValue in V")]
    if machine_rows:
        statements += [
            Table("GeneratingUnit", [Column("mRID"), Column("name"), Column("maxOperatingP", "MW"),
                                     Column("minOperatingP", "MW"), Column("EquipmentContainer")], unit_rows),
            Table("ControlAreaGeneratingUnit", [Column("mRID"), Column("name"), Column("ControlArea"),
                                                Column("GeneratingUnit")], machine_area_rows),
            Table("SynchronousMachine",
                  [Column("mRID"), Column("name"), Column("bus"), Column("p", "MW"), Column("q", "MVAr"),
                   Column("maxQ", "MVAr"), Column("minQ", "MVAr"), Column("ratedS", "MVA"), Column("r", "ohm"),
                   Column("qPercent"), Column("referencePriority"), Column("inService"), Column("controlEnabled"),
                   Column("RegulatingControl"), Column("GeneratingUnit"), Column("BaseVoltage"),
                   Column("EquipmentContainer")],
                  machine_rows, comment=f"WMOD 0\n{untranscribed}"),
        ]
    if converter_rows:
        statements += [
            Table("PowerElectronicsConnection",
                  [Column("mRID"), Column("name"), Column("bus"), Column("p", "MW"), Column("q", "MVAr"),
                   Column("maxQ", "MVAr"), Column("minQ", "MVAr"), Column("ratedS", "MVA"), Column("inService"),
                   Column("controlEnabled"), Column("RegulatingControl"), Column("BaseVoltage"),
                   Column("EquipmentContainer")],
                  converter_rows, comment=f"WMOD 1; untranscribed here also: zr, rmpct (no qPercent)\n"
                                          f"{untranscribed}"),
            Table("PowerElectronicsUnit", [Column("mRID"), Column("name"), Column("maxP", "MW"),
                                           Column("minP", "MW"), Column("PowerElectronicsConnection"),
                                           Column("EquipmentContainer")], converter_unit_rows),
            Table("ControlAreaPowerElectronicsUnit", [Column("mRID"), Column("name"), Column("ControlArea"),
                                                      Column("PowerElectronicsUnit")], converter_area_rows),
        ]
    return Document(name="generator", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(records)))
