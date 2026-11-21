"""VoltageRegulator -> GLM ``regulator`` + ``regulator_configuration``
(``EXPORT_MAPPING.md#x2-transformers-and-regulators``, decision X5; the importer's S3c inverted).

One GLM regulator per VoltageRegulator, on its end's phases (GridLAB-D takes one-phase regulators side by side
between two buses), except where the GLM importer split one: wye units on the same two buses named
``<base>_<their phase>`` (S3c, ``regulator.unit_mrids``) are the GLM regulator ``<base>`` again, so a GLM model
round-trips. Single-phase regulators with a coil between two phases on the same buses (an open or closed
delta bank) are one GLM regulator: GridLAB-D 6.0 solves no delta regulator under NR (``OPEN_DELTA_ABBC`` is FBS
only, the others throw, ``regulator.cpp:385``), so the bank is ``WYE_WYE`` (the user's X3 rule, 2026-11-21), each
coil's tap and compensator on its own phase (an open bank's coils on the phases they do not share, a closed bank's
AB, BC, CA on A, B, C), and logged. Their shared settings must agree. GLM's regulator is ideal, so only the tap
changer and its control are written:

- ``raise_taps`` = highStep - neutralStep, ``lower_taps`` = neutralStep - lowStep, ``regulation`` =
  stepVoltageIncrement x raise_taps, ``tap_pos_X`` = step - neutralStep on each of its phases;
- ``Type`` B for a ``construction`` typeB unit (GridLAB-D's out = in / (1 - tap x step), as the GLM importer reads
  it), else A (out = in x (1 + tap x step), CIM's ratio; ``regulator.cpp:316``);
- ``Control`` MANUAL when the TapChangerControl is disabled or absent, LINE_DROP_COMP with line drop compensation,
  else OUTPUT_VOLTAGE; ``band_center``/``band_width`` the target and deadband (primary volts; on LINE_DROP_COMP over
  ptRatio, as GridLAB-D reads it on the PT secondary), ``compensator_r/x_setting_X`` = lineDropR/X x ctRatio /
  ptRatio, ``current_transducer_ratio``/``power_transducer_ratio`` the CT and PT ratios, ``dwell_time`` the initial
  delay.
"""

from __future__ import annotations

import logging

import cimprofiles.cim18.cim18v17 as cim

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
}
_REGULATOR_SLOTS = {
    "name": Slot("written", "Names (X1)"),
    "phases": Slot("written", "the A, B, C of its end 1"),
    "from_node": Slot("written", "end 1's bus"), "to": Slot("written", "end 2's bus"),
    "configuration": Slot("written", "its regulator_configuration"),
    **{f"continuous_rating_{letter}": Slot("written", "get_current_limits normal") for letter in "ABC"},
    **{f"emergency_rating_{letter}": Slot("written", "get_current_limits emergency") for letter in "ABC"},
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
    slots = {}
    for regulator, phase_letters in group:
        taps = [end.RatioTapChanger for end in _ends(regulator) if end.RatioTapChanger is not None]
        if len(taps) != 1:
            raise ValueError(f"VoltageRegulator {regulator.mRID!r}: has {len(taps)} RatioTapChangers, not 1")
        _merge(slots, _configuration_slots(regulator, taps[0], phase_letters), regulator)
    phase_letters = "".join(sorted(letter for _, letters_on in group for letter in letters_on))
    configuration = schema.RegulatorConfiguration(name=context.names.name(first, suffix="_config", drop=drop),
                                                  **slots)
    record = schema.Regulator(name=context.names.name(first, drop=drop), phases=phase_letters,
                              from_node=context.buses[ends[0].Terminal.ConnectivityNode].name,
                              to=context.buses[ends[1].Terminal.ConnectivityNode].name,
                              configuration=configuration.name,
                              **ratings(first, phase_letters, schema.Regulator))
    return [configuration, record]


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
        return {**slots, "Control": "MANUAL", **_transducers(control)}
    line_drop = bool(settings.line_drop_compensation)
    pt_ratio = control.pt_ratio
    if line_drop and not pt_ratio:
        raise ValueError(f"RatioTapChanger {tap.mRID!r}: line drop compensation without a ptRatio")
    scale = 1 / pt_ratio if line_drop else 1.0
    slots.update(Control="LINE_DROP_COMP" if line_drop else "OUTPUT_VOLTAGE", band_center=control.target * scale,
                 band_width=None if control.deadband is None else control.deadband * scale, **_transducers(control))
    if line_drop:
        ct_ratio = control.ct_ratio
        for part, value in (("r", settings.line_drop.r), ("x", settings.line_drop.x)):
            if value is not None:
                for letter in phase_letters:
                    slots[f"compensator_{part}_setting_{letter}"] = value * ct_ratio / pt_ratio
    return slots


def _transducers(control) -> dict:
    if control is None:
        return {}
    return {"current_transducer_ratio": control.ct_ratio, "power_transducer_ratio": control.pt_ratio}
