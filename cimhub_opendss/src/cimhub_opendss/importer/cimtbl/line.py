"""OpenDSS ``Line`` (with the ``Fuse``, ``Recloser`` and ``SwtControl`` that switch it) -> ``line.cimtbl``.

A Line with ``Switch=y`` is a Switch: a ``Fuse`` or ``Recloser`` naming it as ``SwitchedObj`` sets the class,
otherwise it is a ``LoadBreakSwitch`` (DSS-9). Every other Line is an ``ACLineSegment`` referencing its LineCode
template, its LineGeometry ``WireConfiguration``, or a template synthesized from its own values (DSS-8). No
impedance is computed from geometry (``conductor-geometry`` skill).

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md#line-and-switches``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import NamedTuple

from cimprofiles.units import units
from cimtables.document import Column, Document, ObjectStatement, Row, Table
from cimtopology.core import BusSystem, System

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, lookup, mrid, phases_cell, untranscribed_values
from cimhub_opendss.dss_reader import dss_defaults
from cimhub_opendss.importer.cimtbl import geometry as geometry_mapper
from cimhub_opendss.importer.cimtbl import linecode as linecode_mapper
from cimhub_opendss.importer.cimtbl import wire as wire_mapper
from cimhub_opendss.importer.cimtbl.transformer import parse_bus
from cimhub_opendss.schema import opendss_schema as schema

NATIVE_CLASS = schema.Line
PREFIX = "ln_"
SWITCH_PREFIX = "sw_"

_SEGMENT = "ACLineSegment"
_SWITCH = "Switch"
_NOT_MAPPED = "raises when set: no deck in the sweep sets it, so a mapping waits for one"
_INLINE = ("a synthesized template ln_<name>_lc in line.cimtbl, values per length as written, "
           "through the LineCode mapper's rules (DSS-3 units, DSS-3b, DSS-4); on a switch untranscribed")
_INLINE_GEOMETRY = "with spacing=: a synthesized WireConfiguration ln_<name>_wc on spc_<spacing>, conductors in order"
_RATING = "instance OperationalLimitSet ln_<name>_limits (see Ratings); on a switch untranscribed"
_RELIABILITY = "reliability data; no home in the network profile parts"
_CONTROL_TERMINAL = "the switch opens both terminals in CIM; DSS's terminal choice has no home"

FIELDS = {
    "name": Field("copied", ((_SEGMENT, "name", None), (_SWITCH, "name", None)),
                  "mRID = ln_ + name (segment) or sw_ + name (switch), lowercased"),
    "bus1": Field("structural", note="node1, and the phases from its nodes: 1/2/3 = A/B/C, s1/s2 on a split-phase "
                                     "island (DSS-5); no nodes = 1..phases"),
    "bus2": Field("structural", note="node2; its phase nodes must equal bus1's (a transposition raises)"),
    "phases": Field("structural", note="the phase count; unset = the code's or geometry's nphases, else 3; one "
                                       "that differs from the code's nphases raises (DSS-10)"),
    "linecode": Field("structural", note="ACLineSegment.PerLengthImpedance = the code's template for the line's "
                                         "unit (lc_<code> or lc_<code>_<unit>, DSS-3)"),
    "geometry": Field("structural", note="ACLineSegment.WireConfiguration = wc_<geometry>"),
    "spacing": Field("structural", note=_INLINE_GEOMETRY),
    "wires": Field("structural", note=_INLINE_GEOMETRY),
    "cncables": Field("structural", note=_INLINE_GEOMETRY),
    "tscables": Field("structural", note=_INLINE_GEOMETRY),
    "length": Field("copied", ((_SEGMENT, "length", "{length}"),), "default 1 (defaulted); none on a switch"),
    "units": Field("mapped", note="the length unit (LENGTH_UNIT); unset: the template's unit (DSS-3)"),
    **{slot: Field("structural", note=_INLINE) for slot in ("r1", "x1", "r0", "x0", "C1", "C0", "B1", "B0",
                                          "rmatrix", "xmatrix", "cmatrix")},
    "basefreq": Field("structural", note="the synthesized template's calculatedFrequency and the frequency of its "
                                         "b; unset: the deck's (DSS-3b)"),
    "Switch": Field("structural", note="a Switch (sw_) instead of an ACLineSegment; class from its control (DSS-9)"),
    "normamps": Field("structural", note=_RATING),
    "emergamps": Field("structural", note=_RATING),
    "Seasons": Field("structural", note=_NOT_MAPPED + " (an indexed rating array that names no calendar season; "
                                                       "home OperationalLimitType.season)"),
    "Ratings": Field("structural", note=_NOT_MAPPED + " (with Seasons)"),
    "Rg": Field("structural", note=_NOT_MAPPED + " (Carson earth return; the consumer's choice for geometry)"),
    "Xg": Field("structural", note=_NOT_MAPPED + " (Carson earth return; the consumer's choice for geometry)"),
    "rho": Field("structural", note="the deck's EarthResistivity.rho (ohm-m), which every geometry line must "
                                    "agree on (geometry.earth_statement); on another line it raises"),
    "EarthModel": Field("untranscribed", note="the earth model of the impedance calculation; the consumer's choice"),
    "EpsRmedium": Field("structural", note=_NOT_MAPPED),
    "HeightOffset": Field("structural", note=_NOT_MAPPED),
    "HeightUnit": Field("structural", note=_NOT_MAPPED),
    "conductors": Field("structural", note=_NOT_MAPPED),
    "LineType": Field("untranscribed", note="no home in the network profile parts"),
    "faultrate": Field("untranscribed", note=_RELIABILITY),
    "pct_perm": Field("untranscribed", note=_RELIABILITY),
    "repair": Field("untranscribed", note=_RELIABILITY),
    "enabled": Field("copied", ((_SEGMENT, "normallyInService", None), (_SWITCH, "normallyInService", None))),
    "like": Field("untranscribed", note="the reader resolves like= before mapping"),
}

_SWITCHED = "the Line it switches: SwitchedObj, else MonitoredObj (the DSS default); not a Switch=y line raises"
_PROTECTION = "protection setting; no home in cim18v17's protection function blocks (DSS-11)"
_RECLOSE = ("one RecloseSequence <switch>_rs<n> per reclosure, Shots - 1 of them, recloseDelay = RecloseIntervals[n] "
            "(s); unset: the engine's Shots 4, intervals 0.5 2 2 (defaulted). Both given and disagreeing raise, and "
            "so does Shots above 4 without intervals (the engine reads past its defaults)")
_STATE = ("Normal -> normalOpen, State -> open on the switch; with an Open command on the line they must agree")


def _control_fields(target: str) -> dict[str, Field]:
    """The slots Fuse, Recloser and SwtControl share."""
    return {
        "name": Field("untranscribed", note=f"the switch takes the Line's name; the {target} names no CIM object"),
        "SwitchedObj": Field("structural", note=_SWITCHED),
        "SwitchedTerm": Field("untranscribed", note=_CONTROL_TERMINAL),
        "Normal": Field("structural", note=_STATE),
        "State": Field("structural", note=_STATE),
        "Action": Field("structural", note=_NOT_MAPPED + " (the deprecated form of State)"),
        "Delay": Field("untranscribed", note="control timing; no home on a Switch"),
        "basefreq": Field("untranscribed", note="no home on a switch"),
        "enabled": Field("untranscribed", note="a disabled control leaves its switch in place; no home"),
        "like": Field("untranscribed", note="the reader resolves like= before mapping"),
    }


FUSE_FIELDS = {
    **_control_fields("Fuse"),
    "MonitoredObj": Field("structural", note=_SWITCHED),
    "MonitoredTerm": Field("untranscribed", note=_CONTROL_TERMINAL),
    "FuseCurve": Field("untranscribed", note=_PROTECTION),
    "RatedCurrent": Field("copied", (("Fuse", "ratedCurrent", "A"),)),
}

RECLOSER_FIELDS = {
    **_control_fields("Recloser"),
    "MonitoredObj": Field("structural", note=_SWITCHED),
    "MonitoredTerm": Field("untranscribed", note=_CONTROL_TERMINAL),
    "Shots": Field("structural", note=_RECLOSE),
    "RecloseIntervals": Field("structural", note=_RECLOSE),
    **{slot: Field("untranscribed", note=_PROTECTION)
       for slot in ("NumFast", "PhaseFast", "PhaseDelayed", "GroundFast", "GroundDelayed", "PhaseTrip", "GroundTrip",
                    "PhaseInst", "GroundInst", "Reset", "TDPhFast", "TDGrFast", "TDPhDelayed", "TDGrDelayed")},
}

SWTCONTROL_FIELDS = {
    **_control_fields("SwtControl"),
    "Lock": Field("untranscribed", note="control lock; no home on a Switch"),
    "Reset": Field("untranscribed", note="a command, not a setting"),
}

#: ``(native class, FIELDS)`` of the controls whose ``SwitchedObj`` the line mapper indexes (DSS-9).
CONTROLS = (
    (schema.Fuse, FUSE_FIELDS),
    (schema.Recloser, RECLOSER_FIELDS),
    (schema.Swtcontrol, SWTCONTROL_FIELDS),
)


#: The master's two limit types (``map_master``); every CurrentLimit names one.
LIMIT_TYPES = (("olt_normal", "normal", "true"), ("olt_emergency", "emergency", "false"))

_INLINE_SLOTS = (*linecode_mapper.SEQUENCE_SLOTS, "rmatrix", "xmatrix", "cmatrix")
_GEOMETRY_ARRAYS = ("wires", "cncables", "tscables")
_UNMAPPED = tuple(slot for slot, field in FIELDS.items() if field.note.startswith(_NOT_MAPPED))
#: Slots a switch has no home for; they are listed on its row (DSS-8).
_SWITCH_DROPPED = ("linecode", "geometry", "spacing", *_GEOMETRY_ARRAYS, "length", "units", *_INLINE_SLOTS,
                   "basefreq", "normamps", "emergamps")
_PHASE_OF_NODE = {1: "A", 2: "B", 3: "C"}
_SPLIT_PHASE_OF_NODE = {1: "s1", 2: "s2"}
#: The engine reads the length of a geometry line with no units in metres (checked against the engine).
_GEOMETRY_LENGTH_UNIT = "m"

_PROVENANCE = """OpenDSS Line -> ACLineSegment (by LineCode, LineGeometry or a synthesized template) or a Switch
(Fuse / Recloser / LoadBreakSwitch by the control that switches it; DSS-9).
Source table: Line (records: {count})
Mapping: cimhub_opendss/docs/CIMTBL_MAPPING.md#line-and-switches"""


