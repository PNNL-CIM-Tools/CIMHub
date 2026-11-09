"""A DER's output: an inverter's or a machine's p and q, in total and per phase (skill `export-getters`, semantic
rule 2).

CIM's sign is the load's: p and q are positive into the equipment, so generation and discharge are negative. The
caller names the sign it wants: ``'load'`` as stored, ``'generation'`` negated (positive output), so no spoke negates
on its own.
"""

from __future__ import annotations

from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe
from cimhub_core.getters.phase_power import PhasePower, device_power

SIGNS = ("load", "generation")


class DerOutput(NamedTuple):
    phases: tuple[cim.SinglePhaseKind, ...]  # the phase conductors; no neutral
    connection: cim.PhaseShuntConnectionKind | None  # a RotatingMachine has none (UPSTREAM_REQUESTS U8)
    total: PhasePower
    per_phase: dict[cim.SinglePhaseKind, PhasePower]
    split: bool  # True: the total split evenly; False: PowerElectronicsConnectionPhase values


def get_der_output(equipment: cim.PowerElectronicsConnection | cim.RotatingMachine, active_unit: str = "W",
                   reactive_unit: str = "VAr", *, sign: str) -> DerOutput:
    """p and q (required) in the ``sign`` convention. An inverter's per-phase values are its
    ``PowerElectronicsConnectionPhase``s' when every one has them; a machine's phases hold none, so its total is
    split evenly."""
    if sign not in SIGNS:
        raise ValueError(f"sign must be one of {list(SIGNS)}, not {sign!r}")
    if isinstance(equipment, cim.PowerElectronicsConnection):
        children, connection = equipment.PowerElectronicsConnectionPhase, equipment.phaseConnection
    elif isinstance(equipment, cim.RotatingMachine):
        children, connection = (), None
    else:
        raise ValueError(f"{describe(equipment)}: is not a PowerElectronicsConnection or RotatingMachine")
    power = device_power(equipment, children, active_unit, reactive_unit)

    def signed(value: PhasePower) -> PhasePower:
        if sign == "load":
            return value
        return PhasePower(0.0 - value.p, 0.0 - value.q)  # 0.0 - v, not -v: a zero stays 0.0, never -0.0

    return DerOutput(power.phases, connection, signed(power.total),
                     {phase: signed(value) for phase, value in power.per_phase.items()}, power.split)
