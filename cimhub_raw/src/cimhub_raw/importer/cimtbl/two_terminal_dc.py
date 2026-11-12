"""RAW Two-terminal DC line -> ``two_terminal_dc.cimtbl``: a ``DCLine`` holding a ``DCLineSegment`` between two
``DCTopologicalNode``s (P2-1), and per converter (rectifier, inverter) a ``CsConverter`` behind its converter
transformer: a 2-winding ``PowerTransformer`` from the AC bus to an internal valve-side ``TopologicalNode``, with a
``RatioTapChanger`` from TAP (P2-4, P2-5; the core shape ``behind_transformer.cimtbl``, plan C8). A tie (converters
in two AREAs) gets its ``TieFlow``s on the metered converter's transformer terminal at the AC bus (R5).

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#two-terminal-dc-line-decision-p2-4``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, Row, Table
from cimtopology.core.voltage import base_voltage_mrid

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, fill_defaults, lookup, mrid, untranscribed_names
from cimhub_raw.importer.cimtbl.area_interchange import control_area_numbers
from cimhub_raw.importer.cimtbl.dc_topology import DCRows
from cimhub_raw.importer.cimtbl.derived import VALVES_PER_BRIDGE, converter_tap, converter_transformer_ohms
from cimhub_raw.importer.cimtbl.records import listed_off_default, raw_defaults
from cimhub_raw.importer.cimtbl.tie_flow import TieFlowRows

NATIVE_CLASS = schema.TwoTerminalDCRecord
PREFIX = "dc2_"  # requested from the cimtbl-translate table owners (plan C3)
#: converter end -> (slot suffix, operatingMode); the rectifier is converter 1 (node n1)
ENDS = (("r", "rectifier"), ("i", "inverter"))

#: MDC -> the rectifier's pPccControl; 0 is blocked (every converter out of service)
RECTIFIER_CONTROL = {0: None, 1: "activePower", 2: "dcCurrent"}
POWER, CURRENT = 1, 2
#: METER -> the home (non-metered) converter, 1 rectifier or 2 inverter (R5)
HOME_END = {"R": 2, "I": 1}
#: line slots CIM cannot hold, listed on the DCLine row when not the default
LINE_LISTED = ("vcmod", "rcomp", "delti", "dcvmin", "cccitmx", "cccacc")

_LINE = "no CIM home (CIM 18 gap); listed on the DCLine row when not the default"


def _end_fields(e: str, which: str) -> dict[str, Field]:
    return {
        f"ip{e}": Field("structural", note=f"IP{e.upper()}: the {which}'s AC bus: end 1 of its converter transformer "
                                           f"{PREFIX}<NAME>_{e}_xf, its substation; the CsConverter {PREFIX}<NAME>_{e} "
                                           f"sits on the internal node {PREFIX}<NAME>_{e}_int"),
        f"nb{e}": Field("derived", note=f"NB{e.upper()}: numberOfValves = 6 x NB; the transformer's r, x divide by NB "
                                        "(converter_transformer_ohms)"),
        f"anmx{e}": Field("copied", (("CsConverter", "maxAlpha" if e == "r" else "maxGamma", "deg"),),
                          note=f"ANMX{e.upper()}"),
        f"anmn{e}": Field("copied", (("CsConverter", "minAlpha" if e == "r" else "minGamma", "deg"),),
                          note=f"ANMN{e.upper()}"),
        f"rc{e}": Field("derived", note=f"RC{e.upper()} (ohm per bridge, valve side): end 1 r = RC / (NB x TR^2) "
                                        "(converter_transformer_ohms)"),
        f"xc{e}": Field("derived", note=f"XC{e.upper()}: end 1 x, as RC"),
        f"ebas{e}": Field("copied", (("PowerTransformerEnd", "ratedU", "kV"),),
                          note=f"EBAS{e.upper()}: end 1 ratedU; end 2 ratedU = EBAS x TR (valve side), the internal "
                               "node's BaseVoltage"),
        f"tr{e}": Field("derived", note=f"TR{e.upper()}: end 2 ratedU = EBAS x TR; blank: 1.0 (defaulted)"),
        f"tap{e}": Field("derived", note=f"TAP{e.upper()}: the RatioTapChanger {PREFIX}<NAME>_{e}_xf_tap1 on end 1: "
                                         "step from TAP over the STP grid from TMN (converter_tap), ltcFlag true; "
                                         "PSS/E adjusts it to hold the firing angle in range, which no "
                                         "TapChangerControl mode says; blank: 1.0 (defaulted)"),
        f"tmx{e}": Field("derived", note=f"TMX{e.upper()}: highStep = the last whole STP step at or below TMX; a TMX "
                                         "off the grid is listed on the tap row; blank: 1.5 (defaulted)"),
        f"tmn{e}": Field("derived", note=f"TMN{e.upper()}: step 1; blank: 0.51 (defaulted)"),
        f"stp{e}": Field("derived", note=f"STP{e.upper()}: stepVoltageIncrement = STP in percent of EBAS; blank: "
                                         "0.00625 (defaulted)"),
        f"ic{e}": Field("untranscribed", note=f"IC{e.upper()}: the firing-angle measuring bus has no CIM home (CIM 18 "
                                              "gap); listed on the converter row when not 0"),
        f"if{e}": Field("structural", note=f"IF{e.upper()}: nonzero (an AC transformer as the converter "
                                           "transformer, COD +-4) raises"),
        f"it{e}": Field("structural", note=f"IT{e.upper()}: as IF{e.upper()}"),
        f"id{e}": Field("untranscribed", note=f"ID{e.upper()}: used only with IF{e.upper()} / IT{e.upper()}, "
                                              "which raise"),
        f"xcap{e}": Field("structural", note=f"XCAP{e.upper()}: nonzero (capacitor commutated) raises"),
        f"nd{e}": Field("untranscribed", note=f"ND{e.upper()}: a node of IC{e.upper()}, as IC{e.upper()}"),
    }


FIELDS = {
    "name": Field("structural", note=f"NAME: the key; DCLine {PREFIX}<NAME>, its segment, nodes, converters and "
                                     "their transformers"),
    "mdc": Field("mapped", note="MDC: 0 blocked (inService false on the segment and both converters), 1 the "
                                "rectifier's pPccControl activePower, 2 dcCurrent; blank: 0 (defaulted)"),
    "rdc": Field("copied", (("DCLineSegment", "resistance", "ohm"),), note="RDC; 0 is still a segment"),
    "setvl": Field("derived", note="SETVL: MDC 1 targetPpcc (MW, load sign as given): > 0 on the rectifier, < 0 on "
                                   "the inverter; MDC 2 the rectifier's targetIdc (A); MDC 0 listed (its unit "
                                   "depends on the MDC it was blocked from)"),
    "vschd": Field("copied", (("CsConverter", "targetUdc", "kV"),),
                   note="VSCHD: the inverter's targetUdc, pPccControl dcVoltage"),
    "vcmod": Field("untranscribed", note=f"VCMOD: {_LINE}"),
    "rcomp": Field("untranscribed", note=f"RCOMP: {_LINE} (0 puts the compounding point at the inverter)"),
    "delti": Field("untranscribed", note=f"DELTI: {_LINE}"),
    "meter": Field("structural", note="METER: on a tie, the metered converter (R rectifier, I inverter); the other "
                                      "is the home end (R5); blank: I (defaulted)"),
    "dcvmin": Field("untranscribed", note=f"DCVMIN: {_LINE}"),
    "cccitmx": Field("untranscribed", note=f"CCCITMX: {_LINE}"),
    "cccacc": Field("untranscribed", note=f"CCCACC: {_LINE}"),
    **_end_fields("r", "rectifier"),
    **_end_fields("i", "inverter"),
}

_PROVENANCE = """PSS/E RAW Two-terminal DC line -> DCLine (DCLineSegment, DCTopologicalNodes) + a CsConverter per converter
behind its converter transformer (PowerTransformer, internal TopologicalNode, RatioTapChanger); TieFlows of ties.
Source table: Two-terminal DC line (records: {count})
Mapping: cimhub_raw/docs/CIMTBL_MAPPING.md#two-terminal-dc-line-decision-p2-4"""


