"""RAW Load -> ``load.cimtbl``: a ``ConformLoad`` (SCALE 1) or ``NonConformLoad`` (SCALE 0) per load, its ZIP
``LoadResponseCharacteristic``, and the ``LoadArea`` > ``SubLoadArea`` > load group hierarchy of its AREA and ZONE.

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#load``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, Row, Table
from cimtopology.core.voltage import base_voltage_mrid

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, lookup, mrid, untranscribed_names
from cimhub_raw.importer.cimtbl.area_interchange import area_mrid, control_area_numbers
from cimhub_raw.importer.cimtbl.derived import load_p_q, zip_mix
from cimhub_raw.importer.cimtbl.records import fill_keyed_defaults, raw_defaults

NATIVE_CLASS = schema.LoadRecord
PREFIX = "ld_"
LOAD_AREA_PREFIX = "la_"  # requested from the cimtbl-translate table owners (plan C3), as the four below
SUB_LOAD_AREA_PREFIX = "sla_"
ZIP_PREFIX = "zip_"

#: STATUS -> inService
IN_SERVICE = {1: True, 0: False}
#: SCALE -> (load class, its group class, the group's mRID prefix)
LOAD_CLASS = {1: ("ConformLoad", "ConformLoadGroup", "clg_"), 0: ("NonConformLoad", "NonConformLoadGroup", "nclg_")}

_P_Q = "the sum is p (MW) / q (MVAr) at 1 pu (load_p_q) and its share a ZIP fraction (zip_mix)"
FIELDS = {
    "bus_number": Field("structural", note="I: bus; BaseVoltage = bus I's bv_<BASKV>; EquipmentContainer = bus I's "
                                           "substation"),
    "load_id": Field("structural", note="ID: with I the key, mRID ld_<I>_<ID>, name I_ID"),
    "status": Field("mapped", note="STATUS: inService = (STATUS == 1); blank: 1 (defaulted)"),
    "area": Field("structural", note="AREA: the LoadArea la_<AREA> (ControlArea ca_<AREA>) of the load's group; an "
                                     "AREA with no area-interchange record raises; blank: the bus's (defaulted)"),
    "zone": Field("structural", note="ZONE: the SubLoadArea sla_<AREA>_<ZONE> of the load's group; the exporter "
                                     "reads ZONE from the bus's substation Region, so a ZONE other than the bus's is "
                                     "also listed untranscribed on the row (CIM 18 gap); blank: the bus's "
                                     "(defaulted)"),
    "constant_real_power": Field("derived", note=f"PL: constant power; {_P_Q}"),
    "constant_imag_power": Field("derived", note=f"QL: constant power; {_P_Q}"),
    "constant_current_real_power": Field("derived", note=f"IP: constant current; {_P_Q}"),
    "constant_current_imag_power": Field("derived", note=f"IQ: constant current; {_P_Q}"),
    "constant_admittance_real_power": Field("derived", note=f"YP: constant admittance; {_P_Q}"),
    "constant_admittance_imag_power": Field("derived", note="YQ: constant admittance, negative for an inductive "
                                                            f"load, so it enters q as -YQ; {_P_Q}"),
    "owner": Field("untranscribed", note="ownership is an asset concept (CIM 18 gap)"),
    "scale": Field("mapped", note="SCALE: the class, 1 ConformLoad (scalable) in a ConformLoadGroup clg_<AREA>_<ZONE>, "
                                  "0 NonConformLoad (fixed) in a NonConformLoadGroup nclg_<AREA>_<ZONE>; blank: 1 "
                                  "(defaulted)"),
    "interruptible": Field("untranscribed", note="INTRPT: no CIM home"),
    "dgenp": Field("untranscribed", note="DGENP: distributed generation behind the load, no CIM home"),
    "dgenq": Field("untranscribed", note="DGENQ: as DGENP"),
    "dgenf": Field("untranscribed", note="DGENM: as DGENP"),
}

_PROVENANCE = """PSS/E RAW Load -> ConformLoad / NonConformLoad (by SCALE), LoadResponseCharacteristic (ZIP), LoadArea,
SubLoadArea, ConformLoadGroup / NonConformLoadGroup (AREA, ZONE).
Source table: Load (records: {count})
Mapping: cimhub_raw/docs/CIMTBL_MAPPING.md#load"""

_LOAD_COLUMNS = [Column("mRID"), Column("name"), Column("bus"), Column("p", "MW"), Column("q", "MVAr"),
                 Column("inService"), Column("LoadResponse"), Column("LoadGroup"), Column("BaseVoltage"),
                 Column("EquipmentContainer")]
