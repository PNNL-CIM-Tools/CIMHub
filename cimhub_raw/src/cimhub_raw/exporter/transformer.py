"""PowerTransformer -> Transformer (``EXPORT_MAPPING.md#e4-transformer-impedance-correction``).

The inverse of the importer's R4 and R4b, with CW = CZ = CM = 1: every impedance, admittance, ratio and band goes
back in pu of SBASE and the winding's bus BASKV. ``get_transformer_model`` gives each value on SBASE and the
winding's ratedU, so it moves by the voltage only (``impedance_on_bus_base``). E3's step-ups and E6's converter
transformers are left out.
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.export_slots import Slot
from cimhub_core.getters import describe
from cimhub_core.getters.base_voltage import get_base_voltage
from cimhub_core.getters.control import get_tap_changer_control
from cimhub_core.getters.in_service import get_in_service
from cimhub_core.getters.tap_changer import get_phase_tap_steps, get_tap_steps, get_tap_voltage
from cimhub_core.getters.transformer import TransformerForm, get_transformer_model, get_transformer_units
from cimhub_raw.exporter import generator, impedance_correction
from cimhub_raw.exporter.identity import keyed_ids, raw_name
from cimhub_raw.exporter.ratings import device_ratings
from cimhub_raw.importer.cimtbl.derived import (admittance_on_bus_base, impedance_on_bus_base, per_unit_from_kv,
                                                per_unit_from_ohms, raw_angle)
from cimhub_raw.importer.cimtbl.ratings import RATING_SETS
from cimhub_raw.importer.cimtbl.transformer import MESH_PAIRS, OUT_WINDING, PREFIX

NATIVE_CLASS = schema.TransformerRecord
CIM_CLASSES = (cim.PowerTransformer,)
ID_WIDTH = 2
NAME_WIDTH = 40
UNIT_CODE = 1  # CW, CZ, CM: pu of the bus base and SBASE
STATUS_OF_OUT_WINDING = {winding: status for status, winding in OUT_WINDING.items()}  # R4b-6
MODE = cim.RegulatingControlModeKind
RATIO_CODE = {MODE.voltage: 1, MODE.reactivePower: 2}  # COD of a RatioTapChanger with ltcFlag true
PHASE_SHIFTER = 3  # COD of a PhaseTapChangerLinear under an activePower control
TARGET_UNIT = {MODE.voltage: "kV", MODE.reactivePower: "MVAr", MODE.activePower: "MW"}

_UNSET = Slot("unset", "ownership is an asset concept (CIM 18 gap)")


def _winding_slots(k: int) -> dict[str, Slot]:
    only = "" if k == 1 else " (3-winding only)"
    return {
        f"windv{k}": Slot("written", f"WINDV{k}: get_tap_voltage(actual) of the end's RatioTapChanger / bus {k}'s "
                                     "BASKV (CW 1); without one, ratedU / BASKV (the import writes no tap at ratio NOMV)"),
        f"nomv{k}": Slot("written", f"NOMV{k}: winding {k}'s ratedU (kV)"),
        f"ang{k}": Slot("written", f"ANG{k}: -(phaseShift + the PhaseTapChangerLinear's (step - neutral) x increment) "
                                   f"(raw_angle); a 2-winding unit's ANG1 is winding 1's less winding 2's{only}"),
        **{f"rate{k}_{n}": Slot("written", f"RATE{k}-{n}: the olt_rate{n} limit on winding {k}'s terminal "
                                            "(device_ratings)") for n in range(1, RATING_SETS + 1)},
        f"cod{k}": Slot("written", f"COD{k}: the controlled tap changer: a RatioTapChanger with ltcFlag false 0, else "
                                   "+-1 voltage, +-2 reactivePower; a PhaseTapChangerLinear under activePower +-3; + "
                                   f"when the control is enabled{only}"),
        f"cont{k}": Slot("written", f"CONT{k}: the busNumber of the control's terminal; the winding's own 0; blank "
                                    f"for COD +-3{only}"),
        f"rma{k}": Slot("written", f"RMA{k}: the stepped tap's highStep voltage / BASKV, or a shifter's larger end "
                                   f"angle (deg); blank for a fixed tap{only}"),
        f"rmi{k}": Slot("written", f"RMI{k}: as RMA{k}, at lowStep or the smaller end angle{only}"),
        f"vma{k}": Slot("written", f"VMA{k}: the control's target + deadband / 2: pu of the regulated bus's BASKV, "
                                   f"Mvar or MW by mode{only}"),
        f"vmi{k}": Slot("written", f"VMI{k}: as VMA{k}, target - deadband / 2{only}"),
        f"ntp{k}": Slot("written", f"NTP{k}: highStep - lowStep + 1 of the stepped tap{only}"),
        f"tab{k}": Slot("written", f"TAB{k}: the number of the end's ImpedanceTapChangerTabular's table{only}"),
        f"cr{k}": Slot("written", f"CR{k}: lineDropR as pu on SBASE and the regulated bus's BASKV "
                                  f"(per_unit_from_ohms){only}"),
        f"cx{k}": Slot("written", f"CX{k}: lineDropX, as CR{k}{only}"),
        f"cnxa{k}": Slot("unset", f"CNXA{k}: only COD +-5 uses it, which is not mapped"),
        f"nod{k}": Slot("unset", f"NOD{k}: a node of a node-breaker bus, written by E5"),
    }


def _pair_slots(i: int, j: int, pair: str) -> dict[str, Slot]:
    note = "2-winding" if pair == "1_2" else "3-winding"
    return {
        f"r{pair}": Slot("written", f"R{i}-{j}: r{i} + r{j} + the mesh r, pu on SBASE moved to bus {i}'s BASKV "
                                    f"(impedance_on_bus_base; CZ 1); {note}"),
        f"x{pair}": Slot("written", f"X{i}-{j}: the mesh ({i}, {j}) x, as R{i}-{j}"),
        f"sbase{pair}": Slot("written", f"SBASE{i}-{j}: a 2-winding unit's ratedS (MVA); a 3-winding unit's SBASE, "
                                        "since no end holds a pair base (R4)"),
    }


SLOTS = {NATIVE_CLASS: {
    "i": Slot("written", "I: end 1's busNumber"),
    "j": Slot("written", "J: end 2's busNumber"),
    "k": Slot("written", "K: end 3's busNumber; 0 for a 2-winding unit"),
    "circuit": Slot("written", "CKT: the xf_<I>_<J>_<K>_<CKT> key, else the next free (X2)"),
    "cw": Slot("rule", "CW 1: WINDV, RMA, RMI in pu of the bus's BASKV"),
    "cz": Slot("rule", "CZ 1: R, X in pu on SBASE and the bus's BASKV"),
    "cm": Slot("rule", "CM 1: MAG1, MAG2 in pu on SBASE and bus 1's BASKV"),
    "mag1": Slot("written", "MAG1: get_transformer_model core g, moved to bus 1's BASKV (admittance_on_bus_base)"),
    "mag2": Slot("written", "MAG2: the core b, as MAG1"),
    "nmetr": Slot("written", "NMETR: on a tie, the winding whose terminal holds no TieFlow (the lower of two); off a "
                             "tie blank (RAW-22)"),
    "name": Slot("written", "NAME: X2; blank when it is the key I_J_K_CKT"),
    "status": Slot("rule", "STAT: 0 when inService is false; 2, 3, 4 when winding 2, 3, 1 alone is disconnected "
                           "(R4b-6); else 1"),
    **{f"{kind}{n}": _UNSET for n in range(1, 5) for kind in ("o", "f")},
    "vecgrp": Slot("written", "VECGRP: vectorGroup"),
    "zcod": Slot("unset", "ZCOD: zero-sequence data is in the sequence file"),
    **{slot: value for i, j, pair in MESH_PAIRS for slot, value in _pair_slots(i, j, pair).items()},
    "vmstar": Slot("unset", "VMSTAR: the star point's solved voltage, which the Delta model omits"),
    "anstar": Slot("unset", "ANSTAR: as VMSTAR"),
    **{slot: value for k in (1, 2, 3) for slot, value in _winding_slots(k).items()},
}}
# a 2-winding unit's winding 2 has only WINDV2 and NOMV2
SLOTS[NATIVE_CLASS]["windv2"] = Slot("written", "WINDV2: a 2-winding unit's fixed RatioTapChanger neutralU / bus 2's "
                                                "BASKV, ratedU / BASKV without one; a 3-winding unit's as WINDV1")


def export(context) -> list[schema.TransformerRecord]:
    """One Transformer per PowerTransformer on numbered buses, by key."""
    step_ups = set(generator.step_ups(context))
    units = []
    for transformer in context.objects(cim.PowerTransformer):
        if transformer in step_ups:
            continue
        ends = sorted(transformer.PowerTransformerEnd, key=lambda end: end.endNumber)
        if len(ends) not in (2, 3):
            raise ValueError(f"{describe(transformer)}: {len(ends)} ends; a RAW transformer has 2 or 3 windings")
        nodes = [end.Terminal.TopologicalNode for end in ends]
        if any(node not in context.bus_numbers for node in nodes):
            if _is_converter_transformer(nodes, context):
                continue  # E6's (P2-5)
            raise ValueError(f"{describe(transformer)}: an end on a node without a busNumber, neither a generator "
                             "step-up (E3) nor a converter transformer (E6)")
        units.append((transformer, tuple(context.bus_numbers[node] for node in nodes)))
    circuits = keyed_ids([(transformer, PREFIX, (*buses, 0)[:3]) for transformer, buses in units], ID_WIDTH)
    tables = impedance_correction.table_numbers(context)
    records = [_record(transformer, buses, circuits[transformer], tables, context) for transformer, buses in units]
    return sorted(records, key=lambda record: (record.i, record.j, record.k, record.circuit))


def _is_converter_transformer(nodes, context) -> bool:
    internal = [node for node in nodes if node not in context.bus_numbers]
    return any(isinstance(terminal.ConductingEquipment, cim.ACDCConverter)
               for node in internal for terminal in node.Terminal)


def _record(transformer, buses: tuple[int, ...], circuit: str, tables: dict, context) -> schema.TransformerRecord:
    base_power = context.network.base_power
    [unit] = get_transformer_units(transformer)
    model = get_transformer_model(unit, "pu", base_power=base_power, voltage_unit="kV", power_unit="MVA")
    if model.form is not TransformerForm.BY_ENDS:
        raise ValueError(f"{describe(transformer)}: the {model.form.value} form; a RAW transformer is by ends")
    windings = model.windings
    three = len(windings) == 3
    bus_kv = [get_base_voltage(winding.end.Terminal.TopologicalNode, "kV", form="LL") for winding in windings]
    slots = {}
    for i, j, pair in MESH_PAIRS if three else MESH_PAIRS[:1]:
        mesh = model.mesh[(i, j)]
        r = (windings[i - 1].r or 0.0) + (windings[j - 1].r or 0.0) + (mesh.r or 0.0)
        slots[f"r{pair}"] = impedance_on_bus_base(r, windings[i - 1].rated_u, bus_kv[i - 1])
        slots[f"x{pair}"] = impedance_on_bus_base(mesh.x, windings[i - 1].rated_u, bus_kv[i - 1])
    g, b = model.core
    first = windings[0]
    slots["mag1"] = None if g is None else admittance_on_bus_base(g, first.rated_u, bus_kv[0])
    slots["mag2"] = None if b is None else admittance_on_bus_base(b, first.rated_u, bus_kv[0])
    if three:
        slots.update({f"sbase{pair}": base_power.to("MVA") for _, _, pair in MESH_PAIRS})
    else:
        slots["sbase1_2"] = _pair_base(transformer, windings)
    angles = [_angle(winding) for winding in windings]
    for k, winding in enumerate(windings, start=1):
        slots[f"nomv{k}"] = winding.rated_u
        if k == 2 and not three:
            slots["windv2"] = _second_winding_ratio(winding, bus_kv[1])
            if any(device_ratings(transformer, winding.end.Terminal)):
                raise ValueError(f"{describe(winding.end)}: rated; a 2-winding unit's ratings are winding 1's")
            continue
        slots.update(_tapped_winding(k, winding, bus_kv[k - 1], three, tables, context))
        slots[f"ang{k}"] = raw_angle(angles[0] - angles[1]) if not three else raw_angle(angles[k - 1])
        for n, rating in enumerate(device_ratings(transformer, winding.end.Terminal), start=1):
            slots[f"rate{k}_{n}"] = rating
    key = f"{buses[0]}_{buses[1]}_{buses[2] if three else 0}_{circuit}"
    return schema.TransformerRecord(
        i=buses[0], j=buses[1], k=buses[2] if three else 0, circuit=circuit, cw=UNIT_CODE, cz=UNIT_CODE,
        cm=UNIT_CODE, nmetr=_non_metered(windings), name=raw_name(transformer, key, NAME_WIDTH),
        status=_status(transformer, windings, three), vecgrp=transformer.vectorGroup or None, **slots)


def _pair_base(transformer, windings) -> float | None:
    """SBASE1-2: the ends' ratedS (MVA), which must agree."""
    rated = {winding.rated_s for winding in windings} - {None}
    if len(rated) > 1:
        raise ValueError(f"{describe(transformer)}: its ends' ratedS {sorted(rated)} differ; SBASE1-2 is one")
    return rated.pop() if rated else None


