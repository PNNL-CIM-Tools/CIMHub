"""A 1- or 2-phase line's phase matrix from its sequence values, as OpenDSS builds the line.

A 3-phase sequence code stays a ``PerLengthSequenceImpedance``. Fewer phases have no CIM sequence convention, so
the matrix is written instead: 1-phase is the positive-sequence value alone; 2-phase is the 3-phase transform
truncated to two conductors, self Zs = (2 Z1 + Z0) / 3 and mutual Zm = (Z0 - Z1) / 3. Closed form, not Carson.
The same holds for r, x and C separately. A candidate for CIM-Tables (UPSTREAM_REQUESTS U4).

``balanced_matrix`` is the n-conductor form, self (2 Z1 + Z0) / 3 and mutual (Z0 - Z1) / 3 on every conductor:
OpenDSS gives it to a matrix line code that leaves out its C matrix (from the default C1, C0).
"""

from __future__ import annotations


def phase_matrix(positive: float, zero: float | None, phases: int) -> dict[tuple[int, int], float]:
    """``{(row, column): value}``, lower triangle, 1-based. ``zero`` is unused (and may be ``None``) on 1 phase."""
    if phases == 1:
        return {(1, 1): positive}
    if phases == 2:
        if zero is None:
            raise ValueError("a 2-phase matrix needs the zero-sequence value")
        self_value = (2 * positive + zero) / 3
        return {(1, 1): self_value, (2, 1): (zero - positive) / 3, (2, 2): self_value}
    raise ValueError(f"phase_matrix is for 1 or 2 phases, not {phases}")


def balanced_matrix(positive: float, zero: float, conductors: int) -> dict[tuple[int, int], float]:
    """``{(row, column): value}``, lower triangle, 1-based: self (2 positive + zero) / 3 on the diagonal, mutual
    (zero - positive) / 3 off it, for any number of conductors."""
    self_value, mutual = (2 * positive + zero) / 3, (zero - positive) / 3
    return {(row, column): self_value if row == column else mutual
            for row in range(1, conductors + 1) for column in range(1, row + 1)}
