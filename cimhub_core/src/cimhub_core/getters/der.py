"""A DER: an inverter's or a machine's output, its ratings and its unit (skill `export-getters`, semantic rule 2).

CIM's sign is the load's: p and q are positive into the equipment, so generation and discharge are negative. The
caller names the sign it wants: ``'load'`` as stored, ``'generation'`` negated (positive output), so no spoke negates
on its own.

The nameplate limits (``maxQ``/``minQ``, ``maxP``/``minP``) are written in the generation sign: a PV unit's maxP is
its output, a battery's minP its charging (negative). Every limit pair comes back as ``(min, max)`` in the caller's
``sign``: as stored for ``'generation'``, negated and swapped for ``'load'``. A minimum above its maximum raises (a
producer that wrote the load sign). ``BatteryUnit.idlingP`` is a loss, "consumed while idling", and is returned as
stored in either sign.

``ratedU`` is line to line, as stored (the DSS importer writes a 1-phase wye device's kV x sqrt 3; its exporter
undoes that). ``ratedS`` and ``ratedU`` are required. One connection has one PowerElectronicsUnit
(``get_inverter_unit``); a wind unit, an AsynchronousMachine and a machine's short-circuit data (``ikk``, ``mu``,
star point earthing), voltage limits and capability curves are not read.
"""

from __future__ import annotations

from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe, required_qty
from cimhub_core.getters.phase_power import PhasePower, device_power

SIGNS = ("load", "generation")
IMPEDANCE_UNITS = ("ohm", "pu")
MACHINE_IMPEDANCE_ATTRIBUTES = ("r", "r0", "x0", "r2", "x2")


class DerOutput(NamedTuple):
    phases: tuple[cim.SinglePhaseKind, ...]  # the phase conductors; no neutral
    connection: cim.PhaseShuntConnectionKind | None  # a RotatingMachine has none (UPSTREAM_REQUESTS U8)
    total: PhasePower
    per_phase: dict[cim.SinglePhaseKind, PhasePower]
    split: bool  # True: the total split evenly; False: PowerElectronicsConnectionPhase values


class InverterRating(NamedTuple):
    rated_s: float  # apparent_unit
    rated_u: float  # voltage_unit, line to line
    min_q: float | None  # reactive_unit, in the caller's sign
    max_q: float | None
    max_fault_current: float | None  # pu of rated current (maxIFault)


class PhotoVoltaicRating(NamedTuple):
    min_p: float | None  # active_unit, in the caller's sign
    max_p: float | None


class BatteryRating(NamedTuple):
    min_p: float | None  # active_unit, in the caller's sign
    max_p: float | None
    rated_e: float | None  # energy_unit
    stored_e: float | None
    minimum_e: float | None
    charging_efficiency: float | None  # percent
    discharging_efficiency: float | None  # percent
    idling_p: float | None  # active_unit, consumed while idling, either sign
    state: cim.BatteryStateKind | None


class MachineRating(NamedTuple):
    rated_s: float  # apparent_unit
    rated_u: float  # voltage_unit, line to line
    rated_power_factor: float | None
    min_q: float | None  # reactive_unit, in the caller's sign
    max_q: float | None
    q_percent: float | None  # percent, its share of a coordinated reactive control
    reference_priority: int | None
    type: cim.SynchronousMachineKind | None
    operating_mode: cim.SynchronousMachineOperatingMode | None
    earthing: bool | None


class MachineImpedance(NamedTuple):
    """No positive-sequence x: cim18v17 has no machine reactance (UPSTREAM_REQUESTS U13)."""

    r: float | None
    r0: float | None
    x0: float | None
    r2: float | None
    x2: float | None


def get_der_output(equipment: cim.PowerElectronicsConnection | cim.RotatingMachine, active_unit: str = "W",
                   reactive_unit: str = "VAr", *, sign: str) -> DerOutput:
    """p and q (required) in the ``sign`` convention. An inverter's per-phase values are its
    ``PowerElectronicsConnectionPhase``s' when every one has them; a machine's phases hold none, so its total is
    split evenly."""
    _check_sign(sign)
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
        return PhasePower(_negated(value.p), _negated(value.q))

    return DerOutput(power.phases, connection, signed(power.total),
                     {phase: signed(value) for phase, value in power.per_phase.items()}, power.split)


def get_inverter_rating(connection: cim.PowerElectronicsConnection, apparent_unit: str = "VA",
                        reactive_unit: str = "VAr", *, sign: str, voltage_unit: str = "V") -> InverterRating:
    """The inverter's nameplate: ratedS and ratedU (required), its q limits in the ``sign`` convention and
    maxIFault."""
    _check_sign(sign)
    min_q, max_q = _limits(connection, "minQ", "maxQ", reactive_unit, sign)
    return InverterRating(
        rated_s=required_qty(connection, "ratedS", apparent_unit),
        rated_u=required_qty(connection, "ratedU", voltage_unit),
        min_q=min_q,
        max_q=max_q,
        max_fault_current=get_qty(connection, "maxIFault", "pu"),
    )


