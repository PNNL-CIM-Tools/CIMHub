"""RAW VSC DC line -> ``vsc_dc.cimtbl``: a ``DCLine`` holding a ``DCLineSegment`` between two
``DCTopologicalNode``s, and a ``VsConverter`` per converter on its AC bus, with its DC and AC controls, its
reactive limits as a ``VsCapabilityCurve`` and its ratings on its terminal (P2-1, P2-3). A tie (converters in two
AREAs) gets its ``TieFlow``s on the MW-control converter's terminal (R5).

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#vsc-dc-line-decision-p2-3``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, Row, Table
from cimtopology.core.voltage import base_voltage_mrid

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, fill_defaults, lookup, mrid, untranscribed_names
from cimhub_raw.importer.cimtbl.area_interchange import control_area_numbers
from cimhub_raw.importer.cimtbl.dc_topology import DCRows
from cimhub_raw.importer.cimtbl.derived import kv_from_per_unit
from cimhub_raw.importer.cimtbl.ratings import rating_type_mrid
from cimhub_raw.importer.cimtbl.records import listed_off_default, raw_defaults
from cimhub_raw.importer.cimtbl.tie_flow import TieFlowRows
from cimhub_raw.importer.node_breaker import NodeBreaker

NATIVE_CLASS = schema.VscDcRecord
PREFIX = "vsc_"  # requested from the cimtbl-translate table owners (plan C3)
CONVERTERS = (1, 2)

#: MDC -> inService of the segment and both converters
IN_SERVICE = {1: True, 0: False}
#: converter TYPE -> pPccControl; 0 is out of service
DC_CONTROL = {0: None, 1: "udc", 2: "pPcc"}
DC_VOLTAGE = 1
#: converter MODE -> qPccControl
AC_CONTROL = {1: "voltagePcc", 2: "powerFactorPcc"}
AC_VOLTAGE = 1
#: converter slots CIM cannot hold, listed on the converter's row when not the default
LISTED = ("minloss", "pwf")
#: what MODE 2 (power factor) does not use, listed when not the default
UNUSED_BY_POWER_FACTOR = ("maxq", "minq", "vsreg", "nreg")

_OWNER = "ownership is an asset concept (CIM 18 gap)"


def _converter_fields(k: int) -> dict[str, Field]:
    c = f"converter {k}"
    return {
        f"ibus_{k}": Field("structural", note=f"IBUS ({c}): VsConverter {PREFIX}<NAME>_c{k} on this bus, its "
                                              "BaseVoltage and EquipmentContainer (its substation)"),
        f"converter_type_{k}": Field("mapped", note=f"TYPE ({c}): 0 inService false, 1 pPccControl udc, 2 pPccControl "
                                                    "pPcc; on a tie the TYPE 1 converter is the home end (R5)"),
        f"mode_{k}": Field("mapped", note=f"MODE ({c}): 1 qPccControl voltagePcc, 2 qPccControl powerFactorPcc; "
                                          "blank: 1 (defaulted)"),
        f"dcset_{k}": Field("derived", note=f"DCSET ({c}): TYPE 1 targetUdc (kV); TYPE 2 targetPpcc = -DCSET (MW: "
                                            "RAW's + feeds the AC network, CIM's load sign); TYPE 0 listed"),
        f"acset_{k}": Field("derived", note=f"ACSET ({c}): MODE 1 targetUpcc = ACSET x BASKV(VSREG or IBUS) "
                                            "(kv_from_per_unit); MODE 2 targetPowerFactorPcc = ACSET; blank: 1.0 "
                                            "(defaulted)"),
        f"aloss_{k}": Field("copied", (("VsConverter", "idleLoss", "kW"),), note=f"ALOSS ({c}); blank: 0 "
                                                                                  "(defaulted)"),
        f"bloss_{k}": Field("copied", (("VsConverter", "switchingLoss", "kW/A"),),
                            note=f"BLOSS ({c}): loss = ALOSS + Idc x BLOSS; blank: 0 (defaulted)"),
        f"minloss_{k}": Field("untranscribed", note=f"MINLOSS ({c}): no CIM home (CIM 18 gap); listed when not 0"),
        f"smax_{k}": Field("structural", note=f"SMAX ({c}): ApparentPowerLimit <converter>_smax (MVA) in the set "
                                              "<converter>_ratings on its T1, typed RATE1; 0 (unlimited) writes no "
                                              "limit"),
        f"imax_{k}": Field("structural", note=f"IMAX ({c}): CurrentLimit <converter>_imax (A), as SMAX"),
        f"pwf_{k}": Field("untranscribed", note=f"PWF ({c}): no CIM home (CIM 18 gap); listed when not 1.0"),
        f"maxq_{k}": Field("copied", (("CurveData", "y2value", "MVAr"),),
                           note=f"MAXQ ({c}): MODE 1: the VsCapabilityCurve <converter>_qcurve's one point (P 0, "
                                "constantYValue), y2 = MAXQ (MVAr); MODE 2 does not use it (listed when not the "
                                "default)"),
        f"minq_{k}": Field("copied", (("CurveData", "y1value", "MVAr"),), note=f"MINQ ({c}): as MAXQ, y1 = MINQ"),
        f"vsreg_{k}": Field("structural", note=f"VSREG ({c}): MODE 1: PccTerminal bb_<VSREG>_T1, or bb_<IBUS>_T1 "
                                               "when 0 (RAW-11), or the NREG node's busbar; MODE 2: bb_<IBUS>_T1"),
        f"rmpct_{k}": Field("copied", (("VsConverter", "qShare", None),), note=f"RMPCT ({c}); blank: 100 "
                                                                                "(defaulted)"),
        f"nreg_{k}": Field("structural", note=f"NREG ({c}): a node of bus VSREG; nonzero: PccTerminal is that "
                                              "node's busbar bb_s<IS>_n<NREG>_T1 (R6)"),
    }


FIELDS = {
    "name": Field("structural", note="NAME: the key; DCLine vsc_<NAME>, its segment, nodes and converters"),
    "mdc": Field("mapped", note="MDC: inService = (MDC == 1) on the segment and both converters; blank: 1 "
                                "(defaulted)"),
    "rdc": Field("copied", (("DCLineSegment", "resistance", "ohm"),), note="RDC"),
    **{f"o{n}": Field("untranscribed", note=_OWNER) for n in range(1, 5)},
    **{f"f{n}": Field("untranscribed", note=_OWNER) for n in range(1, 5)},
    **_converter_fields(1),
    **_converter_fields(2),
}

_PROVENANCE = """PSS/E RAW VSC DC line -> DCLine (DCLineSegment, DCTopologicalNodes) + a VsConverter per converter, its
VsCapabilityCurve and ratings; TieFlows of ties.
Source table: VSC DC line (records: {count})
Mapping: cimhub_raw/docs/CIMTBL_MAPPING.md#vsc-dc-line-decision-p2-3"""


