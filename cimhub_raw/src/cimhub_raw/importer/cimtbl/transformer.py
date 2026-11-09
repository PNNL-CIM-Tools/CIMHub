"""RAW Transformer -> ``transformer.cimtbl``: a ``PowerTransformer`` with a ``PowerTransformerEnd`` per winding (a
fixed phase shift as ``phaseShift``), a 3-winding unit's Z12/Z23/Z31 as ``TransformerMeshImpedance`` rows (Delta
model), each tapped winding's ``TapChangerControl`` with its ``RatioTapChanger`` (stepped or fixed) or, for a phase
shifter, its ``PhaseTapChangerLinear``, a fixed ``RatioTapChanger`` on an off-nominal untapped winding, and an
``ImpedanceTapChangerTabular`` on each winding with an impedance correction table.

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#transformer-r4`` and
``#transformer-the-forms-r4-raised-on-r4b``.
"""

from __future__ import annotations

import math

from cimtables.document import Column, Document, Row, Table
from cimtopology.core.voltage import base_voltage_mrid

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, lookup, mrid, schema_defaults, untranscribed_names
from cimhub_raw.importer.cimtbl.derived import (
    cim_angle,
    magnetizing_siemens,
    ohms_from_per_unit,
    phase_tap,
    ratio_tap,
    transformer_ohms,
    usable_tap_range,
    vars_from_mvar,
    volts_from_per_unit,
    watts_from_mw,
    winding_unit_kv,
)
from cimhub_raw.importer.cimtbl.impedance_correction import TableUser, table_mrid
from cimhub_raw.importer.cimtbl.area_interchange import control_area_numbers
from cimhub_raw.importer.cimtbl.ratings import RATING_SETS, RatingRows
from cimhub_raw.importer.cimtbl.tie_flow import TieFlowRows, off_tie_note
from cimhub_raw.importer.cimtbl.records import fill_keyed_defaults, raw_defaults
from cimhub_raw.importer.node_breaker import NodeBreaker

NATIVE_CLASS = schema.TransformerRecord
PREFIX = "xf_"  # requested from the cimtbl-translate table owners (plan C3)
#: the slots RAW writes only for a 3-winding unit (K != 0): the schema's ``serialize_if``
THREE_WINDING_SLOTS = frozenset(schema_defaults(NATIVE_CLASS, "serialize_if"))
#: the Delta model's pairs: (From end, To end, RAW's pair suffix) (user, 2026-11-08)
MESH_PAIRS = ((1, 2, "1_2"), (2, 3, "2_3"), (1, 3, "3_1"))

#: STAT -> inService; 2, 3 and 4 (one winding of a 3-winding unit out) keep the unit in service (R4b-6)
IN_SERVICE = {1: True, 0: False, 2: True, 3: True, 4: True}
#: STAT -> the winding whose terminal is disconnected (R4b-6)
OUT_WINDING = {2: 2, 3: 3, 4: 1}
#: |COD| -> TapChangerControl mode
CONTROL_MODE = {0: "voltage", 1: "voltage", 2: "reactivePower", 3: "activePower"}
PHASE_SHIFTER = 3
UNMAPPED_COD = {5: "asymmetric phase shift: no case has one yet",
                4: "DC line control: phase 2 (two-terminal DC)"}
#: the schema's raw_default_rules for RMA/RMI (CW 1 or 3, |COD| not 3 or 5) and VMA/VMI (|COD| 1; COD 0 too, R4)
TAP_RANGE_DEFAULT = (1.1, 0.9)
BAND_DEFAULT = (1.1, 0.9)

_OWNER = "ownership is an asset concept (CIM 18 gap)"
_RATING = ("RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) "
           "xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; "
           "blank: 0 (defaulted)")


