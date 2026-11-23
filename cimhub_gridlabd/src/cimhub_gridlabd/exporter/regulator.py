"""VoltageRegulator -> GLM ``regulator`` + ``regulator_configuration``
(``EXPORT_MAPPING.md#x2-transformers-and-regulators``, decision X5; the importer's S3c inverted).

One GLM regulator per VoltageRegulator, on its end's phases (GridLAB-D takes one-phase regulators side by side
between two buses), except where the GLM importer split one: wye units on the same two buses named
``<base>_<their phase>`` (S3c, ``regulator.unit_mrids``) are the GLM regulator ``<base>`` again, so a GLM model
round-trips. Single-phase regulators with a coil between two phases on the same buses (an open or closed
delta bank) are one GLM regulator: GridLAB-D 6.0 solves no delta regulator under NR (``OPEN_DELTA_ABBC`` is FBS
only, the others throw, ``regulator.cpp:385``), so the bank is ``WYE_WYE`` (the user's X3 rule, 2026-11-21), each
coil's tap and compensator on its own phase (an open bank's coils on the phases they do not share, a closed bank's
AB, BC, CA on A, B, C), and logged. Their shared settings must agree. A group of several units is GLM's
``control_level`` INDIVIDUAL (its default); one VoltageRegulator alone (a gang unit on ABC, or one phase not named as
the importer's split) is BANK, which GridLAB-D and the importer read as one unit (GLM-7, S6), sensing
``PT_phase``/``CT_phase`` = the control's monitored phase (its first phase when it has none: MANUAL reads no phase;
an enabled control without one raises). GLM's regulator has no kVA and no reactance, so its mesh r (GridLAB-D's
series ``regulator_resistance``, S3c-2) and the tap changer and its control are written:

- ``raise_taps`` = highStep - neutralStep, ``lower_taps`` = neutralStep - lowStep, ``regulation`` =
  stepVoltageIncrement x raise_taps, ``tap_pos_X`` = step - neutralStep on each of its phases;
- ``Type`` B for a ``construction`` typeB unit (GridLAB-D's out = in / (1 - tap x step), as the GLM importer reads
  it), else A (out = in x (1 + tap x step), CIM's ratio; ``regulator.cpp:316``);
- ``Control`` MANUAL when the TapChangerControl is disabled or absent, LINE_DROP_COMP with line drop compensation,
  else OUTPUT_VOLTAGE; ``band_center``/``band_width`` the target and deadband (primary volts; on LINE_DROP_COMP over
  ptRatio, as GridLAB-D reads it on the PT secondary), ``compensator_r/x_setting_X`` = lineDropR/X x ctRatio /
  ptRatio wherever CIM holds a line drop (GridLAB-D reads them on LINE_DROP_COMP only, the importer on any Control),
  ``current_transducer_ratio``/``power_transducer_ratio`` the CT and PT ratios, ``dwell_time`` the initial delay.
"""

from __future__ import annotations

import logging

import cimprofiles.cim18.cim18v17 as cim

from cimtables.graph_write import get_qty

from cimhub_core.export_slots import Slot, with_default
from cimhub_core.names import export_name
from cimhub_core.getters.control import get_tap_changer_control
from cimhub_core.getters.tap_changer import get_tap_steps
from cimhub_core.getters.terminals import get_terminal_phases
from cimhub_gridlabd.exporter.buses import letters
from cimhub_gridlabd.exporter.line import ratings
from cimhub_gridlabd.exporter.units import glm_unit
from cimhub_gridlabd.schema import gridlabd as schema

_log = logging.getLogger(__name__)

CIM_CLASSES = (cim.VoltageRegulator,)