def _end(record, slot: str, e: str):
    return getattr(record, f"{slot}{e}")


def _valve_kv(record, e: str) -> float:
    return _end(record, "ebas", e) * _end(record, "tr", e)


def valve_kv(native) -> list[float]:
    """The valve-side kV (EBAS x TR) of every converter: its internal node's BaseVoltage, written by the master."""
    defaults = raw_defaults(NATIVE_CLASS)
    return [_valve_kv(fill_defaults(FIELDS, record, defaults)[0], e)
            for record in native.list_by_class(NATIVE_CLASS) for e, _ in ENDS]


def converter_mrid(name: str, e: str) -> str:
    return f"{mrid(PREFIX, name)}_{e}"


def _check_end(record, e: str, base_kv_of: dict[int, float], record_id: str) -> None:
    which = dict(ENDS)[e]
    if _end(record, "ip", e) not in base_kv_of:
        raise ValueError(f"{record_id}: {which} IP{e.upper()} {_end(record, 'ip', e)} is no bus")
    if _end(record, "if", e) or _end(record, "it", e):
        raise NotImplementedError(f"{record_id}: IF{e.upper()} / IT{e.upper()} name an AC transformer as the {which} "
                                  "transformer (COD +-4; no case has one yet)")
    if _end(record, "xcap", e):
        raise NotImplementedError(f"{record_id}: XCAP{e.upper()} {_end(record, 'xcap', e)}, capacitor commutated (no "
                                  "case has one yet)")
    if _end(record, "nb", e) < 1:
        raise ValueError(f"{record_id}: NB{e.upper()} {_end(record, 'nb', e)} bridges")
    if _end(record, "ebas", e) <= 0 or _end(record, "tr", e) <= 0:
        raise ValueError(f"{record_id}: EBAS{e.upper()} x TR{e.upper()} = {_end(record, 'ebas', e)} x "
                         f"{_end(record, 'tr', e)} gives no valve-side voltage")


