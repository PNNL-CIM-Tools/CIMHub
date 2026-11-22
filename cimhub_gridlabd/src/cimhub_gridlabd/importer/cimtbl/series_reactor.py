"""GLM ``series_reactor`` -> ``series_reactor.cimtbl``: one ``SeriesCompensator`` per reactor (S7, shape
``series_compensator``).

GridLAB-D's series reactor is one impedance per phase with no coupling between phases (``series_reactor.cpp:105``),
while CIM's SeriesCompensator is one r + jx for every phase. So the phases' ``phase_X_impedance`` must be equal (else
raises), and r, x come from it with r0 = r, x0 = x, as the DSS importer writes a Reactor. A phase's impedance left
unset raises: GridLAB-D's 0 is a switch stand-in under NR (1e4 + 1e4j S), not a reactor. SeriesCompensator has no
per-phase class, so an ``Update`` gives the Terminals of a reactor on fewer than three phases their phases. Its
ratings go on its own ``OperationalLimitSet``, as a line's (S3a-4).

Mapping spec: ``cimhub_gridlabd/docs/CIMTBL_MAPPING.md#s7-series-reactors``.
"""

from __future__ import annotations

from cimtables.connectivity import parse_phases, phase_code
from cimtables.document import Column, Document, Row, Table

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, mrid, phases_cell, untranscribed_values
from cimhub_gridlabd.glm_reader import GlmModel
from cimhub_gridlabd.glm_schema import registry_unit
from cimhub_gridlabd.importer.cimtbl.catalog import label, native_name
from cimhub_gridlabd.importer.cimtbl.link import Limits, classify, ends, link_ratings, provenance
from cimhub_gridlabd.schema import gridlabd as schema

NATIVE_CLASS = schema.SeriesReactor
PREFIX = "rx_"
ANCHOR = "s7-series-reactors"

_SERIES = "SeriesCompensator"
_PARTS = Field("structural", note="GridLAB-D's alias of the impedance's real or imaginary part; set raises (no "
                                  "deck sets one; the impedance is mapped)")

FIELDS = classify(NATIVE_CLASS, {
    "name": Field("copied", ((_SERIES, "name", None),), "mRID = rx_ + name"),
    "phases": Field("structural", note="the reactor's A, B, C, N dropped; fewer than three: its Terminals' phases"),
    "status": Field("structural", note="unset or CLOSED; OPEN raises in the walk (a reactor is not a switch)"),
    **{f"phase_{letter}_impedance": Field(
        "copied", ((_SERIES, "r", "{unit}"), (_SERIES, "x", "{unit}"), (_SERIES, "r0", "{unit}"),
                   (_SERIES, "x0", "{unit}")),
        "real part r, imaginary x; r0 = r, x0 = x (no coupling); every phase's equal, unset raises")
       for letter in "ABC"},
    **{f"phase_{letter}_{part}": _PARTS for letter in "ABC" for part in ("resistance", "reactance")},
})


def _phases(reactor) -> str:
    written = str(reactor.phases) if reactor.phases is not None else ""
    unknown = set(written) - set("ABCN")
    letters = "".join(letter for letter in "ABC" if letter in written)
    if unknown or not letters:
        raise ValueError(f"{label(reactor)}: phases {reactor.phases or 'unset'}; A, B, C (and N) are mapped")
    return letters


def _impedance(model: GlmModel, reactor, letters: str) -> tuple[complex, str]:
    """``(r + jx, unit)``: the one impedance every phase of the reactor has (raises otherwise)."""
    parts = [native_name(reactor, f"phase_{letter}_{part}") for letter in "ABC" for part in ("resistance", "reactance")
             if getattr(reactor, f"phase_{letter}_{part}") is not None]
    if parts:
        raise ValueError(f"{label(reactor)}: {', '.join(parts)} set; only phase_X_impedance is mapped")
    slots = [f"phase_{letter}_impedance" for letter in letters]
    unset = [native_name(reactor, slot) for slot in slots if getattr(reactor, slot) is None]
    if unset:
        raise ValueError(f"{label(reactor)}: {', '.join(unset)} unset; GridLAB-D's 0 is a switch stand-in, not a "
                         "reactor")
    units = {registry_unit(model.unit(reactor, slot)) for slot in slots}
    values = {complex(float(value.real or 0.0), float(value.imag or 0.0))
              for value in (getattr(reactor, slot) for slot in slots)}
    if len(values) > 1 or len(units) > 1:
        written = ", ".join(f"{native_name(reactor, slot)}={getattr(reactor, slot)}" for slot in slots)
        raise ValueError(f"{label(reactor)}: {written}; CIM's SeriesCompensator has one impedance for every phase")
    return values.pop(), units.pop()


def map_series_reactors(model: GlmModel, roots: dict[str, str], buses, feeder: str) -> Document:
    """Every ``series_reactor`` as one document: the compensators, their Terminals' phases, their limit sets."""
    reactors = model.list_by_class(NATIVE_CLASS)
    by_unit: dict[str, list[Row]] = {}
    terminals: list[Row] = []
    limits = Limits()
    for reactor in reactors:
        letters = _phases(reactor)
        z, unit = _impedance(model, reactor, letters)
        node1, node2, bus = ends(reactor, roots, buses)
        compensator = mrid(PREFIX, reactor.name)
        by_unit.setdefault(unit, []).append(Row(
            [compensator, str(reactor.name), node1, node2, cell(z.real), cell(z.imag), cell(z.real), cell(z.imag),
             bus.base_voltage], comment=untranscribed_values(FIELDS, reactor) or None))
        if phases_cell(letters) is not None:
            code = phase_code(parse_phases(letters))
            terminals += [Row([f"{compensator}_T1", code]), Row([f"{compensator}_T2", code])]
        limits.add(compensator, link_ratings(reactor))
    statements = [
        Table(_SERIES, [Column("mRID"), Column("name"), Column("node1"), Column("node2"),
                        *(Column(attribute, unit) for attribute in ("r", "x", "r0", "x0")), Column("BaseVoltage"),
                        Column("EquipmentContainer", default=feeder)], rows,
              comment="r0 = r, x0 = x: GridLAB-D's reactor has no coupling between phases")
        for unit, rows in by_unit.items()]
    if terminals:
        statements.append(Table("Terminal", [Column("mRID"), Column("phases")], terminals, update=True,
                                comment="SeriesCompensator has no per-phase class: a reactor on fewer than three "
                                        "phases gives its Terminals their phases here"))
    return Document(name=NATIVE_CLASS.class_name, statements=[*statements, *limits.tables()], profile=CIM_PROFILE,
                    comment=provenance(NATIVE_CLASS.class_name, _SERIES, len(reactors), ANCHOR) if reactors else None)