_CONFIGURATION_SLOTS = {
    "name": Slot("written", "<regulator>_config"),
    "connect_type": Slot("written", "WYE_WYE: CIM's AutoTransformerEnds are grounded wye coils"),
    "raise_taps": Slot("written", "highStep - neutralStep"), "lower_taps": Slot("written", "neutralStep - lowStep"),
    "regulation": Slot("written", "stepVoltageIncrement x raise_taps (per unit)"),
    "Type": Slot("written", "B on a construction typeB, else A (module docstring)"),
    **{f"tap_pos_{letter}": Slot("written", "step - neutralStep on each phase") for letter in "ABC"},
    "Control": Slot("written", "MANUAL, LINE_DROP_COMP or OUTPUT_VOLTAGE from the TapChangerControl"),
    "band_center": Slot("written", "the target (V); over ptRatio on LINE_DROP_COMP; unset on a disabled control"),
    "band_width": Slot("written", "the deadband (V), likewise"),
    "dwell_time": Slot("written", "TapChanger.initialDelay (s)"),
    "current_transducer_ratio": Slot("written", "ctRatio"), "power_transducer_ratio": Slot("written", "ptRatio"),
    **{f"compensator_{part}_setting_{letter}": Slot("written", f"lineDrop{part.upper()} x ctRatio / ptRatio")
       for part in "rx" for letter in "ABC"},
    "control_level": Slot("written", "BANK for one VoltageRegulator alone, else unset (INDIVIDUAL)"),
    "PT_phase": Slot("written", "BANK: the monitored phase, else its first"),
    "CT_phase": Slot("written", "BANK: as PT_phase"),
}
_REGULATOR_SLOTS = {
    "name": Slot("written", "Names (X1)"),
    "phases": Slot("written", "the A, B, C of its end 1"),
    "from_node": Slot("written", "end 1's bus"), "to": Slot("written", "end 2's bus"),
    "configuration": Slot("written", "its regulator_configuration"),
    **{f"continuous_rating_{letter}": Slot("written", "get_current_limits normal") for letter in "ABC"},
    **{f"emergency_rating_{letter}": Slot("written", "get_current_limits emergency") for letter in "ABC"},
    "regulator_resistance": Slot("written", "the mesh r (ohm), S3c-2; unset without a mesh r"),
}
SLOTS = {
    schema.RegulatorConfiguration: with_default(schema.RegulatorConfiguration, _CONFIGURATION_SLOTS,
                                                Slot("unset", "not in CIM; GridLAB-D's default")),
    schema.Regulator: with_default(schema.Regulator, _REGULATOR_SLOTS,
                                   Slot("unset", "not in CIM; GridLAB-D's default")),
}


#: the settings GLM holds per phase; every other one a delta bank's coils must share
PER_PHASE = ("tap_pos", "compensator_r_setting", "compensator_x_setting")


def export(context) -> list:
    records = []
    for group, drop in _groups(context.objects(*CIM_CLASSES), context.names):
        records += _regulator(group, drop, context)
    return records


def _groups(regulators, names) -> list[tuple[list[tuple], str]]:
    """``[([(regulator, its GLM letters), ...], name ending to drop), ...]``: one regulator each, a split GLM
    regulator's units together, a delta bank's coils together."""
    groups, banks, wyes = [], {}, {}
    for regulator in regulators:
        ends = _ends(regulator)
        phases = get_terminal_phases(ends[0].Terminal)
        key = tuple(end.Terminal.ConnectivityNode.mRID for end in ends)
        if len(letters(phases)) == 2 and cim.SinglePhaseKind.N not in phases:
            banks.setdefault(key, []).append((regulator, letters(phases)))
        else:
            wyes.setdefault(key, []).append((regulator, letters(phases)))
    for units in wyes.values():
        groups += _split_units(units, names)
    for coils in banks.values():
        coils.sort(key=lambda item: item[0].mRID)
        _log.warning("%s: a delta regulator bank, written WYE_WYE (GridLAB-D solves no delta regulator under NR)",
                     ", ".join(regulator.mRID for regulator, _ in coils))
        groups.append((list(zip((regulator for regulator, _ in coils), _bank_letters([coil for _, coil in coils]),
                                strict=True)), ""))
    return groups