def _winding_fields(k: int) -> dict[str, Field]:
    """The fields of winding k's data line (line 3 + k)."""
    tapped = "winding 1, or any winding of a 3-winding unit"
    return {
        f"windv{k}": Field("derived", note=f"WINDV{k}: the ratio, in CW units: RatioTapChanger step (ratio_tap) on "
                                           f"{tapped}; a fixed RatioTapChanger (neutralU = WINDV in kV, R4b-4) on an "
                                           "off-nominal winding 2 of a 2-winding unit, a COD 0 winding without a "
                                           "usable RMI..RMA, or an off-nominal phase shifter winding; blank: 1.0, or "
                                           "the bus's BASKV for CW 2 (defaulted)"),
        f"nomv{k}": Field("derived", note=f"NOMV{k} (kV): PowerTransformerEnd ratedU, or the bus's BASKV when 0 (RAW-6); "
                                          "blank: 0 (defaulted)"),
        f"ang{k}": Field("derived", note=f"ANG{k} (deg): phaseShift = cim_angle(ANG) on end {k} (R4b-2), or, with "
                                         f"|COD{k}| 3, the PhaseTapChangerLinear's step (phase_tap, R4b-3); blank: 0 "
                                         "(defaulted)"),
        **{f"rate{k}_{n}": Field("structural", note=_RATING) for n in range(1, RATING_SETS + 1)},
        f"cod{k}": Field("mapped", note=f"COD{k}: 0 ltcFlag false, control disabled; +-1 voltage, +-2 reactivePower, "
                                        "+-3 activePower (a PhaseTapChangerLinear, R4b-3), ltcFlag true, "
                                        "controlEnabled and enabled = (COD > 0); +-5 raises (no case), +-4 raises "
                                        "(phase 2); blank: 0 (defaulted)"),
        f"cont{k}": Field("structural", note=f"CONT{k}: the TapChangerControl Terminal bb_<|CONT|>_T1, or the winding's "
                                             "own xf_<key>_T<k> when 0 (user 2026-11-08; COD +-1 too, R4b-7) and for "
                                             "COD +-3; a negative CONT's sign is listed on the control row (R4b-8); "
                                             "blank: 0 (defaulted)"),
        f"rma{k}": Field("derived", note=f"RMA{k}: highStep's ratio, in CW units (ratio_tap: steps 1..NTP from RMI to "
                                         "RMA, stepVoltageIncrement), or angle (deg) for COD +-3 (phase_tap); listed "
                                         "on the row where CIM cannot hold it (R4b-3, -4, -5); blank: 1.1 for CW 1 or "
                                         "3 and |COD| not 3 (defaulted), else raises"),
        f"rmi{k}": Field("derived", note=f"RMI{k}: lowStep's ratio or angle; as RMA{k}; blank: 0.9 (defaulted) as "
                                         f"RMA{k}"),
        f"vma{k}": Field("derived", note=f"VMA{k}: targetValue = (VMA + VMI) / 2 and targetDeadband = VMA - VMI, in V "
                                         "x the regulated bus's BASKV (volts_from_per_unit) for voltage, in VAr from "
                                         "Mvar (vars_from_mvar) for reactivePower, in W from MW (watts_from_mw) for "
                                         "activePower; blank: 1.1 for COD 0 or +-1 (defaulted), else raises"),
        f"vmi{k}": Field("derived", note=f"VMI{k}: as VMA{k}; blank: 0.9 for COD 0 or +-1 (defaulted)"),
        f"ntp{k}": Field("derived", note=f"NTP{k}: highStep = NTP, lowStep = 1 (the steps of a phase shifter too); "
                                         "below 2 raises; blank: 33 (defaulted)"),
        f"tab{k}": Field("structural", note=f"TAB{k}: an ImpedanceTapChangerTabular xf_<key>_ztab<k> on end {k}, "
                                            "naming table ict_<TAB> (R4b-10); a 3-winding unit's raises; blank: 0 "
                                            "(defaulted)"),
        f"cr{k}": Field("derived", note=f"CR{k} (pu on SBASE): lineDropR = CR x BASKV^2 / SBASE ohm "
                                        "(ohms_from_per_unit, the regulated bus's BASKV), lineDropCompensation true "
                                        "(R4b-9); nonzero off COD +-1 raises; blank: 0 (defaulted)"),
        f"cx{k}": Field("derived", note=f"CX{k}: lineDropX, as CR{k}"),
        f"cnxa{k}": Field("structural", note=f"CNXA{k}: only COD +-5 uses it; nonzero raises; blank: 0 (defaulted)"),
        f"nod{k}": Field("structural", note=f"NOD{k}: a node of bus CONT{k}; nonzero: the TapChangerControl Terminal "
                                           f"is that node's busbar bb_s<IS>_n<NOD>_T1 (R6, RAW-11); with CONT{k} 0 "
                                           "it raises; blank: 0 (defaulted)"),
    }


