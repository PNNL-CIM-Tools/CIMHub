"""A line's impedance: whole-line or per-length sequence values, and the per-length phase matrix (skill
`export-getters`).

Bus-branch formats (RAW, MATPOWER) take only sequence values, so the sequence getters may reduce what CIM holds:

1. ``LUMPED``: ``ACLineSegment.r/x/bch/gch`` (and ``r0/x0/b0ch/g0ch``).
2. ``PER_LENGTH_SEQ``: ``PerLengthSequenceImpedance`` (times ``length`` for whole-line values).
3. ``MATRIX_REDUCED``: ``PerLengthPhaseImpedance`` reduced to sequence values, assuming a transposed line and,
   where the matrix has neutral conductors, a neutral grounded at both ends (Kron reduction).
4. ``GEOMETRY``: ``WireConfiguration`` through line constants (not built yet).

``derive=`` caps the step. When the lumped values and a per-length source are both within the cap, they must agree
and the lumped values win. Geometry-capable formats (GLM, DSS) export native geometry and never call the sequence
getters on a line that has a ``WireConfiguration`` (skill ``conductor-geometry``); they take the phase matrix only
where CIM has no geometry.

Every input is read with ``get_qty`` directly in the caller's unit. The reductions (means, differences, Kron) scale
linearly, so no value is converted after it is read.
"""

from __future__ import annotations

import math
from enum import Enum, IntEnum
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty
from cimtables.impedance import z_base

from cimhub_core.derived.kron import kron_reduce
from cimhub_core.derived.sequence import balanced_matrix, phase_matrix


class ImpedanceSource(IntEnum):
    """Where a SequenceImpedance came from; as ``derive=``, the furthest step the getter may take."""

    LUMPED = 1
    PER_LENGTH_SEQ = 2
    MATRIX_REDUCED = 3
    GEOMETRY = 4


class SequenceImpedance(NamedTuple):
    """Series impedance and shunt admittance, whole-line or per length by getter. ``None`` is unset in CIM (zero
    sequence, often b and g)."""

    r: float
    x: float
    b: float | None
    g: float | None
    r0: float | None
    x0: float | None
    b0: float | None
    g0: float | None
    source: ImpedanceSource


class MatrixSource(Enum):
    """Where a PhaseMatrix came from."""

    PHASE_CODE = "PerLengthPhaseImpedance"
    SEQUENCE_EXPANDED = "PerLengthSequenceImpedance expanded, assuming a transposed line"


class PhaseMatrix(NamedTuple):
    """Per-length phase matrices as lower triangles ``{(row, column): value}``, 1-based in conductor order
    (``phases``, from ``ACLineSegmentPhase.sequenceNumber``). ``b``/``g`` are ``None`` when unset."""

    phases: tuple[cim.SinglePhaseKind, ...]
    r: dict[tuple[int, int], float]
    x: dict[tuple[int, int], float]
    b: dict[tuple[int, int], float] | None
    g: dict[tuple[int, int], float] | None
    source: MatrixSource


# the admittance unit that goes with each whole-line impedance unit a caller may ask for
ADMITTANCE_UNIT = {"ohm": "S", "pu": "pu"}
IMPEDANCE_FIELDS = ("r", "x", "r0", "x0")
PHASE_CONDUCTORS = (cim.SinglePhaseKind.A, cim.SinglePhaseKind.B, cim.SinglePhaseKind.C)
# lumped and per-length values computed from the same source differ only by rounding (open: skill reference §3)
DISAGREEMENT_REL_TOL = 1e-6


def get_line_sequence_impedance(
    line: cim.ACLineSegment,
    unit: str = "ohm",
    *,
    base_power=None,
    derive: ImpedanceSource = ImpedanceSource.LUMPED,
) -> SequenceImpedance:
    """The whole line's sequence values in ``unit`` ('ohm' with siemens, or 'pu' with pu admittance). 'pu' is on
    the line's BaseVoltage and ``base_power`` (``network.base_power``), through ``cimtables.impedance.z_base``.
    Raises ValueError when nothing within ``derive`` gives r and x, or when two sources disagree."""
    if unit not in ADMITTANCE_UNIT:
        raise ValueError(f"unit must be one of {sorted(ADMITTANCE_UNIT)}, not {unit!r}")

    lumped = _lumped(line, unit, base_power)
    per_length = None
    if derive > ImpedanceSource.LUMPED:
        per_metre = _per_length_sequence(line, "ohm/m", "S/m", derive)
        if per_metre is not None:
            per_length = _whole_line(line, per_metre, unit, base_power)

    if lumped is not None and per_length is not None:
        _check_agreement(line, lumped, per_length)
        return lumped
    if lumped is not None:
        return lumped
    if per_length is not None:
        return per_length
    raise _no_source(line, derive)