_ZIP_COLUMNS = [Column(name) for name in ("mRID", "exponentModel", "pConstantPower", "pConstantCurrent",
                                          "pConstantImpedance", "qConstantPower", "qConstantCurrent",
                                          "qConstantImpedance")]


def _fraction_text(fraction: float) -> str:
    text = cell(fraction)
    return text[:-2] if text.endswith(".0") else text


def zip_mrid(mix: tuple[float, ...]) -> str:
    """``zip_`` + the six fractions, ``zip_0_1_0_0_0_1``: one shared row per distinct mix."""
    return ZIP_PREFIX + "_".join(_fraction_text(fraction) for fraction in mix)


def map_load(native, substations_by_bus: dict[int, str], base_kv_of: dict[int, float], bus_area: dict[int, int],
             bus_zone: dict[int, int]) -> Document:
    records = sorted(native.list_by_class(NATIVE_CLASS), key=lambda load: (load.bus_number, str(load.load_id)))
    if not records:
        return Document(name="load", statements=[], profile=CIM_PROFILE)
    control_areas = control_area_numbers(native)
    defaults = raw_defaults(NATIVE_CLASS)
    load_rows: dict[str, list[Row]] = {}
    zip_rows: dict[str, Row] = {}
    groups: dict[tuple[str, int, int], str] = {}  # (group class, area, zone) -> group mRID
    for record in records:
        bus = record.bus_number
        load, defaulted = fill_keyed_defaults(FIELDS, record,
                                              {**defaults, "area": bus_area[bus], "zone": bus_zone[bus]})
        record_id = f"load {load.ID}"
        if load.area not in control_areas:
            raise ValueError(f"{record_id}: AREA {load.area} has no area-interchange record (no ControlArea "
                             f"{area_mrid(load.area)})")
        load_class, group_class, group_prefix = lookup(LOAD_CLASS, load.scale, slot="scale", record_id=record_id)
        group = groups.setdefault((group_class, load.area, load.zone), mrid(group_prefix, f"{load.area}_{load.zone}"))
        mix = zip_mix(load)
        zip_rows.setdefault(zip_mrid(mix), Row([zip_mrid(mix), "false", *(cell(fraction) for fraction in mix)]))
        p, q = load_p_q(load)
        comments = [defaulted]
        if load.zone != bus_zone[bus]:
            comments.append(f"untranscribed: zone={load.zone} (bus {bus} is in zone {bus_zone[bus]})")
        load_rows.setdefault(load_class, []).append(Row([
            mrid(PREFIX, load.ID), load.ID, str(bus), cell(p), cell(q),
            cell(lookup(IN_SERVICE, load.status, slot="status", record_id=record_id)), zip_mrid(mix), group,
            base_voltage_mrid(base_kv_of[bus]), substations_by_bus[bus]],
            comment="\n".join(filter(None, comments)) or None))

    areas = sorted({area for _, area, _ in groups})
    sub_areas = sorted({(area, zone) for _, area, zone in groups})
    statements = [
        Table("LoadArea", [Column("mRID"), Column("name"), Column("ControlArea")],
              [Row([mrid(LOAD_AREA_PREFIX, area), str(area), area_mrid(area)]) for area in areas]),
        Table("SubLoadArea", [Column("mRID"), Column("name"), Column("LoadArea")],
              [Row([mrid(SUB_LOAD_AREA_PREFIX, f"{area}_{zone}"), f"{area}_{zone}", mrid(LOAD_AREA_PREFIX, area)])
               for area, zone in sub_areas]),
    ]
    for group_class in ("ConformLoadGroup", "NonConformLoadGroup"):
        rows = [Row([group, f"{area}_{zone}", mrid(SUB_LOAD_AREA_PREFIX, f"{area}_{zone}")])
                for (cls, area, zone), group in sorted(groups.items()) if cls == group_class]
        if rows:
            statements.append(Table(group_class, [Column("mRID"), Column("name"), Column("SubLoadArea")], rows))
    statements.append(Table("LoadResponseCharacteristic", _ZIP_COLUMNS, list(zip_rows.values()),
                            comment="ZIP fractions: PL, IP, YP over p; QL, IQ, -YQ over q (zip_mix)"))
    untranscribed = untranscribed_names(FIELDS)
    for load_class in ("ConformLoad", "NonConformLoad"):
        if load_class in load_rows:
            statements.append(Table(load_class, _LOAD_COLUMNS, load_rows[load_class], comment=untranscribed))
            untranscribed = None
    return Document(name="load", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(records)))
