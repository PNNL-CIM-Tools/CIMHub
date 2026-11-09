"""TapChangerControl -> OpenDSS ``RegControl`` (``EXPORT_MAPPING.md#regcontrol``).

The importer's settings inverted: CIM's primary volts and ohms back to the relay's PT-secondary volts
(``cimhub_core.derived.regulator``). ``ctRatio`` is not read: the engine's CT secondary is fixed at 0.2 A, and R/X
go through ``CTprim``. What DSS cannot hold raises: another mode, remote sensing, voltage limits.
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.derived.regulator import line_drop_volts, primary_to_secondary
from cimhub_core.getters import describe
from cimhub_core.getters.control import TapChangerSettings, get_tap_changer_control
from cimhub_opendss.exporter import windings
from cimhub_opendss.exporter.naming import Names
from cimhub_opendss.exporter.slots import Slot, with_default
from cimhub_opendss.schema import opendss_schema as schema

CIM_CLASSES = (cim.TapChangerControl,)
NATIVE_CLASS = schema.Regcontrol
NAMESPACE = "RegControl"

_SECONDARY = "/ ptRatio (primary_to_secondary); unset -> not written, the engine's default"
_LINE_DROP = "x CTprim / ptRatio (line_drop_volts); unset -> not written (0)"
SLOTS = {NATIVE_CLASS: with_default(NATIVE_CLASS, {
    "name": Slot("written", "Names, the RegControl namespace"),
    "transformer": Slot("written", "the DSS Transformer of the tap's unit (one unit)"),
    "winding": Slot("written", "the winding whose end holds the RatioTapChanger"),
    "vreg": Slot("written", "targetValue (V) / ptRatio (primary_to_secondary)"),
    "band": Slot("written", f"targetDeadband (V) {_SECONDARY}"),
    "ptratio": Slot("written", "ptRatio, the tap's and the control's agreed; unset raises"),
    "CTprim": Slot("written", "ctRating (A); unset -> not written, and a line drop then raises"),
    "R": Slot("written", f"lineDropR (ohm) {_LINE_DROP}"), "X": Slot("written", f"lineDropX (ohm) {_LINE_DROP}"),
    "bus": Slot("not mapped", "the control must monitor its tap end's Terminal (remote sensing raises)"),
    "delay": Slot("written", "initialDelay (s); unset -> not written"),
    "reversible": Slot("written", "TapChangerControl.reversible"),
    "revvreg": Slot("written", f"reverseTargetValue (V) {_SECONDARY}"),
    "revband": Slot("written", f"reverseTargetDeadband (V) {_SECONDARY}"),
    "revR": Slot("written", f"reverseLineDropR (ohm) {_LINE_DROP}"),
    "revX": Slot("written", f"reverseLineDropX (ohm) {_LINE_DROP}"),
    "tapdelay": Slot("written", "subsequentDelay (s); unset -> not written"),
    "tapwinding": Slot("not mapped", "the tap winding is the monitored one"),
    "vlimit": Slot("not mapped", "maxLimitVoltage raises (untranscribed on import)"),
    "PTphase": Slot("written", "1-based place of monitoredPhase among the winding's phase conductors"),
    "revThreshold": Slot("written", "reversingPowerThreshold (kW)"),
    "revDelay": Slot("written", "reversingDelay (s)"),
    "revNeutral": Slot("written", "reverseToNeutral"),
    "enabled": Slot("written", "the control's enabled; the tap's controlEnabled must agree"),
    "like": Slot("not mapped", "the writer never writes like="),
}, Slot("unset", "untranscribed or raising on import; not in CIM"))}


def export(context) -> list[schema.Regcontrol]:
    """One RegControl per TapChangerControl."""
    return [_regcontrol(control, context.names) for control in context.objects(*CIM_CLASSES)]


def _regcontrol(control: cim.TapChangerControl, names: Names) -> schema.Regcontrol:
    if control.mode is not cim.RegulatingControlModeKind.voltage:
        mode = control.mode.value if control.mode is not None else None
        raise ValueError(f"{describe(control)}: mode {mode}; a RegControl regulates voltage")
    tap = _tap(control)
    transformer_name, winding = _tap_winding(tap, names)
    settings = get_tap_changer_control(tap, unit="V", time_unit="s", power_unit="kW")
    regulating = settings.control
    if regulating.terminal is not winding.end.Terminal:
        raise ValueError(f"{describe(control)}: monitors another Terminal than its tap's end (remote sensing and "
                         f"tapwinding are not mapped)")
    limits = [name for name, value in (("maxLimitVoltage", settings.max_limit_u),
                                       ("minLimitVoltage", settings.min_limit_u)) if value is not None]
    if limits:
        raise ValueError(f"{describe(control)}: {limits} are not mapped")
    pt_ratio = regulating.pt_ratio
    if pt_ratio is None:
        raise ValueError(f"{describe(control)}: ptRatio is unset; vreg is on the PT secondary")
    return NATIVE_CLASS(
        name=names.name(control, NAMESPACE),
        transformer=transformer_name,
        winding=winding.number,
        vreg=primary_to_secondary(regulating.target, pt_ratio),
        band=_secondary(regulating.deadband, pt_ratio),
        ptratio=pt_ratio,
        CTprim=settings.ct_rating,
        **_line_drop(control, settings, pt_ratio),
        delay=settings.initial_delay,
        tapdelay=settings.subsequent_delay,
        reversible=settings.reversible,
        revvreg=_secondary(regulating.reverse_target, pt_ratio),
        revband=_secondary(regulating.reverse_deadband, pt_ratio),
        PTphase=_pt_phase(control, regulating.monitored_phases, winding),
        revThreshold=settings.reversing_power_threshold,
        revDelay=settings.reversing_delay,
        revNeutral=settings.reverse_to_neutral,
        enabled=_enabled(control, regulating.enabled, settings.control_enabled),
    )


def _tap(control: cim.TapChangerControl) -> cim.RatioTapChanger:
    taps = control.TapChanger
    if len(taps) != 1 or not isinstance(taps[0], cim.RatioTapChanger):
        raise ValueError(f"{describe(control)}: controls {len(taps)} tap changers; one RatioTapChanger is mapped")
    return taps[0]


def _tap_winding(tap: cim.RatioTapChanger, names: Names):
    """``(DSS Transformer name, winding)`` of the tap's end."""
    end = tap.TransformerEnd
    transformer = end.PowerTransformer if isinstance(end, cim.PowerTransformerEnd) else end.AutoTransformer
    if transformer is None:
        raise ValueError(f"{describe(tap)}: its end {describe(end)} is on no transformer")
    units = windings.units(transformer)
    if len(units) != 1:
        raise ValueError(f"{describe(tap)}: a tap changer on a several-tank transformer is not mapped (T4)")
    [unit] = units
    [(winding, _)] = [(winding, found) for winding, found in windings.tap_windings(windings.read_unit(unit))
                      if found is tap]
    return windings.unit_name(transformer, unit, names), winding


