"""GLM ``capacitor`` -> ``capacitor.cimtbl``: ``LinearShuntCompensator`` units and their ``RegulatingControl`` (S4a).

GridLAB-D switches each capacitor phase on its own (``switchA``/``B``/``C``). Under ``control_level INDIVIDUAL`` (the
default) VOLT switches only the ``pt_phase`` phases, each on its own phase voltage, and leaves the others at their
initial state (``capacitor.cpp:1180-1205``). So a unit is a set of phases that switch together (S4a-8, the user's
option (a)): a MANUAL capacitor is one gang unit, an automatic INDIVIDUAL one is a 1-phase unit per connected phase
(``cap_<name>_<phase>``), with a control on the ``pt_phase`` units only, and BANK is one gang unit. A unit is wye and
grounded (S4a-11); ``nomU`` is the phase-to-neutral rating, x sqrt 3 on 2-3 phases, and ``bPerSection`` = nomQ /
nomU^2 (S4a-10). ``sections`` is the switch state GridLAB-D starts with, OPEN when unset (S4a-9).

Mapping spec: ``cimhub_gridlabd/docs/CIMTBL_MAPPING.md#s4a-loads-and-capacitors``; the cross-solver note there says
where these units differ from a DSS CapControl.
"""

from __future__ import annotations

from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimprofiles.units import units
from cimtables.document import Column, Document, Row, Table
from cimtopology.core import BusSystem, System

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, fill_defaults, mrid, phases_cell, untranscribed_values
from cimhub_core.derived.control_band import band_from_on_off
from cimhub_gridlabd.glm_reader import GlmModel
from cimhub_gridlabd.glm_schema import registry_unit
from cimhub_gridlabd.importer.cimtbl import bus
from cimhub_gridlabd.importer.cimtbl.catalog import label
from cimhub_gridlabd.importer.cimtbl.link import provenance
from cimhub_gridlabd.importer.topology import line_voltage
from cimhub_gridlabd.schema import gridlabd as schema

NATIVE_CLASS = schema.Capacitor
PREFIX = "cap_"
CONTROL_PREFIX = "cc_"
ANCHOR = "s4a-loads-and-capacitors"

_SHUNT = "LinearShuntCompensator"
_CONTROL = "RegulatingControl"
_NOT_MAPPED = "raises when set: no deck sets it, so a mapping waits for one"
#: GridLAB-D's ``capacitor::create()`` values for the slots the mapper reads (``capacitor.cpp:151-195``).
DEFAULTS = {"control": "MANUAL", "control_level": "INDIVIDUAL", "switchA": "OPEN", "switchB": "OPEN",
            "switchC": "OPEN", "dwell_time": 0.0, "time_delay": 0.0}
#: The ``control`` modes mapped; VAR, VARVOLT and CURRENT raise.
CONTROLS = ("MANUAL", "VOLT")

#: The capacitor's own slots (its row comments list their untranscribed values); its bus slots are counted on the
#: table comment.
OWN = {
    "phases_connected": Field("structural", note="the connected phases (else phases): wye, grounded with or "
                                                 "without N (S4a-11); D raises"),
    "pt_phase": Field("structural", note="VOLT: the units that get a control (INDIVIDUAL) or the gang unit's "
                                         "monitored phase (BANK); D raises"),
    **{f"switch{letter}": Field("derived", note="sections = normalSections: 1 CLOSED, 0 OPEN; default OPEN "
                                                "(S4a-9); a gang unit's must agree") for letter in "ABC"},
    "control": Field("structural", note="VOLT: a RegulatingControl; MANUAL (default): none; VAR, VARVOLT, "
                                        "CURRENT raise"),
    "control_level": Field("structural", note="the units (S4a-8): INDIVIDUAL (default) VOLT is a unit per phase"),
    **{f"cap_{letter}_switch_count": Field("untranscribed", note="solver output") for letter in "ABC"},
    "voltage_set_high": Field("derived", note="targetValue = the midpoint, targetDeadband = high - low "
                                              "(band_from_on_off); opens at or above it"),
    "voltage_set_low": Field("derived", note="with voltage_set_high; closes at or below it"),
    **{f"{kind}_deadband_center": Field("structural", note=_NOT_MAPPED) for kind in ("voltage", "VAr", "current")},
    **{f"{kind}_deadband": Field("structural", note=_NOT_MAPPED) for kind in ("voltage", "VAr", "current")},
    **{f"{kind}_set_{side}": Field("untranscribed", note="read only by the VAR, VARVOLT and CURRENT modes")
       for kind in ("VAr", "current") for side in ("high", "low")},
    **{f"capacitor_{letter}": Field("derived", note="the phase's VAr via pint: nomQ = the unit's sum, bPerSection "
                                                    "= nomQ / nomU^2 (S4a-10); on a phase not connected: dropped, "
                                                    "GridLAB-D ignores it (capacitor.cpp:1447)")
       for letter in "ABC"},
    "cap_nominal_voltage": Field("derived", note="nomU: the phase-to-neutral rating (else nominal_voltage, "
                                                 "capacitor.cpp:376), x sqrt 3 on 2-3 phases"),
    "time_delay": Field("derived", note="aVRDelay = dwell_time + time_delay (s), as S3c-5"),
    "dwell_time": Field("derived", note="with time_delay"),
    "lockout_time": Field("untranscribed", note="read only by VARVOLT"),
    "remote_sense": Field("structural", note=_NOT_MAPPED),
    "remote_sense_B": Field("structural", note=_NOT_MAPPED),
}
FIELDS = bus.classify(NATIVE_CLASS, OWN)


