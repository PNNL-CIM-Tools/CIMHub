"""A wire spacing's conductor positions and distances, and a line's conductor heights (skill `export-getters`).

DSS ``LineSpacing`` wants x and height per conductor (``get_line_conductor_xy``); GLM ``line_spacing`` wants
pairwise distances (``get_spacing_distances``) and heights. The spacing getters read either CIM form:

- ``XYSpacing``: ``XYConductorPosition.xCoord/yCoord`` as stored, in the spacing's frame. The origin may be ground,
  the top of the pole or the centre of the crossarm; the line's ``spacingYOffset`` lifts it to its height above
  ground, so one crossarm design serves poles of any height. A ``ConductorGroupPosition`` (a bundle, such as a
  triplex) is expanded into its ``SubConductorPosition``s: a ``RegularBundlePosition``'s at the corners of its
  polygon, any other group's at their own coordinates in the group's frame, both rotated by ``orientation``. A
  sub-conductor's unset sequence number or kind is its group's.
- ``ConductorDistanceSpacing``: ``ConductorDistance.distance`` between ``sequenceNumber1`` and ``sequenceNumber2``,
  and each conductor's height above ground as its distance to a position of kind ``earth``. Positions come from
  ``cimhub_core.derived.spacing`` (first conductor at x = 0, mirror images to the right).

Conductors are keyed by sequence number, which matches ``ACLineSegmentPhase.sequenceNumber`` on a line using the
spacing: the spacing itself names no phases. A spacing may hold several circuits (a double circuit, a secondary
under a primary); a line takes the positions of its own phases' sequence numbers. ``circuitNumber`` is not read:
an ACLineSegment's circuitNumber need not match its positions' (cim18v17 ``ACLineSegment.circuitNumber``). Parallel
conductors (two on one sequence number) are not read. A missing coordinate, distance or height raises; there is no
default height. Values are read with ``get_qty`` in the caller's unit (positions scale linearly).
"""

from __future__ import annotations

import math
from itertools import combinations
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.derived.spacing import positions_from_distances
from cimhub_core.getters import describe

EARTH = cim.ConductorPositionKind.earth
# stored distances are rounded (GLM writes 6 digits); beyond this they do not describe one geometry
DISTANCE_REL_TOL = 1e-4


class ConductorXY(NamedTuple):
    """One conductor position: x across the structure, y up (from the spacing's origin, or above ground from
    ``get_line_conductor_xy``)."""

    sequence_number: int
    kind: cim.ConductorPositionKind | None
    x: float
    y: float


def get_line_conductor_xy(line: cim.ACLineSegment, unit: str = "m") -> tuple[ConductorXY, ...]:
    """The line's conductors with y above ground: the positions of its ACLineSegmentPhases' sequence numbers, phase
    conductors then neutrals, each in sequence-number order (the order of its terminal phases), raised by
    ``spacingYOffset``. A line without ACLineSegmentPhases takes every position in sequence-number order. An unset
    offset means the spacing's origin is ground. A ConductorDistanceSpacing already holds heights above ground, so
    an offset on its line raises."""
    spacing = _line_spacing(line)
    positions = _line_positions(line, spacing, get_spacing_xy(spacing, unit))
    offset = get_qty(line, "spacingYOffset", unit)
    if offset is None:
        return positions
    if isinstance(spacing, cim.ConductorDistanceSpacing):
        raise ValueError(f"{describe(line)}: has a spacingYOffset, but its {describe(spacing)} holds heights above "
                         f"ground")
    return tuple(position._replace(y=position.y + offset) for position in positions)


def get_spacing_xy(spacing: cim.WireSpacing, unit: str = "m") -> tuple[ConductorXY, ...]:
    """The spacing's conductors in sequence-number order, in ``unit``, in the spacing's frame."""
    if isinstance(spacing, cim.XYSpacing):
        return _stored_positions(spacing, unit)
    if isinstance(spacing, cim.ConductorDistanceSpacing):
        kinds, heights, distances = _stored_distances(spacing, unit)
        try:
            positions = positions_from_distances(heights, distances, rel_tol=DISTANCE_REL_TOL)
        except ValueError as error:
            raise ValueError(f"{describe(spacing)}: {error}") from error
        return tuple(ConductorXY(number, kinds[number], x, y) for number, (x, y) in positions.items())
    raise _no_positions(spacing)


