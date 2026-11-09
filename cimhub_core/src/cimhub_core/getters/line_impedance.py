"""A line's sequence impedance, through a caller-limited resolution order (skill `export-getters`).

Bus-branch formats (RAW, MATPOWER) take only sequence values, so the getter may reduce what CIM holds:

1. ``LUMPED``: ``ACLineSegment.r/x/bch/gch`` (and ``r0/x0/b0ch/g0ch``).
2. ``PER_LENGTH_SEQ``: ``PerLengthSequenceImpedance`` times ``length``.
3. ``MATRIX_REDUCED``: ``PerLengthPhaseImpedance`` reduced to sequence values, assuming a transposed line.
4. ``GEOMETRY``: ``WireConfiguration`` through line constants (not built yet).

``derive=`` caps the step; the default reads lumped values only. When the lumped values and a per-length source are
both within the cap, they must agree and the lumped values win. Geometry-capable formats (GLM, DSS) export native
geometry and never call this on a line that has a ``WireConfiguration`` (skill ``conductor-geometry``).
"""

from __future__ import annotations

import math
from enum import IntEnum
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty
from cimtables.impedance import z_base


class ImpedanceSource(IntEnum):
    """Where a SequenceImpedance came from; as ``derive=``, the furthest step the getter may take."""

    LUMPED = 1
    PER_LENGTH_SEQ = 2
    MATRIX_REDUCED = 3
    GEOMETRY = 4


class SequenceImpedance(NamedTuple):
    """Whole-line series impedance and shunt admittance. ``None`` is unset in CIM (zero sequence, often b and g)."""

    r: float
    x: float
    b: float | None
    g: float | None
    r0: float | None
    x0: float | None
    b0: float | None
    g0: float | None
    source: ImpedanceSource


# the admittance unit that goes with each impedance unit a caller may ask for
ADMITTANCE_UNIT = {"ohm": "S", "pu": "pu"}
IMPEDANCE_FIELDS = ("r", "x", "r0", "x0")
# lumped and per-length values computed from the same source differ only by rounding (open: skill reference §3)
DISAGREEMENT_REL_TOL = 1e-6


def get_line_sequence_impedance(
    line: cim.ACLineSegment,
    unit: str = "ohm",
    *,
    base_power=None,
    derive: ImpedanceSource = ImpedanceSource.LUMPED,
) -> SequenceImpedance:
    """The line's sequence values in ``unit`` ('ohm' with siemens, or 'pu' with pu admittance). 'pu' is on the
    line's BaseVoltage and ``base_power`` (``network.base_power``), through ``cimtables.impedance.z_base``.
    Raises ValueError when nothing within ``derive`` gives r and x, or when two sources disagree."""
    if unit not in ADMITTANCE_UNIT:
        raise ValueError(f"unit must be one of {sorted(ADMITTANCE_UNIT)}, not {unit!r}")

    lumped = _lumped(line, unit, base_power)
    per_length = None
    if derive > ImpedanceSource.LUMPED:
        per_length = _per_length(line, unit, base_power, derive)

    if lumped is not None and per_length is not None:
        _check_agreement(line, lumped, per_length)
        return lumped
    if lumped is not None:
        return lumped
    if per_length is not None:
        return per_length
    raise ValueError(
        f"{_describe(line)}: no sequence impedance within derive={derive.name} (lumped r/x: unset, "
        f"PerLengthImpedance: {type(line.PerLengthImpedance).__name__ if line.PerLengthImpedance else 'none'}, "
        f"WireConfiguration: {'set' if line.WireConfiguration else 'none'})"
    )


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


def _per_length(line: cim.ACLineSegment, unit: str, base_power, derive: ImpedanceSource) -> SequenceImpedance | None:
    """Steps 2-4 scaled to the whole line, or None when the line's per-length source is beyond ``derive``."""
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
        per_metre = _sequence_code_per_metre(code)
    elif source == ImpedanceSource.MATRIX_REDUCED:
        per_metre = _phase_code_per_metre(line, code)
    else:
        raise NotImplementedError(f"{_describe(line)}: the geometry -> impedance engine (step 4) is not built")

    length = get_qty(line, "length", "m")
    if length is None:
        raise ValueError(f"{_describe(line)}: a per-length impedance needs the line's length")
    base = z_base(line, base_power) if unit == "pu" else 1.0
    totals = {}
    for name, value in per_metre.items():
        if value is None:
            totals[name] = None
        elif name in IMPEDANCE_FIELDS:
            totals[name] = value * length / base
        else:
            totals[name] = value * length * base
    return SequenceImpedance(**totals, source=source)


