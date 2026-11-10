"""A load's p and q per phase and its voltage response (skill `export-getters`, semantic rule 3).

CIM load sign: consumption is positive p. The response is the load's ``LoadResponseCharacteristic``: ZIP fractions
as stored (zeros stay zeros, each set of three must sum to 1), or voltage exponents.
"""

from __future__ import annotations

import math
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe
from cimhub_core.getters.phase_power import SUM_REL_TOL, PhasePower, device_power

ZIP = {"p": ("pConstantImpedance", "pConstantCurrent", "pConstantPower"),
       "q": ("qConstantImpedance", "qConstantCurrent", "qConstantPower")}
EXPONENTS = ("pVoltageExponent", "qVoltageExponent")


class PhaseLoads(NamedTuple):
    phases: tuple[cim.SinglePhaseKind, ...]  # the phase conductors; no neutral
    connection: cim.PhaseShuntConnectionKind | None
    grounded: bool | None
    total: PhasePower
    per_phase: dict[cim.SinglePhaseKind, PhasePower]
    split: bool  # True: the total split evenly; False: EnergyConsumerPhase values


class LoadResponse(NamedTuple):
    """ZIP fractions (``exponential`` False) or voltage exponents (True); the other form's fields are None."""

    exponential: bool
    p_impedance: float | None
    p_current: float | None
    p_power: float | None
    q_impedance: float | None
    q_current: float | None
    q_power: float | None
    p_exponent: float | None
    q_exponent: float | None


def get_phase_loads(consumer: cim.EnergyConsumer, active_unit: str = "W",
                    reactive_unit: str = "VAr") -> PhaseLoads:
    """The load's p and q (required), per phase from ``EnergyConsumerPhase`` when every child has them, else the
    total split evenly over its phase conductors."""
    power = device_power(consumer, consumer.EnergyConsumerPhase, active_unit, reactive_unit)
    return PhaseLoads(power.phases, consumer.phaseConnection, consumer.grounded, power.total, power.per_phase,
                      power.split)


def get_load_response(consumer: cim.EnergyConsumer) -> LoadResponse:
    """The load's ``LoadResponseCharacteristic`` (required); every value its form needs must be set."""
    response = consumer.LoadResponse
    if response is None:
        raise ValueError(f"{describe(consumer)}: has no LoadResponse")
    if response.exponentModel is None:
        raise ValueError(f"{describe(response)}: exponentModel is unset")
    if response.exponentModel:
        p_exponent, q_exponent = (_required(response, name) for name in EXPONENTS)
        return LoadResponse(True, None, None, None, None, None, None, p_exponent, q_exponent)

    fractions = {}
    for power, names in ZIP.items():
        values = [_required(response, name) for name in names]
        if not math.isclose(sum(values), 1.0, rel_tol=SUM_REL_TOL):
            raise ValueError(f"{describe(response)}: the {power} fractions {values} do not sum to 1")
        fractions[power] = values
    return LoadResponse(False, *fractions["p"], *fractions["q"], None, None)


def _required(response: cim.LoadResponseCharacteristic, name: str) -> float:
    value = getattr(response, name)
    if value is None:
        raise ValueError(f"{describe(response)}: {name} is unset")
    return value