class Reclose(NamedTuple):
    """A Recloser's reclosures: the delay (s) before each, and what was defaulted."""
    delays: tuple[float, ...]
    defaulted: str | None


def reclose(recloser) -> Reclose:
    """``Shots`` - 1 reclosures at ``RecloseIntervals``, the engine's defaults filling either (DSS-6). The engine
    keeps the first Shots - 1 intervals, and giving intervals sets Shots, so both given must agree."""
    defaults = dss_defaults(schema.Recloser)
    shots, intervals = recloser.Shots, recloser.RecloseIntervals or None
    if shots is not None and intervals is not None and shots - 1 != len(intervals):
        raise ValueError(f"Recloser {recloser.name}: Shots={shots} with {len(intervals)} RecloseIntervals; the "
                         "engine's result depends on their order")
    if intervals is not None:
        return Reclose(tuple(float(interval) for interval in intervals), None)
    defaulted = [] if shots is not None else [f"Shots={defaults['Shots']}"]
    shots = shots if shots is not None else defaults["Shots"]
    if shots - 1 > len(defaults["RecloseIntervals"]):
        raise ValueError(f"Recloser {recloser.name}: Shots={shots} without RecloseIntervals; the engine has "
                         f"{len(defaults['RecloseIntervals'])} default intervals and reads past them")
    delays = tuple(defaults["RecloseIntervals"][:shots - 1])
    defaulted.append(f"RecloseIntervals=({' '.join(cell(delay) for delay in delays)})")
    return Reclose(delays, "defaulted: " + ", ".join(defaulted))


