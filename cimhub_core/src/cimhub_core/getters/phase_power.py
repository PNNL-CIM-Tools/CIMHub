"""A device's p and q in total and per phase (skill `export-getters`, semantic rule 3), shared by loads and DER.

Per phase are the ``<Class>Phase`` children's own p and q when every child has them, else the total split evenly over
the device's phase conductors (the neutral carries none). Children with values must be exactly those conductors and
sum to the total.
"""

from __future__ import annotations

import math
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimprofiles.units.units import ureg

from cimhub_core.getters import describe, required_qty
from cimhub_core.getters.terminals import get_conductor_phases

SUM_REL_TOL = 1e-6
# pint converts W and VAr into each other (VAr is W times the dimensionless `imaginary`), so a swapped unit would pass
# unnoticed; the root units still tell them apart
ACTIVE_ROOT_UNITS = ureg.Quantity(1, "W").to_root_units().units
REACTIVE_ROOT_UNITS = ureg.Quantity(1, "VAr").to_root_units().units


class PhasePower(NamedTuple):
    p: float
    q: float


class DevicePower(NamedTuple):
    phases: tuple[cim.SinglePhaseKind, ...]  # the phase conductors, in PhaseCode order; no neutral
    total: PhasePower
    per_phase: dict[cim.SinglePhaseKind, PhasePower]
    split: bool  # True: the total split evenly; False: the children's own values


def device_power(device, children, active_unit: str, reactive_unit: str) -> DevicePower:
    """The device's p and q (both required) and their per-phase values from ``children``. ``active_unit`` must be a
    W unit and ``reactive_unit`` a VAr unit."""
    active_root = ureg.Quantity(1, active_unit).to_root_units().units
    reactive_root = ureg.Quantity(1, reactive_unit).to_root_units().units
    if active_root != ACTIVE_ROOT_UNITS or reactive_root != REACTIVE_ROOT_UNITS:
        raise ValueError(f"active unit {active_unit!r} and reactive unit {reactive_unit!r}: p takes a W unit and q a "
                         f"VAr unit")
    phases = tuple(phase for phase in get_conductor_phases(device) if phase is not cim.SinglePhaseKind.N)
    total = PhasePower(required_qty(device, "p", active_unit), required_qty(device, "q", reactive_unit))
    valued = [child for child in children if child.p is not None or child.q is not None]
    if not valued:
        share = PhasePower(total.p / len(phases), total.q / len(phases))
        return DevicePower(phases, total, {phase: share for phase in phases}, split=True)
    if len(valued) != len(children):
        raise ValueError(f"{describe(device)}: some of its phases have p and q and some do not")

    per_phase = {child.phase: PhasePower(required_qty(child, "p", active_unit), required_qty(child, "q", reactive_unit))
                 for child in children}
    if len(per_phase) != len(children) or set(per_phase) != set(phases):
        raise ValueError(f"{describe(device)}: its phases {[child.phase.value for child in children]} are not its "
                         f"conductors {[phase.value for phase in phases]}")
    for name in ("p", "q"):
        summed = sum(getattr(value, name) for value in per_phase.values())
        if not math.isclose(summed, getattr(total, name), rel_tol=SUM_REL_TOL):
            raise ValueError(f"{describe(device)}: its phases' {name} sum to {summed}, not its {getattr(total, name)}")
    return DevicePower(phases, total, {phase: per_phase[phase] for phase in phases}, split=False)
