"""OpenDSS ``LineCode`` -> ``linecode.cimtbl``.

A matrix code (``rmatrix``/``xmatrix``/``cmatrix``) becomes a ``PerLengthPhaseImpedance``
with one ``PhaseImpedanceData`` row per lower-triangle element; ``row``/``column`` are
conductor indices, not phases, so a line's phase order picks the row. A sequence code
(``r1``/``x1``/``r0``/``x0``/``C1``/``C0``/``B1``/``B0``) becomes a ``PerLengthSequenceImpedance``.
Values are written as the reader holds them, per the code's own ``units`` (plan I2).

A LineCode is a template its lines share by name: ``isTemplate=true``, and a ``WireConfiguration``
``<template>_wc`` with that ``PerLengthImpedance`` and no ``WireSpacing``, which the lines reference (DSS-14).
The Line mapper writes a line's own inline values through the same rules with ``isTemplate=false``.

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md#linecode``.
"""

from __future__ import annotations

import dataclasses
import statistics
from typing import NamedTuple

from cimtables.document import Column, Document, Row, Table

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, copied_columns, lookup, mrid, untranscribed_values
from cimhub_core.derived.capacitance import b_from_c
from cimhub_core.derived.sequence import balanced_matrix, phase_matrix
from cimhub_opendss.dss_reader import dss_defaults
from cimhub_opendss.schema import opendss_schema as schema

NATIVE_CLASS = schema.Linecode
PREFIX = "lc_"

_RATING = "catalog ratings have no home on PerLengthImpedance; instance limits or untranscribed (plan D9)"
_RELIABILITY = "reliability data; no home in the network profile parts"
_CARSON = ("Carson earth return per length; home PerLengthImpedance.rg/xg (ohm/<units>), "
           "not mapped until a deck sets it (none of the test decks do)")
_KRON = "input of the matrix calculation; no CIM home"
_SEQ = "PerLengthSequenceImpedance"
_PHASE = "PerLengthPhaseImpedance"
_CONFIGURATION = "WireConfiguration"

FIELDS = {
    "name": Field("copied", ((_PHASE, "name", None), (_SEQ, "name", None), (_CONFIGURATION, "name", None)),
                  "mRID = lc_ + name, lowercased; its WireConfiguration's lc_<name>_wc (DSS-14)"),
    "nphases": Field("copied", ((_PHASE, "conductorCount", None),),
                     "the matrix order of rmatrix/xmatrix/cmatrix; a 1- or 2-phase sequence code becomes a "
                     "phase matrix as the engine builds the line (phase_matrix): 1-phase z = Z1, 2-phase "
                     "Zs = (2 Z1 + Z0)/3 and Zm = (Z0 - Z1)/3 (DSS-4)"),
    "r1": Field("copied", ((_SEQ, "r", "ohm/{length}"),)),
    "x1": Field("copied", ((_SEQ, "x", "ohm/{length}"),)),
    "r0": Field("copied", ((_SEQ, "r0", "ohm/{length}"),)),
    "x0": Field("copied", ((_SEQ, "x0", "ohm/{length}"),)),
    "C1": Field("derived", note="PerLengthSequenceImpedance bch = 2 pi baseFreq C1 (b_from_c): nF -> nS"),
    "C0": Field("derived", note="PerLengthSequenceImpedance b0ch = 2 pi baseFreq C0 (b_from_c): nF -> nS"),
    "units": Field("mapped", note="the length unit of every per-length header via LENGTH_UNIT; unset: the unit "
                                  "of the lines that use the code, else the deck's magnitude gate (DSS-3)"),
    "rmatrix": Field("structural", note="PhaseImpedanceData r, one row per lower-triangle element"),
    "xmatrix": Field("structural", note="PhaseImpedanceData x, one row per lower-triangle element"),
    "cmatrix": Field("derived", note="PhaseImpedanceData b = 2 pi baseFreq C (b_from_c): nF -> nS"),
    "baseFreq": Field("copied", ((_PHASE, "calculatedFrequency", "Hz"), (_SEQ, "calculatedFrequency", "Hz")),
                      "also the frequency of the derived b; unset with a nonzero C: the deck's base frequency, "
                      "defaulted (DSS-3b)"),
    "normamps": Field("untranscribed", note=_RATING),
    "emergamps": Field("untranscribed", note=_RATING),
    "faultrate": Field("untranscribed", note=_RELIABILITY),
    "pctperm": Field("untranscribed", note=_RELIABILITY),
    "repair": Field("untranscribed", note=_RELIABILITY),
    "Kron": Field("untranscribed", note=_KRON),
    "Rg": Field("untranscribed", note=_CARSON),
    "Xg": Field("untranscribed", note=_CARSON),
    "rho": Field("untranscribed", note="earth resistivity; home EarthResistivity.rho, an object of its own, "
                                       "not mapped until a deck sets it"),
    "neutral": Field("untranscribed", note=_KRON),
    "B1": Field("copied", ((_SEQ, "bch", "uS/{length}"),), "the alternative to C1"),
    "B0": Field("copied", ((_SEQ, "b0ch", "uS/{length}"),), "the alternative to C0"),
    "Seasons": Field("untranscribed", note=_RATING),
    "Ratings": Field("untranscribed", note=_RATING),
    "LineType": Field("untranscribed", note="no home in the network profile parts"),
    "like": Field("untranscribed", note="the reader resolves like= before mapping"),
}