class SwitchControl(NamedTuple):
    """What the Fuse, Recloser and SwtControl objects say about the line they switch."""
    cim_class: str
    rated_current: float | None
    normal_open: bool | None
    open: bool | None
    fuse_phase_states: int | None = None  # how many per-phase values a Fuse's Normal/State give (engine: per phase)
    reclose: Reclose | None = None  # a Recloser's reclosures


def _switched_line(control, target) -> str:
    """The lowered Line name of a control's ``SwitchedObj``/``MonitoredObj`` (``Line.<name>``)."""
    kind, _, name = str(target).partition(".")
    if kind.lower() != "line" or not name:
        raise ValueError(f"{type(control).__name__} {control.name}: switches {target}; only a Line is mapped")
    return name.lower()


def _is_open(control, slot: str) -> bool | None:
    """``Normal``/``State`` as ``True`` (open), ``False`` (closed) or ``None`` (unset); a per-phase list must agree."""
    value = getattr(control, slot)
    values = {str(item).lower() for item in (value if isinstance(value, list) else [value]) if item is not None}
    if not values:
        return None
    if len(values) > 1 or not values <= {"open", "closed"}:
        raise ValueError(f"{type(control).__name__} {control.name}: {slot}={value}; one of open, closed for every "
                         "phase is mapped")
    return values == {"open"}


def _merged(name: str, label: str, old, new):
    if old is not None and new is not None and old != new:
        raise ValueError(f"Line {name}: its controls disagree on {label} ({old}, {new})")
    return new if new is not None else old