def _sequence_code_per_metre(code: cim.PerLengthSequenceImpedance) -> dict[str, float | None]:
    """Step 2 in ohm/m and S/m."""
    per_metre = {
        "r": get_qty(code, "r", "ohm/m"),
        "x": get_qty(code, "x", "ohm/m"),
        "b": get_qty(code, "bch", "S/m"),
        "g": get_qty(code, "gch", "S/m"),
        "r0": get_qty(code, "r0", "ohm/m"),
        "x0": get_qty(code, "x0", "ohm/m"),
        "b0": get_qty(code, "b0ch", "S/m"),
        "g0": get_qty(code, "g0ch", "S/m"),
    }
    if per_metre["r"] is None or per_metre["x"] is None:
        raise ValueError(f"{_describe(code)}: r and x must be set")
    return per_metre


def _phase_code_per_metre(line: cim.ACLineSegment, code: cim.PerLengthPhaseImpedance) -> dict[str, float | None]:
    """Step 3 in ohm/m and S/m: the inverse of ``cimhub_core.derived.sequence.phase_matrix``. Self Zs and mutual
    Zm are the means of the diagonal and off-diagonal entries; positive = Zs - Zm, zero = Zs + 2 Zm. One conductor
    has positive = Z11 and no zero sequence. Conductors other than A, B, C (a neutral, s1/s2) raise."""
    phases = [phase.phase for phase in sorted(line.ACLineSegmentPhases, key=lambda phase: phase.sequenceNumber)]
    if not phases:
        raise ValueError(f"{_describe(line)}: a phase matrix needs ACLineSegmentPhases for its conductor order")
    others = [phase.value for phase in phases if phase not in (cim.SinglePhaseKind.A, cim.SinglePhaseKind.B,
                                                               cim.SinglePhaseKind.C)]
    if others:
        raise ValueError(f"{_describe(line)}: conductors {others} need Kron reduction, which is not built")

    count = len(phases)
    entries = {(max(data.row, data.column), min(data.row, data.column)): data for data in code.PhaseImpedanceData}
    expected = {(row, column) for row in range(1, count + 1) for column in range(1, row + 1)}
    if set(entries) != expected:
        raise ValueError(f"{_describe(code)}: entries {sorted(entries)} are not the lower triangle of the "
                         f"{count} conductors of {_describe(line)}")

    per_metre = {}
    for attribute, unit, positive_name, zero_name in (("r", "ohm/m", "r", "r0"), ("x", "ohm/m", "x", "x0"),
                                                      ("b", "S/m", "b", "b0"), ("g", "S/m", "g", "g0")):
        values = {key: get_qty(data, attribute, unit) for key, data in entries.items()}
        if all(value is None for value in values.values()) and attribute in ("b", "g"):
            per_metre[positive_name] = per_metre[zero_name] = None
            continue
        if any(value is None for value in values.values()):
            raise ValueError(f"{_describe(code)}: {attribute} is set on some entries but not all")
        diagonal = [value for (row, column), value in values.items() if row == column]
        self_value = sum(diagonal) / len(diagonal)
        if count == 1:
            per_metre[positive_name], per_metre[zero_name] = self_value, None
            continue
        off_diagonal = [value for (row, column), value in values.items() if row != column]
        mutual = sum(off_diagonal) / len(off_diagonal)
        per_metre[positive_name] = self_value - mutual
        per_metre[zero_name] = self_value + 2 * mutual
    return per_metre


def _check_agreement(line: cim.ACLineSegment, lumped: SequenceImpedance, per_length: SequenceImpedance) -> None:
    """Raise when a value set in both sources differs by more than DISAGREEMENT_REL_TOL."""
    for name in SequenceImpedance._fields[:-1]:
        lumped_value, per_length_value = getattr(lumped, name), getattr(per_length, name)
        if lumped_value is None or per_length_value is None:
            continue
        if not math.isclose(lumped_value, per_length_value, rel_tol=DISAGREEMENT_REL_TOL):
            raise ValueError(f"{_describe(line)}: lumped {name}={lumped_value} disagrees with "
                             f"{per_length.source.name} {name}={per_length_value}")


def _describe(obj) -> str:
    return f"{type(obj).__name__} {obj.mRID!r}"