def _slot(record, name: str, k: int):
    return getattr(record, f"{name}_{k}")


def _regulated_bus(record, k: int) -> int:
    """The bus converter ``k`` regulates: VSREG (or IBUS when 0) in MODE 1, IBUS in MODE 2."""
    if _slot(record, "mode", k) == AC_VOLTAGE:
        return _slot(record, "vsreg", k) or _slot(record, "ibus", k)
    return _slot(record, "ibus", k)


def regulated_nodes(native) -> list[tuple[int, int, str]]:
    """``(regulated bus, NREG, record id)`` of every MODE 1 converter whose PCC is a node (R6)."""
    return [(_regulated_bus(record, k), _slot(record, "nreg", k), f"VSC DC line {record.name} converter {k}")
            for record in native.list_by_class(NATIVE_CLASS) for k in CONVERTERS
            if _slot(record, "mode", k) == AC_VOLTAGE and _slot(record, "nreg", k)]


def converter_mrid(name: str, k: int) -> str:
    return f"{mrid(PREFIX, name)}_c{k}"


def _listed(record, k: int, defaults: dict) -> str | None:
    slots = [f"{slot}_{k}" for slot in LISTED]
    if _slot(record, "mode", k) != AC_VOLTAGE:
        slots += [f"{slot}_{k}" for slot in UNUSED_BY_POWER_FACTOR]
    note = listed_off_default(record, slots, defaults)
    if _slot(record, "converter_type", k) == 0:
        dcset = f"dcset_{k}={cell(_slot(record, 'dcset', k))}"
        note = f"{note}, {dcset}" if note else f"untranscribed: {dcset}"
    return note