#: The slots that make a sequence code; a code sets these or a matrix, never both.
SEQUENCE_SLOTS = ("r1", "x1", "r0", "x0", "C1", "C0", "B1", "B0")
#: (capacitance slot, susceptance slot, PerLengthSequenceImpedance column): DSS takes C or B for each.
_SHUNT = (("C1", "B1", "bch"), ("C0", "B0", "b0ch"))

#: DSS ``units`` code -> the length unit written in the headers. ``none`` has no length, so it raises.
LENGTH_UNIT = {"mi": "mi", "kft": "kft", "km": "km", "m": "m", "ft": "ft", "in": "in", "cm": "cm", "mm": "mm"}

_PROVENANCE = """OpenDSS LineCode -> PerLengthPhaseImpedance + PhaseImpedanceData, PerLengthSequenceImpedance (templates),
each with the WireConfiguration its lines reference (DSS-14).
Source table: LineCode (records: {count})
Mapping: cimhub_opendss/docs/CIMTBL_MAPPING.md#linecode"""


def lower_triangle(values: list[float], order: int, *, name: str, slot: str) -> dict[tuple[int, int], float]:
    """``{(row, column): value}`` for row >= column, 1-based.

    DSS writes a matrix as its lower triangle row by row (``11 | 21 22 | ...``) or in full.
    """
    triangle = order * (order + 1) // 2
    if len(values) == triangle:
        cells = iter(values)
        return {(row, column): next(cells) for row in range(1, order + 1) for column in range(1, row + 1)}
    if len(values) == order * order:
        return {(row, column): values[(row - 1) * order + column - 1]
                for row in range(1, order + 1) for column in range(1, row + 1)}
    raise ValueError(f"LineCode {name}: {slot} has {len(values)} values; nphases={order} needs "
                     f"{triangle} (lower triangle) or {order * order} (full)")


def susceptance(c: float, frequency: float | None, *, name: str, slot: str) -> float:
    """``b_from_c`` for one capacitance. C = 0 gives b = 0 with or without a ``baseFreq``."""
    if c == 0.0:
        return 0.0
    if frequency is None:
        raise ValueError(f"LineCode {name}: {slot} needs baseFreq for b")
    return b_from_c(c, frequency)


