"""GLM ``regulator`` (with its ``regulator_configuration``) -> ``regulator.cimtbl`` (S3c).

A GridLAB-D regulator is a 1:1 step-voltage regulator with no nameplate impedance and no kVA, so each unit is a
``VoltageRegulator`` (an AutoTransformer) with two ``AutoTransformerEnd``s: node, phase, grounding, the coil voltage
and a ``ratedS`` from the continuous rating, and a ``TransformerMeshImpedance`` of ``regulator_resistance`` and a
stand-in x (S3c-2). There is no step-down LTC in GLM (a regulator has no voltage ratio),
so no ``PowerTransformerEnd`` and no tank. ``control_level INDIVIDUAL`` (GridLAB-D's default) is one 1-phase unit
per wired phase with its own ``RatioTapChanger`` and ``TapChangerControl``, as the DSS import's IEEE 13; ``BANK``
is one gang unit (GLM-7). CIM has no regulator template, so a configuration's values go on every unit that names
it. ``step`` is a tap position, never a ratio.

Mapping spec: ``cimhub_gridlabd/docs/CIMTBL_MAPPING.md#s3c-regulators``.
"""

from __future__ import annotations

import math
from typing import NamedTuple

from cimprofiles.units import units
from cimtables.document import Column, Document, Row, Table
from cimtopology.core import BusSystem, System

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, fill_defaults, mrid, untranscribed_values
from cimhub_core.derived.regulator import line_drop_ohms, secondary_to_primary
from cimhub_gridlabd.glm_reader import GlmModel
from cimhub_gridlabd.glm_schema import registry_unit
from cimhub_gridlabd.importer.cimtbl.catalog import HEADER_FIELDS, label
from cimhub_gridlabd.importer.cimtbl.link import RATING_SLOTS, Limits, classify, link_ratings, provenance
from cimhub_gridlabd.importer.topology import line_voltage
from cimhub_gridlabd.schema import gridlabd as schema

NATIVE_CLASS = schema.Regulator
CONFIGURATION_CLASS = schema.RegulatorConfiguration
PREFIX = "xf_"
CONTROL_PREFIX = "rc_"

_CONTROL = "TapChangerControl"
_TAP = "RatioTapChanger"
_NOT_MAPPED = "raises when set: no deck sets it, so a mapping waits for one"

#: GridLAB-D's ``regulator_configuration::create()`` values for the slots the mapper reads (``:135``-``:151``).
DEFAULTS = {"Control": "MANUAL", "control_level": "INDIVIDUAL", "Type": "B", "dwell_time": 0.0, "time_delay": 0.0}
#: ``Type`` -> ``VoltageRegulator.construction``.
CONSTRUCTION = {"A": "typeA", "B": "typeB"}
#: The ``Control`` modes mapped; ``REMOTE_NODE`` only on the regulator's own output (S3c-6, S6).
CONTROLS = ("MANUAL", "OUTPUT_VOLTAGE", "LINE_DROP_COMP", "REMOTE_NODE")
#: S3c-2: GridLAB-D's ``powerflow::default_resistance`` (ohm), the regulator's series r when unset, and the mesh x
#: (percent on ratedS) that stands in for none: an exporter's engine may need one (DSS solves XHL=0 wrong), and 0.01 is
#: the IEEE 13 deck's regulators' XHL
DEFAULT_RESISTANCE = 1e-4
STAND_IN_X = 0.01

_BAND = ("{target} = {slot} (V): primary volts on OUTPUT_VOLTAGE and MANUAL, x power_transducer_ratio on "
         "LINE_DROP_COMP, whose band is on the PT secondary (regulator.cpp:1316)")
_LDC = ("{target} (ohm) = the unit's phase setting x power_transducer_ratio / current_transducer_ratio "
        "(line_drop_ohms; regulator.cpp:1330); set without both ratios raises")

