"""A device's p and q in total and per phase (skill `export-getters`, semantic rule 3), shared by loads and DER.

Per phase are the ``<Class>Phase`` children's own p and q when every child has them, else the total split evenly over
the device's phase conductors (the neutral carries none). Children with values must be exactly those conductors and
sum to the total.
"""

from __future__ import annotations

import math
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe
from cimhub_core.getters.terminals import get_conductor_phases

SUM_REL_TOL = 1e-6


class PhasePower(NamedTuple):
    p: float
    q: float


class DevicePower(NamedTuple):
    phases: tuple[cim.SinglePhaseKind, ...]  # the phase conductors, in PhaseCode order; no neutral
    total: PhasePower
    per_phase: dict[cim.SinglePhaseKind, PhasePower]
    split: bool  # True: the total split evenly; False: the children's own values


def device_power(device, children, active_unit: str, reactive_unit: str) -> DevicePower:
    """The device's p and q (both required) and their per-phase values from ``children``."""
    phases = tuple(phase for phase in get_conductor_phases(device) if phase is not cim.SinglePhaseKind.N)
    total = PhasePower(_required(device, "p", active_unit), _required(device, "q", reactive_unit))
    valued = [child for child in children if child.p is not None or child.q is not None]
    if not valued:
        share = PhasePower(total.p / len(phases), total.q / len(phases))
        return DevicePower(phases, total, {phase: share for phase in phases}, split=True)
    if len(valued) != len(children):
        raise ValueError(f"{describe(device)}: some of its phases have p and q and some do not")

    per_phase = {child.phase: PhasePower(_required(child, "p", active_unit), _required(child, "q", reactive_unit))
                 for child in children}
    if len(per_phase) != len(children) or set(per_phase) != set(phases):
        raise ValueError(f"{describe(device)}: its phases {[child.phase.value for child in children]} are not its "
                         f"conductors {[phase.value for phase in phases]}")
    for name in ("p", "q"):
        summed = sum(getattr(value, name) for value in per_phase.values())
        if not math.isclose(summed, getattr(total, name), rel_tol=SUM_REL_TOL):
            raise ValueError(f"{describe(device)}: its phases' {name} sum to {summed}, not its {getattr(total, name)}")
    return DevicePower(phases, total, {phase: per_phase[phase] for phase in phases}, split=False)


def _required(obj, attribute: str, unit: str) -> float:
    value = get_qty(obj, attribute, unit)
    if value is None:
        raise ValueError(f"{describe(obj)}: {attribute} is unset")
    return value
