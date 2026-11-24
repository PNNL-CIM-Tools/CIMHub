# Loads, shunts and compensators

These getters read the equipment that draws or injects power at a node: `EnergyConsumer` loads and their voltage
response, shunt capacitors and reactors, series compensators, and the schedules that vary a load or a device over
time. Calling conventions (keyword-only arguments, unit strings, `None` versus raising) are on the
[reference index](index.md); this page lists only what is specific to each getter.

| Getter | Reads | Returns |
|---|---|---|
| [`get_phase_loads`](#get_phase_loads) | `EnergyConsumer` p, q and its phase children | `PhaseLoads` |
| [`get_load_response`](#get_load_response) | `EnergyConsumer.LoadResponse` | `LoadResponse` |
| [`get_shunt_reactive_power`](#get_shunt_reactive_power) | `LinearShuntCompensator` as Q = b V² n | `ShuntReactivePower` |
| [`get_shunt_admittance`](#get_shunt_admittance) | `LinearShuntCompensator` as g and b | `ShuntAdmittance` |
| [`get_series_compensator`](#get_series_compensator) | `SeriesCompensator` r, x and varistor | `SeriesCompensatorData` |
| [`get_load_schedule`](#get_load_schedule) | a load's `LoadGroup` and its schedule | `LoadSchedule` or `None` |
| [`get_schedule_points`](#get_schedule_points) | a schedule's `RegularTimePoint` rows | `SchedulePoints` or `None` |
| [`log_dropped_schedules`](#log_dropped_schedules) | the loads whose schedules a target skips | one warning |
| [`get_device_schedule`](#get_device_schedule) | an `EnergyConnectionSchedule` and its points | `DeviceSchedule` or `None` |
| [`device_power`](#device_power) | the shared per-phase split behind loads and DER | `DevicePower` |

The examples on this page load a public test atom through the OpenDSS importer. This setup runs once; each example
below runs inside `cim_scope()`, which restores the profile and model scope that loading a model sets process-wide.

```python
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.device_schedule import get_device_schedule
from cimhub_core.getters.load import get_load_response, get_phase_loads
from cimhub_core.getters.load_schedule import get_load_schedule, get_schedule_points, log_dropped_schedules
from cimhub_core.getters.series_compensator import get_series_compensator
from cimhub_core.getters.shunt import get_shunt_admittance, get_shunt_reactive_power
from cimhub_opendss import DssImporter, DssReader

ATOMS = Path("cimhub_opendss/tests/atoms")
SHAPES = Path("cimhub_core/src/cimhub_core/shapes")


def dss_network(atom: str):
    path = ATOMS / atom
    return DssImporter(path.stem, time_points={}).to_cim(DssReader(path).read_all())


def find(network, cim_class, mrid):
    return next(obj for obj in network.graph[cim_class].values() if obj.mRID == mrid)
```

## Rules these getters settle

**Load sign.** Consumption is positive `p`, as CIM stores it. `get_phase_loads` has no `sign=` argument and returns
the stored sign. Generation sign is a choice only for [DER and machines](der.md).

**Per-phase power.** A device's per-phase p and q are its phase children's own values (`EnergyConsumerPhase`) when
every child has them. When no child has a value, the total is split evenly over the device's phase conductors (the
neutral carries none) and `split` is `True`. A device with some valued children and some without raises, as does a
set of children that is not exactly the device's conductors or whose values do not sum to the total
(relative tolerance 1e-6). `get_phase_loads` and the DER output getter share this rule through `device_power`.

**Shunt reactive power.** `Q = bPerSection x V^2 x sections`. The caller names both factors: `sections=` picks the
attribute that holds the count and `voltage=` picks the V. A positive Q is a capacitor's.

| `sections=` | Attribute | Meaning |
|---|---|---|
| `'actual'` | `sections` | sections in service now |
| `'normal'` | `normalSections` | sections in service in the normal state |
| `'maximum'` | `maximumSections` | all installed sections |

| `voltage=` | V is | Use for |
|---|---|---|
| `'nominal'` | `nomU`, the rating `bPerSection` was derived on | formats that state a rating (OpenDSS, GridLAB-D) |
| `'base'` | the equipment's `BaseVoltage` | formats that state B at 1 pu (PSS/E RAW) |

`nomU` is across the unit: line to neutral for one phase conductor, line to line otherwise. The base voltage is read
in the same form, so a single-phase shunt on a 4.16 kV base uses 4.16 / sqrt(3) kV.

**Load groups and schedules.** A `ConformLoad` or `NonConformLoad` points at a `LoadGroup`, and the group holds the
schedules. A conform load follows its group's curve as a multiplier of its own p and q (a GridLAB-D player, an
OpenDSS LoadShape). A non-conform load's group schedule is in power units (`value1Unit`, `value2Unit`). The
schedule carries only the clock (`startTime`, `timeStep`); the points are `RegularTimePoint` rows in the Parquet
sidecar, read through `get_schedule_points`. A device's own p and q over time (a PV array's or a battery's output)
is a different object, the `EnergyConnectionSchedule`, with `EnergyConnectionTimePoint` rows. The sidecar
tables and their writers are covered in [Time series and schedules](../guide/time-points.md).

## get_phase_loads { #get_phase_loads }

```python
get_phase_loads(consumer: EnergyConsumer, active_unit: str = "W", reactive_unit: str = "VAr") -> PhaseLoads
```

Reads `EnergyConsumer.p` and `.q` (both required), the `EnergyConsumerPhase` children, `phaseConnection` and
`grounded`. Units are positional and default to SI. Phases come from the terminal's PhaseCode through
`get_conductor_phases` (see [topology](topology.md)), neutral removed, in PhaseCode order (A, B, C, s1, s2).

`PhaseLoads` fields:

| Field | Meaning |
|---|---|
| `phases` | the phase conductors, no neutral |
| `connection` | `PhaseShuntConnectionKind` (Y, D, ...) or `None` |
| `grounded` | `bool` or `None` |
| `total` | `PhasePower(p, q)` in the caller's units |
| `per_phase` | `{SinglePhaseKind: PhasePower}` in the caller's units |
| `split` | `True`: the total split evenly; `False`: the children's own values |

Raises `ValueError` when `p` or `q` is unset, when the PhaseCode is not a set of conductors, or for the per-phase
cases above. It never returns `None`.

```python
with cim_scope():
    network = dss_network("load/loads.dss")
    loads = get_phase_loads(find(network, cim.EnergyConsumer, "ld_ca"), "kW", "kVAr")
    print([phase.value for phase in loads.phases], loads.connection.value, loads.split)
    print(loads.total)
    print(loads.per_phase[cim.SinglePhaseKind.A])
# ['A', 'C'] D True
# PhasePower(p=170.0, q=82.33475782243494)
# PhasePower(p=85.0, q=41.16737891121747)
```

Called by cimhub_opendss, cimhub_gridlabd, cimhub_gdm and cimhub_raw.

## get_load_response { #get_load_response }

```python
get_load_response(consumer: EnergyConsumer) -> LoadResponse
```

Reads `EnergyConsumer.LoadResponse`, a `LoadResponseCharacteristic`. It has two forms, chosen by
`exponentModel`; the fields of the other form are `None`.

| Field | `exponential=False` (ZIP) | `exponential=True` |
|---|---|---|
| `exponential` | `False` | `True` |
| `p_impedance`, `p_current`, `p_power` | `pConstantImpedance`, `pConstantCurrent`, `pConstantPower` (fractions) | `None` |
| `q_impedance`, `q_current`, `q_power` | `qConstantImpedance`, `qConstantCurrent`, `qConstantPower` (fractions) | `None` |
| `p_exponent`, `q_exponent` | `None` | `pVoltageExponent`, `qVoltageExponent` |

ZIP fractions are returned as stored: zeros stay zeros, nothing is normalised. Each set of three must sum to 1
(relative tolerance 1e-6). Raises `ValueError` when the load has no `LoadResponse`, when `exponentModel` is unset,
when any value the form needs is unset, or when a ZIP set does not sum to 1.

```python
with cim_scope():
    network = dss_network("load/loads.dss")
    constant_current = get_load_response(find(network, cim.EnergyConsumer, "ld_ca"))
    cvr = get_load_response(find(network, cim.EnergyConsumer, "ld_cvr1"))
    print(constant_current.exponential, constant_current.p_current, constant_current.p_power)
    print(cvr.exponential, cvr.p_exponent, cvr.q_exponent)
# False 1.0 0.0
# True 0.8 3.0
```

Called by cimhub_opendss, cimhub_gridlabd, cimhub_gdm and cimhub_raw.

## get_shunt_reactive_power { #get_shunt_reactive_power }

```python
get_shunt_reactive_power(shunt: LinearShuntCompensator, unit: str = "VAr", *, sections: str, voltage: str,
                         voltage_unit: str = "V") -> ShuntReactivePower
```

Reads `bPerSection`, the section count named by `sections=`, and either `nomU` or the base voltage named by
`voltage=` (rules above). `sections=` and `voltage=` have no defaults. `nomQ` is not read.

| Field | Meaning |
|---|---|
| `phases` | the phase conductors, no neutral |
| `connection`, `grounded` | `phaseConnection` and `grounded`, each `None` when unset |
| `voltage` | the V in Q = b V² n, in `voltage_unit` |
| `sections` | the section count used |
| `total` | Q in `unit` |
| `per_phase` | `{SinglePhaseKind: float}`, the total split evenly over the phases |

Raises `ValueError` for a `voltage=` or `sections=` outside the tables above, for a shunt that is not a
`LinearShuntCompensator`, for a set `gPerSection` or any per-phase `bPerSection` (neither is read yet), for an unset
`bPerSection`, `nomU` or section count, and for a missing `BaseVoltage` under `voltage='base'`.

```python
with cim_scope():
    network = dss_network("capacitor/caps.dss")
    shunt = find(network, cim.LinearShuntCompensator, "cap_c3")
    q = get_shunt_reactive_power(shunt, "kVAr", sections="actual", voltage="nominal", voltage_unit="kV")
    print(q.total, q.voltage, q.sections, q.per_phase[cim.SinglePhaseKind.A])
    off = get_shunt_reactive_power(find(network, cim.LinearShuntCompensator, "cap_open"), "kVAr",
                                   sections="actual", voltage="nominal", voltage_unit="kV")
    print(off.total)
# 600.0 4.16 1.0 200.0
# 0.0
```

Called by cimhub_opendss, cimhub_gridlabd and cimhub_gdm.

## get_shunt_admittance { #get_shunt_admittance }

```python
get_shunt_admittance(shunt: LinearShuntCompensator, unit: str = "S", *, sections: str,
                     base_power=None) -> ShuntAdmittance
```

The form for bus-branch formats that write a shunt as G + jB. It returns the conductance and susceptance of the
sections named by `sections=` (`'actual'`, `'normal'` or `'maximum'`): `gPerSection` and `bPerSection` times the
section count.

`unit` is `'S'` for siemens, or `'pu'` for per unit on the shunt's `nomU` and the system base power. The pu form
needs `base_power` (`network.base_power`). `gPerSection` unset reads as 0.0 here, the one place a shunt getter
defaults a value; `bPerSection` is required.

| Field | Meaning |
|---|---|
| `g` | conductance of the sections in service, in `unit` |
| `b` | susceptance of the sections in service, in `unit` |
| `sections` | the section count used |

Raises `ValueError` for a `unit` other than `'S'` or `'pu'`, a `sections=` outside the table above, a shunt that is
not a `LinearShuntCompensator`, a per-phase `bPerSection`, or an unset `bPerSection` or section count. A `'pu'` read
without `base_power` raises from cimtables.

```python
with cim_scope():
    network = dss_network("capacitor/caps.dss")
    shunt = find(network, cim.LinearShuntCompensator, "cap_c3")
    print(get_shunt_admittance(shunt, "S", sections="normal"))
# ShuntAdmittance(g=0.0, b=0.03467085798816568, sections=1)
```

Called by cimhub_raw.

## get_series_compensator { #get_series_compensator }

```python
get_series_compensator(compensator: SeriesCompensator, unit: str = "ohm", *, base_power=None) -> SeriesCompensatorData
```

Reads `r`, `x`, `r0`, `x0` and the varistor attributes. `unit` is `'ohm'` or `'pu'`; `'pu'` is on the compensator's
`BaseVoltage` and `base_power` (`network.base_power`), the same way the line getters read a line (see
[lines and wires](lines.md)).

| Field | Meaning |
|---|---|
| `r`, `x` | positive-sequence resistance and reactance per phase, in `unit`; required |
| `r0`, `x0` | zero-sequence values in `unit`, or `None` |
| `compensator_type` | `CompensatorKind` (capacitor, reactor) or `None` |
| `varistor_present` | `bool` or `None` |
| `varistor_rated_current` | amperes, or `None` |
| `varistor_voltage_threshold` | volts, or `None` |

Raises `ValueError` for an object that is not a `SeriesCompensator`, a `unit` other than `'ohm'` or `'pu'`, or an
unset `r` or `x`.

```python
with cim_scope():
    network = load_model(SHAPES / "series_compensator.cimtbl")
    compensator = next(iter(network.graph[cim.SeriesCompensator].values()))
    data = get_series_compensator(compensator)
    print(data.r, data.x, data.x0, data.compensator_type)
# 0.0 14.798307 14.798307 None
```

Called by cimhub_opendss, cimhub_gridlabd, cimhub_gdm and cimhub_raw.

## get_load_schedule { #get_load_schedule }

```python
get_load_schedule(consumer: EnergyConsumer) -> LoadSchedule | None
```

Follows `ConformLoad -> ConformLoadGroup <- ConformLoadSchedule` (or the `NonConformLoad` equivalents). Returns
`None` for a plain `EnergyConsumer` and for a conform or non-conform load with no group.

| Field | Meaning |
|---|---|
| `conform` | `True`: a `ConformLoad` (the curve is a multiplier); `False`: a `NonConformLoad` (power units) |
| `group` | the `LoadGroup`; kept even when it has no schedule, so its name survives |
| `schedule` | the group's one time series, or `None` |
| `start` | the time series' `startTime`, an ISO 8601 string with its offset, or `None` |
| `step` | the time series' `timeStep` in seconds, or `None` |
| `days` | the group's schedules that belong to a `Season` or `DayType` (a recurring day), sorted by mRID; empty for a time series |

A group has either one time series (a schedule with no `Season` and no `DayType`: an OpenDSS LoadShape or a
GridLAB-D player, counted from its `startTime`) or recurring days (a GridLAB-D schedule). Two time series, or a time
series beside days, raise `ValueError`.

```python
with cim_scope():
    network = dss_network("loadshape/loadshapes.dss")
    found = get_load_schedule(find(network, cim.ConformLoad, "ld_r1"))
    print(found.conform, found.group.mRID, found.schedule.mRID, found.start, found.step)
    print(get_load_schedule(find(network, cim.ConformLoad, "ld_f1")).schedule)
    print(get_load_schedule(find(network, cim.EnergyConsumer, "ld_static")))
# True lg_res ls_res 2020-01-01T01:00:00+00:00 3600.0
# None
# None
```

`ld_f1` has a group but no schedule; `ld_static` is a plain consumer. Called by cimhub_opendss, cimhub_gridlabd
and cimhub_gdm.

## get_schedule_points { #get_schedule_points }

```python
get_schedule_points(schedule: RegularIntervalSchedule, rows_by_schedule: dict) -> SchedulePoints | None
```

Reads one schedule's points from the sidecar. `rows_by_schedule` is `cimhub_core.time_points.rows_by_schedule` of
the `RegularTimePoint` table (`{uri: rows}`), so this module itself needs no pyarrow. Returns `None` when the
schedule has no rows.

| Field | Meaning |
|---|---|
| `value1` | one float per point, `sequenceNumber` 0, 1, ...; a multiplier for a conform load |
| `value2` | one float per point, or `None` when value2 is unset at every point |

Raises `ValueError` when the sequence numbers are not 0, 1, 2, ... in order, when `value1` is unset at any point, or
when `value2` is set at only some points.

```python
from cimhub_core import time_points

with cim_scope():
    time_points_by_class = {}
    path = ATOMS / "loadshape/loadshapes.dss"
    network = DssImporter("loadshapes", time_points=time_points_by_class).to_cim(DssReader(path).read_all())
    rows = time_points.rows_by_schedule(time_points_by_class["RegularTimePoint"])
    schedule = get_load_schedule(find(network, cim.ConformLoad, "ld_r1")).schedule
    print(get_schedule_points(schedule, rows))
# SchedulePoints(value1=[0.5, 0.75, 1.0, 0.8], value2=[0.4, 0.6, 0.9, 0.7])
```

Called by cimhub_opendss, cimhub_gridlabd and cimhub_gdm.

## log_dropped_schedules { #log_dropped_schedules }

```python
log_dropped_schedules(consumers, target: str) -> None
```

For an exporter whose target format writes loads static. It runs `get_load_schedule` on each consumer and emits
one `WARNING` on the `cimhub_core.getters.load_schedule` logger that names the groups with a schedule or days,
sorted by name (the mRID when a group has none). It logs nothing when no load has a schedule, and returns `None`
either way.

```python
import logging

logging.basicConfig(format="%(levelname)s %(message)s")
with cim_scope():
    network = dss_network("loadshape/loadshapes.dss")
    log_dropped_schedules(network.graph[cim.ConformLoad].values(), "PSS/E RAW")
# WARNING PSS/E RAW: the schedules of 3 load group(s) are not exported; their loads are written static: ['com', 'ind', 'res']
```

Called by cimhub_raw.

## get_device_schedule { #get_device_schedule }

```python
get_device_schedule(equipment: EnergyConnection, rows_by_schedule: dict, p_unit: str, q_unit: str, *,
                    sign: str) -> DeviceSchedule | None
```

Reads an `EnergyConnectionSchedule` on a PV system, battery or machine, with its points from the
`EnergyConnectionTimePoint` sidecar rows (`time_points.rows_by_schedule` of that table). `sign=` is `'load'` (as
stored) or `'generation'` (negated), the same as [`get_der_output`](der.md#get_der_output); it has no default. The
sidecar stores p and q in W and VAr in the load sign.

| Field | Meaning |
|---|---|
| `schedule` | the `EnergyConnectionSchedule` |
| `times` | the instant each point takes effect, UTC `datetime`s |
| `step` | the one interval between points in seconds; `None` when the points are unevenly spaced or there is one |
| `p` | list in `p_unit` and the caller's sign, or `None` when the schedule carries no p |
| `q` | list in `q_unit` and the caller's sign, or `None` |

Returns `None` when the equipment has no schedule with rows. Raises `ValueError` for a `sign` other than `'load'` or
`'generation'`, two schedules with points, an `interpolationKind` other than `previous` (a sample holds until the next; unset
reads as `previous`), a p or q column null at only some points, and points with neither p nor q.

```python
with cim_scope():
    time_points_by_class = {}
    path = ATOMS / "loadshape/devices.dss"
    network = DssImporter("devices", time_points=time_points_by_class).to_cim(DssReader(path).read_all())
    rows = time_points.rows_by_schedule(time_points_by_class["EnergyConnectionTimePoint"])
    battery = find(network, cim.PowerElectronicsConnection, "storage_s1")
    found = get_device_schedule(battery, rows, "kW", "kVAr", sign="generation")
    print(found.schedule.mRID, found.step, found.p, found.q)
# storage_s1_yearly 3600.0 [50.0, -50.0, -1.0, 80.0] None
```

Called by cimhub_opendss.

## device_power { #device_power }

```python
device_power(device, children, active_unit: str, reactive_unit: str) -> DevicePower
```

A helper in `cimhub_core.getters.phase_power` (`from cimhub_core.getters.phase_power import device_power`), listed
here because it is where the per-phase rule above lives. `get_phase_loads` and
[`get_der_output`](der.md#get_der_output) are thin wrappers: the load passes its `EnergyConsumerPhase` children and
the inverter its `PowerElectronicsConnectionPhase` children (a machine passes none). Spokes call the wrappers, not
this function. `DevicePower` has the fields `phases`, `total`
(`PhasePower`), `per_phase` and `split`, as `PhaseLoads` without `connection` and `grounded`. `PhasePower` is the
`(p, q)` pair, and `SUM_REL_TOL = 1e-6` is the tolerance of the sum check.