CONFIGURATION_FIELDS = {
    "name": Field("structural", note="read by every regulator that names it; CIM has no regulator template, so "
                                     "nothing carries it but the units' row comments"),
    **HEADER_FIELDS,
    "connect_type": Field("structural", note="WYE_WYE (every unit wye, grounded); any other raises "
                                             "(regulator_configuration.cpp:232: NR takes WYE_WYE only)"),
    "band_center": Field("derived", note=_BAND.format(target="targetValue", slot="band_center")),
    "band_width": Field("derived", note=_BAND.format(target="targetDeadband", slot="band_width")
                                        + "; the full band, as CIM's"),
    "time_delay": Field("derived", note="initialDelay = subsequentDelay = dwell_time + time_delay (s): every tap "
                                        "change waits both (regulator.cpp:598-611, S3c-5); default 0"),
    "dwell_time": Field("derived", note="with time_delay; default 0"),
    "raise_taps": Field("copied", ((_TAP, "highStep", None),), "also the stepVoltageIncrement divisor; 0 raises "
                                                                "(regulator_configuration.cpp:198)"),
    "lower_taps": Field("derived", note="RatioTapChanger.lowStep = -lower_taps; 0 raises"),
    "current_transducer_ratio": Field("copied", ((_TAP, "ctRatio", None),), "and the line drop's CT ratio"),
    "power_transducer_ratio": Field("copied", ((_CONTROL, "ptRatio", None), (_TAP, "ptRatio", None)),
                                    "and the line drop's and LINE_DROP_COMP band's PT ratio"),
    **{f"compensator_r_setting_{phase}": Field("derived", note=_LDC.format(target="lineDropR")) for phase in "ABC"},
    **{f"compensator_x_setting_{phase}": Field("derived", note=_LDC.format(target="lineDropX")) for phase in "ABC"},
    "CT_phase": Field("structural", note="BANK: the phase whose compensator setting is read, which must be "
                                         "PT_phase; INDIVIDUAL: GridLAB-D ignores it (regulator.cpp:1328), listed "
                                         "on the row (S6)"),
    "PT_phase": Field("structural", note="BANK: TapChangerControl.monitoredPhase; INDIVIDUAL: GridLAB-D ignores it "
                                         "(regulator.cpp:1378), listed on the row (S6)"),
    "regulation": Field("derived", note="RatioTapChanger.stepVoltageIncrement = regulation / raise_taps (percent), "
                                        "GridLAB-D's tapChangePer (regulator.cpp:244); 0 raises unless MANUAL"),
    "control_level": Field("structural", note="INDIVIDUAL (default): one unit per wired phase; BANK: one gang unit "
                                              "on ABC (GLM-7), or one unit on its one PT_phase (S6)"),
    "Control": Field("structural", note="MANUAL (default): enabled = controlEnabled = false; OUTPUT_VOLTAGE, "
                                        "LINE_DROP_COMP: true, lineDropCompensation on LINE_DROP_COMP only; "
                                        "REMOTE_NODE on the regulator's own to bus: as OUTPUT_VOLTAGE (the same "
                                        "voltages, regulator.cpp:1376-1420), elsewhere raises (S3c-6, S6)"),
    "reverse_flow_control": Field("structural", note="unset or LOCK_NONE; others " + _NOT_MAPPED),
    "Type": Field("mapped", (("VoltageRegulator", "construction", None),),
                  "A -> typeA, B -> typeB (default B): GridLAB-D's ratio 1 / (1 + tap x step) or 1 - tap x step"),
    **{f"tap_pos_{phase}": Field("derived", note="RatioTapChanger.step of the phase's unit, unless the regulator's "
                                                 f"tap_{phase}; default 0 (regulator.cpp:146)") for phase in "ABC"},
}

FIELDS = classify(NATIVE_CLASS, {
    "name": Field("derived", note="VoltageRegulator.name = name (BANK) or name_<phase> (INDIVIDUAL); mRID = xf_ + "
                                  "that; the controls rc_ + that"),
    "phases": Field("structural", note="the wired phases A, B, C (N optional: every unit is wye to neutral); S "
                                       "raises"),
    "status": Field("structural", note="unset or CLOSED; OPEN raises (the walk)"),
    "configuration": Field("structural", note="a regulator_configuration: its values on every unit"),
    **{f"tap_{phase}": Field("derived", note=f"RatioTapChanger.step of the phase's unit (over tap_pos_{phase})")
       for phase in "ABC"},
    "msg_mode": Field("untranscribed", note="co-simulation messaging"),
    **{f"remote_voltage_{phase}": Field("untranscribed", note="solver output or state") for phase in "ABC"},
    **{f"tap_{phase}_change_count": Field("untranscribed", note="solver output or state") for phase in "ABC"},
    "sense_node": Field("structural", note="REMOTE_NODE's monitored node: must solve as the regulator's to bus; "
                                           "on another Control GridLAB-D ignores it, listed on the row (S6)"),
    "regulator_resistance": Field("copied", (("TransformerMeshImpedance", "r", "ohm"),),
                                  "GridLAB-D's series resistance, on every unit; default powerflow::default_resistance, "
                                  "1e-4 ohm (S3c-2)"),
})