def is_sequence(code) -> bool:
    """True for a sequence code, False for a matrix code; a code with both or neither raises."""
    matrix = bool(code.rmatrix or code.xmatrix or code.cmatrix)
    sequence = any(getattr(code, slot) is not None for slot in SEQUENCE_SLOTS)
    if matrix and sequence:
        raise ValueError(f"LineCode {code.name}: sets both matrix and sequence values; "
                         "DSS keeps whichever was set last, which the reader does not record")
    if not matrix and not sequence:
        raise ValueError(f"LineCode {code.name}: sets no impedance; DSS would apply its defaults")
    return sequence


#: The magnitude gate for codes with no units on code or line (DSS-3): median positive r per unit -> length unit.
#: Real conductors run about 0.01 to 3.5 ohm/km, so the per-m/ft and per-km/kft/mile bands do not overlap.
UNITS_GATE = ((0.006, 10.0, "km"), (1e-5, 0.006, "m"))


class Template(NamedTuple):
    """One impedance template a code becomes: its mRID, length unit and how the unit was found (``None``: the
    code's own ``units``). ``capacitance_unit`` is the length unit of C1/C0/cmatrix when it is not ``unit`` (a
    line's engine-default C is per kft, ``line.inline_code``)."""
    mrid: str
    unit: str
    note: str | None
    capacitance_unit: str | None = None


def _units_text(value) -> str | None:
    """A ``units`` value as lowercase text; unset and ``none`` are ``None``."""
    text = cell(value)
    return None if text is None or text.lower() == "none" else text.lower()


def _nphases(code) -> int:
    """``code.nphases`` with the DSS default 3."""
    return 3 if code.nphases is None else int(code.nphases)


def _resistances(code) -> list[float]:
    """The positive per-unit resistances the magnitude gate looks at: r1, or the rmatrix diagonal."""
    if code.rmatrix:
        diagonal = lower_triangle(code.rmatrix, _nphases(code), name=code.name, slot="rmatrix")
        values = [value for (row, column), value in diagonal.items() if row == column]
    else:
        values = [code.r1] if code.r1 is not None else []
    return [float(value) for value in values if float(value) > 0]


def gated_unit(codes) -> tuple[str, float]:
    """``(unit, median r)`` for codes with no units on code or line: the median positive r per unit through
    ``UNITS_GATE``; a median in no band raises."""
    values = [value for code in codes for value in _resistances(code)]
    if not values:
        raise ValueError(f"LineCodes {', '.join(str(code.name) for code in codes)}: no units and no positive r to "
                         "infer them from; pass length_unit=")
    median = statistics.median(values)
    for low, high, unit in UNITS_GATE:
        if low <= median < high:
            return unit, median
    raise ValueError(f"LineCodes with no units: median r {median:g} per unit fits no length unit "
                     f"({UNITS_GATE}); pass length_unit=")


def templates(native, length_unit: str | None = None) -> dict[str, list[Template]]:
    """``{lowered code name: [Template, ...]}`` (DSS-3).

    A code with ``units`` is one template in them. A unitless code takes the units of the lines that use it, as
    DSS reads it per unit of the line's length; lines in several units give one template per unit,
    ``lc_<name>_<unit>``. A unitless code whose lines give none either (or that no line uses) takes
    ``length_unit``, else the deck-level magnitude gate. A code used by lines with and without units raises.
    """
    codes = native.list_by_class(NATIVE_CLASS)
    line_units: dict[str, set] = {}
    for line in native.list_by_class(schema.Line):
        if line.linecode and not line.Switch:
            line_units.setdefault(str(line.linecode).lower(), set()).add(_units_text(line.units))
    result: dict[str, list[Template]] = {}
    gated = []
    for code in codes:
        key = str(code.name).lower()
        lc = mrid(PREFIX, code.name, lowercase=True)
        own = _units_text(code.units)
        if own is not None:
            result[key] = [Template(lc, lookup(LENGTH_UNIT, own, slot="units", record_id=code.name), None)]
            continue
        used = line_units.get(key, set())
        if None in used and len(used) > 1:
            raise ValueError(f"LineCode {code.name}: no units, and its lines give units on some lines only "
                             f"({', '.join(sorted(str(unit) for unit in used))})")
        given = sorted(unit for unit in used if unit is not None)
        if given:
            note = "units from its lines: {unit} (no units on the code; DSS reads it per unit of line length)"
            result[key] = [Template(lc if len(given) == 1 else f"{lc}_{unit}",
                                    lookup(LENGTH_UNIT, unit, slot="Line units", record_id=code.name),
                                    note.format(unit=unit)) for unit in given]
        else:
            gated.append(code)
    result.update(gated_templates(gated, length_unit, lambda code: mrid(PREFIX, code.name, lowercase=True)))
    return result