def _split_units(units: list[tuple], names) -> list[tuple[list[tuple], str]]:
    """Wye regulators on two buses: one group named ``<base>`` when each is one phase named ``<base>_<its phase>``
    (the GLM importer's split, inverted; one such unit alone too), else one group each."""
    texts = [export_name(regulator, names.source) for regulator, _ in units]
    phase_letters = [letters_on for _, letters_on in units]
    split = (all(len(letter) == 1 and text.endswith(f"_{letter}") for text, letter in zip(texts, phase_letters,
                                                                                          strict=True))
             and len({text[:-2] for text in texts}) == 1 and len(set(phase_letters)) == len(units))
    if split:
        ordered = sorted(units, key=lambda unit: unit[1])
        return [(ordered, f"_{ordered[0][1]}")]
    return [([unit], "") for unit in units]


def _bank_letters(coils: list[str]) -> list[str]:
    """Each delta coil's GLM phase: an open bank's the letter it does not share, a closed bank's AB, BC, CA as A, B,
    C, a lone coil its first."""
    if len(coils) == 3:
        return [{"AB": "A", "BC": "B", "AC": "C"}[coil] for coil in coils]
    if len(coils) == 2:
        shared = set(coils[0]) & set(coils[1])
        return [(set(coil) - shared).pop() for coil in coils]
    return [coils[0][0]]


def _ends(regulator: cim.VoltageRegulator) -> list:
    ends = sorted(regulator.AutoTransformerEnd, key=lambda end: end.endNumber)
    if len(ends) != 2:
        raise ValueError(f"VoltageRegulator {regulator.mRID!r}: has {len(ends)} ends, not 2")
    return ends


def _regulator(group: list[tuple], drop: str, context) -> list:
    first, _ = group[0]
    ends = _ends(first)
    slots, resistance = {}, {}
    for regulator, phase_letters in group:
        taps = [end.RatioTapChanger for end in _ends(regulator) if end.RatioTapChanger is not None]
        if len(taps) != 1:
            raise ValueError(f"VoltageRegulator {regulator.mRID!r}: has {len(taps)} RatioTapChangers, not 1")
        _merge(slots, _configuration_slots(regulator, taps[0], phase_letters), regulator)
        _merge(resistance, _resistance(regulator), regulator)
    phase_letters = "".join(sorted(letter for _, letters_on in group for letter in letters_on))
    if len(group) == 1 and not drop:
        slots.update(_bank_slots(first, phase_letters))
    configuration = schema.RegulatorConfiguration(name=context.names.name(first, suffix="_config", drop=drop),
                                                  **slots)
    record = schema.Regulator(name=context.names.name(first, drop=drop), phases=phase_letters,
                              from_node=context.buses[ends[0].Terminal.ConnectivityNode].name,
                              to=context.buses[ends[1].Terminal.ConnectivityNode].name,
                              configuration=configuration.name, **resistance,
                              **ratings(first, phase_letters, schema.Regulator))
    return [configuration, record]


def _resistance(regulator: cim.VoltageRegulator) -> dict:
    """``{"regulator_resistance": ohm}`` from the unit's mesh r, or nothing when it has none (GridLAB-D's default)."""
    meshes = [mesh for end in _ends(regulator) for mesh in end.FromMeshImpedance]
    if len(meshes) > 1:
        raise ValueError(f"VoltageRegulator {regulator.mRID!r}: has {len(meshes)} TransformerMeshImpedances, not 1")
    if not meshes or meshes[0].r is None:
        return {}
    return {"regulator_resistance": get_qty(meshes[0], "r", glm_unit(schema.Regulator, "regulator_resistance"))}


def _bank_slots(regulator: cim.VoltageRegulator, phase_letters: str) -> dict:
    """GLM's BANK on one VoltageRegulator, sensing its control's monitored phase (module docstring)."""
    [tap] = [end.RatioTapChanger for end in _ends(regulator) if end.RatioTapChanger is not None]
    control = get_tap_changer_control(tap).control
    enabled = control is not None and control.enabled is not False
    if control is not None and control.monitored_phases:
        sensed = letters(control.monitored_phases)
    elif enabled:
        raise ValueError(f"VoltageRegulator {regulator.mRID!r}: an enabled control without a monitoredPhase; GLM's "
                         f"BANK senses one")
    else:
        sensed = phase_letters[0]
    if len(sensed) != 1:
        raise ValueError(f"VoltageRegulator {regulator.mRID!r}: monitors {sensed}; GLM's BANK senses one phase")
    return {"control_level": "BANK", "PT_phase": sensed, "CT_phase": sensed}