def _quantity(model: GlmModel, record, slot: str, unit: str) -> float:
    """``slot`` of ``record`` in ``unit``, from the unit it is written in."""
    return units.Quantity(float(getattr(record, slot)), registry_unit(model.unit(record, slot))).to(unit).magnitude


def letters_of(reg) -> str:
    """The wired phases, in ABC order (``CAB`` -> ``ABC``)."""
    written = str(reg.phases or "")
    letters = "".join(letter for letter in "ABC" if letter in written)
    if set(written) - set("ABCN") or not letters:
        raise ValueError(f"{label(reg)}: phases {reg.phases or 'unset'}; A, B, C and N are mapped")
    return letters


def configuration_of(model: GlmModel, reg):
    """The regulator's configuration with GridLAB-D's ``create()`` values filled, and the ``defaulted:`` note."""
    config = model.by_name(reg.configuration) if reg.configuration is not None else None
    if not isinstance(config, CONFIGURATION_CLASS):
        raise ValueError(f"{label(reg)}: configuration {reg.configuration or 'unset'} is no regulator_configuration")
    check(config)
    return fill_defaults(CONFIGURATION_FIELDS, config, DEFAULTS)


def check(config) -> None:
    """What GridLAB-D's ``init()`` throws on, and what is not mapped (S3c fail fast)."""
    if str(config.connect_type) != "WYE_WYE":
        raise ValueError(f"{label(config)}: connect_type {config.connect_type or 'unset'}; WYE_WYE is mapped")
    if not config.raise_taps or not config.lower_taps or config.raise_taps < 0 or config.lower_taps < 0:
        raise ValueError(f"{label(config)}: raise_taps {config.raise_taps}, lower_taps {config.lower_taps}; both "
                         "must be positive (regulator_configuration.cpp:198)")
    control = str(config.Control or DEFAULTS["Control"])
    if control not in CONTROLS:
        raise ValueError(f"{label(config)}: Control {control}; {', '.join(CONTROLS)} are mapped")
    if control != "MANUAL" and not config.regulation:
        raise ValueError(f"{label(config)}: regulation unset or 0 on Control {control} "
                         "(regulator_configuration.cpp:212)")
    if config.reverse_flow_control is not None and str(config.reverse_flow_control) != "LOCK_NONE":
        raise ValueError(f"{label(config)}: reverse_flow_control {config.reverse_flow_control}; not mapped")


def ignored_phases(config) -> str | None:
    """``PT_phase`` and ``CT_phase`` on INDIVIDUAL, which GridLAB-D does not read there (``regulator.cpp:1328``,
    ``:1378``: each phase is its own), as a row note (S6)."""
    if str(config.control_level) != "INDIVIDUAL":
        return None
    given = [f"{slot} {getattr(config, slot)}" for slot in ("PT_phase", "CT_phase") if getattr(config, slot) is not None]
    return f"ignored on INDIVIDUAL (GridLAB-D reads each phase): {', '.join(given)}" if given else None


def check_sense_node(reg, control: str, roots: dict[str, str]) -> str | None:
    """REMOTE_NODE is mapped when it senses the regulator's own output, where GridLAB-D reads the voltages
    OUTPUT_VOLTAGE reads; a sense node elsewhere raises. On another Control GridLAB-D does not read it
    (``regulator.cpp:150``): a row note (S6)."""
    if control != "REMOTE_NODE":
        return None if reg.sense_node is None else f"ignored on Control {control}: sense_node {reg.sense_node}"
    if reg.sense_node is None:
        raise ValueError(f"{label(reg)}: REMOTE_NODE without sense_node (regulator.cpp:152)")
    if reg.sense_node not in roots:
        raise ValueError(f"{label(reg)}: sense_node {reg.sense_node} is not a bus object")
    if roots[reg.sense_node] != roots[reg.to]:
        raise ValueError(f"{label(reg)}: REMOTE_NODE senses {reg.sense_node}, not its own output {reg.to}; a remote "
                         "sense node is not mapped")
    return None


