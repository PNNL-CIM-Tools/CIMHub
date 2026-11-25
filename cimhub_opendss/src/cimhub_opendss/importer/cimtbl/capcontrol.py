"""OpenDSS ``CapControl`` -> ``capcontrol.cimtbl``: one ``RegulatingControl`` per control.

The control monitors a Terminal of a Line or of its own capacitor, which ``Line``/``Capacitor`` generate first.
Its ON and OFF settings become a target and a deadband in primary units (EPRI ExportCIMXML's convention):
targetValue = (ON + OFF) / 2 and targetDeadband = abs(OFF - ON), each x PTratio (voltage), x CTratio (current) or
in kvar with ``targetValueUnitMultiplier`` k (kvar). The compensator gets ``RegulatingControl``, ``aVRDelay`` and
``controlEnabled`` by an ``Update``, which also breaks the reference cycle of a control on its own capacitor (U3).

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md#capcontrol``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import NamedTuple

from cimtables.document import Column, Document, Row, Table
from cimtopology.core import BusSystem

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, fill_defaults, mrid, untranscribed_values
from cimhub_core.derived.control_band import band_from_on_off
from cimhub_opendss.dss_reader import dss_defaults
from cimhub_opendss.importer.cimtbl import capacitor as capacitor_mapper
from cimhub_opendss.importer.cimtbl import line as line_mapper
from cimhub_opendss.importer.cimtbl.injection import device_terminal, is_delta
from cimhub_opendss.schema import opendss_schema as schema

NATIVE_CLASS = schema.Capcontrol
PREFIX = "cc_"

_CONTROL = "RegulatingControl"
_SHUNT = "LinearShuntCompensator"
_NOT_MAPPED = "raises when set: no deck in the sweep sets it, so a mapping waits for one"
_SOLVER = "DSS solution control; no home in the network profile parts"
_SETTING = ("{target} = {formula} (on_off_target); voltage x PTratio (V), current x CTratio (A), kvar in kvar "
            "(targetValueUnitMultiplier k), time in hours")

FIELDS = {
    "name": Field("copied", ((_CONTROL, "name", None),), "mRID = cc_ + name, lowercased"),
    "element": Field("structural", note="Terminal = ln_<line>_T<n> (sw_ for a switch) or cap_<capacitor>_T<n>; "
                                        "another element class raises"),
    "terminal": Field("structural", note="the element's terminal; default 1"),
    "capacitor": Field("structural", note="the Update row: LinearShuntCompensator cap_<capacitor> gets "
                                          "RegulatingControl; a capacitor no New defines raises"),
    "type": Field("mapped", ((_CONTROL, "mode", None),),
                  "voltage -> voltage, current -> currentFlow, kvar -> reactivePower, time -> timeScheduled "
                  "(a unique prefix, as the engine reads it: J1's volt); PF and Follow raise; default current"),
    "PTratio": Field("copied", ((_CONTROL, "ptRatio", None),), "default 60"),
    "CTratio": Field("copied", ((_CONTROL, "ctRatio", None),), "default 60"),
    "ONsetting": Field("derived", note=_SETTING.format(target="targetValue", formula="(ON + OFF) / 2")
                                      + "; ON on the wrong side of OFF for the type raises; default 300"),
    "OFFsetting": Field("derived", note=_SETTING.format(target="targetDeadband", formula="abs(OFF - ON)")
                                       + "; default 200"),
    "Delay": Field("copied", ((_SHUNT, "aVRDelay", "s"),), "on the Update row; default 15"),
    "VoltOverride": Field("untranscribed", note="a voltage override band of a kvar/current control; no home "
                                                "(maxAllowedTargetValue limits the target, not the voltage)"),
    "Vmax": Field("untranscribed", note="the VoltOverride band (V on the PT secondary)"),
    "Vmin": Field("untranscribed", note="the VoltOverride band (V on the PT secondary)"),
    "DelayOFF": Field("untranscribed", note="CIM has one aVRDelay (Delay); " + _SOLVER),
    "DeadTime": Field("untranscribed", note=_SOLVER),
    "CTPhase": Field("structural", note=_NOT_MAPPED),
    "PTPhase": Field("structural", note="monitoredPhase = the phase of the monitored terminal's conductor "
                                        "PTPhase (default 1); AVG/MAX/MIN raise"),
    "VBus": Field("structural", note=_NOT_MAPPED + " (remote voltage sensing)"),
    "EventLog": Field("untranscribed", note="DSS report flag"),
    "UserModel": Field("structural", note=_NOT_MAPPED),
    "UserData": Field("structural", note=_NOT_MAPPED),
    "pctMinkvar": Field("untranscribed", note="used only by PF control, which raises"),
    "Reset": Field("untranscribed", note="a command, not a setting"),
    "ControlSignal": Field("structural", note=_NOT_MAPPED),
    "basefreq": Field("untranscribed", note="no home on a control"),
    "enabled": Field("copied", ((_CONTROL, "enabled", None), (_SHUNT, "controlEnabled", None)),
                     "default true; controlEnabled on the Update row"),
    "like": Field("untranscribed", note="the reader resolves like= before mapping"),
}

_UNMAPPED = tuple(slot for slot, field in FIELDS.items() if field.note.startswith(_NOT_MAPPED))

#: DSS control type -> RegulatingControlModeKind; ``None``: not mapped. The engine reads a unique prefix.
_MODES = {"current": "currentFlow", "voltage": "voltage", "kvar": "reactivePower", "time": "timeScheduled",
          "pf": None, "follow": None}
#: targetValueUnitMultiplier by mode: a kvar control's settings stay in kvar (k VAr); the others' are V, A or hours.
_KVAR_MULTIPLIER = {"reactivePower": "k"}
#: Modes whose ON setting is above OFF (switch on when the measured value rises); the others' is below.
_ON_ABOVE = ("currentFlow", "reactivePower")
_PHASE_TOKEN = re.compile(r"s[12]|[ABC]")

_PROVENANCE = """OpenDSS CapControl -> RegulatingControl on the monitored Terminal; the compensator gets it, its
delay and controlEnabled by an Update. targetValue = (ON + OFF) / 2, targetDeadband = abs(OFF - ON), in
primary units: voltage x PTratio (V), current x CTratio (A), kvar in kvar (targetValueUnitMultiplier k), time in
hours from midnight.
Source table: CapControl (records: {count})
Mapping: cimhub_opendss/docs/CIMTBL_MAPPING.md#capcontrol"""