def get_line_sequence_impedance_per_length(
    line: cim.ACLineSegment,
    impedance_unit: str = "ohm/m",
    admittance_unit: str = "S/m",
    *,
    derive: ImpedanceSource = ImpedanceSource.PER_LENGTH_SEQ,
) -> SequenceImpedance:
    """The line's per-length sequence values, from its PerLengthImpedance (steps 2-3; lumped values are whole-line
    and never read). Raises ValueError when nothing within ``derive`` gives r and x."""
    if derive < ImpedanceSource.PER_LENGTH_SEQ:
        raise ValueError(f"per-length values start at derive=PER_LENGTH_SEQ, not {derive.name}")
    per_length = _per_length_sequence(line, impedance_unit, admittance_unit, derive)
    if per_length is None:
        raise _no_source(line, derive)
    return per_length


def get_line_phase_impedance_matrix(
    line: cim.ACLineSegment,
    impedance_unit: str = "ohm/m",
    admittance_unit: str = "S/m",
    *,
    expand_sequence: bool = False,
) -> PhaseMatrix:
    """The line's per-length phase matrix in conductor order, neutrals and s1/s2 included as stored. A
    PerLengthSequenceImpedance is expanded only with ``expand_sequence=True`` (``derived.sequence``: one phase is
    Z1 alone, more are self (2 Z1 + Z0) / 3 and mutual (Z0 - Z1) / 3). A line with geometry and no
    PerLengthImpedance raises: export the geometry instead (skill ``conductor-geometry``)."""
    code = line.PerLengthImpedance
    phases = _conductor_phases(line)
    if isinstance(code, cim.PerLengthPhaseImpedance):
        entries = _matrix_entries(line, code, len(phases))
        r = _entry_values(code, entries, "r", impedance_unit)
        x = _entry_values(code, entries, "x", impedance_unit)
        if r is None or x is None:
            raise ValueError(f"{_describe(code)}: r and x must be set")
        return PhaseMatrix(phases=phases, r=r, x=x,
                           b=_entry_values(code, entries, "b", admittance_unit),
                           g=_entry_values(code, entries, "g", admittance_unit),
                           source=MatrixSource.PHASE_CODE)
    if isinstance(code, cim.PerLengthSequenceImpedance):
        if not expand_sequence:
            raise ValueError(f"{_describe(line)}: its PerLengthSequenceImpedance becomes a phase matrix only by "
                             f"assuming a transposed line: pass expand_sequence=True")
        return _expand_sequence_code(line, code, phases, impedance_unit, admittance_unit)
    if line.WireConfiguration is not None:
        raise ValueError(f"{_describe(line)}: has a WireConfiguration and no PerLengthImpedance; export its "
                         f"geometry through the spacing getters, never a computed matrix")
    raise ValueError(f"{_describe(line)}: has no PerLengthImpedance")


def _lumped(line: cim.ACLineSegment, unit: str, base_power) -> SequenceImpedance | None:
    """Step 1, or None when the line has neither r nor x."""
    r = get_qty(line, "r", unit, system_base=base_power)
    x = get_qty(line, "x", unit, system_base=base_power)
    if r is None and x is None:
        return None
    if r is None or x is None:
        raise ValueError(f"{_describe(line)}: lumped r and x must be set together (r={r}, x={x})")
    admittance_unit = ADMITTANCE_UNIT[unit]
    return SequenceImpedance(
        r=r,
        x=x,
        b=get_qty(line, "bch", admittance_unit, system_base=base_power),
        g=get_qty(line, "gch", admittance_unit, system_base=base_power),
        r0=get_qty(line, "r0", unit, system_base=base_power),
        x0=get_qty(line, "x0", unit, system_base=base_power),
        b0=get_qty(line, "b0ch", admittance_unit, system_base=base_power),
        g0=get_qty(line, "g0ch", admittance_unit, system_base=base_power),
        source=ImpedanceSource.LUMPED,
    )


def _per_length_sequence(line: cim.ACLineSegment, impedance_unit: str, admittance_unit: str,
                         derive: ImpedanceSource) -> SequenceImpedance | None:
    """Steps 2-4 per length, or None when the line's per-length source is absent or beyond ``derive``."""
    code = line.PerLengthImpedance
    if isinstance(code, cim.PerLengthSequenceImpedance):
        source = ImpedanceSource.PER_LENGTH_SEQ
    elif isinstance(code, cim.PerLengthPhaseImpedance):
        source = ImpedanceSource.MATRIX_REDUCED
    elif code is None and line.WireConfiguration is not None:
        source = ImpedanceSource.GEOMETRY
    else:
        return None
    if source > derive:
        return None

    if source == ImpedanceSource.PER_LENGTH_SEQ:
        values = _sequence_code_values(code, impedance_unit, admittance_unit)
    elif source == ImpedanceSource.MATRIX_REDUCED:
        values = _phase_code_sequence_values(line, code, impedance_unit, admittance_unit)
    else:
        raise NotImplementedError(f"{_describe(line)}: the geometry -> impedance engine (step 4) is not built")
    return SequenceImpedance(**values, source=source)


