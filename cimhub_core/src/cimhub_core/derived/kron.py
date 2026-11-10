"""Kron reduction: fold grounded conductors (neutrals) out of a series impedance matrix.

With a conductor grounded at both ends its voltage drop is zero, so its current is eliminated:
Z' = Z_pp - Z_pn Z_nn^-1 Z_np. One conductor at a time, Z'_ij = Z_ij - Z_ik Z_kj / Z_kk, gives the same result as
the block form, in any order. Pure Python, so no numpy dependency. A candidate for CIM-Tables (UPSTREAM_REQUESTS U4).

Only the series impedance is Kron-reduced. A shunt matrix with grounded conductors (V_n = 0) keeps its phase block
as it is, because C_reduced = (P_reduced)^-1 is the phase block of C = P^-1.
"""

from __future__ import annotations

from collections.abc import Iterable


def kron_reduce(matrix: dict[tuple[int, int], complex], eliminate: Iterable[int]) -> dict[tuple[int, int], complex]:
    """``{(row, column): value}``, lower triangle, 1-based, with the ``eliminate`` conductors folded out. The kept
    conductors are renumbered 1..k in their original order. Raises ValueError on a zero pivot."""
    size = max(row for row, _ in matrix)
    full = {}
    for (row, column), value in matrix.items():
        full[row, column] = full[column, row] = value

    kept = list(range(1, size + 1))
    for conductor in eliminate:
        pivot = full[conductor, conductor]
        if pivot == 0:
            raise ValueError(f"cannot eliminate conductor {conductor}: its self impedance is zero")
        kept.remove(conductor)
        full = {(i, j): full[i, j] - full[i, conductor] * full[conductor, j] / pivot for i in kept for j in kept}

    return {(new_row, new_column): full[row, column]
            for new_row, row in enumerate(kept, start=1)
            for new_column, column in enumerate(kept, start=1) if new_column <= new_row}