def gated_templates(codes, length_unit: str | None, mrid_of) -> dict[str, list[Template]]:
    """``{lowered name: [Template]}`` for codes with no units on code or line: ``length_unit`` if given, else
    the magnitude gate over these codes (DSS-3). ``mrid_of(code)`` names each template."""
    if not codes:
        return {}
    if length_unit is not None:
        unit = lookup(LENGTH_UNIT, str(length_unit).lower(), slot="length_unit", record_id="the importer")
        note = f"units given: {unit} (length_unit=; no units on code or line)"
    else:
        unit, median = gated_unit(codes)
        count = f"{len(codes)} code" + ("s" if len(codes) > 1 else "")
        note = f"units inferred: {unit} (median r {median:.3g} per unit over {count}; no units on code or line)"
    return {str(code.name).lower(): [Template(mrid_of(code), unit, note)] for code in codes}


def _has_capacitance(code) -> bool:
    values = list(code.cmatrix or []) + [code.C1, code.C0]
    return any(value is not None and value != 0 for value in values)


def with_default_capacitance(code):
    """``(code, comment)``: a matrix code without ``cmatrix`` keeps the engine's default C matrix, self
    (2 C1 + C0)/3 and mutual (C0 - C1)/3 from the default C1, C0 per unit length (balanced_matrix)."""
    if code.cmatrix or not code.rmatrix:
        return code, None
    defaults = dss_defaults(NATIVE_CLASS)
    c = balanced_matrix(defaults["C1"], defaults["C0"], _nphases(code))
    return dataclasses.replace(code, cmatrix=list(c.values())), \
        f"defaulted: cmatrix from C1={cell(defaults['C1'])}, C0={cell(defaults['C0'])} (balanced_matrix)"


def with_frequency(code, base_frequency: float):
    """``(code, comment)``: a code with a nonzero C and no ``baseFreq`` takes the deck's base frequency (DSS-3b)."""
    if code.baseFreq is not None or not _has_capacitance(code):
        return code, None
    return dataclasses.replace(code, baseFreq=base_frequency), f"defaulted: baseFreq={cell(base_frequency)}"


def _comment(*parts) -> str | None:
    return "\n".join(part for part in parts if part) or None


def _phase_rows(code, template: Template, matrices, note: str | None, is_template: bool) -> tuple[Row, list[Row]]:
    """The ``PerLengthPhaseImpedance`` row and its ``PhaseImpedanceData`` rows; ``matrices`` is ``(r, x, c)``,
    each ``{(row, column): value}`` (``c`` may be empty)."""
    lc = template.mrid
    impedance = Row([lc, *(cell(getattr(code, slot)) for slot, _ in copied_columns(FIELDS, _PHASE)),
                     cell(is_template)], comment=_comment(note, untranscribed_values(FIELDS, code)))
    r, x, c = matrices
    data = []
    for row, column in r:
        b = susceptance(c[(row, column)], code.baseFreq, name=code.name, slot="cmatrix") if c else None
        data.append(Row([f"{lc}_{row}{column}", lc, str(row), str(column),
                         cell(r[(row, column)]), cell(x[(row, column)]), cell(b)]))
    return impedance, data