def _angle(winding) -> float:
    """The end's whole shift in CIM's sign (deg): its phaseShift and its phase tap changer's step (R4b-1)."""
    phase = winding.end.PhaseTapChanger
    shift = winding.phase_shift or 0.0
    if phase is None:
        return shift
    steps = _phase_steps(phase)
    return shift + (steps.step - steps.neutral) * steps.increment


def _phase_steps(phase):
    if not isinstance(phase, cim.PhaseTapChangerLinear):
        raise ValueError(f"{describe(phase)}: a {type(phase).__name__}; a RAW phase shifter is linear")
    steps = get_phase_tap_steps(phase)
    if steps.step is None:
        raise ValueError(f"{describe(phase)}: step is unset")
    return steps


def _second_winding_ratio(winding, bus_kv: float) -> float:
    """WINDV2 of a 2-winding unit: a fixed ratio tap's neutralU, or 1 (R4b-4)."""
    end = winding.end
    if end.PhaseTapChanger is not None or end.ImpedanceTapChanger is not None:
        raise ValueError(f"{describe(end)}: a phase or impedance tap changer on winding 2 of a 2-winding unit, which "
                         "RAW gives only WINDV2")
    tap = end.RatioTapChanger
    if tap is None:
        return per_unit_from_kv(winding.rated_u, bus_kv)  # at its rating
    steps = get_tap_steps(tap)
    if steps.low != steps.high or tap.TapChangerControl is not None:
        control = "none" if tap.TapChangerControl is None else describe(tap.TapChangerControl)
        raise ValueError(f"{describe(tap)}: steps {steps.low}..{steps.high}, control {control}; winding 2 of a "
                         "2-winding unit has only a fixed ratio")
    return per_unit_from_kv(get_tap_voltage(tap, which="actual", voltage_unit="kV"), bus_kv)


