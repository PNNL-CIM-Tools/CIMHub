# Coverage

Which DSS classes import and export today. The source of truth is the code: the importer's mappers in
`importer/cimtbl/` (listed in `MAPPING_ORDER` in `importer/dss_to_cimtbl.py`) and the exporter modules in
`exporter/` (listed in `EXPORT_ORDER` in `exporter/cim_to_dss.py`). Property-level detail is in the
[import mapping](../CIMTBL_MAPPING.md) and the [export mapping](../EXPORT_MAPPING.md), where every property is
classified.

## Classes that convert

| DSS class | CIM class (cim18v17) | Import | Export |
|---|---|:---:|:---:|
| `Vsource` | `EnergySource` | yes | yes |
| `WireData` | `OverheadWireInfo` | yes | yes |
| `CNData` | `ConcentricNeutralCableInfo` | yes | yes |
| `TSData` | `TapeShieldCableInfo` | yes | yes |
| `LineSpacing` | `XYSpacing` (template) | yes | inline in `LineGeometry` |
| `LineGeometry` | `WireConfiguration` + `WireSpacing` | yes | yes |
| `LineCode` | `PerLengthPhaseImpedance`, `PerLengthSequenceImpedance` | yes | yes |
| `Line` | `ACLineSegment`, or a switch class when `Switch=y` | yes | yes |
| `Fuse`, `Recloser`, `SwtControl` | `Fuse`, `Recloser`, switch state | yes | yes |
| `XfmrCode` | `TransformerTankConfiguration` | yes | yes |
| `Transformer` | `PowerTransformer`, `VoltageRegulator` | yes | yes |
| `RegControl` | `TapChangerControl` on a `RatioTapChanger` | yes | yes |
| `Load` | `EnergyConsumer` (with a `LoadResponse`) | yes | yes |
| `Capacitor` | `LinearShuntCompensator` | yes | yes |
| `CapControl` | `RegulatingControl` on the compensator | yes | yes |
| `PVSystem` | `PowerElectronicsConnection` + `PhotoVoltaicUnit` | yes | yes |
| `Storage` | `PowerElectronicsConnection` + `BatteryUnit` | yes | yes |
| `Generator` | `SynchronousMachine` | yes | yes |
| `Reactor` | `SeriesCompensator` | yes | yes |
| `BusCoords`, `LatLongCoords` files | `Location` | yes | yes |
| `Set` options: circuit, `defaultbasefreq`, `voltagebases`, `earthmodel` | containers, `BaseFrequency`, `BaseVoltage`, `EarthResistivity` | yes | yes |

Notes:

- A `Line` with `Switch=y` imports as a switch; its `Fuse`, `Recloser` or `SwtControl` supplies the class and state.
  On export, every switch class other than `Fuse` and `Recloser` comes back as a `LoadBreakSwitch`.
- A regulated `Transformer` with equal winding voltages imports as a `VoltageRegulator`.
- On export, a CIM `AutoTransformer` is written as a DSS `Transformer`.
- A `Line` that names a `Geometry` imports as a `WireConfiguration`, never as a computed impedance matrix, and exports
  back as a `LineGeometry`. See the repository's `conductor-geometry` skill for the rule.

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
| Shapes and curves | `LoadShape`, `GrowthShape`, `PriceShape`, `TShape`, `XYCurve`, `TCC_Curve`, `Spectrum` |

A deck that uses one of these still imports. What the class would have configured is absent from the CIM network.
For example, a `Load` that names a `daily` load shape imports with its base power and no time series.

## Properties that raise or are skipped

Inside a class that converts, a property can be classified as raising when set. The importer refuses it instead of
dropping it. Examples from the mapping spec:

| Class | Properties | Why |
|---|---|---|
| `Line`, `WireData`, `CNData`, `TSData` | `Seasons`, `Ratings` | An indexed rating array that names no calendar season. |
| `Vsource` | `Z1`, `Z0`, `Z2`, `puZ1`, `puZ0`, `puZ2`, `baseMVA` | No vendored deck uses them. |
| `WireData`, `CNData`, `TSData` | `GMRac` unset, both `radius` and `diam` set | The engine default or the last-set value is not recorded by the reader. |
| `WireData`, `CNData`, `TSData` | `Capradius` | No mapping yet. |
| `CNData` | `SemiconLayer` | No mapping yet. |

The complete list is the classification table in each section of the [import mapping](../CIMTBL_MAPPING.md). Each
raising property says in its row what deck would justify mapping it.

## Export limits

Export is the inverse of the same mappings, with these limits:

- Conducting equipment of a CIM class no exporter module handles raises, naming the class and count.
- Protection settings with no home in cim18v17's protection function blocks (for example `FuseCurve`) are written as
  the engine's default. The [export mapping](../EXPORT_MAPPING.md) marks them `unset`.
- Property-level gaps are marked `not mapped` in the same tables.
