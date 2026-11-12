"""A conductor catalog entry (a WireInfo), and a WireConfiguration's or a line's per-phase conductors (skill
`export-getters`).

Three WireInfo kinds are read: ``OverheadWireInfo`` (a bare wire), ``ConcentricNeutralCableInfo`` and
``TapeShieldCableInfo``. Every value is as stored, in the caller's units; unset is None. Only ``rAC25`` of the
three AC resistances is read (the one the DSS importer writes); a set ``rAC50``/``rAC75`` raises until a producer
writes one. The ratings are ``ratedCurrent`` and the limits of the wire's own ``AssetInfo.OperationalLimitSet``;
a ``ratedCurrent`` and a normal limit that are both set must agree.
"""

from __future__ import annotations

import math
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe
from cimhub_core.getters.current_limits import CurrentLimits, get_asset_info_current_limits

WIRE_KINDS = (cim.OverheadWireInfo, cim.ConcentricNeutralCableInfo, cim.TapeShieldCableInfo)
UNREAD_RESISTANCES = ("rAC50", "rAC75")


class CableValues(NamedTuple):
    """A cable's construction, in the length unit; the concentric-neutral fields are None on a tape-shield cable and
    the tape fields on a concentric-neutral one."""

    insulation_thickness: float | None
    diameter_over_insulation: float | None
    diameter_over_jacket: float | None
    diameter_over_screen: float | None
    diameter_over_neutral: float | None
    neutral_strand_count: int | None
    neutral_strand_radius: float | None
    neutral_strand_gmr: float | None
    neutral_strand_r_dc20: float | None  # resistance unit
    tape_thickness: float | None
    tape_lap: float | None  # percent


class WireValues(NamedTuple):
    kind: type  # one of WIRE_KINDS
    r_dc20: float | None  # resistance unit (per length)
    r_ac25: float | None
    gmr: float | None  # length unit
    radius: float | None
    rated_current: float | None  # current unit
    limits: CurrentLimits  # the wire's own OperationalLimitSet
    cable: CableValues | None  # None on an OverheadWireInfo


def get_wire_info(wire: cim.WireInfo, length_unit: str = "m", resistance_unit: str = "ohm/m",
                  current_unit: str = "A") -> WireValues:
    """The wire's resistances, gmr, radius, ratings and, on a cable, its construction."""
    kind = type(wire)
    if kind not in WIRE_KINDS:
        raise ValueError(f"{describe(wire)}: is not one of {[cls.__name__ for cls in WIRE_KINDS]}")
    unread = [name for name in UNREAD_RESISTANCES if getattr(wire, name) is not None]
    if unread:
        raise ValueError(f"{describe(wire)}: {unread} are set; only rAC25 is read")
    rated_current = get_qty(wire, "ratedCurrent", current_unit)
    limits = get_asset_info_current_limits(wire, current_unit)
    if rated_current is not None and limits.normal is not None and not math.isclose(rated_current, limits.normal):
        raise ValueError(f"{describe(wire)}: ratedCurrent {rated_current} disagrees with its normal limit "
                         f"{limits.normal}")
    return WireValues(
        kind=kind,
        r_dc20=get_qty(wire, "rDC20", resistance_unit),
        r_ac25=get_qty(wire, "rAC25", resistance_unit),
        gmr=get_qty(wire, "gmr", length_unit),
        radius=get_qty(wire, "radius", length_unit),
        rated_current=rated_current,
        limits=limits,
        cable=None if kind is cim.OverheadWireInfo else _cable(wire, length_unit, resistance_unit),
    )


def get_configuration_wires(configuration: cim.WireConfiguration) -> tuple[tuple[int, cim.WireInfo], ...]:
    """``(sequenceNumber, WireInfo)`` of each WireSequenceConfiguration, in sequence-number order. An unset or
    repeated sequence number, or a conductor without a WireInfo, raises."""
    wires = {}
    for sequence in configuration.WireSequence:
        number = sequence.sequenceNumber
        if number is None or number in wires:
            raise ValueError(f"{describe(configuration)}: {describe(sequence)} has sequence number {number!r}, "
                             f"unset or repeated")
        if sequence.WireInfo is None:
            raise ValueError(f"{describe(configuration)}: {describe(sequence)} has no WireInfo")
        wires[number] = sequence.WireInfo
    return tuple(sorted(wires.items()))


def get_line_phase_wires(line: cim.ACLineSegment) -> tuple[tuple[int, cim.WireInfo], ...]:
    """``(sequenceNumber, WireInfo)`` of each ACLineSegmentPhase, in sequence-number order; empty when no phase
    names a WireInfo. A phase without one beside a phase with one, or an unset or repeated sequence number, raises."""
    phases = line.ACLineSegmentPhases
    if not any(phase.WireInfo is not None for phase in phases):
        return ()
    wires = {}
    for phase in phases:
        number = phase.sequenceNumber
        if number is None or number in wires:
            raise ValueError(f"{describe(line)}: {describe(phase)} has sequence number {number!r}, unset or repeated")
        if phase.WireInfo is None:
            raise ValueError(f"{describe(line)}: {describe(phase)} has no WireInfo, and other phases have one")
        wires[number] = phase.WireInfo
    return tuple(sorted(wires.items(), key=lambda item: item[0]))


def _cable(cable: cim.CableInfo, length_unit: str, resistance_unit: str) -> CableValues:
    concentric = isinstance(cable, cim.ConcentricNeutralCableInfo)
    tape = isinstance(cable, cim.TapeShieldCableInfo)
    return CableValues(
        insulation_thickness=get_qty(cable, "insulationThickness", length_unit),
        diameter_over_insulation=get_qty(cable, "diameterOverInsulation", length_unit),
        diameter_over_jacket=get_qty(cable, "diameterOverJacket", length_unit),
        diameter_over_screen=get_qty(cable, "diameterOverScreen", length_unit),
        diameter_over_neutral=get_qty(cable, "diameterOverNeutral", length_unit) if concentric else None,
        neutral_strand_count=cable.neutralStrandCount if concentric else None,
        neutral_strand_radius=get_qty(cable, "neutralStrandRadius", length_unit) if concentric else None,
        neutral_strand_gmr=get_qty(cable, "neutralStrandGmr", length_unit) if concentric else None,
        neutral_strand_r_dc20=get_qty(cable, "neutralStrandRDC20", resistance_unit) if concentric else None,
        tape_thickness=get_qty(cable, "tapeThickness", length_unit) if tape else None,
        tape_lap=get_qty(cable, "tapeLap", "percent") if tape else None,
    )