def switch_controls(native) -> dict[str, SwitchControl]:
    """``{lowered line name: SwitchControl}`` from every Fuse, Recloser and SwtControl (DSS-9)."""
    classes = {schema.Fuse: "Fuse", schema.Recloser: "Recloser"}
    result: dict[str, SwitchControl] = {}
    for native_class, _ in CONTROLS:
        for control in native.list_by_class(native_class):
            if control.Action is not None:
                raise ValueError(f"{native_class.__name__} {control.name}: Action is not mapped yet (no deck in "
                                 "the sweep sets it)")
            target = control.SwitchedObj or getattr(control, "MonitoredObj", None)
            if target is None:
                raise ValueError(f"{native_class.__name__} {control.name}: switches no object")
            key = _switched_line(control, target)
            old = result.get(key, SwitchControl("LoadBreakSwitch", None, None, None))
            states = _fuse_phase_states(control) if native_class is schema.Fuse else None
            cim_class = classes.get(native_class)
            if cim_class and old.cim_class != "LoadBreakSwitch" and old.cim_class != cim_class:
                raise ValueError(f"Line {key}: switched by a {old.cim_class} and a {cim_class}")
            rated = float(control.RatedCurrent) if native_class is schema.Fuse and control.RatedCurrent else None
            recloses = reclose(control) if native_class is schema.Recloser else None
            result[key] = SwitchControl(cim_class or old.cim_class, _merged(key, "ratedCurrent", old.rated_current, rated),
                                        _merged(key, "Normal", old.normal_open, _is_open(control, "Normal")),
                                        _merged(key, "State", old.open, _is_open(control, "State")),
                                        _merged(key, "Fuse Normal/State values", old.fuse_phase_states, states),
                                        _merged(key, "reclosures", old.reclose, recloses))
    return result


def _fuse_phase_states(fuse) -> int | None:
    """How many per-phase values the Fuse's Normal and State give (they must agree), or None when neither is set.
    The engine sets a Fuse's state phase by phase: ``State=open`` on a 3-phase line opens phase 1 only."""
    counts = {len(value) if isinstance(value, list) else 1
              for value in (fuse.Normal, fuse.State) if value not in (None, [])}
    if len(counts) > 1:
        raise ValueError(f"Fuse {fuse.name}: Normal={fuse.Normal} and State={fuse.State} give different phase counts")
    return counts.pop() if counts else None


def opened_lines(native) -> set[str]:
    """Lowered names of the Lines an ``Open`` command opens (either terminal); another class raises."""
    opened = set()
    for entry in native.list_by_class(schema.Options)[0].open_terminals or []:
        target = entry.rsplit(" ", 1)[0]
        kind, _, name = target.partition(".")
        if kind.lower() != "line":
            raise ValueError(f"Open {entry}: only a Line's terminal is mapped (as an open switch)")
        opened.add(name.lower())
    return opened


def line_phases(line, phases: int, buses: Mapping[str, BusSystem], *, label: str | None = None) -> tuple[str, str, str]:
    """``(bus1, bus2, phases)``: the lowered bus names and the phase of each conductor in bus order.

    A conductor with no node takes the DSS default (conductor k on node k). Nodes 1/2/3 are A/B/C, and 1/2 are
    s1/s2 on a split-phase island (DSS-5). A phase conductor on node 0, or bus2 nodes that differ from bus1's,
    raise. ``label`` names the record in errors (default ``Line <name>``; the series reactor passes its own).
    """
    label = label or f"Line {line.name}"
    letters = []
    for spec in (line.bus1, line.bus2):
        bus, given = parse_bus(spec)
        if bus not in buses:
            raise ValueError(f"{label}: bus {bus} has no voltage (the topology walk did not reach it)")
        nodes = (given + tuple(range(len(given) + 1, phases + 1)))[:phases]
        names = _SPLIT_PHASE_OF_NODE if buses[bus].system is System.SPLIT_PHASE else _PHASE_OF_NODE
        unknown = [node for node in nodes if node not in names]
        if unknown:
            raise ValueError(f"{label}: bus {spec} puts conductors on nodes {unknown}, which have no phase")
        letters.append("".join(names[node] for node in nodes))
    if letters[0] != letters[1]:
        raise ValueError(f"{label}: bus1 phases {letters[0]} and bus2 phases {letters[1]} differ "
                         "(a transposition is not mapped)")
    return parse_bus(line.bus1)[0], parse_bus(line.bus2)[0], letters[0]


def _units(line) -> str | None:
    text = cell(line.units)
    if text is None or text.lower() == "none":
        return None
    return lookup(linecode_mapper.LENGTH_UNIT, text.lower(), slot="units", record_id=line.name)