def tap_step(reg, config, letter: str) -> int:
    """The phase's tap position: the regulator's ``tap_X``, else the configuration's ``tap_pos_X``, else 0."""
    for record, slot in ((reg, f"tap_{letter}"), (config, f"tap_pos_{letter}")):
        value = getattr(record, slot)
        if value is not None:
            if not -config.lower_taps <= int(value) <= config.raise_taps:
                raise ValueError(f"{label(record)}: {slot} {value} is outside -{config.lower_taps}..+"
                                 f"{config.raise_taps}")
            return int(value)
    return 0


def line_drop(config, letter: str) -> tuple[float | None, float | None]:
    """``(lineDropR, lineDropX)`` in primary ohms from the phase's compensator settings (S3c-4)."""
    settings = [getattr(config, f"compensator_{part}_setting_{letter}") for part in ("r", "x")]
    if all(setting is None for setting in settings):
        return None, None
    if not config.power_transducer_ratio or not config.current_transducer_ratio:
        raise ValueError(f"{label(config)}: compensator settings on {letter} without power_transducer_ratio and "
                         "current_transducer_ratio; not mapped")
    pt, ct = float(config.power_transducer_ratio), float(config.current_transducer_ratio)
    # GridLAB-D's compensator works on CT secondary amps = primary / current_transducer_ratio (regulator.cpp:1330),
    # so the ratio stands where line_drop_ohms takes a CT primary rating
    return tuple(None if setting is None else line_drop_ohms(float(setting), pt, ct) for setting in settings)


class _Unit(NamedTuple):
    """One VoltageRegulator: its mRID suffix, its phases and its monitored phase."""
    suffix: str
    letters: str
    monitored: str


def units_of(reg, config) -> list[_Unit]:
    """INDIVIDUAL: one unit per wired phase; BANK: one gang unit on ABC, whose taps must agree (GLM-7), or one unit
    on the one phase it monitors (S6)."""
    letters = letters_of(reg)
    if str(config.control_level) == "INDIVIDUAL":
        return [_Unit(f"_{letter}", letter, letter) for letter in letters]
    phases = [str(getattr(config, slot) or "") for slot in ("PT_phase", "CT_phase")]
    if phases[0] not in ("A", "B", "C") or phases[1] != phases[0]:
        raise ValueError(f"{label(config)}: PT_phase {phases[0] or 'unset'}, CT_phase {phases[1] or 'unset'}; a BANK "
                         "monitors one phase, the same for both (regulator_configuration.cpp:183)")
    if letters == phases[0]:
        return [_Unit("", letters, letters)]
    if letters != "ABC":
        raise ValueError(f"{label(reg)}: a BANK regulator on {letters}; a gang unit is mapped on ABC, or on its "
                         "one monitored phase")
    taps = {tap_step(reg, config, letter) for letter in letters}
    if len(taps) > 1:
        raise ValueError(f"{label(reg)}: BANK taps {sorted(taps)} differ; a gang holds one tap")
    return [_Unit("", letters, phases[0])]


def unit_mrids(model: GlmModel, reg) -> list[str]:
    """The mRID of each unit the regulator is written as (``units_of``), in phase order."""
    config, _ = configuration_of(model, reg)
    return [mrid(PREFIX, f"{reg.name}{unit.suffix}") for unit in units_of(reg, config)]


def _phase_ratings(reg, letter: str) -> dict[str, float]:
    """``{"norm": A, "emerg": A}`` of one phase's own ratings."""
    index = "ABC".index(letter)
    return {suffix: float(getattr(reg, slots[index])) for suffix, slots in RATING_SLOTS
            if getattr(reg, slots[index]) is not None}


