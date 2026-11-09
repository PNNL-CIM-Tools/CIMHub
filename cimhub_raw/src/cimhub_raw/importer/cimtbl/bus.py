"""RAW Bus -> ``bus.cimtbl``: the substations, one ``TopologicalNode`` and one ``BusbarSection`` per bus, the bus's
voltage limits on the busbar's terminal, and its solved voltage.

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#bus``.
"""

from __future__ import annotations

import textwrap

from cimtables.document import Column, Document, Row, Table
from cimtopology.core.voltage import base_voltage_mrid

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, fill_defaults, mrid, schema_defaults, untranscribed_names
from cimhub_raw.importer.cimtbl.derived import kv_from_per_unit
from cimhub_raw.importer.cimtbl.zone import zone_mrid
from cimhub_raw.importer.topology import SubstationGroup

NATIVE_CLASS = schema.BusRecord
BUSBAR_PREFIX = "bb_"  # requested from the cimtbl-translate table owners (plan C3)
SUBSTATION_PREFIX = "sub_"

_LIMIT = "(pu): home VoltageLimit bb_<I>_{code} on the BusbarSection terminal's set bb_<I>_limits (RAW-19); " \
         "normalValue (kV) = pu x BASKV (kv_from_per_unit)"
FIELDS = {
    "bus_number": Field("copied", (("TopologicalNode", "busNumber", None),),
                        note="I; node mRID = I (bare, the cimtbl-translate rule for nodes; RAW-18); BusbarSection "
                             "mRID = bb_ + I (RAW-19)"),
    "name": Field("copied", (("TopologicalNode", "name", None), ("BusbarSection", "name", None)),
                  note="NAME; blank: the bus number"),
    "base_voltage": Field("structural", note="BASKV: the node's and the busbar's BaseVoltage bv_<kv>; the master writes "
                                             "one BaseVoltage per distinct BASKV, nominalVoltage (kV) copied; the base "
                                             "of every pu voltage of the bus"),
    "bus_type": Field("structural", note="IDE: 1 and 2 add nothing (the equipment says it); 3 (swing) is the angle "
                                         "reference, written with R3 (SynchronousMachine.referencePriority); 4 "
                                         "(isolated) is listed on the table comment"),
    "area": Field("untranscribed", note="AREA: a node or BusbarSection has no ControlArea association (CIM 18 gap); "
                                        "the bus's generators, loads and tie terminals carry the area (R2, R3, R5)"),
    "zone": Field("structural", note="ZONE: the Region of the node's Substation (srgn_<zone>), and a substation "
                                     "boundary (plan 3.2)"),
    "owner": Field("untranscribed", note="OWNER: ownership is an asset concept (CIM 18 gap)"),
    "voltage_magnitude": Field("derived", note="VM (pu): SvVoltage.v (kV) = VM x BASKV (kv_from_per_unit; RAW-14)"),
    "voltage_angle": Field("copied", (("SvVoltage", "angle", "deg"),), note="VA (RAW-14)"),
    "normal_voltage_magnitude_high_limit": Field("derived", note="NVHI " + _LIMIT.format(code="nvhi")),
    "normal_voltage_magnitude_low_limit": Field("derived", note="NVLO " + _LIMIT.format(code="nvlo")),
    "emergency_voltage_magnitude_high_limit": Field("derived", note="EVHI " + _LIMIT.format(code="evhi")),
    "emergency_voltage_magnitude_low_limit": Field("derived", note="EVLO " + _LIMIT.format(code="evlo")),
}

#: (slot, mRID suffix, OperationalLimitType) of the four bus voltage limits; the types are in the master.
VOLTAGE_LIMITS = (
    ("normal_voltage_magnitude_high_limit", "nvhi", "olt_normal_high"),
    ("normal_voltage_magnitude_low_limit", "nvlo", "olt_normal_low"),
    ("emergency_voltage_magnitude_high_limit", "evhi", "olt_emergency_high"),
    ("emergency_voltage_magnitude_low_limit", "evlo", "olt_emergency_low"),
)

_PROVENANCE = """PSS/E RAW Bus -> Substation (synthesized), TopologicalNode, BusbarSection, OperationalLimitSet +
VoltageLimit, SvVoltage.
Source table: Bus (records: {count})
Mapping: cimhub_raw/docs/CIMTBL_MAPPING.md#bus"""


def busbar_mrid(bus_number: int) -> str:
    return mrid(BUSBAR_PREFIX, bus_number)


def substation_mrid(group: SubstationGroup) -> str:
    return mrid(SUBSTATION_PREFIX, group.buses[0])


