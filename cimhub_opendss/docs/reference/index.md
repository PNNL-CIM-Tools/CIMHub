# Conversion reference

What happens to each DSS class when a deck becomes CIM and when CIM becomes a deck. The pages are lookup tables, one
section per DSS class. For the steps of a conversion see the [user guide](../guide/index.md); for the code behind it, the
[developer docs](../developer/index.md); for the complete design records, the
[import mapping](../CIMTBL_MAPPING.md) and the [export mapping](../EXPORT_MAPPING.md).

The core site documents what the spoke is built on: the [getters](https://pnnl-cim-tools.github.io/CIMHub/core/guide/getters/),
the [`.cimtbl` contract](https://pnnl-cim-tools.github.io/CIMHub/core/developer/cimtbl/), the
[canonical shapes](https://pnnl-cim-tools.github.io/CIMHub/core/developer/shapes/) and its
[reference](https://pnnl-cim-tools.github.io/CIMHub/core/reference/). All CIM names here are cim18v17.

## Which classes convert

Import is the `MAPPING_ORDER` of the importer; export is the `EXPORT_ORDER` of the exporter. A DSS class that is in
neither is read by `DssReader` and never converted: the importer counts it in the master's `not mapped:` comment, and
the exporter has nothing to write it from.

| DSS class | CIM classes | Import | Export | Page |
|---|---|:---:|:---:|---|
| `Vsource`, `New Circuit` | `EnergySource` | yes | yes | [sources](sources.md) |
| `Set` options, `Open`, `Close` | `BaseFrequency`, `BaseVoltage`, `EarthResistivity`, `Switch.open` | some | some | [sources](sources.md) |
| buses | `ConnectivityNode`, `BaseVoltage` | yes | yes | [sources](sources.md) |
| `BusCoords`, `LatLongCoords` | `CoordinateSystem`, `Location` | yes | yes | [sources](sources.md) |
| `WireData` | `OverheadWireInfo` | yes | yes | [lines](lines.md) |
| `CNData` | `ConcentricNeutralCableInfo` | yes | yes | [lines](lines.md) |
| `TSData` | `TapeShieldCableInfo` | yes | yes | [lines](lines.md) |
| `LineSpacing` | `XYSpacing`, `XYConductorPosition` | yes | no (inline in `LineGeometry`) | [lines](lines.md) |
| `LineGeometry` | `WireConfiguration`, `WireSequenceConfiguration` | yes | yes | [lines](lines.md) |
| `LineCode` | `PerLengthPhaseImpedance`, `PhaseImpedanceData`, `PerLengthSequenceImpedance`, `WireConfiguration` | yes | yes | [lines](lines.md) |
| `Line` | `ACLineSegment`, `OperationalLimitSet`, `CurrentLimit` | yes | yes | [lines](lines.md) |
| `Line` with `Switch=y`, `Fuse`, `Recloser`, `SwtControl` | `LoadBreakSwitch`, `Fuse`, `Recloser`, `RecloseSequence` | yes | yes | [lines](lines.md) |
| `Reactor` (series) | `SeriesCompensator` | yes | yes | [lines](lines.md) |
| `XfmrCode` | `TransformerTankConfiguration` | yes | yes | [transformers](transformers.md) |
| `Transformer` | `PowerTransformer`, `PowerTransformerEnd`, `TransformerTank`, `VoltageRegulator`, `AutoTransformerEnd` | yes | yes | [transformers](transformers.md) |
| `RegControl` | `TapChangerControl`, `RatioTapChanger` | yes | yes | [transformers](transformers.md) |
| `LoadShape` | `ConformLoadGroup`, `ConformLoadSchedule`, `EnergyConnectionSchedule` | yes (a shape a Load, PVSystem, Storage or Generator names as `yearly`) | yes, with `time_points` | [loads](loads.md) |
| `Load` | `EnergyConsumer`, `ConformLoad`, `LoadResponseCharacteristic` | yes | yes | [loads](loads.md) |
| `Capacitor` | `LinearShuntCompensator` | yes | yes | [loads](loads.md) |
| `CapControl` | `RegulatingControl` | yes | yes | [loads](loads.md) |
| `PVSystem` | `PowerElectronicsConnection`, `PhotoVoltaicUnit` | yes | yes | [der](der.md) |
| `Storage` | `PowerElectronicsConnection`, `BatteryUnit` | yes | yes | [der](der.md) |
| `Generator` | `SynchronousMachine`, `RegulatingControl` | yes | yes | [der](der.md) |
| `InvControl`, `Relay`, meters, faults, other DSS classes | none | no | no | |

A `Fuse`, `Recloser` or `SwtControl` is read by the `Line` mapper, which takes its switch class and state from it, so it
has no part of its own. On export a CIM `AutoTransformer` is written as a `Transformer`, and a switch class other than
`Fuse` and `Recloser` as a `LoadBreakSwitch`. Conducting equipment of a class no exporter module writes raises
(`no DSS export yet for {...}`), so nothing is dropped silently.

## How to read a section

Each section starts with the CIM classes and the `.cimtbl` shape a DSS class becomes, then a table of its DSS properties,
its fail-fast rules, what a round trip changes, and a short excerpt copied from a golden file in
`cimhub_opendss/tests/atoms/`. A property row has three columns:

| Column | Says |
|---|---|
| property | the DSS property, as the schema names it (DSS names are case-insensitive) |
| import | what the importer does with it: the field class, and for a copied value the CIM `Class.attribute` and the unit in the `.cimtbl` header |
| export | what the exporter does: how it is written back and which getter it reads |

Properties the mapper does not read, and the exporter does not write, are grouped in one row at the foot of the table.

### The five field classes (import)

Every property of a mapped DSS class has exactly one of these, and a test checks that the classification covers every
slot of the schema.

| Class | Means |
|---|---|
| copied | the value lands unchanged in a column, with its source unit in the header (`r (ohm/mi)`, `length (ft)`) |
| mapped | the value goes through a code table, such as a DSS `units` word to a header unit |
| structural | the value decides rows: one record becomes several rows, or a value sits on one specific row, or it names another object |
| derived | the value is computed by a named, tested function, because CIM has no attribute for the source quantity (`thevenin_from_short_circuit`, `b_from_c`) |
| untranscribed | CIM has no home for it; it is recorded in a comment on the artifact, never dropped silently |

### Export slot kinds

Every slot of a DSS class is listed by the exporter, so nothing is dropped unnoticed. The export column shows one of three:

| Kind | Means |
|---|---|
| written | the value comes from a getter and is written |
| written by rule | CIM leaves the value unset and DSS needs one; the rule is stated (an unset `C1` is written 0, so the engine's default capacitance never applies) |
| not written | CIM cannot hold it, so the engine's default applies, or another form of the same data is written instead (`C1` for `B1`) |

### Units and fail-fast

Values are copied in the deck's own units and the unit is in the `.cimtbl` column header; cimtables converts them when it
builds the model. A header such as `ohm/{length}` stands for the unit the row states (`ohm/mi`). On export the
getters convert once, through `get_qty`, to the unit DSS expects: lengths in metres, per-length values per metre, voltages
in kV. See [Units, bases and signs](https://pnnl-cim-tools.github.io/CIMHub/core/guide/units/) on the core site.

"Raises" means fail fast: the mapper stops with a `ValueError` that names the class, the object and the rule, and nothing
is guessed. Unknown fields, unmapped enumerations and unresolved references all raise. IDs are quoted, never sanitized,
on import; on export `dss_safe_name` sanitizes a name and two objects that land on one name raise.

### Names on export

Exported objects are named by `name_source`: `"name"` (the CIM name), `"mrid"` or `"uri"`; else `$CIMHUB_NAME_SOURCE`,
else `"mrid"`. The tables say "Names" where a name is written. Under `mrid` a deck's `Line.l1` comes back as `ln_l1`.

## Pages

| Page | Covers |
|---|---|
| [Sources, options and coordinates](sources.md) | `New Circuit` and `Vsource`; `Set defaultbasefreq`, `voltagebases`, `earthmodel`; `Open`; buses and BaseVoltages; `BusCoords` and `LatLongCoords` |
| [Lines, wires and switches](lines.md) | `LineCode`; `WireData`, `CNData`, `TSData`; `LineSpacing`; `LineGeometry`; `Line`; switches with `Fuse`, `Recloser`, `SwtControl`; series `Reactor` |
| [Transformers and regulators](transformers.md) | `XfmrCode`; `Transformer`, including regulators, LTCs and the export of autotransformers; `RegControl` |
| [Loads, capacitors and shapes](loads.md) | `Load`; `Capacitor`; `CapControl`; `LoadShape` |
| [DER and machines](der.md) | `PVSystem`; `Storage`; `Generator` |