def rated_s(reg, unit: _Unit, base_u: float) -> float:
    """The unit's ``ratedS`` (VA): its continuous rating x ``baseU``, x sqrt 3 on a gang unit (``baseU`` line to line;
    S3c-2). GLM has no kVA, and GridLAB-D's default rating is not the regulator's (S2-7), so an unset one raises."""
    one_phase = len(unit.letters) == 1
    rating = (_phase_ratings(reg, unit.letters) if one_phase else link_ratings(reg)).get("norm")
    if rating is None:
        slots = f"continuous_rating_{unit.letters}" if one_phase else "continuous_rating_A/B/C"
        raise ValueError(f"{label(reg)}: no {slots}; ratedS is the continuous rating x baseU (S3c-2)")
    return rating * base_u if one_phase else rating * base_u * math.sqrt(3)


class _Rows:
    def __init__(self):
        self.regulators: list[Row] = []
        self.ends: list[Row] = []
        self.meshes: list[Row] = []
        self.controls: list[Row] = []
        self.taps: list[Row] = []
        self.limits = Limits()


def _regulator(model: GlmModel, reg, roots: dict[str, str], buses: dict[str, BusSystem], rows: _Rows) -> None:
    if reg.status is not None and str(reg.status) != "CLOSED":
        raise ValueError(f"{label(reg)}: status {reg.status}; a regulator is not a switch")
    config, defaulted = configuration_of(model, reg)
    ignored_sense = check_sense_node(reg, str(config.Control), roots)
    node1, node2 = roots[reg.from_node], roots[reg.to]
    coil = _quantity(model, model.by_name(node1), "nominal_voltage", "V")  # phase to neutral, as GLM writes it
    control = str(config.Control)
    enabled = control != "MANUAL"
    pt = None if config.power_transducer_ratio is None else float(config.power_transducer_ratio)
    increment = 0.0 if not config.regulation else units.Quantity(
        float(config.regulation) / config.raise_taps, "dimensionless").to("percent").magnitude
    delay = _quantity(model, config, "dwell_time", "s") + _quantity(model, config, "time_delay", "s")
    band = [None if getattr(config, slot) is None else _quantity(model, config, slot, "V")
            for slot in ("band_center", "band_width")]
    if control == "LINE_DROP_COMP":
        band = [None if value is None else secondary_to_primary(value, pt) for value in band]
    if reg.regulator_resistance is None:
        resistance = DEFAULT_RESISTANCE
        written = f"regulator_resistance={DEFAULT_RESISTANCE:g}"
        defaulted = f"{defaulted}, {written}" if defaulted else f"defaulted: {written}"
    else:
        resistance = _quantity(model, reg, "regulator_resistance", "ohm")
    comment = "\n".join(part for part in (f"configuration {config.name}", defaulted, untranscribed_values(FIELDS, reg),
                                          untranscribed_values(CONFIGURATION_FIELDS, config), ignored_phases(config),
                                          ignored_sense)
                        if part)
    for unit in units_of(reg, config):
        name = f"{reg.name}{unit.suffix}"
        vr = mrid(PREFIX, name)  # as unit_mrids
        base_u = coil if len(unit.letters) == 1 else line_voltage(coil, System.THREE_PHASE)
        rows.regulators.append(Row([vr, name, CONSTRUCTION[str(config.Type)]], comment=comment))
        rating = rated_s(reg, unit, base_u)
        for number, node in enumerate((node1, node2), start=1):
            rows.ends.append(Row([f"{vr}_{number}", vr, node, f"{unit.letters}N", str(number), cell(base_u),
                                  cell(rating), buses[node].base_voltage]))
        rows.meshes.append(Row([f"{vr}_mesh_12", f"{vr}_1", f"{vr}_2", cell(resistance), cell(STAND_IN_X)]))
        r, x = line_drop(config, unit.monitored)
        control_id = mrid(CONTROL_PREFIX, name)
        rows.controls.append(Row([control_id, name, cell(enabled), unit.monitored, cell(pt), cell(band[0]),
                                  cell(band[1]), cell(control == "LINE_DROP_COMP"), cell(r), cell(x), f"{vr}_T2"]))
        rows.taps.append(Row([f"{control_id}_tap", name, f"{vr}_2", control_id, str(-config.lower_taps),
                              str(config.raise_taps), str(tap_step(reg, config, unit.letters[0])), cell(increment),
                              cell(base_u), cell(enabled), cell(pt), cell(config.current_transducer_ratio),
                              cell(delay), cell(delay)]))
        rows.limits.add(vr, _phase_ratings(reg, unit.letters) if len(unit.letters) == 1 else link_ratings(reg))


