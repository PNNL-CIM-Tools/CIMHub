"""GLM ``overhead_line``, ``underground_line``, ``triplex_line`` -> one ``.cimtbl`` each: ``ACLineSegment`` (S3a).

A line references its configuration's template: the ``WireConfiguration`` of a geometry or triplex configuration,
or the ``PerLengthPhaseImpedance`` of a matrix one (S3a-2). Its ``phases`` cell numbers its ACLineSegmentPhases
1..n in written order, so it is written in the configuration's own order (ABC, then N; ``s1s2N`` on a triplex line)
and must name the configuration's phases (S3a-3). Its own ratings, else its configuration's, go on its own
``OperationalLimitSet`` (S3a-4). No impedance is computed (skill ``conductor-geometry``).

Mapping spec: ``cimhub_gridlabd/docs/CIMTBL_MAPPING.md#s3a-lines-and-switches``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, Row, Table
from cimtopology.core import System

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, mrid, untranscribed_values
from cimhub_gridlabd.glm_reader import GlmModel
from cimhub_gridlabd.glm_schema import registry_unit
from cimhub_gridlabd.importer.cimtbl import configuration as configuration_part
from cimhub_gridlabd.importer.cimtbl.catalog import label, ratings, referenced
from cimhub_gridlabd.importer.cimtbl.conductor import info_class
from cimhub_gridlabd.importer.cimtbl.link import Limits, classify, ends, link_ratings, provenance
from cimhub_gridlabd.schema import gridlabd as schema

PREFIX = "ln_"
_SEGMENT = "ACLineSegment"
TRIPLEX_PHASES = "s1s2N"

_OWN = {
    "name": Field("copied", ((_SEGMENT, "name", None),), "mRID = ln_ + name"),
    "phases": Field("structural", note="the phases cell: ABC then N, equal to the configuration's conductors "
                                       "(geometry) or diagonal (matrix); s1s2N on a triplex line (S3a-3)"),
    "status": Field("structural", note="unset or CLOSED; OPEN raises (the walk: a line is not a switch)"),
    "configuration": Field("structural", note="WireConfiguration = wc_<configuration> (geometry, triplex) or "
                                              "PerLengthImpedance = lc_<configuration> (matrix), S3a-2"),
    "length": Field("copied", ((_SEGMENT, "length", "{unit}"),), "in its written unit; unset raises"),
}

#: ``(native class, its configuration class, its conductor class or None)`` per line artifact, in Import order.
LINES = (
    (schema.OverheadLine, schema.LineConfiguration, schema.OverheadLineConductor),
    (schema.UndergroundLine, schema.LineConfiguration, schema.UndergroundLineConductor),
    (schema.TriplexLine, schema.TriplexLineConfiguration, None),
)
FIELDS = {native_class: classify(native_class, _OWN) for native_class, _, _ in LINES}
_CONFIGURATION = {native_class: configuration_class for native_class, configuration_class, _ in LINES}
_CONDUCTOR = {native_class: conductor_class for native_class, _, conductor_class in LINES}


def _check_conductors(model: GlmModel, line, configuration) -> None:
    """A geometry line's conductors are its own class's, and an underground line's phase cables one kind
    (``overhead_line.cpp:923``, ``underground_line.cpp:149`` throw)."""
    expected = _CONDUCTOR[type(line)]
    conductors = {letter: model.by_name(getattr(configuration, f"conductor_{letter}"))
                  for letter in configuration_part.conductor_letters(configuration)}
    wrong = [f"conductor_{letter} {conductor.name} ({conductor.class_name})" for letter, conductor in conductors.items()
             if not isinstance(conductor, expected)]
    if wrong:
        raise ValueError(f"{label(line)}: configuration {configuration.name} has {', '.join(wrong)}; an "
                         f"{line.class_name} needs {expected.class_name}s")
    kinds = {info_class(conductor) for letter, conductor in conductors.items() if letter != "N"}
    if len(kinds) > 1:
        raise ValueError(f"{label(line)}: configuration {configuration.name} mixes phase cables "
                         f"({', '.join(sorted(kinds))}); underground_line.cpp throws")


def _triplex_phases(model: GlmModel, line, roots: dict[str, str], buses) -> str:
    written = str(line.phases)
    primary = set(written) - {"S"}
    if len(written) != 2 or "S" not in written or len(primary) != 1 or not primary <= set("ABC"):
        raise ValueError(f"{label(line)}: phases {written}; a triplex line is AS, BS or CS")
    for slot in ("from_node", "to"):
        root = roots[getattr(line, slot)]
        bus = model.by_name(root)
        if buses[root].system is not System.SPLIT_PHASE or not primary <= set(str(bus.phases)):
            raise ValueError(f"{label(line)}: phases {written}, but its end {bus.class_name} {root} is phases "
                             f"{bus.phases} on a {buses[root].system.name} system")
    return TRIPLEX_PHASES


def _phases(line, configuration) -> str:
    written = str(line.phases)
    unknown = set(written) - set("ABCN")
    if unknown:
        raise ValueError(f"{label(line)}: phases {written}; only A, B, C and N are mapped on an {line.class_name}")
    ordered = "".join(letter for letter in "ABCN" if letter in written)
    if configuration_part.is_matrix(configuration):
        if "N" in ordered:
            raise ValueError(f"{label(line)}: phases {written} with N on the matrix configuration "
                             f"{configuration.name}; not mapped (no deck has one)")
        expected = configuration_part.diagonal_letters(configuration)
    else:
        expected = configuration_part.conductor_letters(configuration)
    if ordered != expected:
        raise ValueError(f"{label(line)}: phases {written} are not the phases {expected} of configuration "
                         f"{configuration.name} (S3a-3)")
    return ordered


def _ratings(line, configuration) -> tuple[dict[str, float], str | None]:
    """The line's own ratings, else its configuration's (S3a-4); both set and different raise."""
    own = link_ratings(line)
    given, _ = ratings(configuration)
    if own and given and own != given:
        raise ValueError(f"{label(line)}: its ratings {own} differ from its configuration {configuration.name}'s "
                         f"{given}")
    if own:
        return own, None
    if given:
        return given, f"ratings: from {configuration.class_name} {configuration.name}"
    return {}, None


def _segment(model: GlmModel, line, roots: dict[str, str], buses) -> tuple[tuple[Column, ...], Row, str]:
    """The columns and row of one line, and the configuration it references."""
    if line.configuration is None:
        raise ValueError(f"{label(line)}: configuration unset ({line.class_name}.cpp throws)")
    if line.length is None:
        raise ValueError(f"{label(line)}: length unset (GridLAB-D's 0 is a line of no impedance)")
    if line.phases is None:
        raise ValueError(f"{label(line)}: phases unset")
    configuration = referenced(model, line, "configuration", (_CONFIGURATION[type(line)],))
    if type(configuration) is not _CONFIGURATION[type(line)]:  # the schema derives the triplex one from it
        raise ValueError(f"{label(line)}: configuration {configuration.name} is a {configuration.class_name}, not a "
                         f"{_CONFIGURATION[type(line)].class_name} ({line.class_name}.cpp throws)")
    if isinstance(line, schema.TriplexLine):
        phases = _triplex_phases(model, line, roots, buses)
    else:
        phases = _phases(line, configuration)
        if not configuration_part.is_matrix(configuration):
            _check_conductors(model, line, configuration)
    column, template = configuration_part.template(configuration)
    node1, node2, bus = ends(line, roots, buses)
    columns = (Column("mRID"), Column("name"), Column("node1"), Column("node2"), Column("phases"),
               Column("length", registry_unit(model.unit(line, "length"))), Column(column), Column("BaseVoltage"))
    row = Row([mrid(PREFIX, line.name), str(line.name), node1, node2, phases, cell(line.length), template,
               bus.base_voltage], comment=untranscribed_values(FIELDS[type(line)], line))
    return columns, row, configuration


def map_lines(model: GlmModel, native_class: type, roots: dict[str, str], buses, feeder: str) -> Document:
    """Every line of one GLM line class as one document: segments, one table per (length unit, template
    column), then their limit sets."""
    lines = model.list_by_class(native_class)
    by_columns: dict[tuple[Column, ...], list[Row]] = {}
    limits = Limits()
    for line in lines:
        columns, row, configuration = _segment(model, line, roots, buses)
        by_columns.setdefault(columns, []).append(row)
        rated, comment = _ratings(line, configuration)
        limits.add(mrid(PREFIX, line.name), rated, comment)
    statements = [Table(_SEGMENT, [*columns, Column("EquipmentContainer", default=feeder)], rows)
                  for columns, rows in by_columns.items()]
    return Document(name=native_class.class_name, statements=[*statements, *limits.tables()], profile=CIM_PROFILE,
                    comment=provenance(native_class.class_name, "ACLineSegment (by its configuration's "
                                       "WireConfiguration or PerLengthPhaseImpedance)", len(lines))
                    if lines else None)