class _Unit(NamedTuple):
    """One LinearShuntCompensator: its mRID suffix, its phases and whether a control switches it."""
    suffix: str
    letters: str
    controlled: bool


def _letters(text) -> str:
    return "".join(letter for letter in "ABC" if letter in str(text or ""))


def check(cap) -> None:
    """What is not mapped (S4a fail fast)."""
    if str(cap.control) not in CONTROLS:
        raise ValueError(f"{label(cap)}: control {cap.control}; {', '.join(CONTROLS)} are mapped")
    for slot in ("phases_connected", "pt_phase"):
        if "D" in str(getattr(cap, slot) or ""):
            raise ValueError(f"{label(cap)}: {slot} {getattr(cap, slot)}; a delta capacitor is not mapped (S4a-11)")
    for slot in ("remote_sense", "remote_sense_B", *(f"{kind}_deadband{part}" for kind in ("voltage", "VAr", "current")
                                                      for part in ("", "_center"))):
        value = getattr(cap, slot)
        if value is not None and not (isinstance(value, float) and value < 0):  # GridLAB-D's unset deadband is -1
            raise ValueError(f"{label(cap)}: {slot} {value}; not mapped")


def units_of(cap) -> list[_Unit]:
    """The phases that switch together (S4a-8): MANUAL and BANK one gang unit, INDIVIDUAL VOLT one per phase."""
    connected = _letters(cap.phases_connected or cap.phases)
    if not connected:
        raise ValueError(f"{label(cap)}: no phase connected")
    automatic = str(cap.control) == "VOLT"
    monitored = _letters(cap.pt_phase)
    if automatic:
        if not monitored or set(monitored) - set(connected):
            raise ValueError(f"{label(cap)}: pt_phase {cap.pt_phase or 'unset'} must name connected phases of "
                             f"{connected}")
        if cap.voltage_set_low is None or cap.voltage_set_high is None:
            raise ValueError(f"{label(cap)}: VOLT without voltage_set_low and voltage_set_high")
    if automatic and str(cap.control_level) == "INDIVIDUAL":
        return [_Unit(f"_{letter}", letter, letter in monitored) for letter in connected]
    if automatic and len(monitored) != 1:
        raise ValueError(f"{label(cap)}: a BANK monitors one phase, pt_phase is {cap.pt_phase}")
    states = {str(getattr(cap, f"switch{letter}")) for letter in connected}
    if len(states) > 1:
        raise ValueError(f"{label(cap)}: switch states {sorted(states)} differ on a gang unit (MANUAL or BANK)")
    return [_Unit("", connected, automatic)]


def _quantity(model: GlmModel, record, slot: str, unit: str) -> float:
    return units.Quantity(float(getattr(record, slot)), registry_unit(model.unit(record, slot))).to(unit).magnitude


def _phase_vars(model: GlmModel, cap, letters: str) -> list[float]:
    """Each phase's capacitor_X in VAr, from the unit it is written in (CIMUnit: pint has no var)."""
    values = []
    for letter in letters:
        slot = f"capacitor_{letter}"
        if not getattr(cap, slot):
            raise ValueError(f"{label(cap)}: {slot} unset or 0 on a connected phase")
        values.append(float(cim.ReactivePower(float(getattr(cap, slot)), model.unit(cap, slot)).to("VAr")))
    return values


def _comment(model: GlmModel, cap, defaulted: str | None, connected: str) -> str | None:
    parts = [defaulted, untranscribed_values(OWN, cap)]
    dropped = [f"capacitor_{letter}={cell(getattr(cap, f'capacitor_{letter}'))} {model.unit(cap, f'capacitor_{letter}')}"
               for letter in "ABC"
               if letter not in connected and getattr(cap, f"capacitor_{letter}") is not None]
    if dropped:
        parts.append(f"not connected (GridLAB-D ignores it): {', '.join(dropped)}")
    if str(cap.control) == "MANUAL":
        unread = [f"{slot}={cell(getattr(cap, slot))}" for slot in ("pt_phase", "voltage_set_low", "voltage_set_high")
                  if getattr(cap, slot) is not None]
        if unread:
            parts.append(f"MANUAL: not read: {', '.join(unread)}")
    return "\n".join(part for part in parts if part) or None


class _Rows:
    def __init__(self):
        self.shunts: list[Row] = []
        self.controls: list[Row] = []
        self.updates: list[Row] = []


