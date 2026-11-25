"""OpenDSS ``RegControl`` -> ``regcontrol.cimtbl``: one ``RatioTapChanger`` + ``TapChangerControl`` per control.

The tap changer goes on the controlled winding's end of the transformer the control names: an
``AutoTransformerEnd`` of a ``VoltageRegulator`` (equal winding kV) or a ``PowerTransformerEnd`` of an LTC
(DSS-13). The control monitors that end's Terminal. Settings DSS gives on the 120 V PT secondary become primary
volts (x ``ptratio``) and line-drop ohms (x ``ptratio`` / ``CTprim``). ``step`` is a tap position, never a ratio.

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md#regcontrol``.
"""

from __future__ import annotations

from typing import NamedTuple

from cimtables.document import Column, Document, Row, Table

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, fill_defaults, mrid, untranscribed_values
from cimhub_core.derived.regulator import line_drop_ohms, secondary_to_primary
from cimhub_opendss.dss_reader import dss_defaults
from cimhub_opendss.importer.cimtbl import transformer as transformer_mapper
from cimhub_opendss.schema import opendss_schema as schema

NATIVE_CLASS = schema.Regcontrol
PREFIX = "rc_"

_CONTROL = "TapChangerControl"
_TAP = "RatioTapChanger"
_NOT_MAPPED = "raises when set: no deck in the sweep sets it, so a mapping waits for one"
_SOLVER = "DSS solution control; no home in the network profile parts"
_PT_VOLTS = "{target} (V) = {slot} x ptratio (secondary_to_primary); default {default}"
_LDC_OHMS = "{target} (ohm) = {slot} x ptratio / CTprim (line_drop_ohms); default 0"

FIELDS = {
    "name": Field("copied", ((_CONTROL, "name", None), (_TAP, "name", None)),
                  "mRID = rc_ + name (control) and rc_ + name + _tap (tap changer), lowercased"),
    "transformer": Field("structural", note="the regulator or LTC (DSS-13); a Transformer no New defines, or one "
                                            "two RegControls name, raises"),
    "winding": Field("structural", note="RatioTapChanger.TransformerEnd = xf_<transformer>_<winding>; "
                                        "TapChangerControl.Terminal = xf_<transformer>_T<winding>; default 1"),
    "tapwinding": Field("structural", note=_NOT_MAPPED + " (a tap winding other than the monitored one)"),
    "bus": Field("structural", note=_NOT_MAPPED + " (remote sensing; 1 RegControl in the sweep, which raises)"),
    "PTphase": Field("structural", note="TapChangerControl.monitoredPhase = the phase of the winding's conductor "
                                        "PTphase (default 1); MAX/MIN raise"),
    "vreg": Field("derived", note=_PT_VOLTS.format(target="targetValue", slot="vreg", default=120)),
    "band": Field("derived", note=_PT_VOLTS.format(target="targetDeadband", slot="band", default=3)),
    "ptratio": Field("copied", ((_CONTROL, "ptRatio", None), (_TAP, "ptRatio", None)), "default 60"),
    "CTprim": Field("copied", ((_TAP, "ctRating", "A"),),
                    "default 300; also ctRatio = CTprim / 0.2 (the DSS CT secondary, 0.2 A) and the LDC base"),
    "R": Field("derived", note=_LDC_OHMS.format(target="lineDropR", slot="R")
                               + "; lineDropCompensation = R or X nonzero"),
    "X": Field("derived", note=_LDC_OHMS.format(target="lineDropX", slot="X")),
    "delay": Field("copied", ((_TAP, "initialDelay", "s"),), "default 15"),
    "tapdelay": Field("copied", ((_TAP, "subsequentDelay", "s"),), "default 2"),
    "reversible": Field("copied", ((_CONTROL, "reversible", None),), "default false"),
    "revvreg": Field("derived", note=_PT_VOLTS.format(target="reverseTargetValue", slot="revvreg", default=120)),
    "revband": Field("derived", note=_PT_VOLTS.format(target="reverseTargetDeadband", slot="revband", default=3)),
    "revR": Field("derived", note=_LDC_OHMS.format(target="reverseLineDropR", slot="revR")),
    "revX": Field("derived", note=_LDC_OHMS.format(target="reverseLineDropX", slot="revX")),
    "revThreshold": Field("copied", ((_CONTROL, "reversingPowerThreshold", "kW"),), "default 100"),
    "revDelay": Field("copied", ((_CONTROL, "reversingDelay", "s"),), "default 60"),
    "revNeutral": Field("copied", ((_CONTROL, "reverseToNeutral", None),), "default false"),
    "vlimit": Field("structural", note=_NOT_MAPPED + " (home TapChangerControl.maxLimitVoltage)"),
    "maxtapchange": Field("untranscribed", note=_SOLVER),
    "inversetime": Field("untranscribed", note=_SOLVER),
    "debugtrace": Field("untranscribed", note="DSS report flag"),
    "EventLog": Field("untranscribed", note="DSS report flag"),
    "Reset": Field("untranscribed", note="a command, not a setting"),
    "TapNum": Field("structural", note=_NOT_MAPPED + " (a tap position that overrides the transformer's tap)"),
    "RemotePTRatio": Field("structural", note=_NOT_MAPPED),
    "LDC_Z": Field("structural", note=_NOT_MAPPED),
    "rev_Z": Field("structural", note=_NOT_MAPPED),
    "Cogen": Field("structural", note=_NOT_MAPPED),
    "idle": Field("structural", note=_NOT_MAPPED),
    "idleReverse": Field("structural", note=_NOT_MAPPED),
    "idleForward": Field("structural", note=_NOT_MAPPED),
    "basefreq": Field("untranscribed", note="no home on a control"),
    "enabled": Field("copied", ((_CONTROL, "enabled", None), (_TAP, "controlEnabled", None)), "default true"),
    "like": Field("untranscribed", note="the reader resolves like= before mapping"),
}