def _matrices(code):
    """``(r, x, c)`` of a matrix code."""
    if not code.rmatrix or not code.xmatrix:
        raise ValueError(f"LineCode {code.name}: a matrix code needs both rmatrix and xmatrix")
    nphases = _nphases(code)
    r = lower_triangle(code.rmatrix, nphases, name=code.name, slot="rmatrix")
    x = lower_triangle(code.xmatrix, nphases, name=code.name, slot="xmatrix")
    c = lower_triangle(code.cmatrix, nphases, name=code.name, slot="cmatrix") if code.cmatrix else {}
    return r, x, c


def _short_sequence_matrices(code):
    """``(r, x, c, note)`` of a 1- or 2-phase sequence code, built as the engine builds its line (DSS-4)."""
    nphases = _nphases(code)
    if code.B1 is not None or code.B0 is not None:
        raise ValueError(f"LineCode {code.name}: B1/B0 on a {nphases}-phase sequence code is not mapped yet "
                         "(no deck in the sweep sets it)")
    if None in (code.r1, code.x1):
        raise ValueError(f"LineCode {code.name}: a {nphases}-phase sequence code needs r1 and x1")
    if nphases == 2 and code.C1 is None and code.C0 is not None:
        raise ValueError(f"LineCode {code.name}: C0={code.C0} without C1 on a 2-phase sequence code")
    r = phase_matrix(code.r1, code.r0, nphases)
    x = phase_matrix(code.x1, code.x0, nphases)
    c = phase_matrix(code.C1, code.C0, nphases) if code.C1 is not None else {}
    if nphases == 1:
        unused = [f"{slot}={cell(getattr(code, slot))}" for slot in ("r0", "x0", "C0") if getattr(code, slot) is not None]
        note = "derived from a 1-phase sequence code: z = Z1 (phase_matrix)" + \
            (f"; a 1-phase line does not use {', '.join(unused)}" if unused else "")
    else:
        note = "derived from a 2-phase sequence code: Zs = (2 Z1 + Z0)/3, Zm = (Z0 - Z1)/3 (phase_matrix)"
    return r, x, c, note


def _sequence_row(code, template: Template, note: str | None, is_template: bool) -> tuple[tuple[Column, ...], Row]:
    """The ``PerLengthSequenceImpedance`` columns and row of a 3-phase sequence code.

    ``bch``/``b0ch`` are copied from ``B1``/``B0`` (uS) or derived from ``C1``/``C0`` (nS),
    so the columns, and with them the table, depend on the code.
    """
    if _nphases(code) != 3:
        raise ValueError(f"LineCode {code.name}: nphases={code.nphases}; a sequence code has 1, 2 or 3 phases")
    unit = template.unit
    c_unit = template.capacitance_unit or unit
    cells = {column.name: (column, cell(getattr(code, slot)))
             for slot, column in copied_columns(FIELDS, _SEQ, length=unit)}
    for c_slot, b_slot, name in _SHUNT:
        c = getattr(code, c_slot)
        if c is None:
            continue
        if getattr(code, b_slot) is not None:
            raise ValueError(f"LineCode {code.name}: sets both {c_slot} and {b_slot}; "
                             "DSS keeps whichever was set last, which the reader does not record")
        cells[name] = (Column(name, f"nS/{c_unit}"),
                       cell(susceptance(c, code.baseFreq, name=code.name, slot=c_slot)))
    cells["isTemplate"] = (Column("isTemplate"), cell(is_template))
    columns = tuple(column for column, _ in cells.values())
    row = Row([template.mrid, *(text for _, text in cells.values())],
              comment=_comment(note, untranscribed_values(FIELDS, code)))
    return columns, row