class Setting(NamedTuple):
    """A control's target and deadband, in primary units."""

    target: float
    deadband: float


def control_mode(control_type, *, name: str) -> str:
    """The RegulatingControlModeKind of a DSS control type (a unique prefix, as the engine reads ``volt``)."""
    text = str(getattr(control_type, "text", control_type)).lower()
    matches = [key for key in _MODES if key.startswith(text)]
    if len(matches) != 1:
        raise ValueError(f"CapControl {name}: type={control_type} is not one DSS control type")
    mode = _MODES[matches[0]]
    if mode is None:
        raise ValueError(f"CapControl {name}: type={matches[0]} is not mapped")
    return mode


def on_off_target(on: float, off: float, mode: str, *, ptratio: float, ctratio: float, name: str) -> Setting:
    """The midpoint and full width of the ON/OFF band (EPRI ExportCIMXML's convention, the width positive), in
    primary units: V, A, kvar (as the deck gives it) or hours. ON on the wrong side of OFF for the mode raises, so
    the pair can be rebuilt from the mode."""
    if (on < off) if mode in _ON_ABOVE else (on > off):
        side = "above" if mode in _ON_ABOVE else "below"
        raise ValueError(f"CapControl {name}: ON {on} is not {side} OFF {off} for a {mode} control")
    scale = {"voltage": ptratio, "currentFlow": ctratio, "reactivePower": 1.0, "timeScheduled": 1.0}[mode]
    return Setting(*band_from_on_off(on * scale, off * scale))


def _line_phase_count(line, native) -> int:
    """A line's phases: its own, else its LineCode's or LineGeometry's ``nphases``, else the DSS default 3."""
    if line.phases is not None:
        return int(line.phases)
    for slot, native_class in (("linecode", schema.Linecode), ("geometry", schema.Linegeometry)):
        name = getattr(line, slot)
        if name:
            template = {str(t.name).lower(): t for t in native.list_by_class(native_class)}.get(str(name).lower())
            if template is not None and template.nphases is not None:
                return int(template.nphases)
    return 3