def _tapped_winding(k: int, winding, bus_kv: float, three: bool, tables: dict, context) -> dict:
    """WINDVk, CODk, CONTk, RMAk, RMIk, VMAk, VMIk, NTPk, TABk, CRk, CXk."""
    end = winding.end
    ratio, phase = end.RatioTapChanger, end.PhaseTapChanger
    winding_kv = winding.rated_u if ratio is None else get_tap_voltage(ratio, which="actual", voltage_unit="kV")
    slots = {f"windv{k}": per_unit_from_kv(winding_kv, bus_kv)}
    if phase is not None:
        steps = _phase_steps(phase)
        if ratio is not None and get_tap_steps(ratio).low != get_tap_steps(ratio).high:
            raise ValueError(f"{describe(end)}: a stepped ratio tap beside a phase tap changer; RMA/RMI hold one")
        end_angles = [raw_angle((position - steps.neutral) * steps.increment) for position in (steps.low, steps.high)]
        slots.update({f"rma{k}": max(end_angles), f"rmi{k}": min(end_angles), f"ntp{k}": steps.high - steps.low + 1})
    elif ratio is not None:
        steps = get_tap_steps(ratio)
        if steps.low != steps.high:
            slots.update({
                f"rma{k}": per_unit_from_kv(get_tap_voltage(ratio, which="high", voltage_unit="kV"), bus_kv),
                f"rmi{k}": per_unit_from_kv(get_tap_voltage(ratio, which="low", voltage_unit="kV"), bus_kv),
                f"ntp{k}": steps.high - steps.low + 1})
    controlled = [tap for tap in (ratio, phase) if tap is not None and tap.TapChangerControl is not None]
    if len(controlled) > 1:
        raise ValueError(f"{describe(end)}: both its tap changers have a control; COD{k} is one")
    if controlled:
        slots.update(_control(k, controlled[0], winding, context))
    tabular = end.ImpedanceTapChanger
    if tabular is not None:
        if tabular.ImpedanceTapChangerTable is None:
            raise ValueError(f"{describe(tabular)}: names no ImpedanceTapChangerTable")
        if three:
            raise ValueError(f"{describe(tabular)}: on a 3-winding unit, whose TAB the import does not map (R4b-10)")
        slots[f"tab{k}"] = tables[tabular.ImpedanceTapChangerTable]
    return slots


