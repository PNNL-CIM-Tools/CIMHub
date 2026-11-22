"""A DER: an inverter's or a machine's output, its ratings and its unit (skill `export-getters`, semantic rule 2).

CIM's sign is the load's: p and q are positive into the equipment, so generation and discharge are negative. The
caller names the sign it wants: ``'load'`` as stored, ``'generation'`` negated (positive output), so no spoke negates
on its own.

The nameplate limits (``maxQ``/``minQ``, ``maxP``/``minP``, a GeneratingUnit's ``maxOperatingP``/``minOperatingP``)
are written in the generation sign: a PV unit's maxP is its output, a battery's minP its charging (negative).
Every limit pair comes back as ``(min, max)`` in the caller's ``sign``: as stored for ``'generation'``, negated and
swapped for ``'load'``. A minimum above its maximum raises (a producer that wrote the load sign), except a unit's
active power limits (``get_unit_limits``), which come back as stored: a source can hold PB above PT on a unit out of
service, and an exporter maps it as written.
``BatteryUnit.idlingP`` is a loss, "consumed while idling", and is returned as stored in either sign.

``ratedU`` is line to line, as stored (the DSS importer writes a 1-phase wye device's kV x sqrt 3; its exporter
undoes that). ``ratedS`` and ``ratedU`` are required.

CIM lets several PowerElectronicsUnits share one connection (a PV array and a battery behind one inverter); a
format with one DC device per inverter takes each unit's share of it (``get_inverter_units``, the GDM exporter's
rule): the share is the unit's maxP over the units' total, and the connection's ratedS, q and q limits are split by
it. A unit's p is its own (cim18v17's ``PowerElectronicsUnit.p``) when every unit has one, else its share of the
connection's p. ``get_inverter_unit`` is the strict form, one unit only. A wind unit, an AsynchronousMachine and a
machine's short-circuit data (``ikk``, ``mu``, star point earthing), voltage limits and capability curves are not
read.
"""

from __future__ import annotations

import math
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe, required_qty
from cimhub_core.getters.phase_power import SUM_REL_TOL, PhasePower, device_power

SIGNS = ("load", "generation")
IMPEDANCE_UNITS = ("ohm", "pu")
MACHINE_IMPEDANCE_ATTRIBUTES = ("r", "r0", "x0", "r2", "x2")
#: a unit class -> its (minimum, maximum) active power attributes, in the generation sign
UNIT_LIMIT_ATTRIBUTES = {cim.GeneratingUnit: ("minOperatingP", "maxOperatingP"),
                         cim.PowerElectronicsUnit: ("minP", "maxP")}


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


class InverterUnitShare(NamedTuple):
    unit: cim.PowerElectronicsUnit
    share: float  # of the connection's ratedS, q and q limits: the unit's maxP / the units' total (1 for one unit)
    p: float  # active_unit, in the caller's sign: the unit's own p, else share x the connection's p
    q: float  # reactive_unit, in the caller's sign: share x the connection's q (a unit has no q)


class PhotoVoltaicRating(NamedTuple):
    min_p: float | None  # active_unit, in the caller's sign
    max_p: float | None
    irradiance: float | None  # irradiance_unit; the gridappsd extension PhotoVoltaicUnit.irradiance


class PhotoVoltaicDatasheet(NamedTuple):
    """A PV unit's SolarArrayInfo and that array's SolarPanelInfo."""
    tilt: float | None  # angle_unit
    azimuth: float | None  # angle_unit
    shading: float | None  # percent
    panel_efficiency: float | None  # percent; None without a panel
    reference_irradiance: float | None  # irradiance_unit; None without a panel


class InverterDatasheet(NamedTuple):
    """An inverter's GenerationInverterInfo or StorageInverterInfo."""
    apparent_power_max: float | None  # apparent_unit
    reactive_injected_max: float | None  # reactive_unit
    reactive_absorbed_max: float | None  # reactive_unit
    charge_rate_max: float | None  # active_unit; a StorageInverterInfo's only


class UnitLimits(NamedTuple):
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


def get_inverter_units(connection: cim.PowerElectronicsConnection, active_unit: str = "W",
                       reactive_unit: str = "VAr", *, sign: str) -> tuple[InverterUnitShare, ...]:
    """Each PowerElectronicsUnit's share of its connection, in the connection's order. One unit is the whole
    connection (its own p, when set, must be the connection's). Several each need a positive maxP (the share), and
    either every unit has its own p, summing to the connection's, or none has (each takes its share of it)."""
    output = get_der_output(connection, active_unit, reactive_unit, sign=sign)
    units = connection.PowerElectronicsUnit
    if not units:
        raise ValueError(f"{describe(connection)}: has no PowerElectronicsUnit")
    if len(units) == 1:
        shares = [1.0]
    else:
        max_ps = [get_qty(unit, "maxP", active_unit) for unit in units]
        if any(max_p is None or max_p <= 0 for max_p in max_ps):
            raise ValueError(f"{describe(connection)}: its units' maxP {max_ps}; sharing it between several units "
                             f"needs each unit's maxP above 0")
        shares = [max_p / sum(max_ps) for max_p in max_ps]
    own = [get_qty(unit, "p", active_unit) for unit in units]
    if all(p is None for p in own):
        powers = [share * output.total.p for share in shares]
    elif any(p is None for p in own):
        raise ValueError(f"{describe(connection)}: some of its units have p and some do not")
    else:
        powers = own if sign == "load" else [_negated(p) for p in own]
        if not math.isclose(sum(powers), output.total.p, rel_tol=SUM_REL_TOL):
            raise ValueError(f"{describe(connection)}: its units' p sum to {sum(powers)}, not its {output.total.p}")
    return tuple(InverterUnitShare(unit, share, p + 0.0, share * output.total.q + 0.0)
                 for unit, share, p in zip(units, shares, powers))


