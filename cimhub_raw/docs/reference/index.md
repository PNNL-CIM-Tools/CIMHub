# Conversion reference

What happens to each PSS/E RAW v34 table when a `.raw` case becomes CIM and when CIM becomes a `.raw` case. The pages
are lookup tables, one section per RAW table. For the steps of a conversion see the [user guide](../guide/index.md); for
the code behind it, the [developer docs](../developer/index.md); for the complete design records, the
[import mapping](../CIMTBL_MAPPING.md) and the [export mapping](../EXPORT_MAPPING.md).

The core site documents what the spoke is built on: the [getters](https://pnnl-cim-tools.github.io/CIMHub/core/guide/getters/),
the [`.cimtbl` contract](https://pnnl-cim-tools.github.io/CIMHub/core/developer/cimtbl/), the
[canonical shapes](https://pnnl-cim-tools.github.io/CIMHub/core/developer/shapes/), the
[units rules](https://pnnl-cim-tools.github.io/CIMHub/core/guide/units/) and its
[reference](https://pnnl-cim-tools.github.io/CIMHub/core/reference/). All CIM names here are cim18v17.

## How to read these pages

**The five field classes.** The importer classifies every field of every RAW record in one of five ways. A test checks
that the classification covers every field of the schema.

| class | meaning |
|---|---|
| copied | the value lands in one `.cimtbl` column unchanged, in the unit RAW uses, and the unit is in the column header |
| mapped | the value picks something through a code table (a CIM class, an enum, a flag), or sets how other values are read |
| structural | the value is an identifier, a key or a link (a bus number, a substation number, an ID), not a quantity |
| derived | the importer computes the value from RAW fields (a sign flip, a pu voltage times its base), and the formula is on the table comment |
| untranscribed | CIM 18 has no home for it. The value is listed in a comment of the `.cimtbl` document, or the field is dropped and the page says so |

**Units.** A `.cimtbl` column header carries the unit of the RAW value, as in `normalValue (kV)` or `pTolerance (MW)`.
A per-unit value on the system base is written verbatim with the header `(pu system)`; cimtables converts it on the
`BasePower` the master writes first. The importer does no unit math of its own, except the derived pu-times-base values
named in each section. The exporter reads every quantity through a core getter or `cimtables.graph_write.get_qty`,
which returns it in the unit the RAW field uses.

**Raises.** A rule that "raises" is fail fast: the importer or exporter stops with an error that names the record, the
field and the value. Nothing is skipped or guessed. Unknown codes, unresolved references and records the converter
cannot place all raise.

**Defaults.** A blank RAW field is read as `None`. The importer fills it from the schema's default and marks the row
`# defaulted: field=value`, so a default is never silent.

**Section layout.** Each section starts with the CIM classes and `.cimtbl` shape a RAW table becomes, then a table with
one row per RAW field:

| column | says |
|---|---|
| field | the RAW field name, with the schema's Python slot name in backticks where it differs |
| import | the CIM class and attribute it reaches, with the header unit; or `untranscribed`; or `raises when ...` |
| export | how it is written back, and through which getter; or `not exported` |

After the table come the fail-fast rules, what a round trip changes, and a short excerpt copied from a golden file in
`cimhub_raw/tests/goldens/` or from the artifact the importer writes for a hand-built atom in
`cimhub_raw/tests/atoms/`.

## Which tables convert

Import is the importer's `MAPPING_ORDER` plus the equipment-terminal step that follows it and the master document;
export is the exporter's `EXPORT_ORDER`. The phase-2 stubs are the tables whose mapper exists only to fail fast. A RAW
record class that is in none of these is counted in the master's `not mapped:` comment, so nothing disappears silently.

| RAW table | CIM classes | Import | Export | Page |
|---|---|:---:|:---:|---|
| Case identification (IC, SBASE, REV, XFRRAT, NXFRAT, BASFRQ) | `BasePower`, `BaseFrequency`, `GeographicalRegion`, `BaseVoltage` | yes (IC other than 0 raises) | yes | [buses](buses.md) |
| System-wide options (GENERAL, GAUSS, NEWTON, ADJUST, TYSL, SOLVER) | none; THRSHZ steers the substation grouping | untranscribed | no | [buses](buses.md) |
| Rating sets (RATING) | `OperationalLimitType` `olt_rate1` to `olt_rate12` | yes | yes | [buses](buses.md) |
| Bus | `TopologicalNode`, `BusbarSection`, `OperationalLimitSet`, `VoltageLimit`, `SvVoltage`, `Substation` | yes | yes | [buses](buses.md) |
| Zone | `SubGeographicalRegion` | yes | yes | [buses](buses.md) |
| Area interchange | `ControlArea` | yes | yes | [buses](buses.md) |
| Inter-area transfer | none (listed on the `ControlArea` comment) | untranscribed | no | [buses](buses.md) |
| Owner | none | untranscribed | no | [buses](buses.md) |
| Tie flows (MET, METERED, NMETR on a tie) | `TieFlow` | yes | yes | [buses](buses.md) |
| Substation (SUBSTATION block) | `Substation`, `Location`, `PositionPoint`, `CoordinateSystem` | yes | no | [substations](substations.md) |
| Substation node | `ConnectivityNode`, `BusbarSection` (regulated nodes only) | yes | no | [substations](substations.md) |
| Substation switching device | `Switch`, `Breaker`, `Disconnector` | yes | no | [substations](substations.md) |
| Equipment terminal | `Terminal` (an `Update` row) | yes (TYP I, D, V, N, A raise) | no | [substations](substations.md) |
| Branch | `ACLineSegment`, `SeriesCompensator`, `LinearShuntCompensator` (line shunts), `OperationalLimitSet`, `TieFlow` | yes | yes | [branches](branches.md) |
| System switching device | `Switch`, `Breaker`, `Disconnector` | yes | yes | [branches](branches.md) |
| Multi-section line grouping | `Line` | yes | yes | [branches](branches.md) |
| Load | `ConformLoad`, `NonConformLoad`, `LoadResponseCharacteristic`, `LoadArea`, `SubLoadArea`, load groups | yes | yes | [loads](loads.md) |
| Fixed shunt | `LinearShuntCompensator` | yes | yes | [loads](loads.md) |
| Switched shunt | `LinearShuntCompensator` per block, `RegulatingControl` | yes | yes | [loads](loads.md) |
| Generator | `SynchronousMachine`, `GeneratingUnit`, `PowerElectronicsConnection`, `PowerElectronicsUnit`, `RegulatingControl`, a step-up `PowerTransformer` | yes | yes | [generators](generators.md) |
| Transformer | `PowerTransformer`, `PowerTransformerEnd`, `TransformerMeshImpedance`, `RatioTapChanger`, `PhaseTapChangerLinear`, `TapChangerControl` | yes | yes | [transformers](transformers.md) |
| Impedance correction | `ImpedanceTapChangerTable`, `ImpedanceTapChangerTablePoint` | yes | yes | [transformers](transformers.md) |
| Two-terminal DC | `DCLine`, `DCLineSegment`, `DCTopologicalNode`, `CsConverter`, converter `PowerTransformer` | yes | no | [dc](dc.md) |
| VSC DC | `DCLine`, `DCLineSegment`, `DCTopologicalNode`, `VsConverter`, `VsCapabilityCurve` | yes | no | [dc](dc.md) |
| FACTS device | `StaticSynchronousCompensator`, `RegulatingControl` (a shunt-only device; a series element raises) | yes | no | [dc](dc.md) |
| Multi-terminal DC | none | raises | no | [dc](dc.md) |
| GNE device | none | raises | no | [dc](dc.md) |
| Induction machine | none | raises | no | [dc](dc.md) |

"Export no" for the node-breaker rows and the DC rows is the state of the exporter today, not a CIM limit. On export,
conducting equipment of a class no exporter module writes raises (`no RAW export yet for {...}`), so a case with a DC
line or a FACTS device stops instead of losing it. The node-breaker substation data is the exception: see the
[substations page](substations.md).

## Pages

| page | covers |
|---|---|
| [Case, buses, areas and zones](buses.md) | case identification and system-wide data, rating sets, bus, zone, area interchange, inter-area transfer, tie flows, owner |
| [Substations and node-breaker data](substations.md) | the substations the importer synthesizes from buses, SUBSTATION blocks with their nodes, switching devices and equipment terminals |
| [Branches, switches and multi-section lines](branches.md) | branch, system switching device, multi-section line, ratings |
| [Transformers and impedance correction](transformers.md) | two- and three-winding transformers, impedance correction tables |
| [Loads and shunts](loads.md) | load, fixed shunt, switched shunt |
| [Generators](generators.md) | generators, renewables, the implicit step-up transformer |
| [DC lines and FACTS devices](dc.md) | two-terminal DC, VSC DC, FACTS, and the record types that raise |