def _whole_line(line: cim.ACLineSegment, per_metre: SequenceImpedance, unit: str, base_power) -> SequenceImpedance:
    """Per-metre values times the line's length, then in pu on z_base when asked."""
    length = get_qty(line, "length", "m")
    if length is None:
        raise ValueError(f"{_describe(line)}: a per-length impedance needs the line's length")
    base = z_base(line, base_power) if unit == "pu" else 1.0
    totals = {}
    for name, value in per_metre._asdict().items():
        if name == "source" or value is None:
            totals[name] = value
        elif name in IMPEDANCE_FIELDS:
            totals[name] = value * length / base
        else:
            totals[name] = value * length * base
    return SequenceImpedance(**totals)


def _sequence_code_values(code: cim.PerLengthSequenceImpedance, impedance_unit: str,
                          admittance_unit: str) -> dict[str, float | None]:
    """Step 2: the code's own values."""
    values = {
        "r": get_qty(code, "r", impedance_unit),
        "x": get_qty(code, "x", impedance_unit),
        "b": get_qty(code, "bch", admittance_unit),
        "g": get_qty(code, "gch", admittance_unit),
        "r0": get_qty(code, "r0", impedance_unit),
        "x0": get_qty(code, "x0", impedance_unit),
        "b0": get_qty(code, "b0ch", admittance_unit),
        "g0": get_qty(code, "g0ch", admittance_unit),
    }
    if values["r"] is None or values["x"] is None:
        raise ValueError(f"{_describe(code)}: r and x must be set")
    return values


def _phase_code_sequence_values(line: cim.ACLineSegment, code: cim.PerLengthPhaseImpedance, impedance_unit: str,
                                admittance_unit: str) -> dict[str, float | None]:
    """Step 3. Neutral (N) conductors are folded out first, as grounded at both ends: the series impedance by Kron
    reduction (``cimhub_core.derived.kron``), the shunt admittance by keeping its phase block. Then the inverse of
    ``cimhub_core.derived.sequence.phase_matrix``: self Zs and mutual Zm are the means of the diagonal and
    off-diagonal entries; positive = Zs - Zm, zero = Zs + 2 Zm. One phase conductor has positive = Z11 and no
    zero sequence. Split-phase (s1/s2) and other conductor kinds raise."""
    phases = _conductor_phases(line)
    _require_phase_conductors(line, phases)
    neutrals = [index for index, phase in enumerate(phases, start=1) if phase is cim.SinglePhaseKind.N]
    if len(neutrals) == len(phases):
        raise ValueError(f"{_describe(line)}: no phase conductor, only neutrals")

    count = len(phases)
    entries = _matrix_entries(line, code, count)
    r = _entry_values(code, entries, "r", impedance_unit)
    x = _entry_values(code, entries, "x", impedance_unit)
    if r is None or x is None:
        raise ValueError(f"{_describe(code)}: r and x must be set")
    impedance = kron_reduce({key: complex(r[key], x[key]) for key in entries}, neutrals)
    positive, zero = _sequence_values(impedance)
    values = {"r": positive.real, "x": positive.imag,
              "r0": None if zero is None else zero.real, "x0": None if zero is None else zero.imag}

    for attribute in ("b", "g"):
        admittance = _entry_values(code, entries, attribute, admittance_unit)
        if admittance is None:
            values[attribute] = values[attribute + "0"] = None
            continue
        values[attribute], values[attribute + "0"] = _sequence_values(_phase_block(admittance, count, neutrals))
    return values


def _expand_sequence_code(line: cim.ACLineSegment, code: cim.PerLengthSequenceImpedance,
                          phases: tuple[cim.SinglePhaseKind, ...], impedance_unit: str,
                          admittance_unit: str) -> PhaseMatrix:
    """A sequence code as a phase matrix on the line's conductors, by ``derived.sequence``."""
    _require_phase_conductors(line, phases)
    values = _sequence_code_values(code, impedance_unit, admittance_unit)
    count = len(phases)
    matrices = {}
    for positive_name in ("r", "x", "b", "g"):
        positive, zero = values[positive_name], values[positive_name + "0"]
        if positive is None and zero is None:
            matrices[positive_name] = None
        elif positive is None:
            raise ValueError(f"{_describe(code)}: {positive_name}0 is set without {positive_name}")
        elif count == 1:
            matrices[positive_name] = phase_matrix(positive, zero, 1)
        elif zero is None:
            raise ValueError(f"{_describe(code)}: {count} conductors need {positive_name}0 to expand {positive_name}")
        else:
            matrices[positive_name] = balanced_matrix(positive, zero, count)
    return PhaseMatrix(phases=phases, **matrices, source=MatrixSource.SEQUENCE_EXPANDED)