def _capacitor(model: GlmModel, cap, roots: dict[str, str], buses: dict[str, BusSystem], rows: _Rows) -> None:
    connected = _letters(cap.phases_connected or cap.phases)
    unconnected = {f"switch{letter}" for letter in "ABC" if letter not in connected}
    cap, defaulted = fill_defaults(FIELDS, cap, {slot: value for slot, value in DEFAULTS.items()
                                                if slot not in unconnected})
    check(cap)
    node = roots[str(cap.name)]
    rating_slot = "cap_nominal_voltage" if cap.cap_nominal_voltage else "nominal_voltage"
    if not getattr(cap, rating_slot):
        raise ValueError(f"{label(cap)}: no cap_nominal_voltage and no nominal_voltage (capacitor.cpp:380)")
    coil = _quantity(model, cap, rating_slot, "V")
    delay = _quantity(model, cap, "dwell_time", "s") + _quantity(model, cap, "time_delay", "s")
    comment = _comment(model, cap, defaulted, connected)
    for index, unit in enumerate(units_of(cap)):
        name = f"{cap.name}{unit.suffix}"
        shunt = mrid(PREFIX, name)
        phase_vars = _phase_vars(model, cap, unit.letters)
        if len(set(phase_vars)) > 1:
            raise ValueError(f"{label(cap)}: phases {unit.letters} differ ({phase_vars} VAr) on a gang unit; a "
                             "per-phase rating is not mapped (S4a-10)")
        nom_q = sum(phase_vars)
        nom_u = coil if len(unit.letters) == 1 else line_voltage(coil, System.THREE_PHASE)
        sections = 1 if str(getattr(cap, f"switch{unit.letters[0]}")) == "CLOSED" else 0
        rows.shunts.append(Row([shunt, name, node, phases_cell(unit.letters), cell(nom_q), cell(nom_u),
                                cell(nom_q / nom_u ** 2), str(sections), str(sections), buses[node].base_voltage],
                               comment=comment if index == 0 else None))
        if not unit.controlled:
            continue
        control = mrid(CONTROL_PREFIX, name)
        target, deadband = band_from_on_off(_quantity(model, cap, "voltage_set_low", "V"),
                                            _quantity(model, cap, "voltage_set_high", "V"))
        monitored = unit.letters if len(unit.letters) == 1 else _letters(cap.pt_phase)
        rows.controls.append(Row([control, name, monitored, cell(target), cell(deadband), f"{shunt}_T1"]))
        rows.updates.append(Row([shunt, control, cell(delay)]))


def map_capacitors(model: GlmModel, roots: dict[str, str], buses: dict[str, BusSystem], feeder: str) -> Document:
    """Every capacitor as one document: the units, then the controls and the units' control references."""
    capacitors = model.list_by_class(NATIVE_CLASS)
    if not capacitors:
        return Document(name=NATIVE_CLASS.class_name, statements=[], profile=CIM_PROFILE)
    rows = _Rows()
    for cap in capacitors:
        _capacitor(model, cap, roots, buses, rows)
    counted = bus.untranscribed_set(model, capacitors, {NATIVE_CLASS: bus.inherited(FIELDS, OWN)})
    statements = [Table(_SHUNT, [Column("mRID"), Column("name"), Column("node"), Column("phases"),
                                 Column("phaseConnection", default="Y"), Column("grounded", default="true"),
                                 Column("nomQ", "VAr"), Column("nomU", "V"), Column("bPerSection", "S"),
                                 Column("sections"), Column("normalSections"), Column("maximumSections", default="1"),
                                 Column("BaseVoltage"), Column("EquipmentContainer", default=feeder)], rows.shunts,
                        comment="\n".join(part for part in (
                            "a unit per set of phases that switch together (S4a-8); sections: the switch state "
                            "GridLAB-D starts with, OPEN when unset (S4a-9)", counted) if part))]
    if rows.controls:
        statements.append(Table(_CONTROL, [Column("mRID"), Column("name"), Column("mode", default="voltage"),
                                           Column("discrete", default="true"), Column("enabled", default="true"),
                                           Column("monitoredPhase"), Column("targetValue"), Column("targetDeadband"),
                                           Column("Terminal")], rows.controls,
                                comment="VOLT: the unit's own terminal, primary phase-to-neutral volts, no PT; "
                                        "closes at or below target - deadband/2, opens at or above target + "
                                        "deadband/2 (capacitor.cpp:1180)"))
        statements.append(Table(_SHUNT, [Column("mRID"), Column("RegulatingControl"), Column("aVRDelay", "s"),
                                         Column("controlEnabled", default="true")], rows.updates, update=True,
                                comment="aVRDelay = dwell_time + time_delay"))
    header = provenance(NATIVE_CLASS.class_name, "LinearShuntCompensator + RegulatingControl", len(capacitors),
                        ANCHOR)
    return Document(name=NATIVE_CLASS.class_name, statements=statements, profile=CIM_PROFILE, comment=header)
