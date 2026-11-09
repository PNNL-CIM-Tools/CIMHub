"""RAW Transformer -> ``transformer.cimtbl``: a ``PowerTransformer`` with a ``PowerTransformerEnd`` per winding, a
3-winding unit's Z12/Z23/Z31 as ``TransformerMeshImpedance`` rows (Delta model), and each tapped winding's
``RatioTapChanger`` + ``TapChangerControl``.

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#transformer-r4``.
"""

from __future__ import annotations

import math

from cimtables.document import Column, Document, Row, Table
from cimtopology.core.voltage import base_voltage_mrid

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, lookup, mrid, schema_defaults, untranscribed_names
from cimhub_raw.importer.cimtbl.bus import busbar_mrid
from cimhub_raw.importer.cimtbl.derived import (
    magnetizing_siemens,
    ratio_tap,
    transformer_ohms,
    vars_from_mvar,
    volts_from_per_unit,
    winding_unit_kv,
)
from cimhub_raw.importer.cimtbl.area_interchange import control_area_numbers
from cimhub_raw.importer.cimtbl.ratings import RATING_SETS, RatingRows
from cimhub_raw.importer.cimtbl.tie_flow import TieFlowRows, off_tie_note
from cimhub_raw.importer.cimtbl.records import fill_keyed_defaults, raw_defaults

NATIVE_CLASS = schema.TransformerRecord
PREFIX = "xf_"  # requested from the cimtbl-translate table owners (plan C3)
#: the slots RAW writes only for a 3-winding unit (K != 0): the schema's ``serialize_if``
THREE_WINDING_SLOTS = frozenset(schema_defaults(NATIVE_CLASS, "serialize_if"))
#: the Delta model's pairs: (From end, To end, RAW's pair suffix) (user, 2026-11-08)
MESH_PAIRS = ((1, 2, "1_2"), (2, 3, "2_3"), (1, 3, "3_1"))

#: STAT -> inService
IN_SERVICE = {1: True, 0: False}
UNMAPPED_STATUS = {2: "winding 2 out", 3: "winding 3 out", 4: "winding 1 out"}
#: |COD| -> TapChangerControl mode
CONTROL_MODE = {0: "voltage", 1: "voltage", 2: "reactivePower"}
UNMAPPED_COD = {3: "phase shift: no case has one yet (a PhaseTapChanger)",
                5: "asymmetric phase shift: no case has one yet (a PhaseTapChanger)",
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
                                           f"{tapped}; winding 2 of a 2-winding unit must be ratio 1 (else raises); "
                                           "blank: 1.0, or the bus's BASKV for CW 2 (defaulted)"),
        f"nomv{k}": Field("derived", note=f"NOMV{k} (kV): PowerTransformerEnd ratedU, or the bus's BASKV when 0 (RAW-6); "
                                          "blank: 0 (defaulted)"),
        f"ang{k}": Field("structural", note=f"ANG{k}: a phase shift; nonzero raises until a case has one (a "
                                            "PhaseTapChanger); blank: 0 (defaulted)"),
        **{f"rate{k}_{n}": Field("structural", note=_RATING) for n in range(1, RATING_SETS + 1)},
        f"cod{k}": Field("mapped", note=f"COD{k}: 0 ltcFlag false, control disabled; +-1 voltage, +-2 reactivePower, "
                                        "ltcFlag true, controlEnabled and enabled = (COD > 0); +-3, +-5 raise (no "
                                        "case), +-4 raises (phase 2); blank: 0 (defaulted)"),
        f"cont{k}": Field("structural", note=f"CONT{k}: the TapChangerControl Terminal bb_<CONT>_T1, or the winding's "
                                             "own xf_<key>_T<k> when 0 (user 2026-11-08); COD +-1 with 0, or a "
                                             "negative CONT, raises; blank: 0 (defaulted)"),
        f"rma{k}": Field("derived", note=f"RMA{k}: highStep's ratio, in CW units (ratio_tap: steps 1..NTP from RMI to "
                                         "RMA, stepVoltageIncrement); blank: 1.1 for CW 1 or 3 (defaulted), else "
                                         "raises"),
        f"rmi{k}": Field("derived", note=f"RMI{k}: lowStep's ratio; as RMA{k}; blank: 0.9 for CW 1 or 3 (defaulted)"),
        f"vma{k}": Field("derived", note=f"VMA{k}: targetValue = (VMA + VMI) / 2 and targetDeadband = VMA - VMI, in V "
                                         "x the regulated bus's BASKV (volts_from_per_unit) for voltage, in VAr from "
                                         "Mvar (vars_from_mvar) for reactivePower; blank: 1.1 for COD 0 or +-1 "
                                         "(defaulted), else raises"),
        f"vmi{k}": Field("derived", note=f"VMI{k}: as VMA{k}; blank: 0.9 for COD 0 or +-1 (defaulted)"),
        f"ntp{k}": Field("derived", note=f"NTP{k}: highStep = NTP, lowStep = 1; below 2 raises; blank: 33 (defaulted)"),
        f"tab{k}": Field("structural", note=f"TAB{k}: an impedance correction table; nonzero raises until phase 2; "
                                            "blank: 0 (defaulted)"),
        f"cr{k}": Field("structural", note=f"CR{k}: load-drop compensation; nonzero raises until a case has one; "
                                           "blank: 0 (defaulted)"),
        f"cx{k}": Field("structural", note=f"CX{k}: as CR{k}"),
        f"cnxa{k}": Field("structural", note=f"CNXA{k}: only COD +-5 uses it; nonzero raises; blank: 0 (defaulted)"),
        f"nod{k}": Field("structural", note=f"NOD{k}: a node of bus CONT{k}; nonzero raises until R6 (node-breaker); "
                                           "blank: 0 (defaulted)"),
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
    "status": Field("mapped", note="STAT: inService = (STAT == 1); 2, 3 and 4 (one winding out) raise until a case "
                                   "has one; blank: 1 (defaulted)"),
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
(3-winding, Delta model); RatioTapChanger + TapChangerControl per tapped winding; ratings per winding.
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
        if cw in (1, 3) and code not in (3, 5):
            rules[f"rma{winding}"], rules[f"rmi{winding}"] = TAP_RANGE_DEFAULT
        if code in (0, 1):
            rules[f"vma{winding}"], rules[f"vmi{winding}"] = BAND_DEFAULT
    defaults = {**static, **rules}
    if not record.k:
        defaults = {slot: value for slot, value in defaults.items() if slot not in THREE_WINDING_SLOTS}
    return defaults


