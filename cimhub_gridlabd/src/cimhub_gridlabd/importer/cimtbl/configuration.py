"""GLM ``line_configuration`` and ``triplex_line_configuration`` -> one ``.cimtbl`` each (S2-8, S2-9).

A line configuration is geometry or a matrix, never both (GridLAB-D would use the matrix, so a record with both
raises). Geometry, ``spacing`` + ``conductor_X``: a ``WireConfiguration`` with one ``WireSequenceConfiguration``
per conductor, numbered 1..n in ABCN order like its spacing's positions (S2-3). Matrix, ``z11``..``z33``: a
``PerLengthPhaseImpedance`` with one ``PhaseImpedanceData`` per lower-triangle element, rows compacted to 1..n
(CIM's range), and b derived from c at the base frequency.

A triplex configuration is geometry too: GridLAB-D computes its spacing from ``diameter`` and
``insulation_thickness`` (``triplex_spacing``), so that spacing is written as a derived ConductorDistanceSpacing.
No impedance is computed from geometry (skill ``conductor-geometry``).

Mapping spec: ``cimhub_gridlabd/docs/CIMTBL_MAPPING.md#s2-catalogs``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, ObjectStatement, Row, Table

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, mrid, untranscribed_values
from cimhub_core.derived.capacitance import b_from_c
from cimhub_gridlabd.glm_reader import GlmModel
from cimhub_gridlabd.glm_schema import registry_unit
from cimhub_gridlabd.importer.cimtbl import spacing as spacing_part
from cimhub_gridlabd.importer.cimtbl.catalog import HEADER_FIELDS, label, provenance, referenced
from cimhub_gridlabd.importer.cimtbl.conductor import wire_info_mrid
from cimhub_gridlabd.schema import gridlabd as schema

GEOMETRY_PREFIX, MATRIX_PREFIX = "wc_", "lc_"
_WIRE, _PHASE = "WireConfiguration", "PerLengthPhaseImpedance"
_INDEX = "123"
_LETTER = dict(zip(_INDEX, "ABC"))
Z_SLOTS = tuple(f"z{i}{j}" for i in _INDEX for j in _INDEX)
C_SLOTS = tuple(f"c{i}{j}" for i in _INDEX for j in _INDEX)
_RATING = Field("structural", note="not on the template (D9): the S3a line mapper puts it on each line's own "
                                   "OperationalLimitSet")
_RATINGS = {slot: _RATING for slot in ("rating_summer_continuous", "rating_summer_emergency",
                                       "rating_winter_continuous", "rating_winter_emergency")}

LINE_FIELDS = {
    "name": Field("copied", ((_WIRE, "name", None), (_PHASE, "name", None)), "mRID = wc_ or lc_ + name"),
    **HEADER_FIELDS,
    "spacing": Field("structural", note="geometry: WireConfiguration.WireSpacing = spc_ + spacing"),
    **{f"conductor_{letter}": Field("structural", note="geometry: one WireSequenceConfiguration, sequenceNumber "
                                                       "1..n in ABCN order (S2-3), WireInfo = the conductor's mRID; "
                                                       "numberOfPhases = the A, B, C conductors set")
       for letter in "ABCN"},
    **{slot: Field("structural", note="matrix: one PhaseImpedanceData per lower-triangle element, r and x the "
                                      "real and imaginary parts; rows and columns compacted in ABC order; z_ij must "
                                      "equal z_ji") for slot in Z_SLOTS},
    **{slot: Field("derived", note="matrix: PhaseImpedanceData b = 2 pi f c (b_from_c), nF gives nS, f the base "
                                   "frequency (also calculatedFrequency). Unset with its z set: GridLAB-D's 0, "
                                   "defaulted") for slot in C_SLOTS},
    **_RATINGS,
}

_NOT_READ = "inherited from line_configuration and not read by GridLAB-D's triplex line: set raises"
_TRIPLEX_Z = "no readable deck sets a triplex matrix: set raises until one does"

TRIPLEX_FIELDS = {
    "name": Field("copied", ((_WIRE, "name", None),), "mRID = wc_ + name; its spacing wc_<name>_spc"),
    **HEADER_FIELDS,
    "spacing": Field("structural", note=_NOT_READ),
    **{f"conductor_{letter}": Field("structural", note=_NOT_READ) for letter in "ABC"},
    "conductor_1": Field("structural", note="WireSequenceConfiguration 1 (spacing phase s1); required"),
    "conductor_2": Field("structural", note="WireSequenceConfiguration 2 (spacing phase s2); required"),
    "conductor_N": Field("structural", note="WireSequenceConfiguration 3 (spacing phase N; GridLAB-D keeps it in "
                                            "its phase C slot); required"),
    "diameter": Field("derived", note="the spacing's distances (triplex_spacing): D12 = diameter + 2 "
                                      "insulation_thickness, D1N = D2N = diameter + insulation_thickness"),
    "insulation_thickness": Field("derived", note="see diameter"),
    **{slot: Field("structural", note=_TRIPLEX_Z) for slot in Z_SLOTS + C_SLOTS},
    **_RATINGS,
}

FIELDS = {schema.LineConfiguration: LINE_FIELDS, schema.TriplexLineConfiguration: TRIPLEX_FIELDS}

_LINE_CONDUCTORS = (schema.OverheadLineConductor, schema.UndergroundLineConductor)


def _is_set(record, slots) -> list[str]:
    return [slot for slot in slots if getattr(record, slot) is not None]


def conductor_letters(configuration) -> str:
    """The ``conductor_X`` letters a line_configuration sets, in ABCN order (its positions, S2-3)."""
    return "".join(letter for letter in "ABCN" if getattr(configuration, f"conductor_{letter}") is not None)


def _nonzero(configuration, slot: str) -> bool:
    """A matrix value set to something other than 0: a written 0 is GridLAB-D's default (S6, the Milsoft exports
    write all nine z terms)."""
    value = getattr(configuration, slot)
    return value is not None and (float(value.real or 0.0), float(value.imag or 0.0)) != (0.0, 0.0)


def diagonal_letters(configuration) -> str:
    """The phases whose ``z_ii`` a matrix line_configuration sets to other than 0, in ABC order (its compacted
    rows, S2-9)."""
    return "".join(_LETTER[i] for i in _INDEX if _nonzero(configuration, f"z{i}{i}"))


def is_matrix(configuration) -> bool:
    """A line_configuration given by z (and c) values, not by spacing and conductors (S2-9)."""
    return bool(_is_set(configuration, Z_SLOTS + C_SLOTS))


def template(configuration) -> tuple[str, str]:
    """``(ACLineSegment column, mRID)`` of the template a line on ``configuration`` references (S3a-2)."""
    if isinstance(configuration, schema.LineConfiguration) and is_matrix(configuration):
        return "PerLengthImpedance", mrid(MATRIX_PREFIX, configuration.name)
    return _WIRE, mrid(GEOMETRY_PREFIX, configuration.name)


# ---------------------------------------------------------------------------
# line_configuration: geometry
# ---------------------------------------------------------------------------

def _geometry(model: GlmModel, configuration) -> list:
    spacing = referenced(model, configuration, "spacing", (schema.LineSpacing,))
    letters = conductor_letters(configuration)
    spaced = spacing_part.phases(spacing)
    if spaced and spaced != letters:
        raise ValueError(f"{label(configuration)}: its conductors {letters} are not the phases {spaced} its "
                         f"spacing {spacing.name} names (S2-3)")
    configuration_mrid = mrid(GEOMETRY_PREFIX, configuration.name)
    infos = [wire_info_mrid(referenced(model, configuration, f"conductor_{letter}", _LINE_CONDUCTORS))
             for letter in letters]
    phase_count = sum(letter != "N" for letter in letters)
    return wire_configuration(configuration_mrid, str(configuration.name), phase_count,
                              spacing_part.spacing_mrid(spacing), list(zip(letters, infos)),
                              comment=untranscribed_values(LINE_FIELDS, configuration))


def wire_configuration(configuration_mrid: str, name: str, phase_count: int, spacing_mrid: str,
                       conductors: list[tuple[str, str]], *, comment: str | None = None) -> list:
    """A ``WireConfiguration`` and its ``WireSequenceConfiguration`` rows; ``conductors`` is ``(suffix, WireInfo
    mRID)`` in position order."""
    rows = [Row([f"{configuration_mrid}_{suffix}", str(number), info])
            for number, (suffix, info) in enumerate(conductors, start=1)]
    return [
        ObjectStatement(_WIRE, [(Column("mRID"), configuration_mrid), (Column("name"), name),
                                (Column("numberOfPhases"), str(phase_count)), (Column("WireSpacing"), spacing_mrid)],
                        comment=comment),
        Table("WireSequenceConfiguration", [Column("mRID"), Column(_WIRE, default=configuration_mrid),
                                            Column("sequenceNumber"), Column("WireInfo")], rows),
    ]


# ---------------------------------------------------------------------------
# line_configuration: matrix
# ---------------------------------------------------------------------------

def _one_unit(model: GlmModel, configuration, slots: list[str], what: str) -> str:
    written = {registry_unit(model.unit(configuration, slot)) for slot in slots}
    if len(written) != 1:
        raise ValueError(f"{label(configuration)}: the {what} values are written in {sorted(written)}; one unit "
                         "per matrix")
    return written.pop()


def _symmetric_value(configuration, prefix: str, i: str, j: str):
    lower, upper = getattr(configuration, f"{prefix}{i}{j}"), getattr(configuration, f"{prefix}{j}{i}")
    if lower != upper:
        raise ValueError(f"{label(configuration)}: {prefix}{i}{j}={lower} but {prefix}{j}{i}={upper}; only a "
                         "symmetric matrix is mapped")
    return lower


def _matrix(model: GlmModel, configuration, frequency: float) -> list:
    diagonal = [i for i in _INDEX if _nonzero(configuration, f"z{i}{i}")]
    if not diagonal:
        raise ValueError(f"{label(configuration)}: every z_ii is unset or 0")
    for slot in _is_set(configuration, Z_SLOTS + C_SLOTS):
        if not {slot[1], slot[2]} <= set(diagonal) and _nonzero(configuration, slot):
            raise ValueError(f"{label(configuration)}: {slot} is set without z{slot[1]}{slot[1]} and "
                             f"z{slot[2]}{slot[2]}")
    z_unit = _one_unit(model, configuration, _is_set(configuration, Z_SLOTS), "z")
    c_set = _is_set(configuration, C_SLOTS)
    c_unit = _one_unit(model, configuration, c_set, "c") if c_set else "nF/mile"
    capacitance, per_length = c_unit.split("/", 1)
    if capacitance != "nF":
        raise ValueError(f"{label(configuration)}: c is written in {c_unit}; nF per length is mapped")
    impedance_mrid = mrid(MATRIX_PREFIX, configuration.name)
    rows = []
    for row, i in enumerate(diagonal, start=1):
        for column, j in enumerate(diagonal[:row], start=1):
            z = _symmetric_value(configuration, "z", i, j)
            c = _symmetric_value(configuration, "c", i, j)
            letters = _LETTER[i] if i == j else f"{_LETTER[i]}{_LETTER[j]}"
            defaulted = [f"{prefix} = 0" for prefix, value in (("z", z), ("c", c)) if value is None]
            note = f"z{i}{j} ({letters})" + (f"; defaulted: {', '.join(defaulted)}" if defaulted else "")
            if z is None:  # an unset mutual term: GridLAB-D's create() 0
                z = schema.Complex(real=0.0, imag=0.0)
            rows.append(Row([f"{impedance_mrid}_{row}{column}", str(row), str(column), cell(z.real), cell(z.imag),
                             cell(b_from_c(c or 0.0, frequency))], comment=note))
    return [
        ObjectStatement(_PHASE, [(Column("mRID"), impedance_mrid), (Column("name"), str(configuration.name)),
                                 (Column("conductorCount"), str(len(diagonal))),
                                 (Column("calculatedFrequency", "Hz"), cell(frequency))],
                        comment=untranscribed_values(LINE_FIELDS, configuration)),
        Table("PhaseImpedanceData", [Column("identifier"), Column("PhaseImpedance", default=impedance_mrid),
                                     Column("row"), Column("column"), Column("r", z_unit), Column("x", z_unit),
                                     Column("b", f"nS/{per_length}")], rows,
              comment="derived: b = 2 pi f c (b_from_c)"),
    ]


def _line_statements(model: GlmModel, configuration, frequency: float) -> list:
    matrix = _is_set(configuration, Z_SLOTS + C_SLOTS)
    geometry = _is_set(configuration, ("spacing", "conductor_A", "conductor_B", "conductor_C", "conductor_N"))
    if matrix and geometry:
        raise ValueError(f"{label(configuration)}: sets both a matrix ({', '.join(matrix)}) and geometry "
                         f"({', '.join(geometry)}); GridLAB-D would use the matrix (S2-9)")
    if matrix:
        return _matrix(model, configuration, frequency)
    if not geometry:
        raise ValueError(f"{label(configuration)}: sets neither a matrix nor spacing and conductors")
    if configuration.spacing is None or geometry == ["spacing"]:
        raise ValueError(f"{label(configuration)}: geometry needs both spacing and conductors "
                         f"(sets {', '.join(geometry)}; overhead_line.cpp throws)")
    return _geometry(model, configuration)


def map_line_configuration(model: GlmModel, frequency: float) -> Document:
    """Every ``line_configuration`` as a WireConfiguration or a PerLengthPhaseImpedance."""
    configurations = model.list_by_class(schema.LineConfiguration)
    statements = [statement for configuration in configurations
                  for statement in _line_statements(model, configuration, frequency)]
    return Document(name="line_configuration", statements=statements, profile=CIM_PROFILE,
                    comment=provenance("line_configuration", "WireConfiguration + WireSequenceConfiguration, "
                                       "PerLengthPhaseImpedance + PhaseImpedanceData", len(configurations))
                    if configurations else None)


# ---------------------------------------------------------------------------
# triplex_line_configuration
# ---------------------------------------------------------------------------

def triplex_spacing(diameter: float, insulation_thickness: float) -> tuple[float, float]:
    """``(D12, D1N)`` of a triplex cable, in the unit of its inputs: D12 = d + 2t, D1N = D2N = d + t.

    GridLAB-D ``triplex_line.cpp`` (``D12 = (dcond + 2 * ins_thick) / 12``, ``D13 = (dcond + ins_thick) / 12``, the
    ``/ 12`` taking inches to feet), after Kersting: the two insulated phase conductors touch, the bare neutral
    touches both. The inverse: t = D12 - D1N, d = 2 D1N - D12.
    """
    return diameter + 2 * insulation_thickness, diameter + insulation_thickness


def _triplex_statements(model: GlmModel, configuration) -> list:
    stray = _is_set(configuration, ("spacing", "conductor_A", "conductor_B", "conductor_C") + Z_SLOTS + C_SLOTS)
    if stray:
        raise ValueError(f"{label(configuration)}: {', '.join(stray)} not mapped on a triplex configuration (S2-8)")
    for slot in ("conductor_1", "conductor_2", "conductor_N", "diameter", "insulation_thickness"):
        if getattr(configuration, slot) is None:
            raise ValueError(f"{label(configuration)}: {slot} unset (triplex_line.cpp throws)")
    unit = _one_unit(model, configuration, ["diameter", "insulation_thickness"], "diameter and insulation_thickness")
    d12, d1n = triplex_spacing(configuration.diameter, configuration.insulation_thickness)
    if d12 <= 0 or d1n <= 0:
        raise ValueError(f"{label(configuration)}: D12={d12}, D1N={d1n} {unit}; both must be positive "
                         "(triplex_line.cpp throws)")
    configuration_mrid = mrid(GEOMETRY_PREFIX, configuration.name)
    spacing_mrid = f"{configuration_mrid}_spc"
    distances = [("12", "s1", "s2", d12, unit), ("1N", "s1", "N", d1n, unit), ("2N", "s2", "N", d1n, unit)]
    conductors = [(suffix, wire_info_mrid(referenced(model, configuration, slot, (schema.TriplexLineConductor,))))
                  for suffix, slot in (("1", "conductor_1"), ("2", "conductor_2"), ("N", "conductor_N"))]
    return [
        *spacing_part.spacing_statements(
            spacing_mrid, str(configuration.name), ["s1", "s2", "N"], distances,
            comment=f"derived (triplex_spacing): D12 = diameter + 2 insulation_thickness, D1N = D2N = diameter + "
                    f"insulation_thickness; diameter={cell(configuration.diameter)}, "
                    f"insulation_thickness={cell(configuration.insulation_thickness)} {unit}"),
        *wire_configuration(configuration_mrid, str(configuration.name), 2, spacing_mrid, conductors,
                            comment=untranscribed_values(TRIPLEX_FIELDS, configuration)),
    ]


def map_triplex_line_configuration(model: GlmModel) -> Document:
    """Every ``triplex_line_configuration`` as a WireConfiguration on a derived ConductorDistanceSpacing."""
    configurations = model.list_by_class(schema.TriplexLineConfiguration)
    statements = [statement for configuration in configurations
                  for statement in _triplex_statements(model, configuration)]
    return Document(name="triplex_line_configuration", statements=statements, profile=CIM_PROFILE,
                    comment=provenance("triplex_line_configuration", "WireConfiguration + WireSequenceConfiguration "
                                       "on a derived ConductorDistanceSpacing", len(configurations))
                    if configurations else None)
