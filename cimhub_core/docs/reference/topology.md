# Topology, voltage and state

These getters answer where equipment connects, what voltage it sits at, what state it is in and where it is drawn.
Most exporters call several of them for every device. Calling conventions are on the [reference index](index.md).

| Getter | Reads | Returns |
|---|---|---|
| [`get_terminal_nodes`](#get_terminal_nodes) | each terminal's node | tuple of nodes |
| [`get_conductor_phases`](#get_conductor_phases) | the equipment's conductors | tuple of `SinglePhaseKind` |
| [`get_terminal_phases`](#get_terminal_phases) | one terminal's conductors | tuple of `SinglePhaseKind` |
| [`get_switch_sides`](#get_switch_sides) | a switch's conductors on each side | pair of tuples |
| [`phase_code_tokens`](#phase_code_tokens) | a `PhaseCode` as conductors | tuple of `SinglePhaseKind` |
| [`get_base_voltage`](#get_base_voltage) | the `BaseVoltage` of a node or equipment | float |
| [`get_node_voltage`](#get_node_voltage) | a node's solved voltage | `NodeVoltage` or `None` |
| [`get_voltage_limits`](#get_voltage_limits) | an equipment's `VoltageLimit`s | `VoltageLimits` |
| [`get_switch_state`](#get_switch_state) | `open` or `normalOpen` | `bool` |
| [`get_reclose_delays`](#get_reclose_delays) | a protected switch's `RecloseSequence`s | tuple of floats |
| [`get_in_service`](#get_in_service) | `inService` or `normallyInService` | `bool` or `None` |
| [`get_location_coordinates`](#get_location_coordinates) | a `Location`'s `PositionPoint`s | `LocationCoordinates` or `None` |
| [`get_limits_by_type`](#get_limits_by_type) | limits of one class, by `OperationalLimitType` | dict |
| [`get_configuration_limits_by_type`](#get_configuration_limits_by_type) | a template's limits of one class, by `OperationalLimitType` | dict |

The examples run public test atoms through the OpenDSS and PSS/E RAW importers and the shape files in core, inside
`cim_scope()`, which restores the profile and model scope that loading a model sets process-wide.

```python
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.base_voltage import get_base_voltage
from cimhub_core.getters.in_service import get_in_service
from cimhub_core.getters.limits_by_type import get_configuration_limits_by_type, get_limits_by_type
from cimhub_core.getters.location import get_location_coordinates
from cimhub_core.getters.switch_state import get_reclose_delays, get_switch_state
from cimhub_core.getters.terminals import (get_conductor_phases, get_switch_sides, get_terminal_nodes,
                                           get_terminal_phases)
from cimhub_core.getters.voltage import get_node_voltage, get_voltage_limits
from cimhub_opendss import DssImporter, DssReader
from cimhub_raw.importer.raw_to_cimtbl import raw_to_cim
from cimhub_raw.raw34_reader import Raw34Reader

SHAPES = Path("cimhub_core/src/cimhub_core/shapes")
DSS_ATOMS = Path("cimhub_opendss/tests/atoms")
RAW_ATOMS = Path("cimhub_raw/tests/atoms")


def dss_network(atom: str):
    path = DSS_ATOMS / atom
    return DssImporter(path.stem).to_cim(DssReader(path).read_all())


def raw_network(atom: str):
    path = RAW_ATOMS / atom
    return raw_to_cim(Raw34Reader(str(path)).read_all(), name=f"{path.stem}_case")


def find(network, cim_class, mrid):
    return next(obj for obj in network.graph[cim_class].values() if obj.mRID == mrid)
```

## Phases and nodes

Phases come from `Terminal.phases`, the unordered `PhaseCode` of the conductors at a terminal. A blank one is CIM's
balanced three-phase default, ABC. Only a line orders its conductors, through `ACLineSegmentPhase.sequenceNumber`,
which is the row and column order of its impedance matrix. Spoke spellings (GridLAB-D `BCN`, OpenDSS `.3.2`) are
built from the tokens in the spoke.

### get_terminal_nodes { #get_terminal_nodes }

```python
get_terminal_nodes(equipment: ConductingEquipment, *, topological: bool = False)
    -> tuple[ConnectivityNode | TopologicalNode, ...]
```

Each terminal's `ConnectivityNode`, or its `TopologicalNode` with `topological=True` (a bus-branch model), in
`Terminal.sequenceNumber` order. Raises `ValueError` when the equipment has no terminals, a terminal has no
`sequenceNumber`, or a terminal has no node of the requested kind. A node-breaker model has no `TopologicalNode`
and a bus-branch model has no `ConnectivityNode`, so the flag must match the model.

```python
with cim_scope():
    network = load_model(SHAPES / "switch.cimtbl")
    recloser = find(network, cim.Recloser, "sw_r1")
    print([node.mRID for node in get_terminal_nodes(recloser)])
# ['n5', 'n8']
```

Called by every spoke: cimhub_opendss, cimhub_gridlabd, cimhub_gdm and cimhub_raw.

### get_conductor_phases { #get_conductor_phases }

```python
get_conductor_phases(equipment: ConductingEquipment) -> tuple[SinglePhaseKind, ...]
```

The equipment's conductors. A line's come in `ACLineSegmentPhase.sequenceNumber` order, for example `(C, B)`.
Every other device's, and a line with no `ACLineSegmentPhase`s, come in PhaseCode order (A, B, C, s1, s2, N). Every terminal must have the same phases; a
transformer's ends differ, so read each end's terminal with [`get_terminal_phases`](#get_terminal_phases). Raises
`ValueError` when the terminals disagree, or when a line's `ACLineSegmentPhase`s are not the conductors at its
terminals.

```python
with cim_scope():
    network = load_model(SHAPES / "switch.cimtbl")
    print([phase.value for phase in get_conductor_phases(find(network, cim.Fuse, "sw_f1"))])
    print([phase.value for phase in get_conductor_phases(find(network, cim.Breaker, "sw_brkr"))])
# ['C']
# ['A', 'B', 'C']
```

Called by cimhub_opendss, cimhub_gridlabd and cimhub_gdm.

### get_terminal_phases { #get_terminal_phases }

```python
get_terminal_phases(terminal: Terminal) -> tuple[SinglePhaseKind, ...]
```

One terminal's conductors in PhaseCode order; a blank `phases` is `(A, B, C)`. Use it for a transformer end or any
equipment whose terminals differ. Called by cimhub_gridlabd and cimhub_gdm.

### get_switch_sides { #get_switch_sides }

```python
get_switch_sides(switch: Switch) -> tuple[tuple[SinglePhaseKind, ...], tuple[SinglePhaseKind, ...]]
```

Side 1's and side 2's conductors, paired by position. A switch whose terminals agree has the same conductors on both
sides. A switch between laterals on different phases (a tie) pairs them through its `SwitchPhase`s,
`phaseSide1` to `phaseSide2`, in side 1's PhaseCode order. The pairs must be exactly the two terminals'
conductors, or `ValueError` is raised.

```python
with cim_scope():
    network = load_model(SHAPES / "switch.cimtbl")
    side1, side2 = get_switch_sides(find(network, cim.Fuse, "sw_f1"))
    print([phase.value for phase in side1], [phase.value for phase in side2])
# ['C'] ['C']
```

Called by cimhub_opendss and cimhub_gridlabd.

### phase_code_tokens { #phase_code_tokens }

```python
phase_code_tokens(code: PhaseCode, owner) -> tuple[SinglePhaseKind, ...]
```

A `PhaseCode`'s conductors in PhaseCode order. `owner` names the object holding the code in the error message
when the code is not a set of conductors A, B, C, s1, s2, N. This is the function the other phase getters call, and
the control getters call it for `monitoredPhase`. No spoke calls it directly.

## Base voltage

### get_base_voltage { #get_base_voltage }

```python
get_base_voltage(obj, unit: str, *, form: str) -> float
```

One rule, CIM's: a `ConnectivityNode` or `ConductingEquipment` contained in a `VoltageLevel` takes
`VoltageLevel.BaseVoltage` and its own association is disregarded. One in any other container (a feeder, a
substation) takes its own. A `TopologicalNode` and a `TransformerEnd` always take their own. There is no walk to a
neighbouring node or connected equipment. A `PowerTransformer` has no `BaseVoltage` (CIM: not used for
transformers), so read each end.

`form=` has no default:

| `form` | Returns |
|---|---|
| `'LL'` | `BaseVoltage.nominalVoltage` as stored, line to line |
| `'LN'` | `nominalVoltage / sqrt(3)`, the three-phase line-to-neutral value |

`'LN'` raises for equipment or a transformer end on a split-phase secondary (s1 or s2), because a 120 V leg is not
LL / sqrt(3); read `'LL'`. A node carries no phases, so its `'LN'` is always LL / sqrt(3). Also raises
`ValueError` for a `form` other than `'LL'` or `'LN'`, an object (or its `VoltageLevel`) with no `BaseVoltage`, a
`BaseVoltage` with no `nominalVoltage`, and a transformer end with no terminal when `'LN'` is asked.

```python
with cim_scope():
    network = dss_network("load/loads.dss")
    delta = find(network, cim.EnergyConsumer, "ld_ca")
    print(get_base_voltage(delta, "kV", form="LL"), round(get_base_voltage(delta, "kV", form="LN"), 4))
    house = find(network, cim.EnergyConsumer, "ld_house")
    print(get_base_voltage(house, "V", form="LL"))
    try:
        get_base_voltage(house, "V", form="LN")
    except ValueError as error:
        print(error)
# 4.16 2.4018
# 240.0
# EnergyConsumer 'ld_house': a split-phase leg voltage is not LL / sqrt(3); read form='LL'
```

Called by cimhub_opendss, cimhub_gridlabd, cimhub_gdm and cimhub_raw.

## Solved voltage and voltage limits

### get_node_voltage { #get_node_voltage }

```python
get_node_voltage(node: TopologicalNode, voltage_unit: str = "V", angle_unit: str = "deg") -> NodeVoltage | None
```

A balanced node's `SvVoltage` is the one with no `phase`. Per-phase `SvVoltage`s (an unbalanced solution) are not
read here. Returns `None` when the node has no balanced `SvVoltage`.

| Field | Meaning |
|---|---|
| `v` | the line-to-line magnitude in `voltage_unit` |
| `angle` | the angle in `angle_unit`, or `None` when the `SvVoltage` has none |

Raises `ValueError` for two balanced `SvVoltage`s on one node, or one with no `v`.

```python
with cim_scope():
    network = raw_network("branch/line_shunts.raw")
    node = find(network, cim.TopologicalNode, "1")
    print(get_node_voltage(node, "kV", "deg"))
# NodeVoltage(v=115.0, angle=0.0)
```

Called by cimhub_raw.

### get_voltage_limits { #get_voltage_limits }

```python
get_voltage_limits(equipment: ConductingEquipment, unit: str = "V") -> VoltageLimits
```

Finds every `OperationalLimitSet` on the equipment and on its terminals, and classifies each `VoltageLimit` by its
`OperationalLimitType`: `durationKind` normal or emergency, `direction` high or low. Limits of one kind must
agree. The result has one field per kind, each `None` when the equipment has no limit of that kind:

| Field | `durationKind` | `direction` |
|---|---|---|
| `normal_high` | normal | high |
| `normal_low` | normal | low |
| `emergency_high` | emergency | high |
| `emergency_low` | emergency | low |

Raises `ValueError` for a limit with no `OperationalLimitType`, a seasonal type, any other duration or direction
(none is read yet), an unset `normalValue`, or two limits of one kind that disagree.

```python
with cim_scope():
    network = raw_network("branch/line_shunts.raw")
    busbar = next(iter(network.graph[cim.BusbarSection].values()))
    limits = get_voltage_limits(busbar, "kV")
    print(round(limits.normal_high, 1), round(limits.normal_low, 1))
# 126.5 103.5
```

Called by cimhub_raw.

## State

### get_switch_state { #get_switch_state }

```python
get_switch_state(switch: Switch, *, which: str) -> bool
```

`True` when the switch is open. `which='actual'` reads `Switch.open`; `which='normal'` reads `Switch.normalOpen`.
There is no default, because the two differ in any model that is not as built. Raises `ValueError` for any other
`which`, or when the chosen attribute is unset; this getter never returns `None`.

```python
with cim_scope():
    network = load_model(SHAPES / "switch.cimtbl")
    for name in ("sw_brkr", "sw_s1"):
        switch = next(obj for objects in network.graph.values() for obj in objects.values() if obj.mRID == name)
        print(name, get_switch_state(switch, which="actual"), get_switch_state(switch, which="normal"))
# sw_brkr False False
# sw_s1 True True
```

Called by cimhub_opendss, cimhub_gridlabd, cimhub_gdm and cimhub_raw.

### get_reclose_delays { #get_reclose_delays }

```python
get_reclose_delays(switch: ProtectedSwitch, time_unit: str = "s") -> tuple[float, ...]
```

The delay before each automatic reclosure, in `recloseStep` order: one per `RecloseSequence`, and an empty tuple
for a switch that does not reclose. The steps must be 1..n and each needs a `recloseDelay`, or `ValueError` is
raised.

```python
with cim_scope():
    network = load_model(SHAPES / "switch.cimtbl")
    print(get_reclose_delays(find(network, cim.Recloser, "sw_r1")))
# (0.5, 2.0)
```

Called by cimhub_opendss.

### get_in_service { #get_in_service }

```python
get_in_service(equipment: Equipment, *, which: str) -> bool | None
```

`which='actual'` reads `Equipment.inService`; `which='normal'` reads `normallyInService`. There is no default, as
for a switch's state. Unlike `get_switch_state`, an unset value is returned as `None` and the spoke decides what its
format assumes. Raises `ValueError` for any other `which`.

```python
with cim_scope():
    network = dss_network("load/loads.dss")
    off = find(network, cim.EnergyConsumer, "ld_off")
    on = find(network, cim.EnergyConsumer, "ld_ca")
    print(get_in_service(off, which="normal"), get_in_service(on, which="normal"), get_in_service(on, which="actual"))
# False True None
```

Called by every spoke.

## Coordinates and limits by type

### get_location_coordinates { #get_location_coordinates }

```python
get_location_coordinates(equipment: ConductingEquipment) -> LocationCoordinates | None
```

A `ConnectivityNode` is not a `PowerSystemResource`, so CIM puts coordinates on the equipment: one `Location` with
`PositionPoint`s in `sequenceNumber` order. The positions are text in CIM and are read as floats in the
`CoordinateSystem`'s own units. `zPosition` is not read.

| Field | Meaning |
|---|---|
| `crs_urn` | the `Location`'s `CoordinateSystem.crsUrn`, or `None` when it has none |
| `points` | `(x, y)` pairs in `sequenceNumber` order |
| `terminals` | each terminal's `(x, y)` in terminal order, or `None` for a device point |

How points pair with terminals:

| Points | Terminals | `terminals` |
|---|---|---|
| one per terminal | n | the points, in order |
| more than two | 2 | the first and last point (a line route) |
| one | several | `None`: a GIS device point (a switch or transformer between its buses); the caller places the buses |

Returns `None` when the equipment has no `Location` or the location has no points. Raises `ValueError` for a point
without a `sequenceNumber`, `xPosition` or `yPosition`, two points with one `sequenceNumber`, any other count of
points than the table's. The equipment's Terminals are counted directly, so a bus-branch model (terminals on `TopologicalNode`s only) works like a node-breaker one.

```python
with cim_scope():
    network = load_model(SHAPES / "location.cimtbl")
    line = find(network, cim.ACLineSegment, "ln_y")
    print(get_location_coordinates(line).terminals)
    device = get_location_coordinates(find(network, cim.SeriesCompensator, "rx_hsb"))
    print(device.points, device.terminals)
# ((200.0, 350.0), (250.0, 300.0))
# ((200.0, 375.0),) None
```

Called by cimhub_opendss.

### get_limits_by_type { #get_limits_by_type }

```python
get_limits_by_type(equipment: ConductingEquipment, limit_class: type, unit: str, *,
                   terminal: Terminal | None = None) -> dict[OperationalLimitType, float]
```

For bus-branch formats that number their ratings by set (PSS/E RAW's RATE1 to RATE12), so a limit is read by its
type rather than by duration. It collects every `limit_class` limit (for example `cim.CurrentLimit` or
`cim.ApparentPowerLimit`) from the `OperationalLimitSet`s on the equipment and its terminals, or only those of
`terminal` when one is named (a transformer's ratings are per winding). It returns each limit's `normalValue` in
`unit`, keyed by its `OperationalLimitType`. An empty dict means the equipment has no limit of that class.

Raises `ValueError` for a `terminal` that is not one of the equipment's, a limit with no `OperationalLimitType`, an
unset `normalValue`, or two limits of one type that disagree.

```python
with cim_scope():
    network = raw_network("branch/line_shunts.raw")
    line = next(iter(network.graph[cim.ACLineSegment].values()))
    ratings = get_limits_by_type(line, cim.ApparentPowerLimit, "MVA")
    print({limit_type.mRID: value for limit_type, value in ratings.items()})
    print(get_limits_by_type(line, cim.CurrentLimit, "A"))
# {'olt_rate1': 100.0, 'olt_rate2': 120.0}
# {}
```

Called by cimhub_opendss (a transformer's seasonal `Ratings`) and cimhub_raw.

### get_configuration_limits_by_type { #get_configuration_limits_by_type }

```python
get_configuration_limits_by_type(configuration: EquipmentConfiguration, limit_class: type,
                                 unit: str) -> dict[OperationalLimitType, float]
```

A template's limits, read as `get_limits_by_type` reads an equipment's: those of the configuration's one
`EquipmentConfiguration.OperationalLimitSet` (a GridAPPS-D extension of cim18v17), for example the seasonal ratings of
a `TransformerTankConfiguration`. An equipment on the template does not inherit them, so `get_limits_by_type` on the
equipment does not return them. An empty dict means the configuration has no limit set, or no limit of that class.

Raises `ValueError` for a limit with no `OperationalLimitType`, an unset `normalValue`, or two limits of one type
that disagree.

```python
with cim_scope():
    network = dss_network("xfmrcode/rated.dss")
    code = find(network, cim.TransformerTankConfiguration, "xc_sub")
    ratings = get_configuration_limits_by_type(code, cim.ApparentPowerLimit, "kVA")
    print({limit_type.mRID: value for limit_type, value in ratings.items()})
    print(get_limits_by_type(find(network, cim.PowerTransformer, "xf_sub"), cim.ApparentPowerLimit, "kVA"))
# {'olt_season1': 22000.0, 'olt_season2': 25000.0}
# {}
```

Called by cimhub_opendss (an XfmrCode's seasonal `Ratings`).