#: The DSS CT secondary rating: CTprim amps on the primary are 0.2 A on the control.
CT_SECONDARY_AMPS = 0.2
_UNMAPPED = tuple(slot for slot, field in FIELDS.items() if field.note.startswith(_NOT_MAPPED))
_TAP_DEFAULTS = ("MaxTap", "MinTap", "NumTaps")

_PROVENANCE = """OpenDSS RegControl -> TapChangerControl + RatioTapChanger on the controlled end (DSS-13).
Settings on the 120 V PT secondary are primary volts (x ptratio); line drop ohms = volts x ptratio / CTprim.
Source table: RegControl (records: {count})
Mapping: cimhub_opendss/docs/CIMTBL_MAPPING.md#regcontrol"""


def ct_ratio(ct_primary: float) -> float:
    return ct_primary / CT_SECONDARY_AMPS


class TapRange(NamedTuple):
    low: int
    high: int
    step: int
    increment_percent: float


def _whole(value: float, *, what: str, name: str) -> int:
    rounded = round(value)
    if abs(value - rounded) > 1e-6:
        raise ValueError(f"Transformer {name}: {what} {value:g} is not a whole tap step")
    return rounded


def tap_range(tap: float, max_tap: float, min_tap: float, num_taps: int, *, name: str) -> TapRange:
    """The tap changer's steps from DSS's per-unit tap range: increment (MaxTap - MinTap) / NumTaps, neutral at 1."""
    increment = (max_tap - min_tap) / num_taps
    return TapRange(-_whole((1 - min_tap) / increment, what="MinTap", name=name),
                    _whole((max_tap - 1) / increment, what="MaxTap", name=name),
                    _whole((tap - 1) / increment, what="tap", name=name), float(f"{increment * 100:.12g}"))


def _phase_letter(winding, phases: int, pt_phase: str, *, name: str) -> str:
    """The phase of the winding's conductor ``PTphase`` (1-based; DSS also takes MAX and MIN, which raise)."""
    if phases == 3:
        if pt_phase not in ("1", "2", "3"):
            raise ValueError(f"RegControl {name}: PTphase={pt_phase}")
        return "ABC"[int(pt_phase) - 1]
    phase_nodes = [node for node in winding.nodes if node in (1, 2, 3)]
    if pt_phase != "1" or not phase_nodes:
        raise ValueError(f"RegControl {name}: PTphase={pt_phase} on a 1-phase winding {winding.nodes}")
    return "ABC"[phase_nodes[0] - 1]


def _end_number(windings, phases: int, number: int, regulator: bool, *, name: str) -> int:
    """The end the winding is on: the winding itself on a regulator, else its bus's end (DSS-2)."""
    if regulator:
        return number
    ends = transformer_mapper.ends_of(windings, phases, name=name)
    return next(end.number for end in ends if any(w.number == number for w in end.windings))