def get_spacing_distances(spacing: cim.WireSpacing, unit: str = "m") -> dict[tuple[int, int], float]:
    """``{(i, j): d}`` for every pair of sequence numbers i < j, in ``unit`` (the same at any offset). A
    ``ConductorDistanceSpacing`` gives its stored values and must hold a distance for every pair."""
    if isinstance(spacing, cim.XYSpacing):
        positions = _stored_positions(spacing, unit)
        return {(first.sequence_number, second.sequence_number): math.dist((first.x, first.y), (second.x, second.y))
                for first, second in combinations(positions, 2)}
    if isinstance(spacing, cim.ConductorDistanceSpacing):
        _, heights, distances = _stored_distances(spacing, unit)
        missing = [pair for pair in combinations(sorted(heights), 2) if pair not in distances]
        if missing:
            raise ValueError(f"{describe(spacing)}: has no distance between conductors {missing}")
        return dict(sorted(distances.items()))
    raise _no_positions(spacing)


def _line_spacing(line: cim.ACLineSegment) -> cim.WireSpacing:
    """``ACLineSegment.WireSpacing`` or ``WireConfiguration.WireSpacing``; both set must be the same spacing."""
    direct = line.WireSpacing
    configured = line.WireConfiguration.WireSpacing if line.WireConfiguration is not None else None
    if direct is not None and configured is not None and direct is not configured:
        raise ValueError(f"{describe(line)}: its WireSpacing {describe(direct)} is not its WireConfiguration's "
                         f"{describe(configured)}")
    spacing = direct or configured
    if spacing is None:
        raise ValueError(f"{describe(line)}: has no WireSpacing (directly or through a WireConfiguration)")
    return spacing


def _line_positions(line: cim.ACLineSegment, spacing: cim.WireSpacing,
                    positions: tuple[ConductorXY, ...]) -> tuple[ConductorXY, ...]:
    if not line.ACLineSegmentPhases:
        return positions
    by_number = {position.sequence_number: position for position in positions}
    for phase in line.ACLineSegmentPhases:
        if phase.sequenceNumber is None:
            raise ValueError(f"{describe(phase)} of {describe(line)}: sequenceNumber is unset")
    missing = sorted(phase.sequenceNumber for phase in line.ACLineSegmentPhases
                     if phase.sequenceNumber not in by_number)
    if missing:
        raise ValueError(f"{describe(line)}: has ACLineSegmentPhases on sequence numbers {missing}, which "
                         f"{describe(spacing)} has no conductor for (it has {sorted(by_number)})")
    ordered = sorted(line.ACLineSegmentPhases,
                     key=lambda phase: (phase.phase is cim.SinglePhaseKind.N, phase.sequenceNumber))
    return tuple(by_number[phase.sequenceNumber] for phase in ordered)


def _stored_positions(spacing: cim.XYSpacing, unit: str) -> tuple[ConductorXY, ...]:
    positions = {}
    for position in spacing.XYConductorPosition:
        for conductor in _position_conductors(spacing, position, unit):
            if conductor.sequence_number in positions:
                raise ValueError(f"{describe(spacing)}: two conductors have sequenceNumber "
                                 f"{conductor.sequence_number}; parallel conductors are not read")
            positions[conductor.sequence_number] = conductor
    if not positions:
        raise ValueError(f"{describe(spacing)}: has no XYConductorPosition")
    return tuple(positions[number] for number in sorted(positions))


def _position_conductors(spacing: cim.XYSpacing, position: cim.XYConductorPosition,
                         unit: str) -> list[ConductorXY]:
    """One conductor for a position, or one per sub-conductor for a group, in the spacing's frame."""
    x, y = _required_xy(spacing, position, unit)
    if not isinstance(position, cim.ConductorGroupPosition):
        if position.sequenceNumber is None:
            raise ValueError(f"{describe(position)} of {describe(spacing)}: sequenceNumber is unset")
        return [ConductorXY(position.sequenceNumber, position.kind, x, y)]
    orientation = math.radians(get_qty(position, "orientation", "deg") or 0.0)
    cos, sin = math.cos(orientation), math.sin(orientation)
    conductors = []
    for sub, (local_x, local_y) in _group_offsets(spacing, position, unit):
        number = sub.sequenceNumber if sub.sequenceNumber is not None else position.sequenceNumber
        kind = sub.kind if sub.kind is not None else position.kind
        if number is None:
            raise ValueError(f"{describe(sub)} of {describe(position)}: sequenceNumber is unset on it and its group")
        if kind is cim.ConductorPositionKind.mixed:
            raise ValueError(f"{describe(sub)} of {describe(position)}: its group is mixed, so it needs its own kind")
        conductors.append(ConductorXY(number, kind, x + local_x * cos - local_y * sin,
                                      y + local_x * sin + local_y * cos))
    return conductors