def _conductor_phases(line: cim.ACLineSegment) -> tuple[cim.SinglePhaseKind, ...]:
    """The line's conductors in ``sequenceNumber`` order, which is the matrix row/column order."""
    phases = tuple(phase.phase for phase in sorted(line.ACLineSegmentPhases, key=lambda phase: phase.sequenceNumber))
    if not phases:
        raise ValueError(f"{_describe(line)}: a phase matrix needs ACLineSegmentPhases for its conductor order")
    return phases


def _require_phase_conductors(line: cim.ACLineSegment, phases: tuple[cim.SinglePhaseKind, ...]) -> None:
    """Sequence values exist only for A, B, C conductors (and neutrals, which the reduction folds out)."""
    unsupported = [phase.value for phase in phases if phase not in (*PHASE_CONDUCTORS, cim.SinglePhaseKind.N)]
    if unsupported:
        raise ValueError(f"{_describe(line)}: conductors {unsupported} have no sequence values")


def _matrix_entries(line: cim.ACLineSegment, code: cim.PerLengthPhaseImpedance, count: int) -> dict:
    """``{(row, column): PhaseImpedanceData}``, lower triangle; it must cover exactly ``count`` conductors."""
    entries = {(max(data.row, data.column), min(data.row, data.column)): data for data in code.PhaseImpedanceData}
    expected = {(row, column) for row in range(1, count + 1) for column in range(1, row + 1)}
    if set(entries) != expected:
        raise ValueError(f"{_describe(code)}: entries {sorted(entries)} are not the lower triangle of the "
                         f"{count} conductors of {_describe(line)}")
    return entries


def _entry_values(code: cim.PerLengthPhaseImpedance, entries: dict, attribute: str, unit: str) -> dict | None:
    """``{(row, column): value}`` of one PhaseImpedanceData attribute, or None when no entry sets it."""
    values = {key: get_qty(data, attribute, unit) for key, data in entries.items()}
    if all(value is None for value in values.values()):
        return None
    if any(value is None for value in values.values()):
        raise ValueError(f"{_describe(code)}: {attribute} is set on some entries but not all")
    return values


def _phase_block(matrix: dict, count: int, neutrals: list[int]) -> dict:
    """The lower triangle without the neutral rows and columns, renumbered 1..k in conductor order."""
    kept = [index for index in range(1, count + 1) if index not in neutrals]
    return {(new_row, new_column): matrix[row, column]
            for new_row, row in enumerate(kept, start=1)
            for new_column, column in enumerate(kept, start=1) if new_column <= new_row}


def _sequence_values(matrix: dict) -> tuple:
    """(positive, zero) of a lower-triangle phase matrix, from its mean self and mutual entries; one conductor has
    no zero sequence (None)."""
    diagonal = [value for (row, column), value in matrix.items() if row == column]
    self_value = sum(diagonal) / len(diagonal)
    if len(diagonal) == 1:
        return self_value, None
    off_diagonal = [value for (row, column), value in matrix.items() if row != column]
    mutual = sum(off_diagonal) / len(off_diagonal)
    return self_value - mutual, self_value + 2 * mutual


def _check_agreement(line: cim.ACLineSegment, lumped: SequenceImpedance, per_length: SequenceImpedance) -> None:
    """Raise when a value set in both sources differs by more than DISAGREEMENT_REL_TOL."""
    for name in SequenceImpedance._fields[:-1]:
        lumped_value, per_length_value = getattr(lumped, name), getattr(per_length, name)
        if lumped_value is None or per_length_value is None:
            continue
        if not math.isclose(lumped_value, per_length_value, rel_tol=DISAGREEMENT_REL_TOL):
            raise ValueError(f"{_describe(line)}: lumped {name}={lumped_value} disagrees with "
                             f"{per_length.source.name} {name}={per_length_value}")


def _no_source(line: cim.ACLineSegment, derive: ImpedanceSource) -> ValueError:
    code = line.PerLengthImpedance
    return ValueError(
        f"{_describe(line)}: no sequence impedance within derive={derive.name} (lumped r/x: "
        f"{'set' if line.r is not None else 'unset'}, PerLengthImpedance: "
        f"{type(code).__name__ if code else 'none'}, WireConfiguration: {'set' if line.WireConfiguration else 'none'})"
    )


def _describe(obj) -> str:
    return f"{type(obj).__name__} {obj.mRID!r}"
