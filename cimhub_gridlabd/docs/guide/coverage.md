# What converts

Which GridLAB-D classes import and export today. The source of truth is the code: the importer's mappers are listed
in `MAPPING_ORDER` in `importer/glm_to_cimtbl.py`, the classes it classifies in `CLASSIFIED` in the same file, and the
exporter's modules in `EXPORT_ORDER` in `exporter/cim_to_glm.py`. The table below follows those lists. Property-level
detail is in the [import mapping](../CIMTBL_MAPPING.md) and the [export mapping](../EXPORT_MAPPING.md), where every
property is classified. Each class links to the [conversion reference](../reference/index.md) page that describes it.

## Classes that convert

The importer writes one `.cimtbl` file per part, named for the class (`overhead_line.cimtbl`), and the master imports
them in this order: catalogs before the equipment that uses them. Two parts come first, `bus.cimtbl` and
`source.cimtbl`, and the core's shared `zip_fractions.cimtbl` (the ZIP load models) follows them. A part with no
objects is not written.

| GLM class | CIM class (cim18v17) | Import | Export | Reference |
|---|---|---|---|---|
| `node` | `ConnectivityNode` | `bus.cimtbl` | `buses` | [buses](../reference/buses.md) |
| `meter` | `ConnectivityNode`: a child bus is its root's node | `bus.cimtbl` | not written | [buses](../reference/buses.md) |
| `triplex_meter` | `ConnectivityNode`: as `meter` | `bus.cimtbl` | not written | [buses](../reference/buses.md) |
| `substation` | `ConnectivityNode`, and the `EnergySource` of the swing bus (a `SWING` node is a source too) | `bus.cimtbl`, `source.cimtbl` | `buses` | [buses](../reference/buses.md) |
| `overhead_line_conductor` | `OverheadWireInfo` | yes | `line` | [lines](../reference/lines.md) |
| `underground_line_conductor` | `ConcentricNeutralCableInfo`, `TapeShieldCableInfo`, or `OverheadWireInfo` when it has neither | yes | `line` | [lines](../reference/lines.md) |
| `triplex_line_conductor` | `OverheadWireInfo` | yes | `line` | [lines](../reference/lines.md) |
| `line_spacing` | `ConductorDistanceSpacing` (template) with `ConductorDistance`s | yes | `line` | [lines](../reference/lines.md) |
| `line_configuration` | `WireConfiguration` with `WireSequenceConfiguration`s (geometry), or `PerLengthPhaseImpedance` in a template `WireConfiguration` (matrix) | yes | `line` | [lines](../reference/lines.md) |
| `triplex_line_configuration` | `WireConfiguration` on a `ConductorDistanceSpacing` derived from its diameters | yes | `line` | [lines](../reference/lines.md) |
| `transformer_configuration` | `TransformerTankConfiguration` | yes | `transformer` | [transformers](../reference/transformers.md) |
| `overhead_line` | `ACLineSegment` by its configuration's `WireConfiguration` | yes | `line` | [lines](../reference/lines.md) |
| `underground_line` | `ACLineSegment` | yes | `line` | [lines](../reference/lines.md) |
| `triplex_line` | `ACLineSegment` | yes | `line` | [lines](../reference/lines.md) |
| `switch` | `LoadBreakSwitch` | yes | `switch` | [lines](../reference/lines.md) |
| `fuse` | `Fuse` | yes | `switch` | [lines](../reference/lines.md) |
| `recloser` | `Recloser` | yes | `switch` | [lines](../reference/lines.md) |
| `series_reactor` | `SeriesCompensator` | yes | `series_reactor` | [lines](../reference/lines.md) |
| `transformer` | `PowerTransformer` with a `TransformerTank` and `PowerTransformerEnd`s | yes | `transformer` | [transformers](../reference/transformers.md) |
| `regulator` | `VoltageRegulator` with `AutoTransformerEnd`s, a `RatioTapChanger` and a `TapChangerControl` | yes | `regulator` | [transformers](../reference/transformers.md) |
| `player` | `ConformLoadGroup` and `ConformLoadSchedule`, with the points in `time_points` | yes | `player` | [loads](../reference/loads.md) |
| `schedule` | `ConformLoadGroup`, and a `ConformLoadSchedule` per `Season` and `DayType` | yes, those a load's base reads | `schedule` | [loads](../reference/loads.md) |
| `load` | `EnergyConsumer`, or `ConformLoad` when its base reads a player or schedule | yes | `load` | [loads](../reference/loads.md) |
| `triplex_load` | `EnergyConsumer` or `ConformLoad`, one for the legs and one for the 240 V part | yes | `load` | [loads](../reference/loads.md) |
| `triplex_node` | `ConnectivityNode` (`bus.cimtbl`), and an `EnergyConsumer` for the power on it | `bus.cimtbl`, `triplex_node.cimtbl` | `buses`; its power as a `triplex_load` | [loads](../reference/loads.md) |
| `capacitor` | `LinearShuntCompensator`, with a `RegulatingControl` for a voltage control | yes | `capacitor` | [loads](../reference/loads.md) |
| `inverter` | `PowerElectronicsConnection` with a `PhotoVoltaicUnit` or `BatteryUnit` | yes | `inverter` | [DER](../reference/der.md) |

Three classes are classified with another class's part and have no file of their own:

| GLM class | CIM class | Import | Export | Reference |
|---|---|---|---|---|
| `regulator_configuration` | the `RatioTapChanger` and `TapChangerControl` of its regulator | in `regulator.cimtbl` | `regulator` | [transformers](../reference/transformers.md) |
| `solar` | the `SolarPanelInfo`, `SolarArrayInfo` and `PhotoVoltaicUnit` of its inverter | in `inverter.cimtbl` | `inverter` | [DER](../reference/der.md) |
| `battery` | the `BatteryInfo` and `BatteryUnit` of its inverter | in `inverter.cimtbl` | `inverter` | [DER](../reference/der.md) |

The exporter's modules, in `EXPORT_ORDER`: `buses`, `line`, `switch`, `series_reactor`, `transformer`, `regulator`,
`player`, `schedule`, `load`, `capacitor`, `inverter`. The `switch` module also writes a `sectionalizer` for a CIM
`Sectionaliser`.

And the deck's settings:

| In the deck | CIM | Import | Export |
|---|---|---|---|
| `module powerflow { nominal_frequency ...; }`, or `#set powerflow::nominal_frequency=...` | `BaseFrequency` | yes; 60 Hz when unset, noted in the master | the module's `nominal_frequency` |
| the buses' voltages | one `BaseVoltage` per distinct bus voltage the topology walk finds | yes | each bus's `nominal_voltage` from its `BaseVoltage` |
| the swing bus | `Substation`, `Feeder`, and the `NormalHeadFeeder` of each link's terminal on it | yes | one `substation` with `bustype SWING` |

Notes:

- A `SWING` bus becomes an `EnergySource` with a stiff default impedance. The exporter writes one swing and does not
  write the source's impedance. Two `EnergySource`s raise.
- A load that reads `<player>.value*K` or `<schedule>*K` imports as a `ConformLoad`. See
  [Players and schedules](time-series.md).
- A plain `triplex_node`'s `power_12` is imported as an `EnergyConsumer`. It exports as a `triplex_load`.
- A regulator with `control_level INDIVIDUAL` (GridLAB-D's default) imports as one single-phase unit per wired phase,
  and a `BANK` regulator as one gang unit. The exporter writes units that the importer split back as one `regulator`.
- A switch, fuse or recloser has one GridLAB-D state, `status`, which is both its `open` and `normalOpen` state. A
  per-phase state that differs from it raises.
- On export, a configuration is written once for each way a line uses it, so one that no equipment uses is not written.

## Classes that do not convert

The reader parses every class in the schema. The classes below have no mapper, so the importer skips them. None has an
exporter module either. The groups follow the schema's modules.

Residential (house and appliances):

| Group | GLM classes |
|---|---|
| The house | `house`, `house_a` |
| Appliances and end uses | `appliance`, `residential_enduse`, `ZIPload`, `lights`, `plugload`, `occupantload`, `clotheswasher`, `dishwasher`, `dryer`, `freezer`, `microwave`, `range`, `refrigerator`, `waterheater` |
| Storage and charging | `thermal_storage`, `evcharger`, `evcharger_det` |

Generators:

| Group | GLM classes |
|---|---|
| Machines | `diesel_dg`, `windturb_dg`, `rectifier` |
| Storage and dynamic inverters | `energy_storage`, `inverter_dyn` |
| Controls | `central_dg_control`, `controller_dg`, `sync_ctrl` |

Powergrid objects:

| Group | GLM classes |
|---|---|
| Dumps and meters | `billdump`, `currdump`, `voltdump`, `impedance_dump`, `jsondump`, `power_metrics`, `emissions` |
| Checks and control | `fault_check`, `sync_check`, `restoration`, `volt_var_control`, `load_tracker` |
| Motors and loads | `motor`, `performance_motor`, `vfd`, `pqload` |
| Links | `series_compensator` |

A type the schema does not have is not parsed at all. The recorders and collectors of the `tape` module are the usual
case: the schema has only `player` from that module. The reader counts the type and reads none of its properties.

### What happens to them on import

A deck that uses one of these still imports. The master's comment lists every GridLAB-D type no mapper read, with
its count, so nothing disappears silently:

```text
not mapped: house 1, recorder 1, schedule 1
```

The count includes the types the schema lacks (`recorder`), and a `schedule` that no load's base reads (a house's).
What the class would have configured is absent from the CIM network: a `house` and its appliances are not loads,
and a `recorder` has no CIM form. The importer reads none of their properties, so an expression such as `LIGHTS*1.2` on one of them does not raise: it
raises only on a class that converts.

## Properties that raise

Inside a class that converts, a property can be classified as raising when set. The importer refuses it instead of
dropping it. The complete list is the classification table in each section of the
[import mapping](../CIMTBL_MAPPING.md); each raising property says in its row what deck would justify mapping it.
Two rules apply to every class:

- A numeric property that holds an expression the reader could not evaluate raises on a converting class, naming the
  object, its file and line and the property. The one exception is a load's `base_power`, which may be
  `<player>.value*K` or `<schedule>*K`.
- A bus's own load accumulators (`constant_power_X` and the like on a `node`) raise: put the load on a `load` object.

## Export limits

Export is the inverse of the same mappings, with these limits:

- Conducting equipment of a CIM class no exporter module handles raises, naming the class and count. A `BusbarSection`
  is the exception: it is its node's bus.
- A CIM property with no GridLAB-D slot is written as GridLAB-D's default. The [export mapping](../EXPORT_MAPPING.md)
  marks each one `unset`. [Round trip](roundtrip.md) lists the differences that follow.
- A `NonConformLoad`, a conform group with no schedule or no points, and a schedule that is not a multiplier are
  written as static loads, with one warning.