def _group_offsets(spacing: cim.XYSpacing, group: cim.ConductorGroupPosition,
                   unit: str) -> list[tuple[cim.SubConductorPosition, tuple[float, float]]]:
    """Each sub-conductor and its (x', y') in the group's frame, before rotation."""
    subs = group.SubConductorPosition
    if not subs:
        raise ValueError(f"{describe(group)} of {describe(spacing)}: has no SubConductorPosition")
    if not isinstance(group, cim.RegularBundlePosition):
        return [(sub, _required_xy(spacing, sub, unit)) for sub in subs]
    count, side = group.subConductorCount, get_qty(group, "subConductorSpacing", unit)
    if count is None or count < 2 or side is None:
        raise ValueError(f"{describe(group)} of {describe(spacing)}: subConductorCount (at least 2) and "
                         f"subConductorSpacing must be set (subConductorCount={count}, subConductorSpacing={side})")
    numbers = sorted(sub.subConductorNumber for sub in subs if sub.subConductorNumber is not None)
    if numbers != list(range(1, count + 1)):
        raise ValueError(f"{describe(group)} of {describe(spacing)}: needs one SubConductorPosition per "
                         f"subConductorNumber 1..{count}, has {numbers} of {len(subs)}")
    radius = side / (2 * math.sin(math.pi / count))
    offsets = []
    for sub in subs:
        angle = math.radians(180 / count - 90 + (sub.subConductorNumber - 1) * 360 / count)
        offsets.append((sub, (radius * math.cos(angle), radius * math.sin(angle))))
    return offsets


def _required_xy(spacing: cim.XYSpacing, position: cim.SpacingPosition, unit: str) -> tuple[float, float]:
    x, y = get_qty(position, "xCoord", unit), get_qty(position, "yCoord", unit)
    if x is None or y is None:
        raise ValueError(f"{describe(position)} of {describe(spacing)}: xCoord and yCoord must be set "
                         f"(xCoord={x}, yCoord={y})")
    return x, y


def _stored_distances(spacing: cim.ConductorDistanceSpacing, unit: str) -> tuple[dict, dict, dict]:
    """``(kinds, heights, distances)`` keyed by sequence number, heights sorted; every conductor needs a height."""
    kinds, heights, distances = {}, {}, {}
    for row in spacing.ConductorDistance:
        distance = get_qty(row, "distance", unit)
        if distance is None:
            raise ValueError(f"{describe(row)} of {describe(spacing)}: distance is unset")
        ends = [(row.sequenceNumber1, row.conductorKind1), (row.sequenceNumber2, row.conductorKind2)]
        conductors = [(number, kind) for number, kind in ends if kind is not EARTH]
        for number, kind in conductors:
            if number is None:
                raise ValueError(f"{describe(row)} of {describe(spacing)}: a conductor end has no sequence number "
                                 f"(sequenceNumber1/2; fromPhase/toPhase are not read)")
            known = kinds.setdefault(number, kind)
            if kind is not None and known not in (None, kind):
                raise ValueError(f"{describe(spacing)}: conductor {number} is both {known.value} and {kind.value}")
            kinds[number] = known or kind
        if len(conductors) == 1:
            _add_once(spacing, heights, conductors[0][0], distance, "height")
        elif len(conductors) == 2 and conductors[0][0] != conductors[1][0]:
            pair = tuple(sorted(number for number, _ in conductors))
            _add_once(spacing, distances, pair, distance, "distance")
        else:
            raise ValueError(f"{describe(row)} of {describe(spacing)}: is not between two conductors or a "
                             f"conductor and earth")
    if not kinds:
        raise ValueError(f"{describe(spacing)}: has no ConductorDistance")
    no_height = sorted(set(kinds) - set(heights))
    if no_height:
        raise ValueError(f"{describe(spacing)}: conductors {no_height} have no height (a ConductorDistance to "
                         f"a position of kind earth)")
    return kinds, dict(sorted(heights.items())), distances


def _add_once(spacing: cim.ConductorDistanceSpacing, values: dict, key, value: float, what: str) -> None:
    if key in values:
        raise ValueError(f"{describe(spacing)}: two values for the {what} of {key}")
    values[key] = value


def _no_positions(spacing: cim.WireSpacing) -> ValueError:
    return ValueError(f"{describe(spacing)}: has no conductor positions; only XYSpacing and "
                      f"ConductorDistanceSpacing are read")
