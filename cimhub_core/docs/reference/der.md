# Sources, DER and machines

These getters read what puts power into the network: the energy source at the substation, inverter-based resources
(`PowerElectronicsConnection` with its PV and battery units) and synchronous machines. Calling conventions are on the
[reference index](index.md). The sign rules below are the part that differs from every other getter page.

| Getter | Reads | Returns |
|---|---|---|
| [`get_source`](#get_source) | `EnergySource` voltage and Thevenin impedance | `Source` |
| [`get_der_output`](#get_der_output) | p and q of an inverter or a machine | `DerOutput` |
| [`get_inverter_rating`](#get_inverter_rating) | `PowerElectronicsConnection` nameplate | `InverterRating` |
| [`get_inverter_unit`](#get_inverter_unit) | the one `PowerElectronicsUnit` of a connection | the unit |
| [`get_inverter_units`](#get_inverter_units) | each unit's share of a shared connection | tuple of `InverterUnitShare` |
| [`get_photovoltaic_unit`](#get_photovoltaic_unit) | `PhotoVoltaicUnit` limits and irradiance | `PhotoVoltaicRating` |
| [`get_photovoltaic_datasheet`](#get_photovoltaic_datasheet) | `SolarArrayInfo` and `SolarPanelInfo` | `PhotoVoltaicDatasheet` or `None` |
| [`get_inverter_datasheet`](#get_inverter_datasheet) | `GenerationInverterInfo` or `StorageInverterInfo` | `InverterDatasheet` or `None` |
| [`get_unit_limits`](#get_unit_limits) | active power limits of a `GeneratingUnit` or `PowerElectronicsUnit` | `UnitLimits` |
| [`get_battery_unit`](#get_battery_unit) | `BatteryUnit` limits, energy, efficiency, state | `BatteryRating` |
| [`get_machine_rating`](#get_machine_rating) | `SynchronousMachine` nameplate and mode | `MachineRating` |
| [`get_machine_impedance`](#get_machine_impedance) | `SynchronousMachine` r and sequence impedances | `MachineImpedance` |

A device's own schedule over time (a PV array's or battery's output curve) is
[`get_device_schedule`](loads.md#get_device_schedule). Terminal, phase and node lookups are on the
[topology page](topology.md).

The examples run a public test atom through the OpenDSS importer (and one GridLAB-D atom for the datasheets), inside
`cim_scope()`, which restores the profile and model scope that loading a model sets process-wide.

```python
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.der import *
from cimhub_core.getters.source import get_source
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.importer.glm_to_cimtbl import glm_to_cim
from cimhub_opendss import DssImporter, DssReader

DSS_ATOMS = Path("cimhub_opendss/tests/atoms")
GLM_ATOMS = Path("cimhub_gridlabd/tests/atoms")


def dss_network(atom: str):
    path = DSS_ATOMS / atom
    return DssImporter(path.stem).to_cim(DssReader(path).read_all())


def find(network, cim_class, mrid):
    return next(obj for obj in network.graph[cim_class].values() if obj.mRID == mrid)
```

## The sign convention

CIM's terminal sign is the load's: `p` and `q` are positive **into** the equipment. A generator, a PV array and a
discharging battery therefore carry negative `p`. A spoke never negates on its own; it asks the getter for the sign
its format wants with `sign=`, a keyword that has no default:

| `sign=` | p and q returned | Limit pairs returned |
|---|---|---|
| `'load'` | as stored (generation negative) | negated and swapped, so still `(min, max)` |
| `'generation'` | negated (positive output) | as stored |

**Limits.** Nameplate limits (`minQ`/`maxQ`, `minP`/`maxP`, a `GeneratingUnit`'s `minOperatingP`/`maxOperatingP`)
are *written* in the generation sign: a PV unit's `maxP` is its output, a battery's `minP` is its charging power
(negative). Every limit pair comes back as `(min, max)` in the sign you asked for. For `'load'` the stored maximum
is negated into the new minimum, and the stored minimum into the new maximum. Zero stays `0.0`, never `-0.0`.

A minimum above its maximum raises `ValueError` (a producer wrote the load sign into a generation-sign field). The
exception is [`get_unit_limits`](#get_unit_limits), which returns the pair as stored.

`BatteryUnit.idlingP` is a loss, "consumed while idling", and is returned as stored in either sign.

**Voltage.** `ratedU` is line to line, as stored.

## get_source { #get_source }

```python
get_source(source: EnergySource, *, angle_unit: str, voltage_unit: str = "V", impedance_unit: str = "ohm",
           base_power=None) -> Source
```

Reads `nominalVoltage` and `voltageMagnitude` (both required), `voltageAngle`, and the Thevenin impedance
`r`, `x`, `r0`, `x0`, `r2`, `x2`. `angle_unit` (`'deg'` or `'rad'`) has no default. `impedance_unit` is `'ohm'` or
`'pu'`; `'pu'` is on the source's `BaseVoltage` and `base_power` (`network.base_power`).

| Field | Meaning |
|---|---|
| `phases` | the source's conductors (`get_conductor_phases`, in PhaseCode order, neutral included if present) |
| `nominal_u` | `nominalVoltage` in `voltage_unit` |
| `magnitude` | `voltageMagnitude` in `voltage_unit` |
| `magnitude_pu` | `magnitude / nominal_u` |
| `angle` | `voltageAngle` in `angle_unit`, or `None` |
| `impedance` | `SourceImpedance(r, x, r0, x0, r2, x2)`, each in `impedance_unit` or `None` when unset |

An unset impedance stays `None`: the spoke decides what its format assumes. Raises `ValueError` for an
`impedance_unit` other than `'ohm'` or `'pu'`, an unset `nominalVoltage` or `voltageMagnitude`, a source with no
terminals, or (from cimtables) `'pu'` without `base_power`.

```python
with cim_scope():
    network = dss_network("vsource/ohms.dss")
    source = get_source(next(iter(network.graph[cim.EnergySource].values())), angle_unit="deg", voltage_unit="kV")
    print(source.nominal_u, source.magnitude_pu, source.angle)
    print(source.impedance.x, source.impedance.r2)
# 4.16 1.0 0.0
# 0.0001 None
```

Called by cimhub_opendss, cimhub_gridlabd and cimhub_gdm.

## get_der_output { #get_der_output }

```python
get_der_output(equipment: PowerElectronicsConnection | RotatingMachine, active_unit: str = "W",
               reactive_unit: str = "VAr", *, sign: str) -> DerOutput
```

Reads `p` and `q` (both required) of an inverter or a machine, in the requested sign. Per-phase values follow the
rule on the [loads page](loads.md#rules-these-getters-settle): an inverter's `PowerElectronicsConnectionPhase`
values when every child has them, otherwise the total split evenly. A machine's phase objects hold no p or q, so a
machine's total is always split evenly.

| Field | Meaning |
|---|---|
| `phases` | the phase conductors, no neutral |
| `connection` | `PhaseShuntConnectionKind` for an inverter; `None` for a machine, which has none in cim18v17 |
| `total` | `PhasePower(p, q)` in the caller's units and sign |
| `per_phase` | `{SinglePhaseKind: PhasePower}` in the caller's units and sign |
| `split` | `True`: the total split evenly; `False`: the children's own values |

Raises `ValueError` for a `sign` other than `'load'` or `'generation'`, for equipment that is neither a
`PowerElectronicsConnection` nor a `RotatingMachine`, and for the per-phase cases on the loads page.

```python
with cim_scope():
    network = dss_network("der/der.dss")
    inverter = find(network, cim.PowerElectronicsConnection, "pv_house")
    print(get_der_output(inverter, "kW", "kVAr", sign="generation").total)
    print(get_der_output(inverter, "kW", "kVAr", sign="load").total)
    print([phase.value for phase in get_der_output(inverter, "kW", "kVAr", sign="load").phases])
# PhasePower(p=4.0, q=0.0)
# PhasePower(p=-4.0, q=0.0)
# ['s1', 's2']
```

Called by cimhub_opendss, cimhub_gridlabd, cimhub_gdm and cimhub_raw.

## get_inverter_rating { #get_inverter_rating }

```python
get_inverter_rating(connection: PowerElectronicsConnection, apparent_unit: str = "VA", reactive_unit: str = "VAr", *,
                    sign: str, voltage_unit: str = "V") -> InverterRating
```

The connection's nameplate: `ratedS` and `ratedU` (both required), `minQ`/`maxQ` in the requested sign, and
`maxIFault`.

| Field | Meaning |
|---|---|
| `rated_s` | `ratedS` in `apparent_unit` |
| `rated_u` | `ratedU` in `voltage_unit`, line to line |
| `min_q`, `max_q` | the q limits as `(min, max)` in `reactive_unit` and the caller's sign, each `None` when unset |
| `max_fault_current` | `maxIFault`, per unit of rated current, or `None` |

Raises `ValueError` for a bad `sign`, an unset `ratedS` or `ratedU`, or a `minQ` above `maxQ`.

```python
with cim_scope():
    network = dss_network("der/der.dss")
    inverter = find(network, cim.PowerElectronicsConnection, "pv_house")
    rating = get_inverter_rating(inverter, "kVA", "kVAr", sign="generation", voltage_unit="kV")
    print(rating.rated_s, round(rating.rated_u, 3), rating.min_q, rating.max_q, round(rating.max_fault_current, 3))
# 5.0 0.208 -5.0 5.0 1.111
```

Called by cimhub_opendss, cimhub_gridlabd, cimhub_gdm and cimhub_raw.

## get_inverter_unit { #get_inverter_unit }

```python
get_inverter_unit(connection: PowerElectronicsConnection) -> PowerElectronicsUnit
```

The connection's one `PowerElectronicsUnit`, a `PhotoVoltaicUnit` or a `BatteryUnit`. This is the strict form: no
unit or several raise `ValueError`. Use [`get_inverter_units`](#get_inverter_units) when several can share a
connection. Called by cimhub_raw.

## get_inverter_units { #get_inverter_units }

```python
get_inverter_units(connection: PowerElectronicsConnection, active_unit: str = "W", reactive_unit: str = "VAr", *,
                   sign: str) -> tuple[InverterUnitShare, ...]
```

CIM lets several units share one connection, a PV array and a battery behind one inverter. A format with one DC
device per inverter takes each unit's share of the connection. The share is the unit's `maxP` over the units' total
`maxP`. `share` is the fraction a spoke applies to the connection's `ratedS` and q limits; the getter itself splits only p and q.

`InverterUnitShare` fields:

| Field | Meaning |
|---|---|
| `unit` | the `PowerElectronicsUnit` |
| `share` | the fraction of the connection (1.0 for a single unit) |
| `p` | the unit's active power in `active_unit` and the caller's sign |
| `q` | `share x` the connection's q in `reactive_unit` and the caller's sign (a unit has no q of its own) |

The units come back in the connection's order. Rules for `p`:

- one unit is the whole connection, and its own `p`, when set, must equal the connection's;
- several units each need a positive `maxP`, which sets the share;
- when every unit has its own `p` (cim18v17's `PowerElectronicsUnit.p`) those are used and must sum to the
  connection's p (relative tolerance 1e-6); when none has, each takes `share x` the connection's p.

Raises `ValueError` for a bad `sign`, a connection with no unit, a missing or non-positive `maxP` among several
units, units where only some have `p`, or a `p` sum that disagrees with the connection.

```python
with cim_scope():
    network = dss_network("der/der.dss")
    shares = get_inverter_units(find(network, cim.PowerElectronicsConnection, "storage_share"), "kW", "kVAr",
                                sign="generation")
    print([(type(item.unit).__name__, item.share, item.p, item.q) for item in shares])
# [('BatteryUnit', 1.0, 50.0, 0.0)]
```

Called by cimhub_opendss, cimhub_gridlabd and cimhub_gdm.

## get_photovoltaic_unit { #get_photovoltaic_unit }

```python
get_photovoltaic_unit(unit: PhotoVoltaicUnit, active_unit: str = "W", irradiance_unit: str = "W/m2", *,
                      sign: str) -> PhotoVoltaicRating
```

| Field | Meaning |
|---|---|
| `min_p`, `max_p` | `minP` and `maxP` as `(min, max)` in `active_unit` and the caller's sign, each `None` when unset |
| `irradiance` | the `irradiance` attribute in `irradiance_unit` (a GridAPPS-D extension), or `None` |

Raises `ValueError` for a bad `sign`, a unit that is not a `PhotoVoltaicUnit`, or `minP` above `maxP`.

```python
with cim_scope():
    network = dss_network("der/der.dss")
    unit = get_inverter_unit(find(network, cim.PowerElectronicsConnection, "pv_house"))
    print(get_photovoltaic_unit(unit, "kW", sign="generation"))
    print(get_photovoltaic_unit(unit, "kW", sign="load"))
# PhotoVoltaicRating(min_p=0.0, max_p=5.0, irradiance=800.0)
# PhotoVoltaicRating(min_p=-5.0, max_p=0.0, irradiance=800.0)
```

Called by cimhub_opendss, cimhub_gridlabd and cimhub_gdm.

## get_photovoltaic_datasheet { #get_photovoltaic_datasheet }

```python
get_photovoltaic_datasheet(unit: PhotoVoltaicUnit, angle_unit: str = "deg",
                           irradiance_unit: str = "W/m2") -> PhotoVoltaicDatasheet | None
```

Reads the unit's `AssetDatasheet`, a `SolarArrayInfo`, and the array's one `SolarPanelInfo`. Returns `None` when the
unit has no datasheet.

| Field | Meaning |
|---|---|
| `tilt`, `azimuth` | `tiltAngle` and `orientationAzimuth` in `angle_unit`, or `None` |
| `shading` | `shadingFactor` in percent, or `None` |
| `panel_efficiency` | the panel's `efficiency` in percent; `None` without a panel |
| `reference_irradiance` | the panel's `referenceIrradiation` in `irradiance_unit`; `None` without a panel |

Raises `ValueError` for a unit that is not a `PhotoVoltaicUnit`, a datasheet that is not a `SolarArrayInfo`, or more
than one panel. Called by cimhub_gridlabd.

## get_inverter_datasheet { #get_inverter_datasheet }

```python
get_inverter_datasheet(connection: PowerElectronicsConnection, apparent_unit: str = "VA",
                       reactive_unit: str = "VAr", active_unit: str = "W") -> InverterDatasheet | None
```

Reads the connection's `AssetDatasheet`, a `GenerationInverterInfo` or a `StorageInverterInfo`. Returns `None` when
there is none; another datasheet class raises `ValueError`. The sign is not a choice here: datasheet values are
magnitudes.

| Field | Meaning |
|---|---|
| `apparent_power_max` | `apparentPowerMaximum` in `apparent_unit`, or `None` |
| `reactive_injected_max` | `reactivePowerInjectedMax` in `reactive_unit`, or `None` |
| `reactive_absorbed_max` | `reactivePowerAbsorbedMax` in `reactive_unit`, or `None` |
| `charge_rate_max` | `chargeRateActiveMax` in `active_unit`; a `StorageInverterInfo` only, otherwise `None` |

```python
with cim_scope():
    path = GLM_ATOMS / "inverter/inverter.glm"
    network = glm_to_cim(GlmReader(path).read_all(), name="inverter_case")
    inverter = find(network, cim.PowerElectronicsConnection, "pv_inv_pv1")
    unit = get_inverter_unit(inverter)
    print(get_inverter_datasheet(inverter, "kVA", "kVAr").apparent_power_max)
    panel = get_photovoltaic_datasheet(unit)
    print(panel.tilt, panel.azimuth, panel.shading, panel.panel_efficiency)
# 10.0
# 45.0 180.0 100.0 20.0
```

Called by cimhub_gridlabd.

## get_unit_limits { #get_unit_limits }

```python
get_unit_limits(unit: GeneratingUnit | PowerElectronicsUnit, active_unit: str = "W", *, sign: str) -> UnitLimits
```

The active power limits of any unit as `UnitLimits(min_p, max_p)`: `minOperatingP`/`maxOperatingP` for a
`GeneratingUnit`, `minP`/`maxP` for a `PowerElectronicsUnit`, each `None` when unset. Unlike the other limit
getters it does **not** raise on a minimum above its maximum. A source such as a PSS/E case can hold PB above PT on
a unit that is out of service, and an exporter maps the pair as written. Raises `ValueError` for a bad `sign` or any
other class.

```python
with cim_scope():
    network = dss_network("der/der.dss")
    unit = get_inverter_unit(find(network, cim.PowerElectronicsConnection, "pv_house"))
    print(get_unit_limits(unit, "kW", sign="load"))
# UnitLimits(min_p=-5.0, max_p=0.0)
```

Called by cimhub_raw.

## get_battery_unit { #get_battery_unit }

```python
get_battery_unit(unit: BatteryUnit, active_unit: str = "W", energy_unit: str = "Wh", *, sign: str) -> BatteryRating
```

| Field | Meaning |
|---|---|
| `min_p`, `max_p` | `minP` (charging, negative in generation sign) and `maxP` as `(min, max)` in the caller's sign |
| `rated_e`, `stored_e`, `minimum_e` | `ratedE`, `storedE`, `minimumE` in `energy_unit` |
| `charging_efficiency`, `discharging_efficiency` | percent |
| `idling_p` | `idlingP` in `active_unit`, as stored in either sign |
| `state` | `BatteryStateKind` (charging, discharging, ...) or `None` |

Every field is `None` when unset. Raises `ValueError` for a bad `sign`, a unit that is not a
`BatteryUnit`, or `minP` above `maxP`.

```python
with cim_scope():
    network = dss_network("der/der.dss")
    battery = get_inverter_unit(find(network, cim.PowerElectronicsConnection, "storage_ess"))
    rating = get_battery_unit(battery, "kW", "kWh", sign="generation")
    print(rating.min_p, rating.max_p, rating.rated_e, rating.charging_efficiency, rating.idling_p)
    print(rating.state.value)
# -250.0 250.0 500.0 90.0 2.5
# discharging
```

Called by cimhub_opendss, cimhub_gridlabd and cimhub_gdm.

## get_machine_rating { #get_machine_rating }

```python
get_machine_rating(machine: SynchronousMachine, apparent_unit: str = "VA", reactive_unit: str = "VAr", *,
                   sign: str, voltage_unit: str = "V") -> MachineRating
```

| Field | Meaning |
|---|---|
| `rated_s`, `rated_u` | `ratedS` in `apparent_unit` and `ratedU` in `voltage_unit` (line to line); both required |
| `rated_power_factor` | `ratedPowerFactor`, or `None` |
| `min_q`, `max_q` | the q limits as `(min, max)` in the caller's sign, each `None` when unset |
| `q_percent` | `qPercent`, a share of a coordinated reactive control, in percent, or `None` |
| `reference_priority` | `referencePriority` or `None` |
| `type` | `SynchronousMachineKind` or `None` |
| `operating_mode` | `SynchronousMachineOperatingMode` or `None` |
| `earthing` | `bool` or `None` |

Raises `ValueError` for a bad `sign`, an object that is not a `SynchronousMachine`, an unset `ratedS` or `ratedU`,
or `minQ` above `maxQ`.

```python
with cim_scope():
    network = dss_network("generator/gens.dss")
    machine = find(network, cim.SynchronousMachine, "gen_delta")
    rating = get_machine_rating(machine, "kVA", "kVAr", sign="generation", voltage_unit="kV")
    print(rating.rated_s, rating.rated_u, rating.type.value, rating.earthing)
    print(get_der_output(machine, "kW", "kVAr", sign="generation").total.p)
# 250.0 0.48 generator False
# 50.0
```

Called by cimhub_opendss and cimhub_raw.

## get_machine_impedance { #get_machine_impedance }

```python
get_machine_impedance(machine: SynchronousMachine, unit: str = "ohm") -> MachineImpedance
```

Reads `r`, `r0`, `x0`, `r2` and `x2`, in ohm or in pu on the machine's own `ratedU` and `ratedS`; an unset value is
`None`. `MachineImpedance` has the fields `r`, `r0`, `x0`, `r2`, `x2`. It has no positive-sequence `x`: cim18v17 has
no machine reactance. Machine short-circuit data (`ikk`, `mu`, star point earthing), voltage limits and capability
curves, wind units and `AsynchronousMachine` are not read by any DER getter.

Raises `ValueError` for a `unit` other than `'ohm'` or `'pu'`, or an object that is not a `SynchronousMachine`.

```python
with cim_scope():
    network = dss_network("generator/gens.dss")
    print(get_machine_impedance(find(network, cim.SynchronousMachine, "gen_delta")))
# MachineImpedance(r=None, r0=None, x0=None, r2=None, x2=None)
```

Called by cimhub_raw.