def get_inverter_unit(connection: cim.PowerElectronicsConnection) -> cim.PowerElectronicsUnit:
    """The connection's one PowerElectronicsUnit (a PhotoVoltaicUnit, a BatteryUnit); none or several raise."""
    units = connection.PowerElectronicsUnit
    if len(units) != 1:
        raise ValueError(f"{describe(connection)}: has {len(units)} PowerElectronicsUnits; one is read")
    return units[0]


def get_photovoltaic_unit(unit: cim.PhotoVoltaicUnit, active_unit: str = "W", *, sign: str) -> PhotoVoltaicRating:
    """The PV array's p limits in the ``sign`` convention."""
    _check_sign(sign)
    if not isinstance(unit, cim.PhotoVoltaicUnit):
        raise ValueError(f"{describe(unit)}: is not a PhotoVoltaicUnit")
    return PhotoVoltaicRating(*_limits(unit, "minP", "maxP", active_unit, sign))


def get_battery_unit(unit: cim.BatteryUnit, active_unit: str = "W", energy_unit: str = "Wh", *,
                     sign: str) -> BatteryRating:
    """The battery's p limits in the ``sign`` convention, its energies, efficiencies, idling loss and state."""
    _check_sign(sign)
    if not isinstance(unit, cim.BatteryUnit):
        raise ValueError(f"{describe(unit)}: is not a BatteryUnit")
    min_p, max_p = _limits(unit, "minP", "maxP", active_unit, sign)
    return BatteryRating(
        min_p=min_p,
        max_p=max_p,
        rated_e=get_qty(unit, "ratedE", energy_unit),
        stored_e=get_qty(unit, "storedE", energy_unit),
        minimum_e=get_qty(unit, "minimumE", energy_unit),
        charging_efficiency=get_qty(unit, "chargingEfficiency", "percent"),
        discharging_efficiency=get_qty(unit, "dischargingEfficiency", "percent"),
        idling_p=get_qty(unit, "idlingP", active_unit),
        state=unit.batteryState,
    )


def get_machine_rating(machine: cim.SynchronousMachine, apparent_unit: str = "VA", reactive_unit: str = "VAr", *,
                       sign: str, voltage_unit: str = "V") -> MachineRating:
    """The machine's nameplate: ratedS and ratedU (required), its q limits in the ``sign`` convention, and how it
    runs."""
    _check_sign(sign)
    _check_synchronous(machine)
    min_q, max_q = _limits(machine, "minQ", "maxQ", reactive_unit, sign)
    return MachineRating(
        rated_s=required_qty(machine, "ratedS", apparent_unit),
        rated_u=required_qty(machine, "ratedU", voltage_unit),
        rated_power_factor=machine.ratedPowerFactor,
        min_q=min_q,
        max_q=max_q,
        q_percent=get_qty(machine, "qPercent", "percent"),
        reference_priority=machine.referencePriority,
        type=machine.type,
        operating_mode=machine.operatingMode,
        earthing=machine.earthing,
    )


def get_machine_impedance(machine: cim.SynchronousMachine, unit: str = "ohm") -> MachineImpedance:
    """r and the zero- and negative-sequence impedance in ohm, or in pu on the machine's ratedU and ratedS; unset is
    None."""
    if unit not in IMPEDANCE_UNITS:
        raise ValueError(f"unit must be one of {list(IMPEDANCE_UNITS)}, not {unit!r}")
    _check_synchronous(machine)
    return MachineImpedance(*(get_qty(machine, name, unit) for name in MACHINE_IMPEDANCE_ATTRIBUTES))


def _limits(obj, low_attribute: str, high_attribute: str, unit: str, sign: str) -> tuple[float | None, float | None]:
    """``(min, max)`` of a limit pair stored in the generation sign, in the caller's ``sign``."""
    low, high = get_qty(obj, low_attribute, unit), get_qty(obj, high_attribute, unit)
    if low is not None and high is not None and low > high:
        raise ValueError(f"{describe(obj)}: {low_attribute} {low} is above {high_attribute} {high}")
    if sign == "generation":
        return low, high
    return _negated(high), _negated(low)


def _negated(value: float | None) -> float | None:
    """-value, with a zero kept 0.0 (never -0.0)."""
    return None if value is None else 0.0 - value


def _check_sign(sign: str) -> None:
    if sign not in SIGNS:
        raise ValueError(f"sign must be one of {list(SIGNS)}, not {sign!r}")


def _check_synchronous(machine) -> None:
    if not isinstance(machine, cim.SynchronousMachine):
        raise ValueError(f"{describe(machine)}: is not a SynchronousMachine")