def _pair_fields(pair: str) -> dict[str, Field]:
    i, j = pair.split("_")
    return {
        f"r{pair}": Field("derived", note=f"R{i}-{j}: with X{i}-{j}, r (ohm) seen from winding {min(i, j)} "
                                          "(transformer_ohms, by CZ); 2-winding: on end 1, 3-winding: on the mesh "
                                          "row; blank: 0 (defaulted)"),
        f"x{pair}": Field("derived", note=f"X{i}-{j}: as R{i}-{j}, x (ohm)"),
        f"sbase{pair}": Field("derived", note=f"SBASE{i}-{j} (MVA): the pair's base for CZ 2 and 3 (and CM 2 on "
                                              "1-2); a 2-winding unit's SBASE1-2 is also both ends' ratedS; a "
                                              "3-winding unit's pair bases have no end to go on; blank: SBASE "
                                              "(defaulted)"),
    }


FIELDS = {
    "i": Field("structural", note="I: winding 1's bus (end 1's bus and BaseVoltage); the transformer's "
                                  "EquipmentContainer is its substation"),
    "j": Field("structural", note="J: winding 2's bus"),
    "k": Field("structural", note="K: winding 3's bus; 0 is a 2-winding unit; blank: 0 (defaulted)"),
    "circuit": Field("structural", note="CKT: with I, J and K the key, mRID xf_<I>_<J>_<K>_<CKT>; blank: 1 "
                                        "(defaulted)"),
    "cw": Field("mapped", note="CW: the unit of WINDV, RMA and RMI (winding_unit_kv); CIM keeps kV, so the exporter "
                               "writes CW 1; blank: 1 (defaulted)"),
    "cz": Field("mapped", note="CZ: the code of R/X (transformer_ohms); CIM keeps ohm, so the exporter writes CZ 1; "
                               "blank: 1 (defaulted)"),
    "cm": Field("mapped", note="CM: the code of MAG1/MAG2 (magnetizing_siemens); the exporter writes CM 1; blank: 1 "
                               "(defaulted)"),
    "mag1": Field("derived", note="MAG1: end 1's g (S) (magnetizing_siemens, by CM); blank: 0 (defaulted)"),
    "mag2": Field("derived", note="MAG2: end 1's b (S), negative inductive; blank: 0 (defaulted)"),
    "nmetr": Field("structural", note="NMETR: the non-metered (home) winding; on a tie (windings' buses in two or "
                                      "more AREAs) each other winding outside the home area carries both TieFlows "
                                      "on its terminal (R5); a code outside 1..windings on a tie raises; elsewhere "
                                      "untranscribed, as branch MET (CIM 18 gap, RAW-22); blank: 2 (defaulted)"),
    "name": Field("copied", (("PowerTransformer", "name", None),), note="NAME; blank: the key I_J_K_CKT"),
    "status": Field("mapped", note="STAT: inService = (STAT != 0); 2, 3 and 4 (a 3-winding unit's winding 2, 3 or "
                                   "1 out): that winding's terminal connected = false, an Update row (R4b-6); blank: 1 "
                                   "(defaulted)"),
    **{f"o{n}": Field("untranscribed", note=_OWNER) for n in range(1, 5)},
    **{f"f{n}": Field("untranscribed", note=_OWNER) for n in range(1, 5)},
    "vecgrp": Field("copied", (("PowerTransformer", "vectorGroup", None),), note="VECGRP; blank: none"),
    "zcod": Field("untranscribed", note="ZCOD: zero-sequence data is in the sequence file, not the RAW"),
    **_pair_fields("1_2"),
    **_pair_fields("2_3"),
    **_pair_fields("3_1"),
    "vmstar": Field("untranscribed", note="VMSTAR: the solved voltage of the star point, which the Delta model omits"),
    "anstar": Field("untranscribed", note="ANSTAR: as VMSTAR"),
    **_winding_fields(1),
    **_winding_fields(2),
    **_winding_fields(3),
}