def _buses(record) -> tuple[int, ...]:
    return (record.i, record.j, record.k) if record.k else (record.i, record.j)


def _check_record(record, record_id: str) -> None:
    """The forms R4 does not map raise."""
    if record.status in UNMAPPED_STATUS:
        raise NotImplementedError(f"{record_id}: STAT {record.status} ({UNMAPPED_STATUS[record.status]}): no case "
                                  "has one yet")
    for winding in range(1, _windings(record) + 1):
        if _winding(record, "ang", winding):
            raise NotImplementedError(f"{record_id}: ANG{winding} = {_winding(record, 'ang', winding)}, a phase shift "
                                      "(a PhaseTapChanger: no case has one yet)")
    for winding in _tapped_windings(record):
        code = _winding(record, "cod", winding)
        if abs(code) in UNMAPPED_COD:
            raise NotImplementedError(f"{record_id}: COD{winding} {code} ({UNMAPPED_COD[abs(code)]})")
        for slot, why in (("tab", "an impedance correction table (phase 2)"),
                          ("cr", "load-drop compensation (no case has one yet)"),
                          ("cx", "load-drop compensation (no case has one yet)"),
                          ("cnxa", "an asymmetric phase shift's angle (COD 5)"),
                          ("nod", "a node in a substation (R6)")):
            if _winding(record, slot, winding):
                raise NotImplementedError(f"{record_id}: {slot.upper()}{winding} = {_winding(record, slot, winding)}, "
                                          f"{why}")
        cont = _winding(record, "cont", winding)
        if cont < 0:
            raise NotImplementedError(f"{record_id}: CONT{winding} {cont} is negative (no case has one yet)")
        if abs(code) == 1 and cont == 0:
            raise ValueError(f"{record_id}: COD{winding} {code} controls a voltage but CONT{winding} is 0")
        for slot in ("rma", "rmi", "vma", "vmi"):
            if _winding(record, slot, winding) is None:
                raise ValueError(f"{record_id}: {slot.upper()}{winding} is blank and has no default (CW {record.cw}, "
                                 f"COD{winding} {code})")