def _has_inline(line) -> bool:
    return any(getattr(line, slot) not in (None, []) for slot in _INLINE_SLOTS)


def _template_kind(line) -> str:
    """Which of linecode, geometry, spacing, inline gives the line's impedance; none or two raise."""
    kinds = [kind for kind, given in (("linecode", line.linecode), ("geometry", line.geometry),
                                      ("spacing", line.spacing), ("inline", _has_inline(line))) if given]
    if len(kinds) != 1:
        raise ValueError(f"Line {line.name}: gives {' and '.join(kinds) or 'no impedance'}; exactly one of linecode, "
                         "geometry, spacing + wires, or inline values is mapped (DSS keeps the last, which the "
                         "reader does not record)")
    if kinds != ["spacing"] and any(getattr(line, slot) for slot in _GEOMETRY_ARRAYS):
        raise ValueError(f"Line {line.name}: wires/cncables/tscables without spacing=")
    return kinds[0]


#: The engine keeps a line's default C1, C0 per kft and converts them to the line's units; its default r0, x0
#: stay per unit length as they are (checked against the engine).
_DEFAULT_C_LENGTH = "kft"


def inline_code(line, phases: int):
    """``(LineCode, comment)``: a line's inline values as a LineCode named after the line (DSS-8). A sequence
    line's unset r1, x1, r0, x0, C1, C0 take the engine's defaults: r and x per unit length as they are, C1 and
    C0 in nF per kft converted to the line's units."""
    values = {slot: getattr(line, slot) for slot in _INLINE_SLOTS if getattr(line, slot) not in (None, [])}
    filled = []
    if not any(slot in values for slot in ("rmatrix", "xmatrix", "cmatrix")):
        defaults = dss_defaults(NATIVE_CLASS)
        unit = _units(line)
        for slot in ("r1", "x1", "r0", "x0", "C1", "C0"):
            alternative = {"C1": "B1", "C0": "B0"}.get(slot)
            if slot in values or (alternative is not None and alternative in values):
                continue
            value = defaults[slot]
            if alternative is not None and unit is not None:
                value = float(units.Quantity(value, f"nF/{_DEFAULT_C_LENGTH}").to(f"nF/{unit}").magnitude)
            values[slot] = value
            filled.append(f"{slot}={cell(value)}")
    code = schema.Linecode(name=line.name, nphases=phases, units=line.units, baseFreq=cell(line.basefreq), **values)
    return code, (f"defaulted: {', '.join(filled)}" if filled else None)


def _check_unmapped(line) -> None:
    unmapped = [slot for slot in _UNMAPPED if getattr(line, slot) not in (None, [])]
    if unmapped:
        raise ValueError(f"Line {line.name}: {', '.join(unmapped)} not mapped yet (no deck in the sweep sets them)")


def _comment(*parts) -> str | None:
    return "\n".join(part for part in parts if part) or None


class _Segment(NamedTuple):
    columns: tuple[Column, ...]
    row: Row


class _Document:
    """The rows of ``line.cimtbl``, gathered per table so each table is written once."""

    def __init__(self):
        self.inline_codes: list = []
        self.configurations: list = []
        self.segments: dict[tuple[Column, ...], list[Row]] = {}
        self.limit_sets: list[Row] = []
        self.limits: list[Row] = []
        self.switches: dict[str, list[Row]] = {}
        self.reclose_sequences: list[Row] = []


def code_ratings(code) -> dict[str, tuple[float, str]]:
    """``{slot: (amps, source)}`` a line copies from its LineCode."""
    return {slot: (float(getattr(code, slot)), f"LineCode {code.name}")
            for slot in ("normamps", "emergamps") if getattr(code, slot) is not None}


def conductor_ratings(record, wires: Mapping[str, object]) -> dict[str, tuple[float, str]]:
    """``{slot: (amps, source)}`` of the first conductor of a LineGeometry (or a Line with ``spacing=``), as the
    engine rates the wire (wire_ratings: an unset emergamps is 1.5 x normamps)."""
    names = next(getattr(record, slot) for slot in _GEOMETRY_ARRAYS if getattr(record, slot))
    first = wires[str(names[0]).lower()]
    label = f"{type(first).__name__} {first.name}"
    return {slot: (amps, f"1.5 x normamps of {label}" if note else label)
            for slot, (amps, note) in wire_mapper.wire_ratings(first).items()}


def geometry_ratings(geometry, wires: Mapping[str, object]) -> dict[str, tuple[float, str]]:
    """``{slot: (amps, source)}`` a line copies from its LineGeometry: the geometry's own, else its first
    conductor's (the engine's rule)."""
    values = conductor_ratings(geometry, wires)
    for slot in ("normamps", "emergamps"):
        if getattr(geometry, slot) is not None:
            values[slot] = (float(getattr(geometry, slot)), f"LineGeometry {geometry.name}")
    return values


