"""OpenDSS ``LineCode`` -> ``linecode.cimtbl``.

A matrix code (``rmatrix``/``xmatrix``/``cmatrix``) becomes a ``PerLengthPhaseImpedance``
with one ``PhaseImpedanceData`` row per lower-triangle element; ``row``/``column`` are
conductor indices, not phases, so a line's phase order picks the row. A sequence code
(``r1``/``x1``/``r0``/``x0``/``C1``/``C0``/``B1``/``B0``) becomes a ``PerLengthSequenceImpedance``.
Values are written as the reader holds them, per the code's own ``units`` (plan I2).

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md#linecode``.
"""

from __future__ import annotations

import math

from cimtables.document import Column, Document, Row, Table

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, copied_columns, lookup, mrid, untranscribed_values
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

FIELDS = {
    "name": Field("copied", ((_PHASE, "name", None), (_SEQ, "name", None)), "mRID = lc_ + name, lowercased"),
    "nphases": Field("copied", ((_PHASE, "conductorCount", None),),
                     "the matrix order of rmatrix/xmatrix/cmatrix; a sequence code must be 3-phase "
                     "(a 1-phase DSS line uses Z1 as its self impedance, a 2-phase one Zs = (2 Z1 + Z0)/3 and "
                     "Zm = (Z0 - Z1)/3; neither is the CIM sequence convention)"),
    "r1": Field("copied", ((_SEQ, "r", "ohm/{length}"),)),
    "x1": Field("copied", ((_SEQ, "x", "ohm/{length}"),)),
    "r0": Field("copied", ((_SEQ, "r0", "ohm/{length}"),)),
    "x0": Field("copied", ((_SEQ, "x0", "ohm/{length}"),)),
    "C1": Field("derived", note="PerLengthSequenceImpedance bch = 2 pi baseFreq C1 (b_from_c): nF -> nS"),
    "C0": Field("derived", note="PerLengthSequenceImpedance b0ch = 2 pi baseFreq C0 (b_from_c): nF -> nS"),
    "units": Field("mapped", note="the length unit of every per-length header via LENGTH_UNIT"),
    "rmatrix": Field("structural", note="PhaseImpedanceData r, one row per lower-triangle element"),
    "xmatrix": Field("structural", note="PhaseImpedanceData x, one row per lower-triangle element"),
    "cmatrix": Field("derived", note="PhaseImpedanceData b = 2 pi baseFreq C (b_from_c): nF -> nS"),
    "baseFreq": Field("copied", ((_PHASE, "calculatedFrequency", "Hz"), (_SEQ, "calculatedFrequency", "Hz")),
                      "also the frequency of the derived b"),
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

_PROVENANCE = """OpenDSS LineCode -> PerLengthPhaseImpedance + PhaseImpedanceData, PerLengthSequenceImpedance (catalog).
Source table: LineCode (records: {count})
Mapping: cimhub_opendss/docs/CIMTBL_MAPPING.md#linecode"""


def b_from_c(c: float, frequency: float) -> float:
    """Susceptance from capacitance: b = 2 pi f C. C in nF and f in Hz give b in nS."""
    return 2 * math.pi * frequency * c


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


def susceptance(c, frequency, *, name: str, slot: str) -> float:
    """``b_from_c`` for one capacitance. C = 0 gives b = 0 with or without a ``baseFreq``."""
    c = float(c)
    if c == 0.0:
        return 0.0
    if frequency is None:
        raise ValueError(f"LineCode {name}: {slot} needs baseFreq for b")
    return b_from_c(c, float(frequency))


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


def _phase_rows(code) -> tuple[Row, str, list[Row]]:
    """The ``PerLengthPhaseImpedance`` row, the length unit and the ``PhaseImpedanceData`` rows of a matrix code."""
    lc = mrid(PREFIX, code.name, lowercase=True)
    impedance = Row([lc, *(cell(getattr(code, slot)) for slot, _ in copied_columns(FIELDS, _PHASE))],
                    comment=untranscribed_values(FIELDS, code))
    unit = lookup(LENGTH_UNIT, code.units, slot="units", record_id=code.name)
    r = lower_triangle(code.rmatrix, code.nphases, name=code.name, slot="rmatrix")
    x = lower_triangle(code.xmatrix, code.nphases, name=code.name, slot="xmatrix")
    c = lower_triangle(code.cmatrix, code.nphases, name=code.name, slot="cmatrix") if code.cmatrix else {}
    data = []
    for row, column in r:
        b = susceptance(c[(row, column)], code.baseFreq, name=code.name, slot="cmatrix") if c else None
        data.append(Row([f"{lc}_{row}{column}", lc, str(row), str(column),
                         cell(r[(row, column)]), cell(x[(row, column)]), cell(b)]))
    return impedance, unit, data


def _sequence_row(code) -> tuple[tuple[Column, ...], Row]:
    """The ``PerLengthSequenceImpedance`` columns and row of a sequence code.

    ``bch``/``b0ch`` are copied from ``B1``/``B0`` (uS) or derived from ``C1``/``C0`` (nS),
    so the columns, and with them the table, depend on the code.
    """
    if code.nphases != 3:
        raise ValueError(f"LineCode {code.name}: nphases={code.nphases} sequence codes are not mapped yet; "
                         "a 1-phase DSS line uses Z1 as its self impedance, a 2-phase one (2 Z1 + Z0)/3, "
                         "which is not the CIM convention")
    unit = lookup(LENGTH_UNIT, code.units, slot="units", record_id=code.name)
    cells = {column.name: (column, cell(getattr(code, slot)))
             for slot, column in copied_columns(FIELDS, _SEQ, length=unit)}
    for c_slot, b_slot, name in _SHUNT:
        c = getattr(code, c_slot)
        if c is None:
            continue
        if getattr(code, b_slot) is not None:
            raise ValueError(f"LineCode {code.name}: sets both {c_slot} and {b_slot}; "
                             "DSS keeps whichever was set last, which the reader does not record")
        cells[name] = (Column(name, f"nS/{unit}"),
                       cell(susceptance(c, code.baseFreq, name=code.name, slot=c_slot)))
    columns = tuple(column for column, _ in cells.values())
    row = Row([mrid(PREFIX, code.name, lowercase=True), *(text for _, text in cells.values())],
              comment=untranscribed_values(FIELDS, code))
    return columns, row


def map_linecode(native) -> Document:
    """Every ``LineCode`` of a DSS model as one ``linecode`` document."""
    codes = native.list_by_class(NATIVE_CLASS)
    if not codes:
        return Document(name="linecode", statements=[], profile=CIM_PROFILE)

    impedances: list[Row] = []
    data_by_unit: dict[str, list[Row]] = {}
    sequences_by_columns: dict[tuple[Column, ...], list[Row]] = {}
    for code in codes:
        if is_sequence(code):
            columns, row = _sequence_row(code)
            sequences_by_columns.setdefault(columns, []).append(row)
        else:
            impedance, unit, data = _phase_rows(code)
            impedances.append(impedance)
            data_by_unit.setdefault(unit, []).extend(data)

    statements = []
    if impedances:
        statements.append(Table(_PHASE, [Column("mRID"), *(column for _, column in copied_columns(FIELDS, _PHASE))],
                                impedances))
    for unit, rows in data_by_unit.items():
        statements.append(Table(
            "PhaseImpedanceData",
            [Column("identifier"), Column("PhaseImpedance"), Column("row"), Column("column"),
             Column("r", f"ohm/{unit}"), Column("x", f"ohm/{unit}"), Column("b", f"nS/{unit}")],
            rows,
            comment=f"units={unit}. row/column are conductor indices of the lower triangle.\n"
                    "derived: b = 2 pi baseFreq C (b_from_c), from cmatrix (nF) -> nS",
        ))
    for columns, rows in sequences_by_columns.items():
        derived = any(column.unit and column.unit.startswith("nS/") for column in columns)
        statements.append(Table(_SEQ, [Column("mRID"), *columns], rows,
                                comment="derived: bch/b0ch = 2 pi baseFreq C1/C0 (b_from_c), from C (nF) -> nS"
                                if derived else None))
    return Document(name="linecode", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(codes)))
