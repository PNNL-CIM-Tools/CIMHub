"""Conductor positions from pairwise distances and heights (a ``ConductorDistanceSpacing`` read as XY).

Each conductor's height is known, so only x is solved. The first conductor (lowest sequence number) is at x = 0.
Each later one is placed from the conductors already placed that it has a distance to: the horizontal run to a
reference is sqrt(d^2 - dy^2), giving x_ref +/- run, and the candidate that best fits every reference wins. Where
the distances leave a mirror image open (the second conductor, or one placed from a vertical stack), it goes to the
right (+x). Every stored distance is then checked against the positions. Pure Python, all lengths in one unit. A
candidate for CIM-Tables (UPSTREAM_REQUESTS U4).
"""

from __future__ import annotations

import math


def positions_from_distances(heights: dict[int, float], distances: dict[tuple[int, int], float], *,
                             rel_tol: float) -> dict[int, tuple[float, float]]:
    """``{sequence number: (x, y)}`` from ``heights`` ``{sequence number: y}`` and ``distances``
    ``{(i, j): d}`` (i < j). Raises ValueError when a conductor has no distance to one placed before it, when a
    distance is shorter than its height difference, or when a distance disagrees with the positions beyond
    ``rel_tol``."""
    order = sorted(heights)
    x = {order[0]: 0.0}
    for conductor in order[1:]:
        references = [(placed, distances[pair]) for placed in x
                      if (pair := (min(placed, conductor), max(placed, conductor))) in distances]
        if not references:
            raise ValueError(f"conductor {conductor}: no distance to a conductor placed before it {sorted(x)}")
        x[conductor] = _best_x(conductor, references, x, heights, rel_tol)

    positions = {conductor: (x[conductor], heights[conductor]) for conductor in order}
    for (first, second), distance in distances.items():
        computed = math.dist(positions[first], positions[second])
        if not math.isclose(computed, distance, rel_tol=rel_tol):
            raise ValueError(f"conductors {first}-{second}: distance {distance} disagrees with the positions "
                             f"({computed}) the other distances give")
    return positions


def _best_x(conductor: int, references: list[tuple[int, float]], x: dict[int, float], heights: dict[int, float],
            rel_tol: float) -> float:
    """The x that best fits every reference distance; the rightmost of equally good fits."""
    candidates = []
    for reference, distance in references:
        run = _horizontal_run(conductor, reference, distance, heights[reference] - heights[conductor], rel_tol)
        candidates += [x[reference] + run, x[reference] - run]

    def misfit(candidate: float) -> float:
        return sum((math.hypot(candidate - x[reference], heights[reference] - heights[conductor]) - distance) ** 2
                   for reference, distance in references)

    best = min(misfit(candidate) for candidate in candidates)
    tie = (rel_tol * max(distance for _, distance in references)) ** 2
    return max(candidate for candidate in candidates if misfit(candidate) <= best + tie)


def _horizontal_run(conductor: int, reference: int, distance: float, rise: float, rel_tol: float) -> float:
    """sqrt(d^2 - dy^2); a distance short of the height difference by no more than ``rel_tol`` is a vertical run."""
    if abs(rise) > distance and not math.isclose(abs(rise), distance, rel_tol=rel_tol):
        raise ValueError(f"conductors {min(conductor, reference)}-{max(conductor, reference)}: distance {distance} "
                         f"is shorter than their height difference {abs(rise)}")
    return math.sqrt(max(distance * distance - rise * rise, 0.0))