def _merge(slots: dict, coil: dict, regulator) -> None:
    """Add one coil's settings: its per-phase ones as they are, the shared ones only when they agree."""
    for slot, value in coil.items():
        if slot.rsplit("_", 1)[0] in PER_PHASE or slot not in slots:
            slots[slot] = value
        elif slots[slot] != value:
            raise ValueError(f"VoltageRegulator {regulator.mRID!r}: its {slot} {value} differs from its bank's "
                             f"{slots[slot]}; GLM's regulator holds one")


def _configuration_slots(regulator: cim.VoltageRegulator, tap: cim.RatioTapChanger, phase_letters: str) -> dict:
    steps = get_tap_steps(tap)
    raise_taps, lower_taps = steps.high - steps.neutral, steps.neutral - steps.low
    if steps.increment is None or raise_taps <= 0:
        raise ValueError(f"RatioTapChanger {tap.mRID!r}: a fixed tap is not a GLM regulator")
    if steps.step is None:
        raise ValueError(f"RatioTapChanger {tap.mRID!r}: step is unset")
    # VoltageRegulator.construction is an enum no getter reads; it only picks GridLAB-D's ratio formula
    regulator_type = "B" if regulator.construction is cim.RegulatorConstructionKind.typeB else "A"
    slots = {"connect_type": "WYE_WYE", "raise_taps": raise_taps, "lower_taps": lower_taps,
             "regulation": steps.increment / 100 * raise_taps, "Type": regulator_type,
             **{f"tap_pos_{letter}": round(steps.step - steps.neutral) for letter in phase_letters}}
    slots.update(_control_slots(tap, phase_letters))
    return slots


def _control_slots(tap: cim.RatioTapChanger, phase_letters: str) -> dict:
    volts = glm_unit(schema.RegulatorConfiguration, "band_center")
    settings = get_tap_changer_control(tap, unit=volts, time_unit=glm_unit(schema.RegulatorConfiguration,
                                                                            "dwell_time"))
    control = settings.control
    slots = {"dwell_time": settings.initial_delay}
    if control is None or control.enabled is False:
        return {**slots, "Control": "MANUAL", **_transducers(control), **_compensator_slots(tap, settings, phase_letters)}
    line_drop = bool(settings.line_drop_compensation)
    pt_ratio = control.pt_ratio
    if line_drop and not pt_ratio:
        raise ValueError(f"RatioTapChanger {tap.mRID!r}: line drop compensation without a ptRatio")
    scale = 1 / pt_ratio if line_drop else 1.0
    slots.update(Control="LINE_DROP_COMP" if line_drop else "OUTPUT_VOLTAGE", band_center=control.target * scale,
                 band_width=None if control.deadband is None else control.deadband * scale, **_transducers(control))
    return {**slots, **_compensator_slots(tap, settings, phase_letters)}


def _compensator_slots(tap: cim.RatioTapChanger, settings, phase_letters: str) -> dict:
    """``compensator_r/x_setting_X`` = lineDrop x ctRatio / ptRatio on each phase, wherever CIM holds a line drop."""
    drops = (("r", settings.line_drop.r), ("x", settings.line_drop.x))
    if all(value is None for _, value in drops):
        return {}
    control = settings.control
    if control is None or not control.pt_ratio or not control.ct_ratio:
        raise ValueError(f"RatioTapChanger {tap.mRID!r}: a line drop without a ptRatio and a ctRatio")
    return {f"compensator_{part}_setting_{letter}": value * control.ct_ratio / control.pt_ratio
            for part, value in drops if value is not None for letter in phase_letters}


def _transducers(control) -> dict:
    if control is None:
        return {}
    return {"current_transducer_ratio": control.ct_ratio, "power_transducer_ratio": control.pt_ratio}
