# What converts

Which DSS classes import and export today. The source of truth is the code: the importer's mappers are listed in
`MAPPING_ORDER` in `importer/dss_to_cimtbl.py` and the exporter modules in `EXPORT_ORDER` in
`exporter/cim_to_dss.py`. The tables below follow those two lists in order. Property-level detail is in the
[import mapping](../CIMTBL_MAPPING.md) and the [export mapping](../EXPORT_MAPPING.md), where every property is
classified. Each class links to the [conversion reference](../reference/index.md) page that describes it.

## Classes that convert

In `MAPPING_ORDER` order, which is the order the importer's `Import`s run: catalogs before the equipment that uses
them.

| DSS class | CIM class (cim18v17) | Import | Export | Reference |
|---|---|:---:|:---:|---|
| `WireData` | `OverheadWireInfo` | yes | yes | [lines](../reference/lines.md) |
| `CNData` | `ConcentricNeutralCableInfo` | yes | yes | [lines](../reference/lines.md) |
| `TSData` | `TapeShieldCableInfo` | yes | yes | [lines](../reference/lines.md) |
| `LineSpacing` | `XYSpacing` (template) | yes | inline in `LineGeometry` | [lines](../reference/lines.md) |
| `LineGeometry` | `WireConfiguration` with a `WireSpacing` | yes | yes | [lines](../reference/lines.md) |
| `LineCode` | `PerLengthPhaseImpedance` (matrix) or `PerLengthSequenceImpedance`, in a template `WireConfiguration` | yes | yes | [lines](../reference/lines.md) |
| `XfmrCode` | `TransformerTankConfiguration` | yes | yes | [transformers](../reference/transformers.md) |
| `Vsource` | `EnergySource` | yes | yes | [sources](../reference/sources.md) |
| `Line` | `ACLineSegment`, or a switch class when `Switch=y` | yes | yes | [lines](../reference/lines.md) |
| `Reactor` | `SeriesCompensator` | yes | yes | [lines](../reference/lines.md) |
| `Transformer` | `PowerTransformer`, `VoltageRegulator` | yes | yes | [transformers](../reference/transformers.md) |
| `RegControl` | `TapChangerControl` on a `RatioTapChanger` | yes | yes | [transformers](../reference/transformers.md) |
| `LoadShape` | `ConformLoadGroup` and `ConformLoadSchedule`, or a device's `EnergyConnectionSchedule` | yes, those named as `yearly` | yes, with time points | [loads](../reference/loads.md) |
| `Load` | `EnergyConsumer` or `ConformLoad`, with a `LoadResponseCharacteristic` | yes | yes | [loads](../reference/loads.md) |
| `Capacitor` | `LinearShuntCompensator` | yes | yes | [loads](../reference/loads.md) |
| `CapControl` | `RegulatingControl` on the compensator | yes | yes | [loads](../reference/loads.md) |
| `PVSystem` | `PowerElectronicsConnection` with a `PhotoVoltaicUnit` | yes | yes | [DER](../reference/der.md) |
| `Storage` | `PowerElectronicsConnection` with a `BatteryUnit` | yes | yes | [DER](../reference/der.md) |
| `Generator` | `SynchronousMachine` | yes | yes | [DER](../reference/der.md) |

The `Line` mapper also reads the controls that switch a line, so they convert with it:

| DSS class | CIM class | Import | Export | Reference |
|---|---|:---:|:---:|---|
| `Fuse` | `Fuse` | yes | yes | [lines](../reference/lines.md) |
| `Recloser` | `Recloser`, with its `RecloseSequence`s | yes | yes | [lines](../reference/lines.md) |
| `SwtControl` | the switch's state | yes | yes | [lines](../reference/lines.md) |

And the deck's settings and coordinates:

| In the deck | CIM | Import | Export | Reference |
|---|---|:---:|:---:|---|
| `New Circuit` | `Substation`, `Feeder` and the circuit's `EnergySource` | yes | yes | [sources](../reference/sources.md) |
| `Set defaultbasefreq` | `BaseFrequency` | yes | yes | [sources](../reference/sources.md) |
| `Set voltagebases` | `BaseVoltage`s: one per bus voltage the topology walk reaches and one per `voltagebases` value, so a base on no bus is kept. On export it is every `BaseVoltage`. | yes | yes | [sources](../reference/sources.md) |
| `Set earthmodel` | `EarthResistivity` of the geometry `WireConfiguration`s; in a deck without geometry, one that no line names | yes | yes | [sources](../reference/sources.md) |
| `BusCoords`, `LatLongCoords` files | `Location`s with `PositionPoint`s | yes | yes | [sources](../reference/sources.md) |

The exporter's modules, in `EXPORT_ORDER`: `vsource`, `wire`, `linecode`, `linegeometry`, `line`, `switch`,
`xfmrcode`, `transformer`, `regcontrol`, `loadshape`, `load`, `capacitor`, `capcontrol`, `pvsystem`, `storage`,
`generator`, `reactor`, `buscoords`.

Notes:

- A `Line` with `Switch=y` imports as a switch. A `Fuse` or `Recloser` that names it as its `SwitchedObj` sets the
  class, and any other switch is a `LoadBreakSwitch`; its `SwtControl` or `Open` command gives the state. On export,
  every switch class other than `Fuse` and `Recloser` comes back as a `LoadBreakSwitch`.
- A regulated `Transformer` with equal winding voltages imports as a `VoltageRegulator`.
- A `Transformer`'s or `XfmrCode`'s `Seasons` and `Ratings` import as one `ApparentPowerLimit` per season (kVA), and
  its `RdcOhms` as each winding's `rDC`; both export back. `normhkVA` and `emerghkVA` are not imported.
- On export, a CIM `AutoTransformer` is written as a DSS `Transformer`.
- A `Line` that names a `Geometry` imports as a `WireConfiguration`, never as a computed impedance matrix, and exports
  back as a `LineGeometry`.
- A `Load` that names a `yearly` shape imports as a `ConformLoad` of that shape's group. `daily` and `duty` are not
  imported, so a load that names only those imports with its base power and no time series.
- The shape's points go to the `time_points` dict (see [Import](import.md#load-shapes-and-time-points)).

## Classes that do not convert

The reader parses every class in the schema. These have no mapper and no exporter, so the importer skips them and
lists each by count in the master's `not mapped:` comment:

| Group | DSS classes |
|---|---|
| Transformers | `AutoTrans`, `GICTransformer` |
| Sources | `Isource`, `GICsource`, `VCCS`, `VSConverter`, `UPFC`, `Generic5` |
| Rotating machines | `IndMach012`, `WindGen` |
| Lines | `GICLine` |
| Controls and dispatch | `InvControl`, `ExpControl`, `StorageController`, `GenDispatcher`, `ESPVLControl`, `UPFCControl`, `Relay`, `PyControl`, `DynamicExp` |
| Meters and faults | `EnergyMeter`, `Monitor`, `Sensor`, `Fault`, `FMonitor` |
| Curves and shapes | `GrowthShape`, `PriceShape`, `TShape`, `XYCurve`, `TCC_Curve`, `Spectrum` |

A `LoadShape` that no `Load`, `PVSystem`, `Storage` or `Generator` names as `yearly` is also not mapped, and the
master's comment counts it (`not mapped: Loadshape 1`).

A deck that uses one of these still imports. What the class would have configured is absent from the CIM network.
For example, a `Load` that names a `daily` load shape imports with its base power and no daily curve.

## Properties that raise

Inside a class that converts, a property can be classified as raising when set. The importer refuses it instead of
dropping it. The ones users meet most are in [Import](import.md#what-raises). The complete list is the classification
table in each section of the [import mapping](../CIMTBL_MAPPING.md); each raising property says in its row what deck
would justify mapping it.

## Export limits

Export is the inverse of the same mappings, with these limits:

- Conducting equipment of a CIM class no exporter module handles raises, naming the class and count.
- Protection settings with no home in cim18v17's protection function blocks (for example `FuseCurve`) are written as
  the engine's default. The [export mapping](../EXPORT_MAPPING.md) marks them `unset`.
- Property-level gaps are marked `not mapped` in the same tables.
- A `NonConformLoad`, a schedule without points and a load group of days by season and day type are written as static
  loads, with one warning.
