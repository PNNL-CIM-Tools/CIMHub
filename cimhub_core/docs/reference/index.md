# Getter reference

Every function in `cimhub_core.getters`, grouped by the CIM concept it reads. A getter takes a cim18v17 object, reads
what CIM holds about it, and returns plain numbers in the units the caller asked for. For a task-oriented tour, see
[Using the getters](../guide/getters.md); to add or change one, see [Writing a getter](../developer/writing-getters.md).

## Conventions

Every getter follows the same rules, so a call on one concept reads like a call on any other.

| Rule | What it means |
|---|---|
| The caller names the unit | `unit`, `impedance_unit`, `voltage_unit`, `power_unit` and similar arguments take a unit string (`'kV'`, `'ohm/km'`, `'MVA'`, `'pu'`, `'percent'`). The result is a plain `float` in that unit; no `CIMUnit` leaves a getter. See [Units, bases and signs](../guide/units.md). |
| Conversion is `get_qty` | Every unit and per-unit conversion goes through `cimtables.graph_write.get_qty`, which picks the base the same way the importers do. A getter never multiplies by `1e3` itself. The one exception is a `RegulatingControl` target, which the profile types as a plain float, not a `CIMUnit`: `get_regulating_control` builds the `CIMUnit` for its mode and calls `.to()`. |
| `NamedTuple` returns | One getter returns all the fields of its concept as a `NamedTuple` (`z.x`, not a bare tuple), so a new field never breaks a caller. |
| `None` means unset | An optional value CIM leaves unset comes back as `None`, never `0.0`. "Not modelled" and "zero" stay distinguishable, and the spoke decides what to write. Two reads do fill in a zero, and say so in their docstrings: `get_shunt_admittance` returns `g = 0.0` when `gPerSection` is unset, and `get_transformer_model` counts an unset end `x` as 0 when it sums the other ends' star `x` into a mesh. |
| Required values raise | A value the getter cannot go on without raises `ValueError` naming the class and mRID: `ACLineSegment 'ln_l2': a per-length impedance needs the line's length`. |
| No defaults for a meaning | Where two readings differ in a model that is not as built, the argument has no default and is keyword-only: `which='actual'` or `'normal'` (switch state, tap position, in service), `sign='load'` or `'generation'` (DER), `sections=` and `voltage=` (shunt Q). |
| Getters are pure | They read and return. They never add objects to the graph or write a computed value back onto a CIM object. |
| cim18v17 only | Paths are the cim18v17 profile's. A getter never reads an electrical `*Info` catalog (`TransformerTankInfo`, `WireSpacingInfo`); it reads the templates (`TransformerTankConfiguration`, `WireConfiguration`, `XYSpacing`). The only `WireInfo` kinds read are the conductor catalog entries (see [Lines and wires](lines.md)). |

The examples on these pages load the public shapes in `cimhub_core/shapes/` with `cimtables.load_model`. In a test,
wrap the loading and the getter calls in `cimhub_core.cimtbl_testing.cim_scope()`, which puts back the profile and
model scope that `load_model` sets process-wide.

```python
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
from cimtables import load_model

from cimhub_core.getters.current_limits import get_current_limits

SHAPES = Path("cimhub_core/src/cimhub_core/shapes")  # from the repo root

network = load_model(SHAPES / "line_by_impedance.cimtbl")
line = next(obj for obj in network.graph[cim.ACLineSegment].values() if obj.mRID == "ln_l1")
print(get_current_limits(line, "A"))
# CurrentLimits(normal=340.0, short_term=None, emergency=600.0)
```

## All getters

Function and module are under `cimhub_core.getters`. The last column is the page that documents it.