_PROVENANCE = """PSS/E RAW Transformer -> PowerTransformer + PowerTransformerEnd per winding; TransformerMeshImpedance
(3-winding, Delta model); TapChangerControl + RatioTapChanger or PhaseTapChangerLinear per tapped winding; fixed
RatioTapChangers; ImpedanceTapChangerTabular per corrected winding; ratings per winding.
Source table: Transformer (records: {count})
Mapping: cimhub_raw/docs/CIMTBL_MAPPING.md#transformer-r4"""


def _windings(record) -> int:
    return 3 if record.k else 2


def _tapped_windings(record) -> range:
    """The windings with COD data: winding 1 of a 2-winding unit, every winding of a 3-winding one."""
    return range(1, _windings(record) + 1) if record.k else range(1, 2)


def _winding(record, slot: str, winding: int):
    return getattr(record, f"{slot}{winding}")


def _record_defaults(record, static: dict, base_mva: float, base_kv_of: dict[int, float]) -> dict:
    """The static ``raw_default``s plus the schema's rules (SBASEij, WINDV by CW, RMA/RMI, VMA/VMI by COD), less
    the 3-winding slots of a 2-winding unit (RAW does not write them)."""
    cw = record.cw if record.cw is not None else static["cw"]
    rules = {f"sbase{pair}": base_mva for _, _, pair in MESH_PAIRS}
    for winding, bus in enumerate(_buses(record), start=1):
        rules[f"windv{winding}"] = base_kv_of[bus] if cw == 2 else 1.0
    for winding in _tapped_windings(record):
        code = _winding(record, "cod", winding)
        code = abs(code if code is not None else static[f"cod{winding}"])
        if cw in (1, 3) and code not in (PHASE_SHIFTER, 5):
            rules[f"rma{winding}"], rules[f"rmi{winding}"] = TAP_RANGE_DEFAULT
        if code in (0, 1):
            rules[f"vma{winding}"], rules[f"vmi{winding}"] = BAND_DEFAULT
    defaults = {**static, **rules}
    if not record.k:
        defaults = {slot: value for slot, value in defaults.items() if slot not in THREE_WINDING_SLOTS}
    return defaults


def _buses(record) -> tuple[int, ...]:
    return (record.i, record.j, record.k) if record.k else (record.i, record.j)


def _regulated_node(record, winding: int, record_id: str) -> tuple[int, int]:
    """``(|CONTk|, NODk)``, blanks as 0; a node of no regulated bus (NODk with CONTk 0) raises. A negative CONT's
    sign is listed on its control row (R4b-8)."""
    cont, node = abs(_winding(record, "cont", winding) or 0), _winding(record, "nod", winding) or 0
    if node and not cont:
        raise ValueError(f"{record_id}: NOD{winding} {node} names a node, but CONT{winding} is 0 (no regulated bus)")
    return cont, node


def regulated_nodes(native) -> list[tuple[int, int, str]]:
    """``(CONTk, NODk, record id)`` of every winding control that regulates a node (R6)."""
    nodes = []
    for record in native.list_by_class(NATIVE_CLASS):
        for winding in _tapped_windings(record):
            cont, node = _regulated_node(record, winding, f"transformer {record.ID}")
            if node:
                nodes.append((cont, node, f"transformer {record.ID} winding {winding}"))
    return nodes


def _check_record(record, record_id: str) -> None:
    """The forms R4b does not map raise."""
    if record.status in OUT_WINDING and not record.k:
        raise ValueError(f"{record_id}: STAT {record.status} (one winding out) on a 2-winding unit")
    for winding in _tapped_windings(record):
        code = _winding(record, "cod", winding)
        if abs(code) in UNMAPPED_COD:
            raise NotImplementedError(f"{record_id}: COD{winding} {code} ({UNMAPPED_COD[abs(code)]})")
        if _winding(record, "cnxa", winding):
            raise NotImplementedError(f"{record_id}: CNXA{winding} = {_winding(record, 'cnxa', winding)}, an "
                                      "asymmetric phase shift's angle (COD 5)")
        if _winding(record, "tab", winding) and record.k:
            raise NotImplementedError(f"{record_id}: TAB{winding} = {_winding(record, 'tab', winding)} on a 3-winding "
                                      "unit (PSS/E applies it by ZCOD to a T-model or bus-to-bus impedance; no case "
                                      "has one yet)")
        if (_winding(record, "cr", winding) or _winding(record, "cx", winding)) and abs(code) != 1:
            raise ValueError(f"{record_id}: CR{winding}/CX{winding} (load-drop compensation) on COD{winding} {code}, "
                             "not a voltage control")
        for slot in ("rma", "rmi", "vma", "vmi"):
            if _winding(record, slot, winding) is None:
                raise ValueError(f"{record_id}: {slot.upper()}{winding} is blank and has no default (CW {record.cw}, "
                                 f"COD{winding} {code})")