def _control(k: int, tap, winding, context) -> dict:
    """CODk, CONTk, VMAk, VMIk, CRk, CXk from the tap changer's control."""
    settings = get_tap_changer_control(tap)
    mode = settings.control.mode
    if mode not in TARGET_UNIT:
        raise ValueError(f"{describe(tap.TapChangerControl)}: mode {mode.value}; a RAW tap regulates voltage, reactive "
                         "or active power")
    control = get_tap_changer_control(tap, unit=TARGET_UNIT[mode]).control
    if settings.control_enabled is not None and settings.control_enabled != control.enabled:
        raise ValueError(f"{describe(tap)}: controlEnabled {settings.control_enabled} and its control's enabled "
                         f"{control.enabled} differ; COD's sign is one")
    sign = 1 if control.enabled else -1
    if isinstance(tap, cim.RatioTapChanger):
        if mode not in RATIO_CODE:
            raise ValueError(f"{describe(tap)}: a ratio tap under a {mode.value} control (COD +-3 is a phase shifter)")
        code = sign * RATIO_CODE[mode] if settings.ltc else 0
    elif mode is MODE.activePower:
        code = sign * PHASE_SHIFTER
    else:
        raise ValueError(f"{describe(tap)}: a phase tap changer under a {mode.value} control; RAW's shifter (COD "
                         "+-3) regulates active power")
    own = control.terminal is winding.end.Terminal
    node = control.terminal.TopologicalNode
    if not own and node not in context.bus_numbers:
        raise ValueError(f"{describe(tap.TapChangerControl)}: its terminal's {describe(node)} has no busNumber")
    half = (control.deadband or 0.0) / 2
    high, low = control.target + half, control.target - half
    slots = {f"cod{k}": code, f"cont{k}": None if abs(code) == PHASE_SHIFTER else 0 if own else context.bus_numbers[node]}
    regulated_kv = get_base_voltage(node, "kV", form="LL")
    if mode is MODE.voltage:
        high, low = per_unit_from_kv(high, regulated_kv), per_unit_from_kv(low, regulated_kv)
    slots.update({f"vma{k}": high, f"vmi{k}": low})
    if settings.line_drop_compensation:
        base_mva = context.network.base_power.to("MVA")
        slots[f"cr{k}"] = per_unit_from_ohms(settings.line_drop.r or 0.0, regulated_kv, base_mva)
        slots[f"cx{k}"] = per_unit_from_ohms(settings.line_drop.x or 0.0, regulated_kv, base_mva)
    return slots


def _status(transformer, windings, three: bool) -> int:
    """STAT: 0 out of service; 2, 3, 4 for winding 2, 3, 1 of a 3-winding unit alone disconnected; else 1."""
    if get_in_service(transformer, which="actual") is False:
        return 0
    out = [number for number, winding in enumerate(windings, start=1) if winding.end.Terminal.connected is False]
    if not out:
        return 1
    if three and len(out) == 1:
        return STATUS_OF_OUT_WINDING[out[0]]
    raise ValueError(f"{describe(transformer)}: windings {out} disconnected; RAW's STAT takes one winding of a "
                     "3-winding unit out")


def _non_metered(windings) -> int | None:
    """NMETR on a tie: the winding whose terminal holds no TieFlow, the lower of two; blank off a tie (RAW-22)."""
    terminals = [winding.end.Terminal for winding in windings]
    if not any(terminal.TieFlow for terminal in terminals):
        return None
    home = [number for number, terminal in enumerate(terminals, start=1) if not terminal.TieFlow]
    if not home:
        raise ValueError(f"{describe(windings[0].end.PowerTransformer)}: TieFlows on every winding; NMETR names the "
                         "one that has none")
    return home[0]