| Function | Module | Returns | What it reads | Page |
|---|---|---|---|---|
| `get_line_sequence_impedance` | `line_impedance` | `SequenceImpedance` | A line's whole-line r, x, b, g and zero-sequence values, from lumped values or a per-length source. | [lines](lines.md) |
| `get_line_sequence_impedance_per_length` | `line_impedance` | `SequenceImpedance` | A line's per-length sequence values. | [lines](lines.md) |
| `get_line_phase_impedance_matrix` | `line_impedance` | `PhaseMatrix` | A line's per-length phase matrix in conductor order. | [lines](lines.md) |
| `get_phase_impedance_code` | `line_impedance` | `CodeMatrix` | A `PerLengthPhaseImpedance` on its own, used or not. | [lines](lines.md) |
| `get_sequence_impedance_code` | `line_impedance` | `SequenceImpedance` | A `PerLengthSequenceImpedance` on its own, used or not. | [lines](lines.md) |
| `get_line_code` | `line_impedance` | `PerLengthImpedance \| None` | The line's own `PerLengthImpedance`, else its WireConfiguration's. | [lines](lines.md) |
| `get_line_geometry` | `line_impedance` | `WireConfiguration \| None` | The line's WireConfiguration when it names a `WireSpacing`. | [lines](lines.md) |
| `get_line_conductor_xy` | `spacing` | `tuple[ConductorXY, ...]` | A line's conductor positions, y above ground. | [lines](lines.md) |
| `get_spacing_xy` | `spacing` | `tuple[ConductorXY, ...]` | A spacing's conductor positions in its own frame. | [lines](lines.md) |
| `get_spacing_distances` | `spacing` | `dict[(i, j), float]` | The distance between every pair of conductors of a spacing. | [lines](lines.md) |
| `get_stored_distances` | `spacing` | `StoredDistances` | A spacing's distances and heights as it stores them. | [lines](lines.md) |
| `get_wire_info` | `wire` | `WireValues` | A conductor catalog entry: resistances, gmr, radius, ratings, cable construction. | [lines](lines.md) |
| `get_configuration_wires` | `wire` | `tuple[(int, WireInfo), ...]` | A WireConfiguration's conductors by sequence number. | [lines](lines.md) |
| `get_line_phase_wires` | `wire` | `tuple[(int, WireInfo), ...]` | A line's own per-phase conductors by sequence number. | [lines](lines.md) |
| `get_current_limits` | `current_limits` | `CurrentLimits` | An equipment's normal, short-term and emergency current limits. | [lines](lines.md) |
| `get_asset_info_current_limits` | `current_limits` | `CurrentLimits` | A catalog entry's (a wire's) current limits. | [lines](lines.md) |
| `equipment_limit_sets` | `current_limits` | `list[OperationalLimitSet]` | The limit sets on an equipment and its terminals, each once. | [lines](lines.md) |
| `agreed_limit` | `current_limits` | `float \| None` | The one value of a limit kind; differing values raise. | [lines](lines.md) |
| `get_impedance_table` | `impedance_table` | `tuple[ImpedanceTablePoint, ...]` | An `ImpedanceTapChangerTable`'s points. | [lines](lines.md) |
| `get_earth_resistivity` | `earth` | `EarthData \| None` | A WireConfiguration's earth model and resistivity. | [lines](lines.md) |
| `get_network_earth` | `earth` | `EarthData` | The network's one `EarthResistivity`, for a line with a direct spacing. | [lines](lines.md) |
| `get_transformer_units` | `transformer` | `tuple` | The units `get_transformer_model` reads: a transformer's tanks, else itself. | [transformers](transformers.md) |
| `get_transformer_model` | `transformer` | `TransformerModel` | A transformer's windings, mesh impedance and core, on one power base. | [transformers](transformers.md) |
| `get_tap_steps` | `tap_changer` | `TapSteps` | A ratio tap changer's positions, increment and neutral voltage. | [transformers](transformers.md) |
| `get_phase_tap_steps` | `tap_changer` | `PhaseTapSteps` | A linear phase tap changer's positions and angle per step. | [transformers](transformers.md) |
| `get_tap_ratio` | `tap_changer` | `float` | The turns ratio at a tap position. | [transformers](transformers.md) |
| `get_tap_voltage` | `tap_changer` | `float` | The end's voltage at a tap position. | [transformers](transformers.md) |
| `get_regulating_control` | `control` | `RegulatingSettings` | A `RegulatingControl`'s mode, target, band and monitored terminal. | [transformers](transformers.md) |
| `get_tap_changer_control` | `control` | `TapChangerSettings` | A tap changer's control, delays and line drop compensation. | [transformers](transformers.md) |
| `get_equipment_control` | `control` | `EquipmentControl \| None` | The control of a regulated shunt, machine or inverter. | [transformers](transformers.md) |
| `get_phase_loads` | `load` | `PhaseLoads` | An `EnergyConsumer`'s p and q, total and per phase. | [loads](loads.md) |
| `get_load_response` | `load` | `LoadResponse` | A load's ZIP fractions or voltage exponents. | [loads](loads.md) |
| `device_power` | `phase_power` | `DevicePower` | A device's p and q in total and per phase (loads and DER). | [loads](loads.md) |
| `get_shunt_reactive_power` | `shunt` | `ShuntReactivePower` | A shunt's Q at a named voltage and section count. | [loads](loads.md) |
| `get_shunt_admittance` | `shunt` | `ShuntAdmittance` | A shunt's g and b for the sections in service. | [loads](loads.md) |
| `get_series_compensator` | `series_compensator` | `SeriesCompensatorData` | A series compensator's r, x and varistor. | [loads](loads.md) |
| `get_load_schedule` | `load_schedule` | `LoadSchedule \| None` | A consumer's group and its one schedule. | [loads](loads.md) |
| `get_schedule_points` | `load_schedule` | `SchedulePoints \| None` | A schedule's `RegularTimePoint` rows. | [loads](loads.md) |
| `log_dropped_schedules` | `load_schedule` | `None` | Log the schedule groups an exporter does not write. | [loads](loads.md) |
| `get_device_schedule` | `device_schedule` | `DeviceSchedule \| None` | A device's one `EnergyConnectionSchedule` that has points. | [loads](loads.md) |
| `get_der_output` | `der` | `DerOutput` | An inverter's or machine's p and q in a named sign. | [der](der.md) |
| `get_inverter_rating` | `der` | `InverterRating` | An inverter's nameplate and q limits. | [der](der.md) |
| `get_inverter_unit` | `der` | `PowerElectronicsUnit` | The connection's one `PowerElectronicsUnit`. | [der](der.md) |
| `get_inverter_units` | `der` | `tuple[InverterUnitShare, ...]` | Each unit's share of a connection that has several. | [der](der.md) |
| `get_photovoltaic_unit` | `der` | `PhotoVoltaicRating` | A PV unit's p limits and irradiance. | [der](der.md) |
| `get_photovoltaic_datasheet` | `der` | `PhotoVoltaicDatasheet \| None` | A PV unit's array and panel datasheets. | [der](der.md) |
| `get_inverter_datasheet` | `der` | `InverterDatasheet \| None` | An inverter's datasheet. | [der](der.md) |
| `get_unit_limits` | `der` | `UnitLimits` | A unit's active power limits as `(min, max)`. | [der](der.md) |
| `get_battery_unit` | `der` | `BatteryRating` | A battery's limits, energies, efficiencies and state. | [der](der.md) |
| `get_machine_rating` | `der` | `MachineRating` | A synchronous machine's nameplate and q limits. | [der](der.md) |
| `get_machine_impedance` | `der` | `MachineImpedance` | A synchronous machine's r and zero- and negative-sequence impedance. | [der](der.md) |
| `get_source` | `source` | `Source` | An `EnergySource`'s voltage and impedance. | [der](der.md) |
| `get_terminal_nodes` | `terminals` | `tuple` | Each terminal's connectivity or topological node. | [topology](topology.md) |
| `get_conductor_phases` | `terminals` | `tuple[SinglePhaseKind, ...]` | An equipment's conductors in order. | [topology](topology.md) |
| `get_switch_sides` | `terminals` | `tuple[tuple, tuple]` | A switch's conductors on each side. | [topology](topology.md) |
| `get_terminal_phases` | `terminals` | `tuple[SinglePhaseKind, ...]` | One terminal's conductors. | [topology](topology.md) |
| `phase_code_tokens` | `terminals` | `tuple[SinglePhaseKind, ...]` | A `PhaseCode`'s conductors. | [topology](topology.md) |
| `get_base_voltage` | `base_voltage` | `float` | A node's or equipment's base voltage, line to line or line to neutral. | [topology](topology.md) |
| `get_node_voltage` | `voltage` | `NodeVoltage \| None` | A topological node's solved voltage. | [topology](topology.md) |
| `get_voltage_limits` | `voltage` | `VoltageLimits` | An equipment's voltage limits. | [topology](topology.md) |
| `get_switch_state` | `switch_state` | `bool` | Whether a switch is open, actual or normal. | [topology](topology.md) |
| `get_reclose_delays` | `switch_state` | `tuple[float, ...]` | The delay before each automatic reclosure. | [topology](topology.md) |
| `get_in_service` | `in_service` | `bool \| None` | Whether an equipment is in service, actual or normal. | [topology](topology.md) |
| `get_location_coordinates` | `location` | `LocationCoordinates \| None` | An equipment's and its terminals' location points. | [topology](topology.md) |
| `get_limits_by_type` | `limits_by_type` | `dict[OperationalLimitType, float]` | An equipment's limits of one class, keyed by type. | [topology](topology.md) |

Two helpers in `getters/__init__.py` are what the getters themselves are built from: `describe(obj)` gives
`ClassName 'mRID'` for an error message, and `required_qty(obj, attribute, unit, **bases)` is `get_qty` that raises
when the attribute is unset.

The values CIM has no attribute for (a susceptance from a capacitance, a Kron-reduced matrix) are not in the getters.
They are pure functions in [Derived values](derived.md).