def impedance_statements(entries, base_frequency: float, *, is_template: bool) -> list:
    """The impedance tables of ``(code, [Template, ...])`` pairs: a phase table, its data per length unit, and
    the sequence tables per header. LineCodes are templates; the Line mapper passes its inline values the same way
    with ``is_template=False`` (DSS-8, DSS-14).
    """
    impedances: list[Row] = []
    data_by_unit: dict[tuple[str, str], list[Row]] = {}  # (r and x length unit, b length unit) -> rows
    sequences_by_columns: dict[tuple[Column, ...], list[Row]] = {}
    derived_matrix = False
    for original, code_templates in entries:
        sequence = is_sequence(original)
        nphases_note = "defaulted: nphases=3" if original.nphases is None else None
        code = dataclasses.replace(original, nphases=_nphases(original)) if original.nphases is None else original
        code, capacitance = with_default_capacitance(code)
        code, defaulted = with_frequency(code, base_frequency)
        for template in code_templates:
            note = _comment(template.note, nphases_note, capacitance, defaulted)
            if sequence and code.nphases == 3:
                columns, row = _sequence_row(code, template, note, is_template)
                sequences_by_columns.setdefault(columns, []).append(row)
                continue
            if sequence:
                r, x, c, derivation = _short_sequence_matrices(code)
                matrices, note, derived_matrix = (r, x, c), _comment(derivation, note), True
            else:
                matrices = _matrices(code)
            impedance, data = _phase_rows(code, template, matrices, note, is_template)
            impedances.append(impedance)
            data_by_unit.setdefault((template.unit, template.capacitance_unit or template.unit), []).extend(data)

    statements = []
    if impedances:
        statements.append(Table(_PHASE, [Column("mRID"), *(column for _, column in copied_columns(FIELDS, _PHASE)),
                                         Column("isTemplate")], impedances))
    for (unit, c_unit), rows in data_by_unit.items():
        comment = (f"units={unit}. row/column are conductor indices of the lower triangle.\n"
                   "derived: b = 2 pi baseFreq C (b_from_c), from cmatrix (nF) -> nS")
        if derived_matrix:
            comment += "; 1- and 2-phase sequence codes: r, x, C by phase_matrix (DSS-4)"
        statements.append(Table(
            "PhaseImpedanceData",
            [Column("identifier"), Column("PhaseImpedance"), Column("row"), Column("column"),
             Column("r", f"ohm/{unit}"), Column("x", f"ohm/{unit}"), Column("b", f"nS/{c_unit}")],
            rows, comment=comment,
        ))
    for columns, rows in sequences_by_columns.items():
        derived = any(column.unit and column.unit.startswith("nS/") for column in columns)
        statements.append(Table(_SEQ, [Column("mRID"), *columns], rows,
                                comment="derived: bch/b0ch = 2 pi baseFreq C1/C0 (b_from_c), from C (nF) -> nS"
                                if derived else None))
    return statements


def map_linecode(native, *, base_frequency: float, length_unit: str | None = None) -> Document:
    """Every ``LineCode`` of a DSS model as one ``linecode`` document.

    ``base_frequency`` (Hz) is the deck's, for a code with C and no ``baseFreq``; ``length_unit`` overrides the
    magnitude gate for codes with no units on code or line.
    """
    codes = native.list_by_class(NATIVE_CLASS)
    if not codes:
        return Document(name="linecode", statements=[], profile=CIM_PROFILE)
    templates_of = templates(native, length_unit)
    entries = [(code, templates_of[str(code.name).lower()]) for code in codes]
    statements = impedance_statements(entries, base_frequency, is_template=True)
    configurations = [Row([f"{template.mrid}_wc", str(code.name), template.mrid])
                      for code, code_templates in entries for template in code_templates]
    statements.append(Table(_CONFIGURATION, [Column("mRID"), Column("name"), Column("PerLengthImpedance")],
                            configurations, comment="the LineCodes' lines share each through its WireConfiguration, "
                                                    "which has no WireSpacing (DSS-14)"))
    return Document(name="linecode", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(codes)))
