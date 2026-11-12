"""GLM ``line_spacing`` -> ``line_spacing.cimtbl``: ``ConductorDistanceSpacing`` + ``ConductorDistance`` (S2-2).

A GLM spacing is pairwise distances and heights above earth, never coordinates, so it stays that: each written
distance is one ``ConductorDistance``, verbatim in its written unit, and a height is a distance to a position of
kind ``earth``. The phases go on the GridAPPS-D extensions ``fromPhase``/``toPhase``; the sequence numbers are
1..n in ABCN order over the phases the written distances name (S2-3), as OpenDSS numbers a LineSpacing. A distance
of 0 is GridLAB-D's "no mutual term" (and its default), not two coincident conductors: it is not written, and the
row lists it (S2-4). No impedance is computed.

Mapping spec: ``cimhub_gridlabd/docs/CIMTBL_MAPPING.md#s2-catalogs``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, ObjectStatement, Row, Table

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, mrid, untranscribed_values
from cimhub_gridlabd.glm_reader import GlmModel
from cimhub_gridlabd.glm_schema import registry_unit
from cimhub_gridlabd.importer.cimtbl.catalog import HEADER_FIELDS, provenance
from cimhub_gridlabd.schema import gridlabd as schema

PREFIX = "spc_"
_SPACING = "ConductorDistanceSpacing"

#: The pair slots in row order, and the height slots (a distance to earth).
PAIRS = ("AB", "AC", "BC", "AN", "BN", "CN")
HEIGHTS = ("AE", "BE", "CE", "NE")
PHASE_ORDER = "ABCN"

_PAIR = Field("structural", note="one ConductorDistance, distance in the written unit; ends numbered 1..n over the "
                                 "spacing's phases (S2-3), fromPhase/toPhase the letters. Unset or 0: no row (S2-4)")
_HEIGHT = Field("structural", note="the conductor's height: a ConductorDistance to a position of kind earth, no "
                                   "second sequence number or phase. Unset or 0: no row (S2-4)")

FIELDS = {
    "name": Field("copied", ((_SPACING, "name", None),), "mRID = spc_ + name; isTemplate = true"),
    **HEADER_FIELDS,
    **{f"distance_{pair}": _PAIR if pair[1] != "E" else _HEIGHT
       for pair in ("AB", "BC", "AC", "AN", "BN", "CN", "AE", "BE", "CE", "NE")},
}

_DISTANCE_COLUMNS = ("mRID", "sequenceNumber1", "conductorKind1", "fromPhase", "sequenceNumber2", "conductorKind2",
                     "toPhase")


def phases(spacing) -> str:
    """The phases the spacing's written, non-zero distances name, in ABCN order."""
    named = {letter for pair in PAIRS + HEIGHTS if getattr(spacing, f"distance_{pair}") not in (None, 0)
             for letter in pair if letter != "E"}
    return "".join(letter for letter in PHASE_ORDER if letter in named)


def _kind(phase: str) -> str:
    return "neutral" if phase == "N" else "phase"


def spacing_statements(spacing_mrid: str, name: str, order: str | list[str],
                       distances: list[tuple[str, str, str | None, float, str]], *, comment: str | None = None):
    """A ``ConductorDistanceSpacing`` template and its ``ConductorDistance`` tables, one per unit.

    ``order`` is the spacing's phases in position order (sequence numbers 1..n); ``distances`` is ``(suffix,
    phase, other phase or None for earth, value, unit)``.
    """
    number = {phase: position for position, phase in enumerate(order, start=1)}
    by_unit: dict[str, list[Row]] = {}
    for suffix, first, second, value, unit in distances:
        ends = [str(number[first]), _kind(first), first]
        ends += [str(number[second]), _kind(second), second] if second is not None else [None, "earth", None]
        by_unit.setdefault(unit, []).append(Row([f"{spacing_mrid}_{suffix}", *ends, cell(value)]))
    statements = [ObjectStatement(_SPACING, [(Column("mRID"), spacing_mrid), (Column("name"), name),
                                             (Column("isTemplate"), "true")], comment=comment)]
    for unit, rows in by_unit.items():
        columns = [Column(_DISTANCE_COLUMNS[0]), Column(_SPACING, default=spacing_mrid),
                   *(Column(column) for column in _DISTANCE_COLUMNS[1:]), Column("distance", unit)]
        statements.append(Table("ConductorDistance", columns, rows))
    return statements


def spacing_mrid(spacing) -> str:
    return mrid(PREFIX, spacing.name)


def _statements(model: GlmModel, spacing) -> list:
    distances, zeros = [], []
    for pair in PAIRS + HEIGHTS:
        slot = f"distance_{pair}"
        value = getattr(spacing, slot)
        if value is None:
            continue
        if value == 0:
            zeros.append(pair)
            continue
        other = None if pair[1] == "E" else pair[1]
        distances.append((pair, pair[0], other, value, registry_unit(model.unit(spacing, slot))))
    notes = [f"0 (GridLAB-D: no coupling): {', '.join(zeros)}"] if zeros else []
    untranscribed = untranscribed_values(FIELDS, spacing)
    if untranscribed:
        notes.append(untranscribed)
    return spacing_statements(spacing_mrid(spacing), str(spacing.name), phases(spacing), distances,
                              comment="\n".join(notes) or None)


def map_line_spacing(model: GlmModel) -> Document:
    """Every ``line_spacing`` as a ``ConductorDistanceSpacing`` in one ``line_spacing`` document."""
    spacings = model.list_by_class(schema.LineSpacing)
    statements = [statement for spacing in spacings for statement in _statements(model, spacing)]
    return Document(name="line_spacing", statements=statements, profile=CIM_PROFILE,
                    comment=provenance("line_spacing", "ConductorDistanceSpacing + ConductorDistance (distances "
                                       "as written; GLM gives no coordinates)", len(spacings)) if spacings else None)