def table_users(native, base_kv_of: dict[int, float], base_mva: float) -> dict[int, list[TableUser]]:
    """Impedance correction table -> the windings that use it (TABk), with their bus's BASKV and end's ratedU."""
    static = raw_defaults(NATIVE_CLASS)
    users: dict[int, list[TableUser]] = {}
    for record in native.list_by_class(NATIVE_CLASS):
        transformer, _ = fill_keyed_defaults(FIELDS, record, _record_defaults(record, static, base_mva, base_kv_of))
        buses = _buses(transformer)
        for winding in _tapped_windings(transformer):
            table = _winding(transformer, "tab", winding)
            if table:
                base_kv = base_kv_of[buses[winding - 1]]
                users.setdefault(table, []).append(TableUser(
                    base_kv, _winding(transformer, "nomv", winding) or base_kv,
                    f"transformer {transformer.ID} winding {winding}"))
    return users


def _fixed_tap(container: str, key: str, winding: int, kv: float, control: str | None, comment: str | None) -> Row:
    """A fixed ``RatioTapChanger`` (R4b-4): one step, its ratio neutralU / ratedU."""
    return Row([f"{container}_tap{winding}", f"{key}_{winding}", "1", "1", "1", cell(kv), None, "1", "false",
                "false", control, f"{container}_{winding}"], comment=comment)


def _listed(record, winding: int, slots: tuple[str, ...], why: str) -> str:
    """``untranscribed: rma1=..., rmi1=... (why)``: winding values CIM cannot hold, listed on their row."""
    values = ", ".join(f"{slot}{winding}={cell(_winding(record, slot, winding))}" for slot in slots)
    return f"untranscribed: {values} ({why})"


def _is_nominal(ratio_kv: float, nominal_kv: float) -> bool:
    return math.isclose(ratio_kv, nominal_kv)