def rating_rows(equipment: str, amps: dict[str, float], comment: str | None = None) -> tuple[Row, list[Row]]:
    """The ``OperationalLimitSet`` row ``<equipment>_limits`` and its ``CurrentLimit`` rows (``_norm``,
    ``_emerg``) for ``amps`` (``{"normamps": A, "emergamps": A}``, either may be missing). Shared with the series
    reactor."""
    limits = f"{equipment}_limits"
    rows = [Row([f"{equipment}_{suffix}", cell(amps[slot]), limit_type, limits])
            for slot, (suffix, limit_type) in (("normamps", ("norm", "olt_normal")),
                                               ("emergamps", ("emerg", "olt_emergency"))) if slot in amps]
    return Row([limits, equipment], comment=comment), rows


def rating_tables(limit_sets: list[Row], limits: list[Row]) -> list[Table]:
    """The ``OperationalLimitSet`` and ``CurrentLimit`` tables of ``rating_rows`` rows (none when empty)."""
    if not limit_sets:
        return []
    return [Table("OperationalLimitSet", [Column("mRID"), Column("Equipment")], limit_sets),
            Table("CurrentLimit", [Column("mRID"), Column("normalValue", "A"), Column("OperationalLimitType"),
                                   Column("OperationalLimitSet")], limits)]


def _ratings(line, borrowed: dict[str, tuple[float, str]], document: _Document, segment: str) -> None:
    """The line's ``OperationalLimitSet`` and ``CurrentLimit``s: each value the line's own (DSS keeps the last
    set, and decks give a line's ratings after its linecode/geometry), else what the line copies from its code
    or geometry. Nothing from DSS's 400/600 A defaults."""
    values, sources = {}, []
    for slot in ("normamps", "emergamps"):
        if getattr(line, slot) is not None:
            values[slot] = float(getattr(line, slot))
        elif slot in borrowed:
            values[slot], source = borrowed[slot]
            sources.append(f"{slot} from {source}")
    if not values:
        return
    limit_set, limits = rating_rows(segment, values, f"ratings: {', '.join(sources)}" if sources else None)
    document.limit_sets.append(limit_set)
    document.limits.extend(limits)


def _segment(line, phases: str, bus1: str, bus2: str, reference: tuple[str, str], length_unit: str,
             notes: list[str], buses, container: str) -> _Segment:
    length = line.length
    if length is None:
        length = 1.0
        notes.append("defaulted: length=1")
    column, value = reference
    columns = (Column("mRID"), Column("name"), Column("node1"), Column("node2"), Column("phases"),
               Column("length", length_unit), Column(column), Column("BaseVoltage"),
               Column("EquipmentContainer", default=container), Column("normallyInService"))
    row = Row([mrid(PREFIX, line.name, lowercase=True), str(line.name), bus1, bus2, phases, cell(float(length)),
               value, buses[bus1].base_voltage, cell(line.enabled)],
              comment=_comment(*notes, untranscribed_values(FIELDS, line)))
    return _Segment(columns, row)


def _switch_row(line, phases: str, bus1: str, bus2: str, control: SwitchControl, opened: bool, buses,
                container: str) -> Row:
    is_open = bool(opened or control.open)
    if opened and control.open is False:
        raise ValueError(f"Line {line.name}: an Open command opens it, but its control's State is closed")
    normal_open = control.normal_open if control.normal_open is not None else is_open
    dropped = [f"{slot}={cell(getattr(line, slot)) if not isinstance(getattr(line, slot), list) else getattr(line, slot)}"
               for slot in _SWITCH_DROPPED if getattr(line, slot) not in (None, [])]
    cells = [mrid(SWITCH_PREFIX, line.name, lowercase=True), str(line.name), bus1, bus2, phases_cell(phases)]
    if control.cim_class == "Fuse":
        cells.append(cell(control.rated_current))
    cells += [cell(is_open), cell(normal_open), buses[bus1].base_voltage, cell(line.enabled)]
    return Row(cells, comment=_comment(f"untranscribed (a switch): {', '.join(dropped)}" if dropped else None,
                                       untranscribed_values(FIELDS, line)))


def reclose_rows(switch: str, recloses: Reclose) -> list[Row]:
    """One ``RecloseSequence`` row per reclosure of ``switch``, steps from 1."""
    return [Row([f"{switch}_rs{step}", switch, str(step), cell(delay)],
                comment=recloses.defaulted if step == 1 else None)
            for step, delay in enumerate(recloses.delays, 1)]


