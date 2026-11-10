"""RATE1..RATE12 of a rated device, and whether a case's ratings are currents (``EXPORT_MAPPING.md#ratings``).

RATEn is the limit whose type has the importer's mRID ``olt_rate<n>`` (RAW-9). The ratings are in MVA
(``ApparentPowerLimit``) or "current expressed as MVA" (``CurrentLimit``: NXFRAT / XFRRAT 1, RATEn = sqrt(3) x kV x
kA on the device's BaseVoltage). One device or one case holding both kinds raises.
"""

from __future__ import annotations

import re

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe
from cimhub_core.getters.base_voltage import get_base_voltage
from cimhub_core.getters.limits_by_type import get_limits_by_type
from cimhub_raw.importer.cimtbl.derived import rating_from_ka
from cimhub_raw.importer.cimtbl.ratings import RATING_SETS

RATING_TYPE = re.compile(r"olt_rate(\d+)")  # the importer's rating-set OperationalLimitTypes (RAW-9)


def rating_set_number(limit_type: cim.OperationalLimitType) -> int | None:
    """n of a rating-set type ``olt_rate<n>``; None for another type."""
    match = RATING_TYPE.fullmatch(limit_type.mRID)
    return None if match is None else int(match.group(1))


def device_limits(device) -> tuple[type | None, dict]:
    """The device's rating kind (``ApparentPowerLimit``, ``CurrentLimit`` or None) and its limits by type, in MVA or
    kA."""
    power = get_limits_by_type(device, cim.ApparentPowerLimit, "MVA")
    current = get_limits_by_type(device, cim.CurrentLimit, "kA")
    if power and current:
        raise ValueError(f"{describe(device)}: holds both ApparentPowerLimits and CurrentLimits; RAW's ratings are "
                         "one or the other")
    if current:
        return cim.CurrentLimit, current
    return (cim.ApparentPowerLimit if power else None), power


def ratings_in_current(devices) -> bool:
    """True when the devices' ratings are CurrentLimits (NXFRAT / XFRRAT 1); False for ApparentPowerLimits or none.
    Both kinds among the devices raise."""
    first_of_kind: dict[type, object] = {}
    for device in devices:
        kind, _ = device_limits(device)
        if kind is not None:
            first_of_kind.setdefault(kind, device)
    if len(first_of_kind) > 1:
        raise ValueError(f"ratings in MVA ({describe(first_of_kind[cim.ApparentPowerLimit])}) and in current "
                         f"({describe(first_of_kind[cim.CurrentLimit])}) in one case; RAW's units flag is one or "
                         "the other")
    return cim.CurrentLimit in first_of_kind


def device_ratings(device) -> list[float]:
    """RATE1..RATE12, 0 where the device has no limit of that set. A limit of another type raises."""
    kind, limits = device_limits(device)
    ratings = [0.0] * RATING_SETS
    base_kv = get_base_voltage(device, "kV", form="LL") if kind is cim.CurrentLimit else None
    for limit_type, value in limits.items():
        number = rating_set_number(limit_type)
        if number is None or not 1 <= number <= RATING_SETS:
            raise ValueError(f"{describe(device)}: limit type {describe(limit_type)} is not a rating set "
                             f"olt_rate1..olt_rate{RATING_SETS}")
        ratings[number - 1] = rating_from_ka(value, base_kv) if kind is cim.CurrentLimit else value
    return ratings