def map_two_terminal_dc(native, substations_by_bus: dict[int, str], base_kv_of: dict[int, float],
                        bus_area: dict[int, int]) -> Document:
    records = sorted(native.list_by_class(NATIVE_CLASS), key=lambda record: record.name)
    if not records:
        return Document(name="two_terminal_dc", statements=[], profile=CIM_PROFILE)
    defaults = raw_defaults(NATIVE_CLASS)
    dc = DCRows()
    ties = TieFlowRows(bus_area, control_area_numbers(native))
    node_rows, transformer_rows, end_rows, tap_rows, converter_rows = [], [], [], [], []
    for record_in in records:
        record, defaulted = fill_defaults(FIELDS, record_in, defaults)
        record_id = f"two-terminal DC line {record.name}"
        rectifier_control = lookup(RECTIFIER_CONTROL, record.mdc, slot="mdc", record_id=record_id)
        in_service = record.mdc != 0
        listed = listed_off_default(record, LINE_LISTED, defaults)
        if not in_service:
            setvl = f"setvl={cell(record.setvl)}"
            listed = f"{listed}, {setvl}" if listed else f"untranscribed: {setvl}"
        line = mrid(PREFIX, record.name)
        nodes = dc.add_line(line, record.name, record.rdc, in_service,
                            comment="; ".join(note for note in (defaulted, listed) if note) or None)
        for (e, mode), dc_node in zip(ENDS, nodes):
            _check_end(record, e, base_kv_of, record_id)
            bus, bridges, ratio, ebas = (_end(record, slot, e) for slot in ("ip", "nb", "tr", "ebas"))
            converter = converter_mrid(record.name, e)
            transformer, internal = f"{converter}_xf", f"{converter}_int"
            valve_kv_e, container = _valve_kv(record, e), substations_by_bus[bus]
            node_rows.append(Row([internal, f"{record.name}_{e} valve side", base_voltage_mrid(valve_kv_e),
                                  container]))
            transformer_rows.append(Row([transformer, f"{record.name}_{e}", "true", container]))
            end_rows += [
                Row([f"{transformer}_1", f"{record.name}_{e}_1", str(bus), "1", cell(ebas),
                     cell(converter_transformer_ohms(_end(record, "rc", e), bridges, ratio)),
                     cell(converter_transformer_ohms(_end(record, "xc", e), bridges, ratio)),
                     base_voltage_mrid(base_kv_of[bus]), transformer]),
                Row([f"{transformer}_2", f"{record.name}_{e}_2", internal, "2", cell(valve_kv_e), None, None,
                     base_voltage_mrid(valve_kv_e), transformer]),
            ]
            tap, top = converter_tap(_end(record, "tap", e), _end(record, "tmx", e), _end(record, "tmn", e),
                                     _end(record, "stp", e), ebas_kv=ebas, record_id=record_id)
            off_grid = None if abs(top - _end(record, "tmx", e)) < 1e-9 else \
                f"untranscribed: tmx{e}={cell(_end(record, 'tmx', e))} (the STP grid tops out at {cell(top)})"
            tap_rows.append(Row([f"{transformer}_tap1", f"{record.name}_{e}_1", str(tap.low_step),
                                 str(tap.high_step), str(tap.neutral_step), cell(tap.neutral_kv),
                                 cell(tap.increment_percent), cell(tap.step), "true", "true", f"{transformer}_1"],
                                comment=off_grid))
            rectifier = e == "r"
            power = record.setvl if record.mdc == POWER and (record.setvl >= 0) == rectifier else None
            converter_rows.append(Row([
                converter, f"{record.name}_{e}", internal, cell(in_service), mode,
                str(VALVES_PER_BRIDGE * bridges),
                cell(_end(record, "anmx", e) if rectifier else None), cell(_end(record, "anmn", e) if rectifier else None),
                cell(None if rectifier else _end(record, "anmx", e)), cell(None if rectifier else _end(record, "anmn", e)),
                rectifier_control if rectifier else "dcVoltage", cell(power),
                cell(record.setvl if rectifier and record.mdc == CURRENT else None),
                cell(None if rectifier else record.vschd), base_voltage_mrid(valve_kv_e), container],
                comment=listed_off_default(record, (f"ic{e}", f"nd{e}"), defaults)))
            dc.add_converter(converter, dc_node)
        buses = tuple(_end(record, "ip", e) for e, _ in ENDS)
        if ties.is_tie(buses):
            ties.add(line, record.name, buses, lookup(HOME_END, record.meter, slot="meter", record_id=record_id),
                     record_id, terminals=tuple(f"{converter_mrid(record.name, e)}_xf_T1" for e, _ in ENDS))

    statements = dc.tables(untranscribed_names(FIELDS)) + [
        Table("TopologicalNode", [Column("mRID"), Column("name"), Column("BaseVoltage"),
                                  Column("ConnectivityNodeContainer")], node_rows,
              comment="each converter's internal valve-side node (behind_transformer, plan C8): no RAW bus"),
        Table("PowerTransformer", [Column("mRID"), Column("name"), Column("inService"), Column("EquipmentContainer")],
              transformer_rows, comment="each converter's transformer: one equivalent of its NB bridges' (P2-5)"),
        Table("PowerTransformerEnd", [Column("mRID"), Column("name"), Column("bus"), Column("endNumber"),
                                      Column("ratedU", "kV"), Column("r", "ohm"), Column("x", "ohm"),
                                      Column("BaseVoltage"), Column("PowerTransformer")], end_rows,
              comment="end 1 at the AC bus: ratedU = EBAS, r = RC / (NB x TR^2), x = XC / (NB x TR^2); end 2 at the "
                      "internal node: ratedU = EBAS x TR"),
        Table("RatioTapChanger", [Column("mRID"), Column("name"), Column("lowStep"), Column("highStep"),
                                  Column("neutralStep"), Column("neutralU", "kV"), Column("stepVoltageIncrement"),
                                  Column("step"), Column("ltcFlag"), Column("controlEnabled"),
                                  Column("TransformerEnd")], tap_rows,
              comment="TAP on the STP grid from TMN (converter_tap); no TapChangerControl: PSS/E holds the firing "
                      "angle in range, which no CIM mode says"),
        Table("CsConverter", [Column("mRID"), Column("name"), Column("bus"), Column("inService"),
                              Column("operatingMode"), Column("numberOfValves"), Column("maxAlpha", "deg"),
                              Column("minAlpha", "deg"), Column("maxGamma", "deg"), Column("minGamma", "deg"),
                              Column("pPccControl"), Column("targetPpcc", "MW"), Column("targetIdc", "A"),
                              Column("targetUdc", "kV"), Column("BaseVoltage"), Column("EquipmentContainer")],
              converter_rows, comment="on its internal node; numberOfValves = 6 x NB; the rectifier holds MDC's "
                                      "order (targetPpcc on the inverter when SETVL < 0), the inverter VSCHD"),
        dc.converter_terminal_table(),
    ]
    statements += ties.tables("METER")
    return Document(name="two_terminal_dc", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(records)))