def map_regulators(model: GlmModel, roots: dict[str, str], buses: dict[str, BusSystem], feeder: str) -> Document:
    """Every regulator as one document: the units, their ends, controls and tap changers, then the limit sets."""
    regulators = model.list_by_class(NATIVE_CLASS)
    if not regulators:
        return Document(name=NATIVE_CLASS.class_name, statements=[], profile=CIM_PROFILE)
    rows = _Rows()
    for reg in regulators:
        _regulator(model, reg, roots, buses, rows)
    used = {str(reg.configuration) for reg in regulators}
    unused = [str(config.name) for config in model.list_by_class(CONFIGURATION_CLASS) if str(config.name) not in used]
    statements = [
        Table("VoltageRegulator", [Column("mRID"), Column("name"), Column("construction"),
                                   Column("EquipmentContainer", default=feeder)], rows.regulators,
              comment="one unit per wired phase (INDIVIDUAL) or a gang unit (BANK), GLM-7"),
        Table("AutoTransformerEnd", [Column("mRID"), Column("AutoTransformer"), Column("node"), Column("phase"),
                                     Column("endNumber"), Column("grounded", default="true"), Column("baseU", "V"),
                                     Column("ratedS", "VA"), Column("BaseVoltage")], rows.ends,
              comment="baseU = the from bus's nominal_voltage (the coil, phase to neutral; a gang unit's x sqrt 3); "
                      "ratedS = the continuous rating x baseU (x sqrt 3 on a gang unit; S3c-2)"),
        Table("TransformerMeshImpedance", [Column("mRID"), Column("FromTransformerEnd"), Column("ToTransformerEnd"),
                                           Column("r", "ohm"), Column("x", "percent")], rows.meshes,
              comment="r = regulator_resistance (default 1e-4 ohm); x = a 0.01 % stand-in on ratedS (S3c-2)"),
        Table(_CONTROL, [Column("mRID"), Column("name"), Column("mode", default="voltage"),
                         Column("discrete", default="true"), Column("enabled"), Column("monitoredPhase"),
                         Column("ptRatio"), Column("targetValue"), Column("targetDeadband"),
                         Column("lineDropCompensation"), Column("lineDropR", "ohm"), Column("lineDropX", "ohm"),
                         Column("Terminal")], rows.controls,
              comment="targetValue/Deadband = band_center/band_width, primary volts (x ptRatio on LINE_DROP_COMP); "
                      "lineDropR/X = compensator setting x ptRatio / ctRatio (line_drop_ohms); enabled = Control "
                      "is not MANUAL"),
        Table(_TAP, [Column("mRID"), Column("name"), Column("TransformerEnd"), Column("TapChangerControl"),
                     Column("lowStep"), Column("highStep"), Column("neutralStep", default="0"), Column("step"),
                     Column("stepVoltageIncrement", "percent"), Column("neutralU", "V"),
                     Column("ltcFlag", default="true"), Column("controlEnabled"), Column("ptRatio"),
                     Column("ctRatio"), Column("initialDelay", "s"), Column("subsequentDelay", "s")], rows.taps,
              comment="stepVoltageIncrement = regulation / raise_taps; step = tap_X, else tap_pos_X, else 0; "
                      "initialDelay = subsequentDelay = dwell_time + time_delay (S3c-5)"),
        *rows.limits.tables(),
    ]
    header = provenance(NATIVE_CLASS.class_name, "VoltageRegulator + AutoTransformerEnd + TapChangerControl + "
                        "RatioTapChanger (with its regulator_configuration)", len(regulators), "s3c-regulators")
    if unused:
        header += f"\nno regulator names (not written): {', '.join(unused)}"
    return Document(name=NATIVE_CLASS.class_name, statements=statements, profile=CIM_PROFILE, comment=header)