def map_transformer(native, substations_by_bus: dict[int, str], base_kv_of: dict[int, float],
                    bus_area: dict[int, int], node_breaker: NodeBreaker, base_mva: float,
                    ratings_in_current: bool) -> Document:
    records = sorted(native.list_by_class(NATIVE_CLASS),
                     key=lambda record: (record.i, record.j, record.k or 0, str(record.circuit)))
    if not records:
        return Document(name="transformer", statements=[], profile=CIM_PROFILE)
    static = raw_defaults(NATIVE_CLASS)
    tables = {table.table_number for table in native.list_by_class(schema.ImpedanceCorrectionRecord)}
    ratings = RatingRows(ratings_in_current, "XFRRAT", "one set per rated winding, on its terminal xf_<key>_T<k>")
    ties = TieFlowRows(bus_area, control_area_numbers(native))
    transformer_rows, end_rows, mesh_rows, control_rows, tap_rows = [], [], [], [], []
    phase_rows, tabular_rows, disconnected_rows = [], [], []
    for record in records:
        record_id = f"transformer {record.ID}"
        transformer, defaulted = fill_keyed_defaults(FIELDS, record,
                                                     _record_defaults(record, static, base_mva, base_kv_of))
        _check_record(transformer, record_id)
        key = transformer.ID
        container = mrid(PREFIX, key)
        buses = _buses(transformer)
        kv = [base_kv_of[bus] for bus in buses]
        nominal = [_winding(transformer, "nomv", winding) or kv[winding - 1] for winding in range(1, len(buses) + 1)]
        unit_kv = [winding_unit_kv(transformer.cw, kv[winding - 1], nominal[winding - 1], record_id)
                   for winding in range(1, len(buses) + 1)]
        ends = [f"{container}_{winding}" for winding in range(1, len(buses) + 1)]
        transformer_rows.append(Row([
            container, transformer.name or key, transformer.vecgrp or None,
            cell(lookup(IN_SERVICE, transformer.status, slot="status", record_id=record_id)),
            substations_by_bus[transformer.i]], comment=defaulted))
        if transformer.status in OUT_WINDING:
            disconnected_rows.append(Row([f"{container}_T{OUT_WINDING[transformer.status]}", "false"],
                                         comment=f"STAT {transformer.status}"))

        g, b = magnetizing_siemens(transformer.mag1, transformer.mag2, transformer.cm, base_kv=kv[0],
                                   nominal_kv=nominal[0], pair_mva=transformer.sbase1_2, system_mva=base_mva,
                                   record_id=record_id)
        if transformer.k:
            impedances = [(None, None, g, b)] + [(None, None, None, None)] * 2
            rated_mva = None
            for start, finish, pair in MESH_PAIRS:
                r, x = transformer_ohms(getattr(transformer, f"r{pair}"), getattr(transformer, f"x{pair}"),
                                        transformer.cz, base_kv=kv[start - 1], nominal_kv=nominal[start - 1],
                                        pair_mva=getattr(transformer, f"sbase{pair}"), system_mva=base_mva,
                                        record_id=record_id)
                mesh_rows.append(Row([f"{container}_mesh_{start}{finish}", f"{key}_{start}{finish}", ends[start - 1],
                                      ends[finish - 1], cell(r), cell(x)]))
        else:
            r, x = transformer_ohms(transformer.r1_2, transformer.x1_2, transformer.cz, base_kv=kv[0],
                                    nominal_kv=nominal[0], pair_mva=transformer.sbase1_2, system_mva=base_mva,
                                    record_id=record_id)
            impedances = [(r, x, g, b), (0.0, 0.0, 0.0, 0.0)]
            rated_mva = transformer.sbase1_2
            ratio_kv = transformer.windv2 * unit_kv[1]
            if not _is_nominal(ratio_kv, nominal[1]):
                tap_rows.append(_fixed_tap(container, key, 2, ratio_kv, None, "fixed: an off-nominal winding 2"))
        tapped = _tapped_windings(transformer)
        for winding, (bus, end, (r, x, g, b)) in enumerate(zip(buses, ends, impedances), start=1):
            shifter = winding in tapped and abs(_winding(transformer, "cod", winding)) == PHASE_SHIFTER
            angle = _winding(transformer, "ang", winding) if winding in tapped or transformer.k else None
            end_rows.append(Row([end, f"{key}_{winding}", str(bus), str(winding), cell(nominal[winding - 1]),
                                 cell(rated_mva), cell(r), cell(x), cell(g), cell(b),
                                 cell(cim_angle(angle)) if angle and not shifter else None,
                                 base_voltage_mrid(kv[winding - 1]), container]))
            if winding == 1 or transformer.k:
                ratings.add(end, [getattr(transformer, f"rate{winding}_{n}") for n in range(1, RATING_SETS + 1)],
                            kv[winding - 1], terminal=f"{container}_T{winding}")

        if ties.is_tie(buses):
            if transformer.nmetr not in range(1, len(buses) + 1):
                raise ValueError(f"{record_id}: NMETR {transformer.nmetr} names no winding of a {len(buses)}-winding "
                                 "tie")
            ties.add(container, key, buses, transformer.nmetr, record_id)

        for winding in tapped:
            code = _winding(transformer, "cod", winding)
            mode = lookup(CONTROL_MODE, abs(code), slot=f"cod{winding}", record_id=record_id)
            own_terminal = f"{container}_T{winding}"
            control = f"{container}_ctrl{winding}"
            notes = []
            if mode == "activePower":
                regulated, terminal = 0, own_terminal
            else:
                regulated, node = _regulated_node(transformer, winding, record_id)
                if regulated and regulated not in base_kv_of:
                    raise ValueError(f"{record_id}: CONT{winding} {regulated} is no bus")
                terminal = node_breaker.regulated_terminal(regulated, node, f"{record_id} winding {winding}") \
                    if regulated else own_terminal
                if _winding(transformer, "cont", winding) < 0:
                    notes.append(f"untranscribed: cont{winding}={_winding(transformer, 'cont', winding)} (bus "
                                 f"{regulated} taken as on winding 1's side)")
                elif not regulated and mode == "voltage" and code:
                    notes.append("CONT 0: regulates its own terminal")
            regulated_kv = base_kv_of[regulated or buses[winding - 1]]
            high, low = _winding(transformer, "vma", winding), _winding(transformer, "vmi", winding)
            if mode == "voltage":
                target, deadband = (volts_from_per_unit((high + low) / 2, regulated_kv),
                                    volts_from_per_unit(high - low, regulated_kv))
            elif mode == "reactivePower":
                target, deadband = vars_from_mvar((high + low) / 2), vars_from_mvar(high - low)
            else:
                target, deadband = watts_from_mw((high + low) / 2), watts_from_mw(high - low)
            line_drop = (_winding(transformer, "cr", winding), _winding(transformer, "cx", winding))
            drop = [None, None, None]
            if any(line_drop):
                drop = ["true", *(cell(ohms_from_per_unit(value, regulated_kv, base_mva)) for value in line_drop)]
            control_rows.append(Row([control, f"{key}_{winding}", mode, "true", cell(code > 0), cell(target),
                                     cell(deadband), terminal, *drop], comment="; ".join(notes) or None))

            windv, rma, rmi = (_winding(transformer, slot, winding) for slot in ("windv", "rma", "rmi"))
            ntp = _winding(transformer, "ntp", winding)
            ratio_kv = windv * unit_kv[winding - 1]
            if mode == "activePower":
                tap = phase_tap(_winding(transformer, "ang", winding), rma, rmi, ntp, record_id)
                phase_rows.append(Row([
                    f"{container}_ptap{winding}", f"{key}_{winding}", "1", str(ntp), str(tap.neutral_step),
                    cell(tap.increment_degrees), cell(tap.step), "true", cell(code > 0), control, ends[winding - 1]],
                    comment=_listed(transformer, winding, ("rma", "rmi"), f"0 deg lies "
                                    f"{cell(abs(tap.zero_offset_degrees))} deg off the step grid")
                    if not math.isclose(tap.zero_offset_degrees, 0.0, abs_tol=1e-9) else None))
                if not _is_nominal(ratio_kv, nominal[winding - 1]):
                    tap_rows.append(_fixed_tap(container, key, winding, ratio_kv, None,
                                               "fixed: a phase shifter's off-nominal ratio"))
            elif not code and not usable_tap_range(windv, rma, rmi):
                tap_rows.append(_fixed_tap(container, key, winding, ratio_kv, control, "fixed: " + _listed(
                    transformer, winding, ("rma", "rmi", "ntp"), "RMI..RMA holds no WINDV; unused at COD 0")))
            else:
                tap = ratio_tap(windv, rma, rmi, ntp, unit_kv=unit_kv[winding - 1], rated_kv=nominal[winding - 1],
                                record_id=record_id)
                extended = (tap.low_step, tap.high_step) != (1, ntp)
                tap_rows.append(Row([
                    f"{container}_tap{winding}", f"{key}_{winding}", str(tap.low_step), str(tap.high_step),
                    str(tap.neutral_step), cell(tap.neutral_kv), cell(tap.increment_percent), cell(tap.step),
                    cell(code != 0), cell(code > 0), control, ends[winding - 1]],
                    comment=_listed(transformer, winding, ("rma", "rmi"), "steps extended to the WINDV")
                    if extended else None))
            table = _winding(transformer, "tab", winding)
            if table:
                if table not in tables:
                    raise ValueError(f"{record_id}: TAB{winding} {table} names no impedance correction table")
                tabular_rows.append(Row([f"{container}_ztab{winding}", f"{key}_{winding}", ends[winding - 1],
                                         table_mrid(table)]))

    shifts = any(row.cells[10] is not None for row in end_rows)
    end_columns = [Column("mRID"), Column("name"), Column("bus"), Column("endNumber"), Column("ratedU", "kV"),
                   Column("ratedS", "MVA"), Column("r", "ohm"), Column("x", "ohm"), Column("g", "S"), Column("b", "S"),
                   Column("phaseShift", "deg"), Column("BaseVoltage"), Column("PowerTransformer")]
    if not shifts:
        end_columns.pop(10)
        end_rows = [Row(row.cells[:10] + row.cells[11:], comment=row.comment) for row in end_rows]
    end_comment = ("r, x, g, b on the end's ratedU (transformer_ohms, magnetizing_siemens): a 2-winding unit's all on "
                   "end 1, end 2 zero; a 3-winding unit's g, b on end 1, r, x on its mesh")
    if shifts:
        end_comment += "; phaseShift = cim_angle(ANGk), a fixed shift (R4b-2)"
    statements = [
        Table("PowerTransformer", [Column(name) for name in ("mRID", "name", "vectorGroup", "inService",
                                                             "EquipmentContainer")],
              transformer_rows, comment=off_tie_note(untranscribed_names(FIELDS), "NMETR")),
        Table("PowerTransformerEnd", end_columns, end_rows, comment=end_comment),
    ]
    if disconnected_rows:
        statements.append(Table("Terminal", [Column("mRID"), Column("connected")], disconnected_rows, update=True,
                                comment="one winding out of service (STAT 2, 3, 4; R4b-6)"))
    if mesh_rows:
        statements.append(Table("TransformerMeshImpedance",
                                [Column("mRID"), Column("name"), Column("FromTransformerEnd"),
                                 Column("ToTransformerEnd"), Column("r", "ohm"), Column("x", "ohm")],
                                mesh_rows, comment="3-winding Z12, Z23, Z31 (Delta model): r, x seen from the From "
                                                   "end"))
    control_columns = [Column(name) for name in ("mRID", "name", "mode", "discrete", "enabled", "targetValue",
                                                 "targetDeadband", "Terminal")]
    control_comment = ("targetValue and targetDeadband in V (voltage) or VAr (reactivePower); COD 0 keeps its "
                       "control, disabled")
    if phase_rows:
        control_comment += "; W (activePower, COD +-3)"
    if any(row.cells[8] for row in control_rows):
        control_columns += [Column("lineDropCompensation"), Column("lineDropR", "ohm"), Column("lineDropX", "ohm")]
        control_comment += "; lineDropR, lineDropX = CR, CX x BASKV^2 / SBASE (ohms_from_per_unit)"
    else:
        control_rows = [Row(row.cells[:8], comment=row.comment) for row in control_rows]
    statements.append(Table("TapChangerControl", control_columns, control_rows, comment=control_comment))
    statements.append(Table(
        "RatioTapChanger",
        [Column("mRID"), Column("name"), Column("lowStep"), Column("highStep"), Column("neutralStep"),
         Column("neutralU", "kV"), Column("stepVoltageIncrement"), Column("step"), Column("ltcFlag"),
         Column("controlEnabled"), Column("TapChangerControl"), Column("TransformerEnd")],
        tap_rows, comment="steps 1..NTP from RMI to RMA; neutralStep nearest ratio 1 at neutralU; "
                          "stepVoltageIncrement in percent of ratedU (ratio_tap)"
                          + ("; a fixed tap: one step at neutralU (R4b-4)" if any(
                              row.cells[2:5] == ["1", "1", "1"] for row in tap_rows) else "")))
    if phase_rows:
        statements.append(Table(
            "PhaseTapChangerLinear",
            [Column("mRID"), Column("name"), Column("lowStep"), Column("highStep"), Column("neutralStep"),
             Column("stepPhaseShiftIncrement", "deg"), Column("step"), Column("ltcFlag"), Column("controlEnabled"),
             Column("TapChangerControl"), Column("TransformerEnd")],
            phase_rows, comment="COD +-3: steps 1..NTP from RMI to RMA, neutralStep nearest 0 deg; "
                                "stepPhaseShiftIncrement in CIM's sign (phase_tap, R4b-3)"))
    if tabular_rows:
        statements.append(Table("ImpedanceTapChangerTabular",
                                [Column("mRID"), Column("name"), Column("TransformerEnd"),
                                 Column("ImpedanceTapChangerTable")],
                                tabular_rows, comment="TABk: the winding's impedance correction table (R4b-10)"))
    statements += [*ratings.tables(), *ties.tables("NMETR")]
    return Document(name="transformer", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(records)))