def _switch_columns(cim_class: str, container: str) -> list[Column]:
    columns = [Column("mRID"), Column("name"), Column("node1"), Column("node2"), Column("phases")]
    if cim_class == "Fuse":
        columns.append(Column("ratedCurrent", "A"))
    return columns + [Column("open"), Column("normalOpen"), Column("BaseVoltage"),
                      Column("EquipmentContainer", default=container), Column("normallyInService")]


def map_line(native, buses: Mapping[str, BusSystem], container: str, *, base_frequency: float,
             length_unit: str | None = None) -> Document:
    """Every ``Line`` of a DSS model as one ``line`` document: segments, switches, synthesized templates and
    the segments' ratings.

    ``buses`` is the topology walk's result (lowercased bus names); ``container`` the EquipmentContainer of every
    segment and switch; ``base_frequency`` (Hz) and ``length_unit`` are the deck's, as for LineCode (DSS-3, 3b).
    """
    lines = native.list_by_class(NATIVE_CLASS)
    if not lines:
        return Document(name="line", statements=[], profile=CIM_PROFILE)
    codes = {str(code.name).lower(): code for code in native.list_by_class(schema.Linecode)}
    code_templates = linecode_mapper.templates(native, length_unit)
    geometries = {str(g.name).lower(): g for g in native.list_by_class(schema.Linegeometry)}
    spacings = {str(s.name).lower(): s for s in native.list_by_class(schema.Linespacing)}
    infos = geometry_mapper.wire_infos(native)
    wires = {str(w.name).lower(): w for native_class, _, _ in wire_mapper.CATALOGS for w in native.list_by_class(native_class)}
    controls = switch_controls(native)
    opened = opened_lines(native)
    names = {str(line.name).lower() for line in lines}
    for missing in sorted((set(controls) | opened) - names):
        raise ValueError(f"Line {missing}: switched by a control or an Open command, but no New defines it")

    document = _Document()
    inline_given, inline_gated = [], []  # (line, code, defaulted)
    pending = []  # (line, phases, bus1, bus2, notes) of inline segments, finished after the gate
    for line in lines:
        _check_unmapped(line)
        key = str(line.name).lower()
        is_switch = bool(line.Switch)
        if not is_switch and (key in controls or key in opened):
            raise ValueError(f"Line {line.name}: a control or an Open command switches it, but it is not Switch=y")
        if is_switch:
            phases = line.phases if line.phases is not None else 3
            bus1, bus2, letters = line_phases(line, phases, buses)
            control = controls.get(key, SwitchControl("LoadBreakSwitch", None, None, None))
            if control.fuse_phase_states not in (None, phases):
                raise ValueError(f"Line {line.name}: its Fuse's Normal/State give {control.fuse_phase_states} values "
                                 f"for {phases} phases; the engine sets a fuse phase by phase, and CIM's state is the "
                                 "whole switch's")
            document.switches.setdefault(control.cim_class, []).append(
                _switch_row(line, letters, bus1, bus2, control, key in opened, buses, container))
            if control.reclose is not None:
                document.reclose_sequences += reclose_rows(mrid(SWITCH_PREFIX, line.name, lowercase=True),
                                                           control.reclose)
            continue
        kind = _template_kind(line)
        if line.rho is not None and kind not in ("geometry", "spacing"):
            raise ValueError(f"Line {line.name}: rho={line.rho} without a geometry; the earth model computes nothing "
                             "there (not mapped)")
        notes: list[str] = []
        if kind == "linecode":
            code = codes.get(str(line.linecode).lower())
            if code is None:
                raise ValueError(f"Line {line.name}: linecode={line.linecode} is no LineCode")
            phases = line.phases if line.phases is not None else code.nphases
            if phases != code.nphases:
                raise ValueError(f"Line {line.name}: phases={phases} with LineCode {code.name} (nphases="
                                 f"{code.nphases}); the engine's rule is not pinned yet (DSS-10)")
            own_unit = _units(line)
            choices = code_templates[str(code.name).lower()]
            template = choices[0] if len(choices) == 1 else next(t for t in choices if t.unit == own_unit)
            bus1, bus2, letters = line_phases(line, phases, buses)
            document_row = _segment(line, letters, bus1, bus2, ("PerLengthImpedance", template.mrid),
                                    own_unit or template.unit, notes, buses, container)
            _ratings(line, code_ratings(code), document, mrid(PREFIX, line.name, lowercase=True))
        elif kind in ("geometry", "spacing"):
            source = geometries.get(str(line.geometry).lower()) if kind == "geometry" else \
                spacings.get(str(line.spacing).lower())
            if source is None:
                raise ValueError(f"Line {line.name}: {kind}={getattr(line, kind)} is no Line{kind.capitalize()}")
            phases = line.phases if line.phases is not None else source.nphases
            if phases != source.nphases:
                raise ValueError(f"Line {line.name}: phases={phases} with {kind} {source.name} (nphases="
                                 f"{source.nphases})")
            neutrals = source.nconds - source.nphases
            if neutrals > 1:
                raise ValueError(f"Line {line.name}: {kind} {source.name} has {neutrals} neutral conductors; one is "
                                 "mapped")
            bus1, bus2, letters = line_phases(line, phases, buses)
            unit = _units(line)
            if unit is None:
                unit = _GEOMETRY_LENGTH_UNIT
                notes.append(f"defaulted: units={unit} (the engine reads a unitless geometry line in metres)")
            if kind == "geometry":
                reference = mrid("wc_", source.name, lowercase=True)
            else:
                reference = f"{mrid(PREFIX, line.name, lowercase=True)}_wc"
                document.configurations += [
                    ObjectStatement("WireConfiguration", [
                        (Column("mRID"), reference), (Column("name"), str(line.name)),
                        (Column("numberOfPhases"), cell(source.nphases)),
                        (Column("WireSpacing"), mrid("spc_", source.name, lowercase=True)),
                        (Column("EarthResistivity"), geometry_mapper.EARTH_MRID)],
                        comment=f"synthesized: the spacing and conductors of Line {line.name}"),
                    geometry_mapper.wire_sequence_table(reference,
                                                        geometry_mapper.conductor_infos(line, source.nconds, infos)),
                ]
            document_row = _segment(line, letters + "N" * neutrals, bus1, bus2, ("WireConfiguration", reference),
                                    unit, notes, buses, container)
            _ratings(line, geometry_ratings(source, wires) if kind == "geometry" else conductor_ratings(line, wires),
                     document,
                     mrid(PREFIX, line.name, lowercase=True))
        else:
            phases = line.phases if line.phases is not None else 3
            bus1, bus2, letters = line_phases(line, phases, buses)
            code, defaulted = inline_code(line, phases)
            (inline_given if _units(line) else inline_gated).append((line, code, defaulted))
            pending.append((line, letters, bus1, bus2, notes))
            continue
        document.segments.setdefault(document_row.columns, []).append(document_row.row)

    synthesized = {}
    for line, code, defaulted in inline_given:
        synthesized[str(line.name).lower()] = [linecode_mapper.Template(
            f"{mrid(PREFIX, line.name, lowercase=True)}_lc", _units(line), None)]
    synthesized.update(linecode_mapper.gated_templates(
        [code for _, code, _ in inline_gated], length_unit,
        lambda code: f"{mrid(PREFIX, code.name, lowercase=True)}_lc"))
    entries = []
    for line, code, defaulted in inline_given + inline_gated:
        [template] = synthesized[str(line.name).lower()]
        note = _comment(f"synthesized: the inline values of Line {line.name}", template.note, defaulted)
        entries.append((code, [template._replace(note=note)]))
    document.inline_codes = linecode_mapper.impedance_statements(entries, base_frequency) if entries else []
    for line, letters, bus1, bus2, notes in pending:
        [template] = synthesized[str(line.name).lower()]
        segment = _segment(line, letters, bus1, bus2, ("PerLengthImpedance", template.mrid),
                           _units(line) or template.unit, notes, buses, container)
        document.segments.setdefault(segment.columns, []).append(segment.row)
        _ratings(line, {}, document, mrid(PREFIX, line.name, lowercase=True))
    return Document(name="line", statements=_statements(document, container), profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(lines)))


def _statements(document: _Document, container: str) -> list:
    statements = [*document.inline_codes, *document.configurations]
    statements += [Table("ACLineSegment", list(columns), rows) for columns, rows in document.segments.items()]
    statements += rating_tables(document.limit_sets, document.limits)
    for cim_class in ("Fuse", "Recloser", "LoadBreakSwitch"):
        if cim_class in document.switches:
            statements.append(Table(cim_class, _switch_columns(cim_class, container), document.switches[cim_class],
                                    comment="open: an Open command or the control's State; normalOpen: the "
                                            "control's Normal, else open"))
    if document.reclose_sequences:
        statements.append(Table("RecloseSequence", [Column("mRID"), Column("ProtectedSwitch"), Column("recloseStep"),
                                                    Column("recloseDelay", "s")], document.reclose_sequences,
                                comment="a Recloser's Shots - 1 reclosures at its RecloseIntervals"))
    return statements