def _secondary(volts: float | None, pt_ratio: float) -> float | None:
    return None if volts is None else primary_to_secondary(volts, pt_ratio)


def _line_drop(control, settings: TapChangerSettings, pt_ratio: float) -> dict:
    """R, X, revR, revX in volts at rated CT current; they need ctRating, and an off compensator has none."""
    ohms = dict(R=settings.line_drop.r, X=settings.line_drop.x, revR=settings.reverse_line_drop.r,
                revX=settings.reverse_line_drop.x)
    set_values = [name for name, value in ohms.items() if value not in (None, 0.0)]
    if not set_values:
        return {}
    if settings.line_drop_compensation is False:
        raise ValueError(f"{describe(control)}: lineDropCompensation is false with {set_values} set")
    if settings.ct_rating is None:
        raise ValueError(f"{describe(control)}: a line drop {set_values} needs the tap's ctRating")
    return {name: None if value is None else line_drop_volts(value, pt_ratio, settings.ct_rating)
            for name, value in ohms.items()}


def _pt_phase(control, monitored, winding) -> int | None:
    if monitored is None:
        return None
    conductors = [phase for phase in winding.phases if phase is not windings.N]
    if len(monitored) != 1 or monitored[0] not in conductors:
        raise ValueError(f"{describe(control)}: monitoredPhase {[p.value for p in monitored]} is not one of its "
                         f"winding's phases {[p.value for p in conductors]}")
    return conductors.index(monitored[0]) + 1


def _enabled(control, enabled: bool | None, control_enabled: bool | None) -> bool | None:
    if enabled is not None and control_enabled is not None and enabled != control_enabled:
        raise ValueError(f"{describe(control)}: enabled {enabled} and its tap's controlEnabled {control_enabled} "
                         f"differ")
    return control_enabled if enabled is None else enabled