def _monitored(control, native, buses, capacitors) -> tuple[str, str]:
    """``(Terminal mRID, its phases)`` of the element the control monitors: a Line or a Capacitor."""
    kind, _, element = str(control.element).partition(".")
    kind, key = kind.lower(), element.lower()
    terminal = int(control.terminal)
    if kind == "line":
        lines = {str(line.name).lower(): line for line in native.list_by_class(schema.Line)}
        if key not in lines:
            raise ValueError(f"CapControl {control.name}: element={control.element} is no Line")
        line = lines[key]
        _, _, phases = line_mapper.line_phases(line, _line_phase_count(line, native), buses)
        prefix = line_mapper.SWITCH_PREFIX if line.Switch else line_mapper.PREFIX
        return f"{mrid(prefix, line.name, lowercase=True)}_T{terminal}", phases
    if kind == "capacitor":
        if key not in capacitors:
            raise ValueError(f"CapControl {control.name}: element={control.element} is no Capacitor")
        capacitor = capacitors[key]
        phases = device_terminal(f"Capacitor {capacitor.name}", capacitor.bus1, int(capacitor.phases),
                                 is_delta(capacitor.conn), buses).phases
        return f"{mrid(capacitor_mapper.PREFIX, capacitor.name, lowercase=True)}_T{terminal}", phases
    raise ValueError(f"CapControl {control.name}: element={control.element}; only a Line or a Capacitor terminal "
                     "is mapped")


def map_capcontrol(native, buses: Mapping[str, BusSystem]) -> Document:
    """Every ``CapControl`` of a DSS model as one ``capcontrol`` document."""
    controls = native.list_by_class(NATIVE_CLASS)
    if not controls:
        return Document(name="capcontrol", statements=[], profile=CIM_PROFILE)
    capacitor_defaults = dss_defaults(schema.Capacitor)
    capacitors = {str(c.name).lower(): fill_defaults(capacitor_mapper.FIELDS, c, capacitor_defaults)[0]
                  for c in native.list_by_class(schema.Capacitor)}
    control_rows, update_rows, controlled = [], [], {}
    for original in controls:
        unmapped = [slot for slot in _UNMAPPED if getattr(original, slot) not in (None, [])]
        if unmapped:
            raise ValueError(f"CapControl {original.name}: {', '.join(unmapped)} not mapped yet (no deck in the "
                             "sweep sets them)")
        control, defaulted = fill_defaults(FIELDS, original, dss_defaults(NATIVE_CLASS))
        key = str(control.capacitor).lower()
        if key not in capacitors:
            raise ValueError(f"CapControl {control.name}: capacitor={control.capacitor} is no Capacitor")
        if key in controlled:
            raise ValueError(f"Capacitor {control.capacitor}: controlled by CapControls {controlled[key]} and "
                             f"{control.name}")
        controlled[key] = control.name
        mode = control_mode(control.type, name=control.name)
        terminal, phases = _monitored(control, native, buses, capacitors)
        tokens = _PHASE_TOKEN.findall(phases)
        pt_phase = int(control.PTPhase)
        if not 1 <= pt_phase <= len(tokens):
            raise ValueError(f"CapControl {control.name}: PTPhase={pt_phase} on a terminal with phases {phases}")
        ptratio, ctratio = float(control.PTratio), float(control.CTratio)
        setting = on_off_target(float(control.ONsetting), float(control.OFFsetting), mode, ptratio=ptratio,
                                ctratio=ctratio, name=control.name)
        control_id = mrid(PREFIX, control.name, lowercase=True)
        derived = f"derived from ON={cell(float(control.ONsetting))}, OFF={cell(float(control.OFFsetting))}"
        comment = "\n".join(part for part in (derived, defaulted, untranscribed_values(FIELDS, control)) if part)
        control_rows.append(Row([
            control_id, str(control.name), mode, cell(control.enabled), tokens[pt_phase - 1], cell(ptratio),
            cell(ctratio), cell(setting.target), cell(setting.deadband), _KVAR_MULTIPLIER.get(mode), terminal,
        ], comment=comment))
        update_rows.append(Row([mrid(capacitor_mapper.PREFIX, control.capacitor, lowercase=True), control_id,
                                cell(float(control.Delay)), cell(control.enabled)]))
    statements = [
        Table(_CONTROL, [Column("mRID"), Column("name"), Column("mode"), Column("discrete", default="true"),
                         Column("enabled"), Column("monitoredPhase"), Column("ptRatio"), Column("ctRatio"),
                         Column("targetValue"), Column("targetDeadband"), Column("targetValueUnitMultiplier"),
                         Column("Terminal")], control_rows),
        Table(_SHUNT, [Column("mRID"), Column("RegulatingControl"), Column("aVRDelay", "s"),
                       Column("controlEnabled")], update_rows, update=True,
              comment="the compensator's control, delay (Delay) and controlEnabled"),
    ]
    return Document(name="capcontrol", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(controls)))