def map_transformer(native, substations_by_bus: dict[int, str], base_kv_of: dict[int, float],
                    bus_area: dict[int, int], base_mva: float, ratings_in_current: bool) -> Document:
    records = sorted(native.list_by_class(NATIVE_CLASS),
                     key=lambda record: (record.i, record.j, record.k or 0, str(record.circuit)))
    if not records:
        return Document(name="transformer", statements=[], profile=CIM_PROFILE)
    static = raw_defaults(NATIVE_CLASS)
    ratings = RatingRows(ratings_in_current, "XFRRAT", "one set per rated winding, on its terminal xf_<key>_T<k>")
    ties = TieFlowRows(bus_area, control_area_numbers(native))
    transformer_rows, end_rows, mesh_rows, control_rows, tap_rows = [], [], [], [], []
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
        ends = [f"{container}_{winding}" for winding in range(1, len(buses) + 1)]
        transformer_rows.append(Row([
            container, transformer.name or key, transformer.vecgrp or None,
            cell(lookup(IN_SERVICE, transformer.status, slot="status", record_id=record_id)),
            substations_by_bus[transformer.i]], comment=defaulted))

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
            ratio_kv = transformer.windv2 * winding_unit_kv(transformer.cw, kv[1], nominal[1], record_id)
            if not math.isclose(ratio_kv, nominal[1]):
                raise NotImplementedError(f"{record_id}: WINDV2 {transformer.windv2} (CW {transformer.cw}) is "
                                          f"{ratio_kv} kV on a {nominal[1]} kV winding, an off-nominal winding 2 (no "
                                          "case has one yet)")
        for winding, (bus, end, (r, x, g, b)) in enumerate(zip(buses, ends, impedances), start=1):
            end_rows.append(Row([end, f"{key}_{winding}", str(bus), str(winding), cell(nominal[winding - 1]),
                                 cell(rated_mva), cell(r), cell(x), cell(g), cell(b),
                                 base_voltage_mrid(kv[winding - 1]), container]))
            if winding == 1 or transformer.k:
                ratings.add(end, [getattr(transformer, f"rate{winding}_{n}") for n in range(1, RATING_SETS + 1)],
                            kv[winding - 1], terminal=f"{container}_T{winding}")

        if ties.is_tie(buses):
            if transformer.nmetr not in range(1, len(buses) + 1):
                raise ValueError(f"{record_id}: NMETR {transformer.nmetr} names no winding of a {len(buses)}-winding "
                                 "tie")
            ties.add(container, key, buses, transformer.nmetr, record_id)

        for winding in _tapped_windings(transformer):
            code = _winding(transformer, "cod", winding)
            mode = lookup(CONTROL_MODE, abs(code), slot=f"cod{winding}", record_id=record_id)
            regulated = _winding(transformer, "cont", winding)
            if regulated and regulated not in base_kv_of:
                raise ValueError(f"{record_id}: CONT{winding} {regulated} is no bus")
            terminal = f"{busbar_mrid(regulated)}_T1" if regulated else f"{container}_T{winding}"
            high, low = _winding(transformer, "vma", winding), _winding(transformer, "vmi", winding)
            if mode == "voltage":
                regulated_kv = base_kv_of[regulated or buses[winding - 1]]
                target, deadband = (volts_from_per_unit((high + low) / 2, regulated_kv),
                                    volts_from_per_unit(high - low, regulated_kv))
            else:
                target, deadband = vars_from_mvar((high + low) / 2), vars_from_mvar(high - low)
            control = f"{container}_ctrl{winding}"
            control_rows.append(Row([control, f"{key}_{winding}", mode, "true", cell(code > 0), cell(target),
                                     cell(deadband), terminal]))
            tap = ratio_tap(_winding(transformer, "windv", winding), _winding(transformer, "rma", winding),
                            _winding(transformer, "rmi", winding), _winding(transformer, "ntp", winding),
                            unit_kv=winding_unit_kv(transformer.cw, kv[winding - 1], nominal[winding - 1], record_id),
                            rated_kv=nominal[winding - 1], record_id=record_id)
            tap_rows.append(Row([
                f"{container}_tap{winding}", f"{key}_{winding}", "1", str(_winding(transformer, "ntp", winding)),
                str(tap.neutral_step), cell(tap.neutral_kv), cell(tap.increment_percent), cell(tap.step),
                cell(code != 0), cell(code > 0), control, ends[winding - 1]]))

    statements = [
        Table("PowerTransformer", [Column(name) for name in ("mRID", "name", "vectorGroup", "inService",
                                                             "EquipmentContainer")],
              transformer_rows, comment=off_tie_note(untranscribed_names(FIELDS), "NMETR")),
        Table("PowerTransformerEnd",
              [Column("mRID"), Column("name"), Column("bus"), Column("endNumber"), Column("ratedU", "kV"),
               Column("ratedS", "MVA"), Column("r", "ohm"), Column("x", "ohm"), Column("g", "S"), Column("b", "S"),
               Column("BaseVoltage"), Column("PowerTransformer")],
              end_rows, comment="r, x, g, b on the end's ratedU (transformer_ohms, magnetizing_siemens): a 2-winding "
                                "unit's all on end 1, end 2 zero; a 3-winding unit's g, b on end 1, r, x on its mesh"),
    ]
    if mesh_rows:
        statements.append(Table("TransformerMeshImpedance",
                                [Column("mRID"), Column("name"), Column("FromTransformerEnd"),
                                 Column("ToTransformerEnd"), Column("r", "ohm"), Column("x", "ohm")],
                                mesh_rows, comment="3-winding Z12, Z23, Z31 (Delta model): r, x seen from the From "
                                                   "end"))
    statements += [
        Table("TapChangerControl",
              [Column(name) for name in ("mRID", "name", "mode", "discrete", "enabled", "targetValue",
                                         "targetDeadband", "Terminal")],
              control_rows, comment="targetValue and targetDeadband in V (voltage) or VAr (reactivePower); COD 0 "
                                    "keeps its control, disabled"),
        Table("RatioTapChanger",
              [Column("mRID"), Column("name"), Column("lowStep"), Column("highStep"), Column("neutralStep"),
               Column("neutralU", "kV"), Column("stepVoltageIncrement"), Column("step"), Column("ltcFlag"),
               Column("controlEnabled"), Column("TapChangerControl"), Column("TransformerEnd")],
              tap_rows, comment="steps 1..NTP from RMI to RMA; neutralStep nearest ratio 1 at neutralU; "
                                "stepVoltageIncrement in percent of ratedU (ratio_tap)"),
        *ratings.tables(),
        *ties.tables("NMETR"),
    ]
    return Document(name="transformer", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(records)))