def map_regcontrol(native) -> Document:
    """Every ``RegControl`` as a ``TapChangerControl`` and its ``RatioTapChanger`` in one ``regcontrol`` document."""
    controls = native.list_by_class(NATIVE_CLASS)
    if not controls:
        return Document(name="regcontrol", statements=[], profile=CIM_PROFILE)
    transformers = {str(xf.name).lower(): xf for xf in native.list_by_class(schema.Transformer)}
    codes = {str(code.name).lower(): code for code in native.list_by_class(schema.Xfmrcode)}
    transformer_mapper.regulated_transformers(native)  # two controls on one transformer raise
    tap_defaults = {slot: dss_defaults(schema.Transformer)[slot] for slot in _TAP_DEFAULTS}
    control_rows, tap_rows = [], []
    for original in controls:
        unmapped = [slot for slot in _UNMAPPED if getattr(original, slot) not in (None, [], False)]
        if unmapped:
            raise ValueError(f"RegControl {original.name}: {', '.join(unmapped)} not mapped yet (no deck in the "
                             "sweep sets them)")
        control, defaulted = fill_defaults(FIELDS, original, dss_defaults(NATIVE_CLASS))
        xf = transformers.get(str(control.transformer).lower())
        if xf is None:
            raise ValueError(f"RegControl {control.name}: transformer={control.transformer} is no Transformer")
        if xf.XfmrCode:
            xf, _ = transformer_mapper.with_code(xf, codes)
        phases = xf.phases if xf.phases is not None else 3
        windings = transformer_mapper.windings_of(xf, phases, [], regulated=True)
        number = int(control.winding)
        if not 1 <= number <= len(windings):
            raise ValueError(f"RegControl {control.name}: winding={number} of a {len(windings)}-winding transformer")
        winding = windings[number - 1]
        regulator = transformer_mapper.is_regulator(windings)
        end = _end_number(windings, phases, number, regulator, name=xf.name)
        xf_id = mrid(transformer_mapper.PREFIX, xf.name, lowercase=True)
        notes = [note for note in (defaulted,) if note]
        tap_slots = {slot: getattr(xf, slot) for slot in _TAP_DEFAULTS}
        unset = [slot for slot, value in tap_slots.items() if value is None]
        tap_slots.update({slot: tap_defaults[slot] for slot in unset})
        if unset:
            notes.append(f"defaulted: Transformer {xf.name} "
                         + ", ".join(f"{slot}={cell(tap_defaults[slot])}" for slot in unset))
        tap = float(xf.taps[number - 1]) if xf.taps else 1.0
        steps = tap_range(tap, float(tap_slots["MaxTap"]), float(tap_slots["MinTap"]), int(tap_slots["NumTaps"]),
                          name=xf.name)
        ptratio, ct_primary = float(control.ptratio), float(control.CTprim)
        r, x = float(control.R), float(control.X)
        control_id = mrid(PREFIX, control.name, lowercase=True)
        comment = "\n".join(part for part in (*notes, untranscribed_values(FIELDS, control)) if part) or None
        control_rows.append(Row([
            control_id, str(control.name), cell(control.enabled),
            _phase_letter(winding, phases, control.PTphase, name=control.name), cell(ptratio),
            cell(secondary_to_primary(float(control.vreg), ptratio)),
            cell(secondary_to_primary(float(control.band), ptratio)),
            cell(r != 0 or x != 0), cell(line_drop_ohms(r, ptratio, ct_primary)), cell(line_drop_ohms(x, ptratio, ct_primary)),
            cell(control.reversible), cell(secondary_to_primary(float(control.revvreg), ptratio)),
            cell(secondary_to_primary(float(control.revband), ptratio)),
            cell(line_drop_ohms(float(control.revR), ptratio, ct_primary)),
            cell(line_drop_ohms(float(control.revX), ptratio, ct_primary)),
            cell(float(control.revThreshold)), cell(float(control.revDelay)), cell(control.revNeutral),
            f"{xf_id}_T{end}",
        ], comment=comment))
        tap_rows.append(Row([
            f"{control_id}_tap", str(control.name), f"{xf_id}_{end}", control_id, str(steps.low), str(steps.high),
            str(steps.step), cell(steps.increment_percent), cell(winding.kv), cell(control.enabled), cell(ptratio),
            cell(ct_primary), cell(ct_ratio(ct_primary)), cell(float(control.delay)), cell(float(control.tapdelay)),
        ]))
    statements = [
        Table("TapChangerControl", [
            Column("mRID"), Column("name"), Column("mode", default="voltage"), Column("discrete", default="true"),
            Column("enabled"), Column("monitoredPhase"), Column("ptRatio"), Column("targetValue"),
            Column("targetDeadband"), Column("lineDropCompensation"), Column("lineDropR", "ohm"),
            Column("lineDropX", "ohm"), Column("reversible"), Column("reverseTargetValue"),
            Column("reverseTargetDeadband"), Column("reverseLineDropR", "ohm"), Column("reverseLineDropX", "ohm"),
            Column("reversingPowerThreshold", "kW"), Column("reversingDelay", "s"), Column("reverseToNeutral"),
            Column("Terminal")], control_rows,
            comment="derived: targetValue/Deadband = vreg/band x ptratio (secondary_to_primary), primary volts "
                    "(plain floats in cim18v17); lineDropR/X = R/X x ptratio / CTprim (line_drop_ohms); the reverse "
                    "settings the same way"),
        Table("RatioTapChanger", [
            Column("mRID"), Column("name"), Column("TransformerEnd"), Column("TapChangerControl"), Column("lowStep"),
            Column("highStep"), Column("neutralStep", default="0"), Column("step"),
            Column("stepVoltageIncrement", "percent"), Column("neutralU", "kV"), Column("ltcFlag", default="true"),
            Column("controlEnabled"), Column("ptRatio"), Column("ctRating"), Column("ctRatio"),
            Column("initialDelay", "s"), Column("subsequentDelay", "s")], tap_rows,
            comment="derived from the transformer's MaxTap, MinTap, NumTaps and its tap on the controlled winding "
                    "(tap_range): increment = (MaxTap - MinTap) / NumTaps, step = (tap - 1) / increment; "
                    "neutralU = the winding kV; ctRating = CTprim (A, a plain float); ctRatio = CTprim / 0.2 A (ct_ratio)"),
    ]
    return Document(name="regcontrol", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(controls)))