def filled_buses(native) -> list[tuple[schema.BusRecord, str | None]]:
    """Every bus in number order with its blank slots filled from ``raw_default``, and the defaulted comment.

    A BASKV that is blank or not positive raises: the spec's default of 0.0 is no base.
    """
    defaults = schema_defaults(NATIVE_CLASS, "raw_default")
    buses = []
    for record in sorted(native.list_by_class(NATIVE_CLASS), key=lambda bus: bus.bus_number):
        if record.base_voltage is None or record.base_voltage <= 0:
            raise ValueError(f"bus {record.bus_number}: BASKV={record.base_voltage!r} is no base voltage")
        buses.append(fill_defaults(FIELDS, record, defaults))
    if not buses:
        raise ValueError("the RAW model has no buses")
    return buses


def base_voltages(native) -> dict[str, float]:
    """BaseVoltage mRID -> BASKV (kV), highest first. Two BASKVs that share an mRID raise."""
    by_mrid: dict[str, float] = {}
    for bus, _ in filled_buses(native):
        key = base_voltage_mrid(bus.base_voltage)
        if by_mrid.setdefault(key, bus.base_voltage) != bus.base_voltage:
            raise ValueError(f"BASKV {by_mrid[key]!r} and {bus.base_voltage!r} both give BaseVoltage {key}")
    return dict(sorted(by_mrid.items(), key=lambda item: -item[1]))


def map_bus(native, groups: list[SubstationGroup], threshold: float) -> Document:
    buses = filled_buses(native)
    by_number = {bus.bus_number: bus for bus, _ in buses}
    substation_of = {number: substation_mrid(group) for group in groups for number in group.buses}

    substation_rows = []
    for group in groups:
        first = by_number[group.buses[0]]
        note = None
        if len(group.buses) > 1:
            note = f"buses {', '.join(map(str, group.buses))}; {', '.join(group.merged_by)}"
        substation_rows.append(Row([substation_mrid(group), cell(first.name or str(first.bus_number)),
                                    zone_mrid(first.zone)], comment=note))
    substations = Table("Substation", [Column("mRID"), Column("name"), Column("Region")], substation_rows,
                        comment=textwrap.fill(f"synthesized: substations, buses merged across switching devices, "
                                              f"zero-impedance branches (R = 0, |X| <= THRSHZ {cell(threshold)}), "
                                              f"series capacitors and transformers, within a zone ({len(groups)} "
                                              f"substations)", width=116))

    node_rows, busbar_rows, set_rows, limit_rows, voltage_rows = [], [], [], [], []
    for bus, defaulted in buses:
        number = bus.bus_number
        name = cell(bus.name or str(number))
        voltage = base_voltage_mrid(bus.base_voltage)
        node_rows.append(Row([str(number), name, str(number), voltage, substation_of[number]], comment=defaulted))
        busbar_rows.append(Row([busbar_mrid(number), name, str(number), voltage, substation_of[number]]))
        set_rows.append(Row([f"{busbar_mrid(number)}_limits", f"{busbar_mrid(number)}_T1"]))
        for slot, suffix, limit_type in VOLTAGE_LIMITS:
            limit_rows.append(Row([f"{busbar_mrid(number)}_{suffix}", f"{busbar_mrid(number)}_limits", limit_type,
                                   cell(kv_from_per_unit(getattr(bus, slot), bus.base_voltage))]))
        voltage_rows.append(Row([f"{number}_sv", str(number),
                                 cell(kv_from_per_unit(bus.voltage_magnitude, bus.base_voltage)),
                                 cell(bus.voltage_angle)]))

    isolated = [str(bus.bus_number) for bus, _ in buses if bus.bus_type == 4]
    node_comment = "; ".join(filter(None, [untranscribed_names(FIELDS),
                                           f"IDE 4 (isolated): {', '.join(isolated) if isolated else 'none'}"]))
    statements = [
        substations,
        Table("TopologicalNode", [Column("mRID"), Column("name"), Column("busNumber"), Column("BaseVoltage"),
                                  Column("ConnectivityNodeContainer")], node_rows, comment=node_comment),
        Table("BusbarSection", [Column("mRID"), Column("name"), Column("bus"), Column("BaseVoltage"),
                                Column("EquipmentContainer")], busbar_rows,
              comment="one BusbarSection per bus: its terminal holds the bus's voltage limits and any regulation\n"
                      "of the bus (RAW-11, RAW-19)"),
        Table("OperationalLimitSet", [Column("mRID"), Column("Terminal")], set_rows),
        Table("VoltageLimit", [Column("mRID"), Column("OperationalLimitSet"), Column("OperationalLimitType"),
                               Column("normalValue", "kV")], limit_rows,
              comment="derived: normalValue = NVHI, NVLO, EVHI, EVLO (pu) x BASKV (kv_from_per_unit)"),
        Table("SvVoltage", [Column("identifier"), Column("TopologicalNode"), Column("v", "kV"),
                            Column("angle", "deg")], voltage_rows,
              comment="solved state; derived: v = VM (pu) x BASKV (kv_from_per_unit); angle = VA"),
    ]
    return Document(name="bus", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(buses)))