def map_vsc_dc(native, substations_by_bus: dict[int, str], base_kv_of: dict[int, float],
               bus_area: dict[int, int], node_breaker: NodeBreaker) -> Document:
    records = sorted(native.list_by_class(NATIVE_CLASS), key=lambda record: record.name)
    if not records:
        return Document(name="vsc_dc", statements=[], profile=CIM_PROFILE)
    defaults = raw_defaults(NATIVE_CLASS)
    dc = DCRows()
    ties = TieFlowRows(bus_area, control_area_numbers(native))
    converter_rows, curve_rows, point_rows, set_rows, power_rows, current_rows = [], [], [], [], [], []
    for record_in in records:
        record, defaulted = fill_defaults(FIELDS, record_in, defaults)
        record_id = f"VSC DC line {record.name}"
        line_in_service = lookup(IN_SERVICE, record.mdc, slot="mdc", record_id=record_id)
        line = mrid(PREFIX, record.name)
        nodes = dc.add_line(line, record.name, record.rdc, line_in_service, comment=defaulted)
        buses = tuple(_slot(record, "ibus", k) for k in CONVERTERS)
        for k, node in zip(CONVERTERS, nodes):
            converter = converter_mrid(record.name, k)
            bus = _slot(record, "ibus", k)
            if bus not in base_kv_of:
                raise ValueError(f"{record_id}: converter {k} IBUS {bus} is no bus")
            dc_type = _slot(record, "converter_type", k)
            p_control = lookup(DC_CONTROL, dc_type, slot=f"converter_type_{k}", record_id=record_id)
            q_control = lookup(AC_CONTROL, _slot(record, "mode", k), slot=f"mode_{k}", record_id=record_id)
            dcset, acset = _slot(record, "dcset", k), _slot(record, "acset", k)
            regulated = _regulated_bus(record, k)
            if regulated not in base_kv_of:
                raise ValueError(f"{record_id}: converter {k} VSREG {regulated} is no bus")
            voltage_control = q_control == AC_CONTROL[AC_VOLTAGE]
            converter_rows.append(Row([
                converter, f"{record.name}_{k}", str(bus), cell(line_in_service and dc_type != 0),
                cell(p_control), cell(dcset if dc_type == DC_VOLTAGE else None),
                cell(0.0 - dcset if dc_type == 2 else None), q_control,
                cell(kv_from_per_unit(acset, base_kv_of[regulated]) if voltage_control else None),
                cell(None if voltage_control else acset), cell(_slot(record, "aloss", k)),
                cell(_slot(record, "bloss", k)), cell(_slot(record, "rmpct", k)),
                node_breaker.regulated_terminal(regulated, _slot(record, "nreg", k) if voltage_control else 0,
                                                record_id),
                base_voltage_mrid(base_kv_of[bus]), substations_by_bus[bus]], comment=_listed(record, k, defaults)))
            dc.add_converter(converter, node)
            if voltage_control:
                curve = f"{converter}_qcurve"
                curve_rows.append(Row([curve, f"{record.name}_{k}", converter]))
                point_rows.append(Row([f"{curve}_1", curve, "0.0", cell(_slot(record, "minq", k)),
                                       cell(_slot(record, "maxq", k))]))
            smax, imax = _slot(record, "smax", k), _slot(record, "imax", k)
            if smax or imax:
                limit_set = f"{converter}_ratings"
                set_rows.append(Row([limit_set, f"{converter}_T1"]))
                if smax:
                    power_rows.append(Row([f"{converter}_smax", limit_set, rating_type_mrid(1), cell(smax)]))
                if imax:
                    current_rows.append(Row([f"{converter}_imax", limit_set, rating_type_mrid(1), cell(imax)]))
        if ties.is_tie(buses):
            types = [_slot(record, "converter_type", k) for k in CONVERTERS]
            if types.count(DC_VOLTAGE) != 1:
                raise ValueError(f"{record_id}: a tie needs exactly one TYPE 1 (DC voltage) converter, its home end; "
                                 f"TYPE {types[0]} and {types[1]}")
            ties.add(line, record.name, buses, types.index(DC_VOLTAGE) + 1, record_id,
                     terminals=tuple(f"{converter_mrid(record.name, k)}_T1" for k in CONVERTERS))

    limit_columns = [Column("mRID"), Column("OperationalLimitSet"), Column("OperationalLimitType")]
    statements = dc.tables(untranscribed_names(FIELDS)) + [
        Table("VsConverter",
              [Column("mRID"), Column("name"), Column("bus"), Column("inService"), Column("pPccControl"),
               Column("targetUdc", "kV"), Column("targetPpcc", "MW"), Column("qPccControl"),
               Column("targetUpcc", "kV"), Column("targetPowerFactorPcc"), Column("idleLoss", "kW"),
               Column("switchingLoss", "kW/A"), Column("qShare"), Column("PccTerminal"), Column("BaseVoltage"),
               Column("EquipmentContainer")],
              converter_rows, comment="targetPpcc = -DCSET (load sign); targetUpcc = ACSET x BASKV(VSREG or IBUS)"),
        dc.converter_terminal_table(),
    ]
    if curve_rows:
        statements += [
            Table("VsCapabilityCurve",
                  [Column("mRID"), Column("name"), Column("VsConverter"),
                   Column("curveStyle", default="constantYValue"), Column("xMultiplier", default="M"),
                   Column("xUnit", default="W"), Column("y1Multiplier", default="M"), Column("y1Unit", default="VAr"),
                   Column("y2Multiplier", default="M"), Column("y2Unit", default="VAr")],
                  curve_rows, comment="MODE 1: MINQ..MAXQ at every P (one point, constantYValue)"),
            Table("CurveData", [Column("identifier"), Column("Curve"), Column("xvalue"), Column("y1value"),
                                Column("y2value")], point_rows, comment="x = P (MW), y1 = MINQ, y2 = MAXQ (MVAr)"),
        ]
    if set_rows:
        statements.append(Table("OperationalLimitSet", [Column("mRID"), Column("Terminal")], set_rows,
                                comment="converter ratings SMAX, IMAX (0 is unlimited, no limit)"))
    if power_rows:
        statements.append(Table("ApparentPowerLimit", limit_columns + [Column("normalValue", "MVA")], power_rows))
    if current_rows:
        statements.append(Table("CurrentLimit", limit_columns + [Column("normalValue", "A")], current_rows))
    statements += ties.tables("the TYPE 1 converter is the home end")
    return Document(name="vsc_dc", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(records)))
