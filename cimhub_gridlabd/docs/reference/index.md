# Conversion reference

What happens to each GridLAB-D class when a `.glm` becomes CIM and when CIM becomes a `.glm`. The pages are lookup
tables, one section per GLM class. For the steps of a conversion see the [user guide](../guide/index.md); for the code
behind it, the [developer docs](../developer/index.md); for the complete design records, the
[import mapping](../CIMTBL_MAPPING.md) and the [export mapping](../EXPORT_MAPPING.md).

The core site documents what the spoke is built on: the [getters](https://pnnl-cim-tools.github.io/CIMHub/core/guide/getters/),
the [`.cimtbl` contract](https://pnnl-cim-tools.github.io/CIMHub/core/developer/cimtbl/), the
[canonical shapes](https://pnnl-cim-tools.github.io/CIMHub/core/developer/shapes/) and its
[reference](https://pnnl-cim-tools.github.io/CIMHub/core/reference/). All CIM names here are cim18v17.

## Which classes convert

Import is the importer's `MAPPING_ORDER` plus the buses and sources it writes first; export is the exporter's
`EXPORT_ORDER`. A GLM class in neither is read by `GlmReader` and never converted. The importer counts it in the master's
`not mapped:` comment, so nothing disappears silently, and the exporter has nothing to write it from.

| GLM class | CIM classes | Import | Export | Page |
|---|---|:---:|:---:|---|
| `module powerflow` `nominal_frequency` | `BaseFrequency` | yes | yes | [buses](buses.md) |
| `node`, `meter` | `ConnectivityNode`, `BaseVoltage` | yes | yes (both come back as `node`) | [buses](buses.md) |
| `triplex_node`, `triplex_meter` | `ConnectivityNode`, `BaseVoltage` | yes | yes (both come back as `triplex_node`) | [buses](buses.md) |
| `substation`, a bus with `bustype SWING` | `EnergySource`, `BasePower` | yes | yes (as a `substation`) | [buses](buses.md) |
| `overhead_line_conductor` | `OverheadWireInfo`, `OperationalLimitSet`, `CurrentLimit` | yes | yes | [lines](lines.md) |
| `underground_line_conductor` | `ConcentricNeutralCableInfo`, `TapeShieldCableInfo` or `OverheadWireInfo` | yes | yes | [lines](lines.md) |
| `triplex_line_conductor` | `OverheadWireInfo` | yes | yes | [lines](lines.md) |
| `line_spacing` | `ConductorDistanceSpacing`, `ConductorDistance` | yes | yes | [lines](lines.md) |
| `line_configuration` | `WireConfiguration`, `WireSequenceConfiguration`; or `PerLengthPhaseImpedance`, `PhaseImpedanceData` | yes | yes | [lines](lines.md) |
| `triplex_line_configuration` | `WireConfiguration`, `WireSequenceConfiguration`, `ConductorDistanceSpacing` | yes | yes | [lines](lines.md) |
| `overhead_line`, `underground_line`, `triplex_line` | `ACLineSegment`, `OperationalLimitSet`, `CurrentLimit` | yes | yes | [lines](lines.md) |
| `switch` | `LoadBreakSwitch` | yes | yes (also every `Switch` class but the three below) | [lines](lines.md) |
| `fuse` | `Fuse` | yes | yes | [lines](lines.md) |
| `recloser` | `Recloser` | yes | yes | [lines](lines.md) |
| `sectionalizer` | `Sectionaliser` | yes | yes | [lines](lines.md) |
| `series_reactor` | `SeriesCompensator` | yes | yes | [lines](lines.md) |
| `transformer_configuration` | `TransformerTankConfiguration`, `TransformerBankConfiguration`, `TransformerTankEnd`, `TransformerLug`, `TransformerWinding` | yes | yes | [transformers](transformers.md) |
| `transformer` | `PowerTransformer`, `TransformerTank`, `PowerTransformerEnd`, `TransformerPhaseEnd` | yes | yes (from a `PowerTransformer`, or an `AutoTransformer` that is not a `VoltageRegulator`) | [transformers](transformers.md) |
| `regulator_configuration` | its values on every unit of the regulators that name it | yes | yes | [transformers](transformers.md) |
| `regulator` | `VoltageRegulator`, `AutoTransformerEnd`, `TransformerMeshImpedance`, `TapChangerControl`, `RatioTapChanger` | yes | yes | [transformers](transformers.md) |
| `load`, `triplex_load`, a `triplex_node`'s `power_1`, `power_2`, `power_12` | `EnergyConsumer`, `LoadResponseCharacteristic` | yes | yes | [loads](loads.md) |
| `capacitor` | `LinearShuntCompensator`, `RegulatingControl` | yes | yes | [loads](loads.md) |
| `player`, `schedule` | `ConformLoadGroup`, `ConformLoadSchedule`, time points in the sidecar tables | yes | yes (with `time_points`) | [loads](loads.md) |
| `inverter`, `solar`, `battery` | `PowerElectronicsConnection`, `PhotoVoltaicUnit`, `BatteryUnit` | yes | yes | [DER](der.md) |
| every other GLM class (`house`, `recorder`, ...) | none | no | no | |

On export a CIM switch of a class other than `Fuse`, `Recloser` and `Sectionaliser` (`LoadBreakSwitch`, `Breaker`,
`Disconnector`, `Jumper`, a plain `Switch`) is a GLM `switch`, since GridLAB-D has no breaker. Conducting equipment of a
class no exporter module writes raises (`no GLM export yet for {...}`), so nothing is dropped silently; a
`BusbarSection` is its node's bus and needs no object.

## How to read a section

Each section starts with the CIM classes and the `.cimtbl` shape a GLM class becomes, then a table of its GLM properties,
its fail-fast rules, what a round trip changes, and a short excerpt copied from a golden file in
`cimhub_gridlabd/tests/atoms/`. A property row has three columns:

| Column | Says |
|---|---|
| property | the GLM property, as the schema names it (`rating.summer.continuous` in a deck is the slot `rating_summer_continuous`) |
| import | what the importer does with it: the field class, and for a copied value the CIM `Class.attribute` and the unit in the `.cimtbl` header |
| export | what the exporter does: how it is written back and which getter it reads |

Properties the mapper does not read, and the exporter does not write, are grouped in one row at the foot of the table.

Excerpts are the golden files' text, with the design-record IDs that the artifact comments carry left out.

### The five field classes (import)

Every property of a mapped GLM class has exactly one of these, and a test checks that the classification covers every
slot of the schema.

| Class | Means |
|---|---|
| copied | the value lands unchanged in a column, with its source unit in the header (`length (ft)`, `rAC50 (ohm/mile)`) |
| mapped | the value goes through a code table, such as `Type A` to `typeA` |
| structural | the value decides rows: one record becomes several rows, or a value sits on one specific row, or it names another object |
| derived | the value is computed by a named, tested function, because CIM has no attribute for the source quantity (`b_from_c`, `radius_from_diameter`, `line_voltage`) |
| untranscribed | CIM has no home for it; it is listed in a comment on the artifact, never dropped silently |

### Export slot kinds

Every slot of a GLM class is listed by the exporter, so nothing is dropped unnoticed. The export column shows one of:

| Kind | Means |
|---|---|
| written | the value comes from a getter and is written |
| unset | CIM cannot hold it, so the slot is left out and GridLAB-D's default applies |
| not mapped | another form of the same data is written instead (the impedance, not its real and imaginary parts) |

### Units and fail-fast

Values are copied in the deck's own units and the unit is in the `.cimtbl` column header; cimtables converts them when it
builds the model. A value written with an inline unit (`length 21 m`) gets that unit in its header, so one artifact holds
a table per unit. On export every getter converts once, through `get_qty`, to the unit the GLM slot declares (`ft`,
`ohm/mile`, `V`, `kVA`). See [Units, bases and signs](https://pnnl-cim-tools.github.io/CIMHub/core/guide/units/) on the
core site.

"Raises" means fail fast: the mapper stops with a `ValueError` that names the class, the object and the rule, and nothing
is guessed. Unknown fields, unmapped enumerations and unresolved references all raise. IDs are quoted, never sanitized,
on import; on export `glm_safe_name` replaces each run of characters GridLAB-D cannot take in a name (whitespace, `.`, `:`,
quotes, `;`, braces, `$`) with `_`, and two objects that land on one name raise. A value the reader kept as an expression
(`LIGHTS*1.2`) in a property a mapper reads raises too, naming the object, file and line.

### Names

On export an object is named by `name_source`: `"name"` (the CIM name), `"mrid"` or `"uri"`; else
`$CIMHUB_NAME_SOURCE`, else `"mrid"`. A model that came from GLM round-trips under `name_source="name"`, and the sections
below assume it.

On import an mRID is a prefix plus the GLM name: `ln_` lines, `sw_` switches, fuses and reclosers, `rx_` series reactors,
`xf_` transformers and regulator units, `xc_` transformer configurations, `xb_` banks, `rc_` regulator controls, `ohc_`,
`ugc_` and `tpc_` conductors, `spc_` spacings, `wc_` and `lc_` configurations, `src_` sources. Buses are the exception: a
bus's mRID is its GLM name, with no prefix.

## Pages

| Page | Covers |
|---|---|
| [Buses, meters and the source](buses.md) | `node`, `meter`, `triplex_node`, `triplex_meter`, `substation` and the swing `EnergySource`; the topology walk that gives buses and BaseVoltages; the master (frequency, containers, feeder head) |
| [Lines, conductors and switches](lines.md) | the three conductor catalogs; `line_spacing`; `line_configuration` and `triplex_line_configuration`; `overhead_line`, `underground_line`, `triplex_line`; `switch`, `fuse`, `recloser`, `sectionalizer`; `series_reactor` |
| [Transformers and regulators](transformers.md) | `transformer_configuration` and `transformer` (connect types, center tap, banks); `regulator_configuration` and `regulator` |
| [Loads, capacitors, players and schedules](loads.md) | `load`, `triplex_load`, ZIP fractions; `capacitor`; `player`; `schedule` |
| [Inverters, solar and batteries](der.md) | `inverter`, `solar`, `battery` |