def get_photovoltaic_unit(unit: cim.PhotoVoltaicUnit, active_unit: str = "W", irradiance_unit: str = "W/m2", *,
                          sign: str) -> PhotoVoltaicRating:
    """The PV array's p limits in the ``sign`` convention and its irradiance."""
    _check_sign(sign)
    if not isinstance(unit, cim.PhotoVoltaicUnit):
        raise ValueError(f"{describe(unit)}: is not a PhotoVoltaicUnit")
    return PhotoVoltaicRating(*_limits(unit, "minP", "maxP", active_unit, sign),
                              irradiance=get_qty(unit, "irradiance", irradiance_unit))


def get_photovoltaic_datasheet(unit: cim.PhotoVoltaicUnit, angle_unit: str = "deg",
                               irradiance_unit: str = "W/m2") -> PhotoVoltaicDatasheet | None:
    """The unit's SolarArrayInfo (its AssetDatasheet) and the array's one SolarPanelInfo; None without an array.
    Another datasheet class or several panels raise."""
    if not isinstance(unit, cim.PhotoVoltaicUnit):
        raise ValueError(f"{describe(unit)}: is not a PhotoVoltaicUnit")
    array = unit.AssetDatasheet
    if array is None:
        return None
    if not isinstance(array, cim.SolarArrayInfo):
        raise ValueError(f"{describe(unit)}: its AssetDatasheet is a {type(array).__name__}, not a SolarArrayInfo")
    if len(array.SolarPanels) > 1:
        raise ValueError(f"{describe(array)}: has {len(array.SolarPanels)} SolarPanelInfos; one is read")
    panel = array.SolarPanels[0] if array.SolarPanels else None
    return PhotoVoltaicDatasheet(
        tilt=get_qty(array, "tiltAngle", angle_unit),
        azimuth=get_qty(array, "orientationAzimuth", angle_unit),
        shading=get_qty(array, "shadingFactor", "percent"),
        panel_efficiency=None if panel is None else get_qty(panel, "efficiency", "percent"),
        reference_irradiance=None if panel is None else get_qty(panel, "referenceIrradiation", irradiance_unit),
    )


def get_inverter_datasheet(connection: cim.PowerElectronicsConnection, apparent_unit: str = "VA",
                           reactive_unit: str = "VAr", active_unit: str = "W") -> InverterDatasheet | None:
    """The connection's GenerationInverterInfo or StorageInverterInfo (its AssetDatasheet); None without one.
    Another datasheet class raises."""
    info = connection.AssetDatasheet
    if info is None:
        return None
    if not isinstance(info, (cim.GenerationInverterInfo, cim.StorageInverterInfo)):
        raise ValueError(f"{describe(connection)}: its AssetDatasheet is a {type(info).__name__}, not an inverter's")
    return InverterDatasheet(
        apparent_power_max=get_qty(info, "apparentPowerMaximum", apparent_unit),
        reactive_injected_max=get_qty(info, "reactivePowerInjectedMax", reactive_unit),
        reactive_absorbed_max=get_qty(info, "reactivePowerAbsorbedMax", reactive_unit),
        charge_rate_max=(get_qty(info, "chargeRateActiveMax", active_unit)
                         if isinstance(info, cim.StorageInverterInfo) else None),
    )


def get_unit_limits(unit: cim.GeneratingUnit | cim.PowerElectronicsUnit, active_unit: str = "W", *,
                    sign: str) -> UnitLimits:
    """A GeneratingUnit's ``minOperatingP``/``maxOperatingP`` or any PowerElectronicsUnit's ``minP``/``maxP``, as
    ``(min, max)`` in the ``sign`` convention, as stored: a minimum above its maximum is returned, not raised (user
    2026-11-09, RAW E3: PB > PT on units out of service)."""
    _check_sign(sign)
    for unit_class, (low, high) in UNIT_LIMIT_ATTRIBUTES.items():
        if isinstance(unit, unit_class):
            return UnitLimits(*_signed(get_qty(unit, low, active_unit), get_qty(unit, high, active_unit), sign))
    raise ValueError(f"{describe(unit)}: is not a GeneratingUnit or a PowerElectronicsUnit")


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
    return _signed(low, high, sign)


def _signed(low: float | None, high: float | None, sign: str) -> tuple[float | None, float | None]:
    """A ``(min, max)`` stored in the generation sign, in the caller's ``sign``: negated and swapped for 'load'."""
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
