"""An equipment's current ratings (skill `export-getters`).

CIM hangs an ``OperationalLimitSet`` on the rated ``Equipment``, on its ``Terminal``s, or on both (one set per
terminal is common). The getter reads every set on the equipment and its terminals. Each ``CurrentLimit`` is
classified by its ``OperationalLimitType.durationKind`` (normal, shortTerm, emergency; ``shapes/common.cimtbl``) and
valued by ``normalValue``. A type's ``season`` (GridAPPS-D extension, ``CalendarSeasonKind``) makes the limit
seasonal; a type with no season holds all year. Limits of one kind and season must agree. A wire's ratings
(``AssetInfo.OperationalLimitSet``) are not the equipment's and are not read here.
"""

from __future__ import annotations

import math
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe

# LimitDurationKind -> CurrentLimits field
DURATION_FIELD = {
    cim.LimitDurationKind.normal: "normal",
    cim.LimitDurationKind.shortTerm: "short_term",
    cim.LimitDurationKind.emergency: "emergency",
}


class CurrentLimits(NamedTuple):
    """Current ratings by duration; ``None`` when the equipment has no limit of that kind."""

    normal: float | None
    short_term: float | None
    emergency: float | None


def get_current_limits(
    equipment: cim.ConductingEquipment, unit: str = "A", *, season: cim.CalendarSeasonKind | None = None
) -> CurrentLimits:
    """The equipment's normal, short-term and emergency current limits in ``unit``. ``season=None`` reads the
    all-year limits only. With a season, each kind is that season's limit, or the all-year one where the season has
    none (an all-year limit holds in every season). Raises when a CurrentLimit has no OperationalLimitType,
    durationKind or normalValue, or when two limits of one kind and season differ."""
    all_year = {field: [] for field in CurrentLimits._fields}
    in_season = {field: [] for field in CurrentLimits._fields}
    for limit_set in _limit_sets(equipment):
        for limit in limit_set.OperationalLimitValue:
            if not isinstance(limit, cim.CurrentLimit):
                continue
            limit_season = limit.OperationalLimitType.season if limit.OperationalLimitType else None
            if limit_season is None:
                found = all_year
            elif season is not None and limit_season is season:
                found = in_season
            else:
                continue
            found[_duration_field(limit)].append((limit, _amps(limit, unit)))
    limits = {}
    for field in CurrentLimits._fields:
        limits[field] = _agreed(equipment, field, in_season[field] or all_year[field])
    return CurrentLimits(**limits)


def _limit_sets(equipment: cim.ConductingEquipment) -> list[cim.OperationalLimitSet]:
    """The sets on the equipment and on its terminals, each once."""
    limit_sets = list(equipment.OperationalLimitSet)
    for terminal in equipment.Terminals:
        limit_sets.extend(limit_set for limit_set in terminal.OperationalLimitSet if limit_set not in limit_sets)
    return limit_sets


def _duration_field(limit: cim.CurrentLimit) -> str:
    limit_type = limit.OperationalLimitType
    if limit_type is None:
        raise ValueError(f"{describe(limit)}: has no OperationalLimitType")
    if limit_type.durationKind not in DURATION_FIELD:
        raise ValueError(f"{describe(limit_type)}: durationKind {limit_type.durationKind} is not one of "
                         f"{[kind.value for kind in DURATION_FIELD]}")
    return DURATION_FIELD[limit_type.durationKind]


def _amps(limit: cim.CurrentLimit, unit: str) -> float:
    value = get_qty(limit, "normalValue", unit)
    if value is None:
        raise ValueError(f"{describe(limit)}: normalValue is unset")
    return value


def _agreed(equipment: cim.ConductingEquipment, field: str, found: list) -> float | None:
    """The one value of a kind, or None when there is none; differing values raise."""
    if not found:
        return None
    _, first = found[0]
    for _, value in found[1:]:
        if not math.isclose(value, first):
            raise ValueError(f"{describe(equipment)}: {field} current limits disagree "
                             f"({[(item.mRID, amount) for item, amount in found]})")
    return first
