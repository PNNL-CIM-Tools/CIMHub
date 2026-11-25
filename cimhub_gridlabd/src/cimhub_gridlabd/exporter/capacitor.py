"""LinearShuntCompensator -> GLM ``capacitor``, parented to its bus (``EXPORT_MAPPING.md#x3-loads-and-capacitors``;
the importer's S4a inverted).

``capacitor_X`` is each phase's Q at its nominal voltage with every section in (``get_shunt_reactive_power``,
``sections='maximum'``); ``cap_nominal_voltage`` that voltage per phase, line to neutral (a polyphase unit's nomU
over sqrt 3). ``switchX`` is CLOSED when the unit's actual sections are in. A unit's ``control`` is VOLT when its
RegulatingControl is a voltage control that is enabled (``voltage_set_low``/``high`` = the target -/+ half the
deadband, ``pt_phase`` the monitored phases, ``dwell_time`` the aVRDelay; ``control_level`` INDIVIDUAL on one phase,
BANK on more), else MANUAL. A control of another mode is written MANUAL at the unit's actual state and logged (GLM's
VAR, VARVOLT and CURRENT are not mapped either way yet, and GLM has no time control), as an LTC's control is (X5).
A delta unit raises: GLM's delta capacitor is not mapped either way yet. Units the GLM importer split from one
automatic INDIVIDUAL capacitor (one-phase units on one bus named ``<base>_<their phase>``, one of them with a
voltage control, S4a-8) are the GLM capacitor ``<base>`` again, VOLT on the phases whose units have a control
(``pt_phase``). Units with no control keep their names: a MANUAL ``cap_B`` is ``cap_B``.
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.export_slots import Slot, with_default
from cimhub_core.getters.control import get_equipment_control
from cimhub_core.getters.shunt import get_shunt_reactive_power
from cimhub_core.getters.terminals import get_conductor_phases, get_terminal_nodes
from cimhub_core.names import export_name
from cimhub_gridlabd.exporter.buses import letters
from cimhub_gridlabd.exporter.units import glm_unit
from cimhub_gridlabd.schema import gridlabd as schema

_log = logging.getLogger(__name__)

CIM_CLASSES = (cim.LinearShuntCompensator,)

SLOTS = {schema.Capacitor: with_default(schema.Capacitor, {
    "name": Slot("written", "Names (X1)"), "parent": Slot("written", "its bus"),
    "phases": Slot("written", "its letters then N"), "phases_connected": Slot("written", "as phases"),
    "nominal_voltage": Slot("written", "its bus's"),
    **{f"capacitor_{letter}": Slot("written", "get_shunt_reactive_power per phase, every section in") for letter in "ABC"},
    "cap_nominal_voltage": Slot("written", "nomU line to neutral (module docstring)"),
    **{f"switch{letter}": Slot("written", "CLOSED when the actual sections are in") for letter in "ABC"},
    "control": Slot("written", "VOLT for an enabled voltage RegulatingControl, else MANUAL"),
    "control_level": Slot("written", "VOLT: INDIVIDUAL on one phase, BANK on more"),
    "pt_phase": Slot("written", "VOLT: the monitored phases"),
    "voltage_set_low": Slot("written", "VOLT: target - deadband / 2"),
    "voltage_set_high": Slot("written", "VOLT: target + deadband / 2"),
    "dwell_time": Slot("written", "VOLT: aVRDelay"),
}, Slot("unset", "not in CIM; GridLAB-D's default"))}


def export(context) -> list:
    by_node, controls = defaultdict(list), {}
    for shunt in context.objects(*CIM_CLASSES):
        by_node[get_terminal_nodes(shunt)[0]].append(shunt)
        controls[shunt] = _control(shunt, letters(get_conductor_phases(shunt)))
    records = []
    for node, shunts in by_node.items():
        for units, drop in _groups(shunts, context.names, controls):
            records.append(_capacitor(units, drop, context.buses[node], context.names, controls))
    return records


def _groups(shunts: list, names, controls: dict) -> list[tuple[list, str]]:
    """``[(units, name ending to drop), ...]`` on one bus: a split capacitor's one-phase units ``<base>_<phase>``,
    one of them controlled, together (the importer's S4a-8 inverted), every other unit alone."""
    by_base, groups = defaultdict(list), []
    for shunt in shunts:
        phase_letters = letters(get_conductor_phases(shunt))
        text = export_name(shunt, names.source)
        if len(phase_letters) == 1 and text.endswith(f"_{phase_letters}"):
            by_base[text[:-2]].append((phase_letters, shunt))
        else:
            groups.append(([shunt], ""))
    for units in by_base.values():
        units.sort(key=lambda unit: unit[0])
        if len({letter for letter, _ in units}) != len(units) or not any(controls[shunt] for _, shunt in units):
            groups += [([shunt], "") for _, shunt in units]
        else:
            groups.append(([shunt for _, shunt in units], f"_{units[0][0]}"))
    return groups


def _capacitor(units: list, drop: str, bus, names, unit_controls: dict) -> schema.Capacitor:
    phase_letters, per_phase, voltages, controls = "", {}, set(), {}
    for shunt in units:
        rated = get_shunt_reactive_power(shunt, glm_unit(schema.Capacitor, "capacitor_A"), sections="maximum",
                                         voltage="nominal",
                                         voltage_unit=glm_unit(schema.Capacitor, "cap_nominal_voltage"))
        if rated.connection is cim.PhaseShuntConnectionKind.D:
            raise ValueError(f"LinearShuntCompensator {shunt.mRID!r}: a delta capacitor is not exported yet")
        unit_letters = letters(rated.phases)
        state = "CLOSED" if get_shunt_reactive_power(shunt, sections="actual", voltage="nominal").sections > 0 \
            else "OPEN"
        phase_letters += unit_letters
        voltages.add(round(rated.voltage / math.sqrt(3) if len(unit_letters) > 1 else rated.voltage, 6))
        for phase, q in rated.per_phase.items():
            per_phase[f"capacitor_{letters((phase,))}"] = q
            per_phase[f"switch{letters((phase,))}"] = state
        control = unit_controls[shunt]
        if control:
            controls[unit_letters] = dict(control)
    if len(voltages) != 1:
        raise ValueError(f"LinearShuntCompensators {[shunt.mRID for shunt in units]}: rated at {sorted(voltages)} V")
    phase_letters = "".join(sorted(phase_letters))
    slots = {"name": names.name(units[0], drop=drop), "parent": bus.name, "phases": phase_letters + "N",
             "phases_connected": phase_letters + "N", "nominal_voltage": bus.nominal_voltage,
             "cap_nominal_voltage": voltages.pop(), **per_phase}
    slots.update(_merged_control(units, controls, split=bool(drop)))
    return schema.Capacitor(**slots)


def _merged_control(units: list, controls: dict, *, split: bool) -> dict:
    """MANUAL without a control; else the units' one VOLT setting on the phases that have it."""
    if not controls:
        return {"control": "MANUAL"}
    monitored = "".join(sorted("".join(control.pop("pt_phase") for control in controls.values())))
    settings = {tuple(sorted(control.items())) for control in controls.values()}
    if len(settings) != 1:
        raise ValueError(f"LinearShuntCompensators {[shunt.mRID for shunt in units]}: different VOLT settings")
    level = "INDIVIDUAL" if split or all(len(unit_letters) == 1 for unit_letters in controls) else "BANK"
    return {"control": "VOLT", "control_level": level, "pt_phase": monitored, **dict(next(iter(settings)))}


def _control(shunt: cim.LinearShuntCompensator, unit_letters: str) -> dict | None:
    """A unit's VOLT settings, or None when it has no enabled voltage control; ``pt_phase`` is the monitored phases
    (a BANK capacitor senses one phase, S4a), else the unit's own."""
    control = get_equipment_control(shunt, time_unit=glm_unit(schema.Capacitor, "dwell_time"))
    if control is None or control.control.enabled is False or control.control_enabled is False:
        return None
    settings = control.control
    if settings.mode is not cim.RegulatingControlModeKind.voltage:
        _log.warning("LinearShuntCompensator %s: a %s control has no GLM form; written MANUAL at its actual state",
                     shunt.mRID, settings.mode.value)
        return None
    if settings.deadband is None:
        raise ValueError(f"LinearShuntCompensator {shunt.mRID!r}: a voltage control without a deadband")
    monitored = letters(settings.monitored_phases) if settings.monitored_phases else unit_letters
    return {"pt_phase": monitored, "voltage_set_low": settings.target - settings.deadband / 2,
            "voltage_set_high": settings.target + settings.deadband / 2, "dwell_time": control.delay}
