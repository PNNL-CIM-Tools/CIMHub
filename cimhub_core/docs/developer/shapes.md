# Canonical shapes

A shape is the one table layout for a CIM family. Spokes differ only in which optional columns they fill and in
the source units they write, never in structure. So two formats' artifacts for the same network compare row by
row, and a getter reads either.

Each shape is a loadable `.cimtbl` example in
[`cimhub_core/src/cimhub_core/shapes/`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_core/src/cimhub_core/shapes).
The file is the spec: read it before writing a mapper. `cimhub_core/tests/test_shapes.py` loads every file under
cim18v17 and checks that each shape is listed in the `cimtbl-shapes` skill. The mappers that emit a shape are
tested against their own goldens ([Testing](testing.md)), and the helpers they use are on
[The .cimtbl import contract](cimtbl.md).

```python
from pathlib import Path
from cimgraph.models import BusBranchModel
from cimtables import load_model
from cimhub_core.cimtbl_testing import cim_scope

shapes = Path("cimhub_core/src/cimhub_core/shapes")
with cim_scope():
    network = load_model(shapes / "load.cimtbl")
    for load in network.graph[network.cim.EnergyConsumer].values():
        print(load.mRID, load.phaseConnection, load.p.to("kW"))
    bus_branch = load_model(shapes / "line_bus_branch.cimtbl", model_cls=BusBranchModel)
    [line] = bus_branch.graph[bus_branch.cim.ACLineSegment].values()
    print(line.mRID, round(float(line.r.to("ohm")), 5))
```

The two bus-branch shapes (`line_bus_branch`, `behind_transformer`) need `model_cls=BusBranchModel`. The rest load
with the default.

## All shapes

| Shape file | Native data | Main classes | Emitted by |
|---|---|---|---|
| [common](#common) | Shared prerequisites | `Substation`, `Feeder`, `BaseVoltage`, `LoadResponseCharacteristic`, `OperationalLimitType` | OpenDSS, GridLAB-D |
| [wire_info](#wire_info) | Wire and cable catalogs | `OverheadWireInfo`, `TapeShieldCableInfo`, `ConcentricNeutralCableInfo` | OpenDSS, GridLAB-D |
| [line_by_impedance](#line_by_impedance) | A line with an impedance code | `PerLengthPhaseImpedance`, `PerLengthSequenceImpedance`, `WireConfiguration`, `ACLineSegment` | OpenDSS, GridLAB-D, GDM |
| [line_by_wire_configuration](#line_by_wire_configuration) | A line by conductor geometry | `XYSpacing`, `WireConfiguration`, `WireSequenceConfiguration`, `ACLineSegment` | OpenDSS, GDM |
| [line_bus_branch](#line_bus_branch) | A line lumped in per unit | `TopologicalNode`, `ACLineSegment` | RAW |
| [transformer_template](#transformer_template) | A 3-phase transformer catalog entry | `TransformerTankConfiguration`, `TransformerTankEnd`, `TransformerWinding`, `TransformerCore` | OpenDSS, GridLAB-D, GDM |
| [transformer_template_1ph](#transformer_template_1ph) | A single-phase center-tapped catalog entry | `TransformerTankConfiguration`, `TransformerLug`, `TransformerWinding` | OpenDSS, GridLAB-D, GDM |
| [transformer_by_template](#transformer_by_template) | A transformer that names a template | `PowerTransformer`, `TransformerTank`, `PowerTransformerEnd`, `TransformerPhaseEnd` | OpenDSS, GridLAB-D, GDM |
| [transformer_by_ends](#transformer_by_ends) | A transformer given as data of its ends | `PowerTransformer`, `PowerTransformerEnd`, `TransformerMeshImpedance` | OpenDSS, RAW |
| [transformer_by_phase_ends](#transformer_by_phase_ends) | A single-phase transformer by coil | `TransformerTank`, `TransformerPhaseEnd`, `TransformerWinding`, `TransformerMeshImpedance` | OpenDSS |
| [transformer_by_tank_impedance](#transformer_by_tank_impedance) | A transformer given as can nameplates (GIS form) | `PowerTransformerEnd`, `TransformerTank` | None yet; the getters read it |
| [regulator](#regulator) | A step-down transformer with a tap changer | `PowerTransformer`, `RatioTapChanger`, `TapChangerControl` | OpenDSS, RAW |
| [voltage_regulator](#voltage_regulator) | A step-voltage regulator | `VoltageRegulator`, `AutoTransformerEnd`, `RatioTapChanger`, `TapChangerControl` | OpenDSS, GridLAB-D, GDM |
| [behind_transformer](#behind_transformer) | Equipment with its own transformer | `PowerTransformer`, `TopologicalNode`, `SynchronousMachine`, `CsConverter` | RAW |
| [load](#load) | A load | `EnergyConsumer`, `EnergyConsumerPhase` | OpenDSS, GridLAB-D, GDM |
| [load_schedule](#load_schedule) | A load that follows a curve | `ConformLoadGroup`, `ConformLoadSchedule`, `ConformLoad`, `NonConformLoad` | OpenDSS, GridLAB-D |
| [shunt](#shunt) | A shunt capacitor with a control | `LinearShuntCompensator`, `RegulatingControl` | OpenDSS, GridLAB-D, GDM, RAW |
| [switch](#switch) | A switching device | `Breaker`, `Fuse`, `LoadBreakSwitch`, `Recloser`, `Disconnector` | OpenDSS, GridLAB-D, GDM, RAW |
| [source](#source) | A source | `EnergySource` | OpenDSS, GridLAB-D, GDM |
| [der](#der) | An inverter-based resource | `PowerElectronicsConnection`, `PhotoVoltaicUnit`, `BatteryUnit` | OpenDSS, GridLAB-D, GDM |
| [synchronous_machine](#synchronous_machine) | A rotating machine on a distribution node | `SynchronousMachine`, `RegulatingControl` | OpenDSS, RAW |
| [series_compensator](#series_compensator) | A series reactor | `SeriesCompensator` | OpenDSS, GridLAB-D, GDM, RAW |
| [location](#location) | Equipment coordinates | `CoordinateSystem`, `PowerSystemResource` (`wkt`) | OpenDSS |

"Emitted by" lists the spokes whose importers write the classes of that shape, checked against their mappers.
GDM is builder-native: it builds the same classes with CIM-Builder and writes no artifact, so its output matches
the shape's classes and columns but not its text. RAW's output for the distribution shapes (`shunt`, `switch`,
`synchronous_machine`, `series_compensator`, `transformer_by_ends`, `regulator`) is the bus-branch form of the same
classes: `bus` columns instead of `node`, and `TopologicalNode`s instead of `ConnectivityNode`s.

## Rules every shape follows

- **Units as written.** The header carries the source unit: `r (ohm/mi)`, `p (kW)`, `x (percent)`,
  `r (pu system)`. Nothing is pre-converted (I2). See [Units](units.md).
- **mRID is a prefix plus the native ID.** The prefix tells the class (`lc_`, `xc_`, `ln_`, `ld_`, `sw_`, ...).
  Source case is kept; only OpenDSS lowercases.
- **Generated, never written:** Terminals (`<equipment>_T<n>`, a transformer end's is `<xf>_T<endNumber>`), phase
  children (`<mRID>_<phase>`), ConnectivityNodes from `node`, `node1`, `node2`, and TopologicalNodes from `bus`,
  `bus1`, `bus2`. A row that refers to a generated Terminal uses that mRID.
- **Declare before reference.** Templates, catalogs and controls come before the rows that name them. The master's
  `Import` order is the dependency order. A reference that would form a cycle (a control on its own equipment's
  terminal) is closed by an `Update` row afterwards.
- **A balanced three-phase device leaves `phases` blank** ([`phases_cell`](cimtbl.md)):
  no per-phase children, and CIM's three-phase default. Lines and transformer ends keep their phases.
- **`TapChanger.step` is a tap position**, never a turns ratio.
- **Identity-only classes** (`PhaseImpedanceData`) have no mRID. They carry an `identifier`, `<parent>_<row><column>`.

## common

`common.cimtbl`: the prerequisites that every instance shape imports.

| Class (mRID) | Columns | Notes |
|---|---|---|
| `Substation` (`sub_shapes`), `Feeder` (`fdr_shapes`) | `name`; a Feeder also `NormalEnergizingSubstation` | The containers that equipment rows name with `EquipmentContainer`. |
| `BaseVoltage` (`bv_<kV>`) | `nominalVoltage (kV)` | Line to line. |
| `LoadResponseCharacteristic` | `exponentModel`, `p/qConstantPower`, `p/qConstantCurrent`, `p/qConstantImpedance` | The three fixed rows `zip_constant_pq`, `zip_constant_z`, `zip_constant_i`, from `cimhub_core.load_response.zip_fractions()` ([`zip_fractions`](cimtbl.md)). |
| `OperationalLimitType` | `name`, `durationKind`, `isInfiniteDuration`, `direction` | `olt_normal` and `olt_emergency`. A rating is an `OperationalLimitSet` with one `CurrentLimit` per type. |

Templates and wire catalogs need none of this.

## wire_info

`wire_info.cimtbl`: wire and cable catalogs. Emitted for OpenDSS `WireData`, `TSData` and `CNData` and GridLAB-D
`*_line_conductor`.

| Class (mRID prefix) | Required | Optional |
|---|---|---|
| `OverheadWireInfo` (`wire_`) | `radius`, `gmr` (in, ft, mm), one resistance (`rDC20 (ohm/kft)`, or `rAC25`, `rAC50`, `rAC75` per length) | `name`, `ratedCurrent (A)` |
| `TapeShieldCableInfo` (`cable_`) | As above | `insulationThickness`, `diameterOverInsulation`, `diameterOverScreen`, `diameterOverJacket`, `tapeThickness`, `tapeLap` (a `PerCent` attribute: unitless, as in the example) |
| `ConcentricNeutralCableInfo` (`cable_`) | As above | `diameterOverNeutral`, `neutralStrandCount`, `neutralStrandRadius`, `neutralStrandGmr`, `neutralStrandRDC20` |

Units are as written. The example holds `radius (in)`, `gmr (in)` and `rAC25 (ohm/mi)`. These are the catalogs of
`line_by_wire_configuration`: a `WireSequenceConfiguration` names them with `WireInfo`.

## line_by_impedance

`line_by_impedance.cimtbl`: a line whose impedance is a per-length matrix or sequence code. There are two forms
(the `wire-configuration` skill has the rule):

| Form | Impedance | Line names |
|---|---|---|
| A named code that lines share (DSS `LineCode`, GLM z-matrix `line_configuration`, a GDM catalog) | `isTemplate=true`, held by a `WireConfiguration` `<lc>_wc` that has no `WireSpacing` | `WireConfiguration=lc_mtx604_wc` |
| A line's own values | `isTemplate=false` | `PerLengthImpedance=ln_l2_lc` |

| Class (mRID) | Required | Optional |
|---|---|---|
| `PerLengthPhaseImpedance` (`lc_`) | `conductorCount`, `isTemplate` | `name`, `calculatedFrequency (Hz)` |
| `PhaseImpedanceData` (`identifier` `<lc>_<row><col>`) | `PhaseImpedance`, `row`, `column` (conductor indices, lower triangle), `r`, `x` (ohm per length) | `b` (nS or uS per length) |
| `PerLengthSequenceImpedance` (`lc_`, or `ln_<line>_lc` for a line's own) | `r`, `x`, `r0`, `x0` (ohm per length), `isTemplate` | `bch`, `b0ch` (nS or uS per length), `calculatedFrequency` |
| `WireConfiguration` (`<lc>_wc`) | `name`, `PerLengthImpedance` | |
| `ACLineSegment` (`ln_`) | `node1`, `node2`, `phases`, `length`, `BaseVoltage`, and `WireConfiguration` or `PerLengthImpedance` | `EquipmentContainer`, and a rating through `OperationalLimitSet` and `CurrentLimit` |

The per-length unit is the source's (`ohm/mi`, `ohm/km`, `nS/mi`). The segment's `length` unit is its own
(`length (ft)`). A matrix row's `row` and `column` are conductor indices, not phases: the line's `phases` order
picks the row.

## line_by_wire_configuration

`line_by_wire_configuration.cimtbl`: a line by geometry. Never substitute an impedance matrix for it.

| Class (mRID) | Required | Optional |
|---|---|---|
| `XYSpacing` (`spc_`) | `isTemplate=true` | `name` |
| `XYConductorPosition` (`<spc>_<n>`) | `XYSpacing`, `sequenceNumber`, `xCoord`, `yCoord` (ft, m), `kind` (`phase`, `neutral`) | |
| `EarthResistivity` (`earth_`) | `earthModelType`, `rho` | `name` |
| `WireConfiguration` (`wc_`) | `WireSpacing` | `numberOfPhases`, `EarthResistivity` |
| `WireSequenceConfiguration` (`<wc>_<n>`) | `WireConfiguration`, `sequenceNumber`, `WireInfo` | |
| `ACLineSegment` (`ln_`) | As `line_by_impedance`, with `WireConfiguration` | |

`rho` is typed `Resistance` in cim18v17, so the header is `rho (ohm)` and the value is ohm-metres. The `WireInfo`
mRIDs come from [wire_info](#wire_info). OpenDSS `LineSpacing` and `LineGeometry` map here, and so do GDM geometry
branches. The shape's own header names GLM `line_spacing` as a source too, but GridLAB-D's importer writes
`ConductorDistanceSpacing` and `ConductorDistance` for a spacing (pairwise distances and heights, never
coordinates), so it does not use `XYSpacing`.

## line_bus_branch

`line_bus_branch.cimtbl`: a line lumped in per unit, for formats whose network is a bus-branch graph (RAW).

| Class (mRID) | Required | Optional |
|---|---|---|
| `BasePower` (`sbase`) | `basePower (MVA)` | |
| `TopologicalNode` (`bus_`) | `BaseVoltage`, `ConnectivityNodeContainer` | `name` |
| `ACLineSegment` (`ln_`) | `bus1`, `bus2`, `r`, `x` (`pu system`), `BaseVoltage` | `phases`, `bch (pu system)` |

`(pu system)` converts on the row's `BaseVoltage` and the model's `BasePower`, which must come first. The example
(`r (pu system)=0.0194` on 115 kV and 100 MVA) loads as 2.56565 ohm. Load it with `model_cls=BusBranchModel`.

## transformer_template

`transformer_template.cimtbl`: a 3-phase catalog entry. TankEnds are for three-phase templates only.

| Class (mRID) | Required | Optional |
|---|---|---|
| `TransformerTankConfiguration` (`xc_`) | | `name`, `percentImpedance`, `percentMagnetizingCurrent`, `noLoadLoss`, `loadLoss` |
| `TransformerTankEnd` (`<xc>_end_<n>`) | `endNumber`, `connectionKind`, `TankConfiguration` | `grounded`, `rground (ohm)`, `xground (ohm)` |
| `TransformerWinding` (`<xc>_wdg_<n>`) | `ratedU`, `baseU`, `ratedS`, `baseS`, `FromTransformerEnd`, `TankConfiguration` | `r (percent)` |
| `TransformerCore` (`<xc>_core`) | `TankConfiguration` | `form` |
| `TransformerMeshImpedance` (`<xc>_mesh_<ij>`) | `FromWinding`, `ToWinding`, `x (percent)` | `r (percent)`, `r0`, `x0` |

A template end has no Terminal and no phases: the instance's `PowerTransformerEnd` carries them. The nameplate
rule: `ratedU` is phase to phase and `ratedS` the normal kVA. `baseU` is the coil voltage (line to line for delta,
line to neutral for wye) and `baseS` the per-phase kVA, which together give the percent-to-ohm basis
`baseU^2 / baseS`. In the example `500 kVA` gives `baseS` 166.667, and `x (percent)` on the mesh is on the From
winding's base.

## transformer_template_1ph

`transformer_template_1ph.cimtbl`: a single-phase can. Every one-phase can uses lugs, never TankEnds. The example
is a center tap (H1 H2 X1 X3 X2).

| Class (mRID) | Required | Optional |
|---|---|---|
| `TransformerTankConfiguration` (`xc_`) | | `name`, `percentMagnetizingCurrent`, `noLoadLoss` |
| `TransformerLug` (`<xc>_lug_<designation>`) | `designation` (IEEE C57.12.70), `sequenceNumber`, `TankConfiguration` | |
| `TransformerWinding` (`<xc>_wdg_<n>`) | `ratedU`, `baseU`, `ratedS`, `baseS`, `FromTransformerLug`, `ToTransformerLug`, `TankConfiguration` | `r (percent)` |
| `TransformerMeshImpedance` (`<xc>_mesh_<ij>`) | `FromWinding`, `ToWinding`, `x (percent)` | |

A lug's `sequenceNumber` names the instance `TransformerPhaseEnd` it lands on: one phase end per phase of each
terminal, end 1 first, neutral last. Several lugs may share one number. `X1` is in phase with `H1` under either
polarity, so `s1 = X1` and `s2 = X3`. Windings run from the polarity end: `H1 to H2`, `X1 to X2` (`s1` to `N`),
`X2 to X3` (`N` to `s2`). A split-phase half is rated `kVA / 2`, and `baseS` is winding 1's kVA on every coil.

## transformer_by_template

`transformer_by_template.cimtbl`: an instance of a template. The ratings and impedances live only in the template.

| Class (mRID) | Required | Optional |
|---|---|---|
| `PowerTransformer` (`xf_`) | | `name`, `vectorGroup`, `EquipmentContainer` |
| `TransformerTank` (`<xf>_tank`) | `PowerTransformer`, `TankConfiguration` | `EquipmentContainer` |
| `PowerTransformerEnd` (`<xf>_<n>`) | `node`, `phases`, `endNumber`, `BaseVoltage`, `PowerTransformer` | `connectionKind`, `grounded` |
| `TransformerPhaseEnd` (`<xf>_<n>_<phase>`) | `endNumber`, `sequenceNumber`, `phase`, `Terminal` | |

With a TankEnd template (`xf_t1` on `xc_xfm1`) the instance's end `n` is the template's end `n`. With a lug template
(`xf_t2` on `xc_ct5`) the instance also has one `TransformerPhaseEnd` per phase of each terminal, on that end's
Terminal (`xf_t2_T1`). `sequenceNumber` runs across the whole transformer, end 1 first, neutral last.

## transformer_by_ends

`transformer_by_ends.cimtbl`: a transformer for formats without catalogs, with ratings as data of each end.

| Class (mRID) | Required | Optional |
|---|---|---|
| `PowerTransformer` (`xf_`) | | `name`, `vectorGroup`, `EquipmentContainer` |
| `PowerTransformerEnd` (`<xf>_<n>`) | `node`, `phases`, `endNumber`, `connectionKind`, `ratedU (kV)`, `ratedS (kVA)`, `r`, `BaseVoltage`, `PowerTransformer` | `grounded`, `rground`, `xground` |
| `TransformerMeshImpedance` (`<xf>_mesh_<ij>`) | `FromTransformerEnd`, `ToTransformerEnd`, `x` | `r` |

`r (percent)` is on the end's own `ratedU^2 / ratedS`. `x (percent)` is on the mesh, on the From end's rating, so
the From end must carry the kVA that the source's percent refers to. Bus-branch formats use `bus` instead of
`node` and `phases`.

## transformer_by_phase_ends

`transformer_by_phase_ends.cimtbl`: a single-phase transformer by coil, for a transformer that names no template
(OpenDSS `Transformer` with `buses=[n1.1.2, house.1.0, house.0.2]`). It has no `TransformerTankEnd`.

| Class (mRID) | Required | Optional |
|---|---|---|
| `PowerTransformerEnd` (`<xf>_<n>`) | `node`, `phases` (`AB`, `s1s2N`), `endNumber`, `BaseVoltage`, `PowerTransformer` | |
| `TransformerTank` (`<xf>_tank`) | `PowerTransformer` | `percentMagnetizingCurrent (percent)`, `noLoadLoss (W)` |
| `TransformerPhaseEnd` (`<xf>_<n>_<phase>`) | `endNumber`, `sequenceNumber`, `phase` | `phaseNeutralU (kV)` |
| `TransformerWinding` (`<xf>_wdg_<n>`) | `ratedU`, `baseU`, `ratedS`, `baseS`, `FromTransformerEnd`, `ToTransformerEnd`, `TransformerTank` | `r (percent)` |
| `TransformerMeshImpedance` (`<xf>_mesh_<ij>`) | `FromWinding`, `ToWinding`, `x (percent)` | |

`sequenceNumber` is unique in the transformer, runs in terminal phase order, and starts with end 1. `phaseNeutralU`
is the coil voltage of a phase-to-neutral coil, 0 on `N`, and is unset on a phase-to-phase coil. A winding's
`From` and `To` are phase ends (`xf_t3_1_A` to `xf_t3_1_B`). `ratedU` is phase to phase (0.24 across the halves of a
split phase, each rated `kVA / 2`), `baseU` the coil voltage, and `baseS` the first winding's kVA on every coil.

## transformer_by_tank_impedance

`transformer_by_tank_impedance.cimtbl`: the form a GIS gives: per can, only its nameplate kVA, percent impedance
and load loss. No importer in this repo writes it yet, but
[`getters/transformer.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_core/src/cimhub_core/getters/transformer.py)
reads it (`_tank_impedance_model`).

| Class (mRID) | Required | Optional |
|---|---|---|
| `PowerTransformerEnd` (`<xf>_<n>`) | `node`, `phases`, `endNumber`, `connectionKind`, `grounded`, `ratedU (kV)`, `ratedS (kVA)`, `BaseVoltage`, `PowerTransformer` | |
| `TransformerTank` (`<xf>_tank`, in a bank `<xf>_<position>`) | `PowerTransformer`, `percentImpedance`, `baseS (kVA)` | `loadLoss (W)`, `noLoadLoss (W)`, `percentMagnetizingCurrent` |

`ratedU` is the phase-to-phase nameplate. `ratedS` is the unit's, or the bank's total. `baseS` is the can's kVA and
is required in a bank. An end on `s1s2N` with `connectionKind` `I` is a center tap. A bank's cans land in tank
order on end 1's phases: the example `xf_t7` is an open wye to open delta, with the L can on A (`a-N-b`) and the T
can on B (`b-c`). There is no template, winding, mesh or phase end.

## regulator

`regulator.cimtbl`: a step-down transformer (an LTC) with a tap changer, as a `PowerTransformer` by ends.

| Class (mRID) | Required | Optional |
|---|---|---|
| `PowerTransformer`, `PowerTransformerEnd`, `TransformerMeshImpedance` | As [transformer_by_ends](#transformer_by_ends) | |
| `RatioTapChanger` (`<xf>_tap`) | `lowStep`, `highStep`, `neutralStep`, `normalStep`, `step`, `stepVoltageIncrement`, `TransformerEnd` | `neutralU`, `ltcFlag`, `controlEnabled`, `ptRatio`, `ctRating`, `ctRatio`, `initialDelay (s)`, `subsequentDelay (s)`, `TapChangerControl` |
| `TapChangerControl` (`<xf>_ctrl`) | `mode`, `Terminal` (the generated `<xf>_T2`), `targetValue`, `targetDeadband` | `discrete`, `enabled`, `monitoredPhase`, `lineDropCompensation`, `lineDropR (ohm)`, `lineDropX (ohm)` |

The tap changer sits on end 2 and the control monitors that end's Terminal. `step` is a tap position, never a
ratio. `stepVoltageIncrement` is a `PerCent` attribute: write `0.625` unitless or `(percent)`, never `(pu)` (see
[Units](units.md#percent-attributes)). A regulator that is not a step-down transformer is
[voltage_regulator](#voltage_regulator).

## voltage_regulator

`voltage_regulator.cimtbl`: a step-voltage regulator (an autotransformer), as OpenDSS names a `Transformer` that a
`RegControl` controls with equal winding kV, a GridLAB-D `regulator`, or a GDM `DistributionRegulator`.

| Class (mRID) | Required | Optional |
|---|---|---|
| `VoltageRegulator` (`xf_`) | | `name`, `EquipmentContainer` |
| `AutoTransformerEnd` (`<xf>_<n>`) | `node`, `phase` (a PhaseCode: `AN`, `AB`, `ABCN`), `endNumber`, `baseU`, `BaseVoltage`, `AutoTransformer` | `grounded`, `ratedS` |
| `TransformerMeshImpedance` (`<xf>_mesh_12`) | `FromTransformerEnd`, `ToTransformerEnd` | `r (percent)`, `x (percent)` |
| `TapChangerControl` (`rc_<name>`) | `mode`, `Terminal`, `targetValue`, `targetDeadband` | as in [regulator](#regulator) |
| `RatioTapChanger` (`rc_<name>_tap`) | `lowStep`, `highStep`, `neutralStep`, `step`, `stepVoltageIncrement`, `TransformerEnd` | as in [regulator](#regulator), no `normalStep` |

`baseU` is the coil voltage and `ratedS` the through rating. The mesh impedance is a solver stand-in, because a
regulator nameplate has no percent impedance; its percent base is end 1's `baseU` and `ratedS`. Both the mesh and
`ratedS` are optional: without a mesh the ends are ideal and need no `ratedS` (a GridLAB-D regulator has neither).
The tap changer sits on the tap-side end, and the control monitors that end's generated Terminal.

## behind_transformer

`behind_transformer.cimtbl`: equipment behind its own transformer in a bus-branch model. The source gives the
transformer as data of the equipment: PSS/E RAW's generator step-up (`RT`, `XT`, `GTAP`) and its two-terminal DC
converter transformer (`EBAS`, `TR`, `TAP`, `RC`, `XC`). Load with `model_cls=BusBranchModel`.

A two-winding `PowerTransformer` `<eq>_xf` joins the network bus (end 1) to an internal `TopologicalNode` `<eq>_int`
(end 2) that only the transformer and the equipment touch. The equipment sits on the internal node.

| Class (mRID) | Required | Optional |
|---|---|---|
| `TopologicalNode` (`<eq>_int`) | `BaseVoltage` (end 2's `ratedU`), `ConnectivityNodeContainer` (the network bus's `Substation`) | `name`. No `busNumber`. |
| `PowerTransformerEnd` (`<eq>_xf_<n>`) | `bus`, `endNumber`, `ratedU (kV)`, `BaseVoltage`, `PowerTransformer` | `ratedS`, `r`, `x` (ohm, on end 1 only, on its `ratedU`) |
| `RatioTapChanger` (`<eq>_xf_tap1`) | As [regulator](#regulator) | A tap on end 1 only |
| `SynchronousMachine` (`gen_`), `CsConverter` (`cs_`) | `bus` (the internal node) | `ratedS`, `p`, `q` (generation negative), `operatingMode`, `numberOfValves` |

## load

`load.cimtbl`: an `EnergyConsumer` on a node. Its `BaseVoltage` is its node's.

| Class (mRID) | Required | Optional |
|---|---|---|
| `EnergyConsumer` (`ld_`) | `node`, `phases`, `p (kW)`, `q (kVAr)`, `BaseVoltage` | `name`, `phaseConnection` (`Y`, `D`), `grounded`, `customerCount`, `LoadResponse`, `EquipmentContainer` |
| `LoadResponseCharacteristic` (`exp_<p>_<q>`) | `exponentModel=true`, `pVoltageExponent`, `qVoltageExponent` | A spoke's own row, written before the loads that name it |
| `EnergyConsumerPhase` (`<mRID>_<phase>`), by `Update` | `mRID`, `p`, `q` | |

- The ZIP models are the shared rows from [common](#common). An exponential model is a row of the spoke's own.
- CIM load sign: consumption is positive `p`.
- A balanced three-phase load leaves `phases` blank. An unbalanced one writes its phases, and an `Update Table
  EnergyConsumerPhase` gives each generated child its own `p` and `q`; the children sum to the total. A single
  child (one delta branch, the 240 V part) takes no row, because the total is its value.
- On a split-phase secondary, `s1s2` wye is two 120 V legs to neutral, `s1` is one leg, and `s1s2` delta is 240 V
  across the legs (GridLAB-D's `power_12`).

## load_schedule

`load_schedule.cimtbl`: loads that follow a curve. Emitted for OpenDSS yearly `LoadShape` and GridLAB-D `schedule`
and `player`. The curve is a multiplier of each load's own `p` and `q`.

| Class (mRID) | Required | Optional |
|---|---|---|
| `ConformLoadGroup`, `NonConformLoadGroup` (`lg_`) | `name` | |
| `ConformLoadSchedule` (`ls_`) | `startTime` (ISO 8601 with its offset), `timeStep (s)`, `value1Unit` (`none`), the group | `name` |
| `NonConformLoadSchedule` (`ls_`) | As above, with `value1Unit` `W`, `value2Unit` `VAr` | `value1Multiplier`, `value2Multiplier` |
| `ConformLoad`, `NonConformLoad` (`ld_`) | The [load](#load) columns and `LoadGroup` | |

A schedule is regular: `startTime` plus `n * timeStep`. Its points are not rows here. They are `RegularTimePoints`
in the Parquet sidecar ([`cimhub_core.time_points`](../guide/time-points.md)), numbered from 0. A group may have no
schedule (a load names a curve the source does not define): only its name is kept. No importer writes a
`NonConformLoadSchedule` yet. RAW writes `ConformLoad` and `NonConformLoad` in groups per area and zone, without
schedules.

## shunt

`shunt.cimtbl`: a shunt capacitor and its control.

| Class (mRID) | Required | Optional |
|---|---|---|
| `LinearShuntCompensator` (`cap_`) | `node`, `nomQ (kVAr)`, `nomU (kV)`, `BaseVoltage` | `name`, `phases`, `phaseConnection`, `grounded`, `bPerSection (S)`, `sections`, `normalSections`, `maximumSections`, `EquipmentContainer` |
| `RegulatingControl` (`cc_`) | `mode`, `Terminal` | `name`, `discrete`, `enabled`, `monitoredPhase`, `targetValue`, `targetDeadband`, `ptRatio`, `ctRatio` |

The compensator comes first. Its `RegulatingControl` monitors a Terminal declared earlier: a line's or switch's (an
OpenDSS `CapControl element=line.j1`) or the compensator's own (`cap_c2_T1`). An `Update LinearShuntCompensator` then
gives the compensator its `RegulatingControl`, `aVRDelay (s)` and `controlEnabled`, which closes the reference
cycle of a control on its own terminal. `targetValue` and `targetDeadband` are plain floats in primary units by
mode (volts for `voltage`), so no unit goes in the header.

## switch

`switch.cimtbl`: switching devices. Every `Switch` subclass shares the `sw_` prefix, so changing the class keeps
the mRID.

| Class | Required | Optional |
|---|---|---|
| `Breaker`, `Fuse`, `LoadBreakSwitch`, `Recloser`, `Disconnector` (`sw_`) | `node1`, `node2`, `open`, `normalOpen`, `BaseVoltage` | `name`, `phases`, `EquipmentContainer`, `ratedCurrent (A)` on a `Fuse` |
| `RecloseSequence` (`<sw>_rs<n>`) | `ProtectedSwitch`, `recloseStep`, `recloseDelay (s)` | |

One `RecloseSequence` row per automatic reclosure, in order. OpenDSS's `Recloser` `Shots - 1` intervals become the
rows. GridLAB-D has one `status`, which becomes both `open` and `normalOpen`.

## source

`source.cimtbl`: an `EnergySource` on a node (OpenDSS `Vsource` and `Circuit`, GridLAB-D swing node).

| Class (mRID) | Required | Optional |
|---|---|---|
| `EnergySource` (`src_`) | `node`, `nominalVoltage (kV)`, `voltageMagnitude (kV)`, `BaseVoltage` | `name`, `phases`, `voltageAngle (deg)`, `r`, `x`, `r0`, `x0` (ohm), `EquipmentContainer` |

The Thevenin `r`, `x`, `r0`, `x0` are in ohm, as computed or written by the source.

## der

`der.cimtbl`: an inverter-based resource (OpenDSS `PVSystem` and `Storage`, GridLAB-D `inverter` with its `solar`
or `battery`).

| Class (mRID) | Required | Optional |
|---|---|---|
| `PowerElectronicsConnection` (`pv_`, `storage_`) | `node`, `ratedS (kVA)`, `ratedU` (line to line), `p`, `q`, `BaseVoltage` | `name`, `phases`, `phaseConnection`, `maxQ`, `minQ`, `maxIFault`, `EquipmentContainer` |
| `PhotoVoltaicUnit` (`<pec>_unit`) | `PowerElectronicsConnection` | `maxP`, `minP`, `irradiance (kW/m2)`, `p` |
| `BatteryUnit` (`<pec>_unit`) | `PowerElectronicsConnection` | `ratedE`, `storedE`, `minimumE` (kWh), `maxP`, `minP`, `chargingEfficiency`, `dischargingEfficiency` (percent), `idlingP`, `batteryState`, `p` |

- CIM load sign: generation and discharge are negative `p`, charging is positive.
- `ratedU` is line to line: a one-phase wye unit's kV times the square root of 3. On a split-phase secondary,
  `s1s2` wye is two 120 V legs.
- `maxIFault` is per unit of rated current.
- A battery's `p` follows its state: discharging negative, charging positive, and waiting at its `idlingP`.
- Several units may share one connection (a hybrid inverter). Each unit's `p` is its own, and they sum to the
  connection's.
- A PV unit's `irradiance` (a GridAPPS-D extension) is the sunlight its `p` was made under. `maxP` is at 1 kW/m2.

## synchronous_machine

`synchronous_machine.cimtbl`: a rotating machine on a distribution node (OpenDSS `Generator`). RAW's machines use
the bus-branch form with a `GeneratingUnit`.

| Class (mRID) | Required | Optional |
|---|---|---|
| `SynchronousMachine` (`gen_`) | `node`, `ratedS (kVA)`, `ratedU (kV)` (line to line), `p`, `q`, `BaseVoltage` | `name`, `phases`, `maxQ`, `minQ`, `type`, `operatingMode`, `earthing`, `EquipmentContainer` |
| `RegulatingControl` (`<gen>_ctrl`) | `mode=voltage`, `Terminal` (`<gen>_T1`), `targetValue` (V, line to line), `targetDeadband` | `discrete`, `enabled` |

CIM load sign: generation is negative `p`. The `phases` column gives one `RotatingMachinePhase` per phase (a
single-phase motor's too). A PV-bus machine (constant P and V) regulates its own terminal, so its control comes after
the machine and an `Update SynchronousMachine` gives the machine its `RegulatingControl` and `controlEnabled`.

## series_compensator

`series_compensator.cimtbl`: a series reactor between two nodes (OpenDSS series `Reactor`, GridLAB-D
`series_reactor`).

| Class (mRID) | Required | Optional |
|---|---|---|
| `SeriesCompensator` (`rx_`) | `node1`, `node2`, `r (ohm)`, `x (ohm)`, `BaseVoltage` | `name`, `r0`, `x0` (ohm), `EquipmentContainer` |
| `Terminal`, by `Update` | `mRID` (`<rx>_T1`, `<rx>_T2`), `phases` | Only for a device of fewer than three phases |
| `OperationalLimitSet` (`<rx>_limits`), `CurrentLimit` | `Equipment`; `normalValue (A)`, `OperationalLimitType`, `OperationalLimitSet` | Ratings, as for a line |

`r` and `x` are per phase, in ohm. With no mutual coupling the zero-sequence values equal them. `SeriesCompensator`
has no per-phase class, so a balanced three-phase one leaves its Terminals' phases unset, and an `Update Table
Terminal` gives a one-phase one its phases.

## location

`location.cimtbl`: equipment coordinates, drawn as a GIS draws them (OpenDSS `BusCoords` and `LatLongCoords`
files). It is written after every equipment file.

| Class (mRID) | Required | Optional |
|---|---|---|
| `CoordinateSystem` (`crs_<kind>`) | `crsUrn` | `name`. Declare it first: the Location takes the first one declared. |
| `PowerSystemResource`, by `Update` | `mRID`, `wkt` | |

An `Update` on the abstract `PowerSystemResource` reaches any equipment. Each `ConductingEquipment` gets one
`Location` through `wkt`, never a `ConnectivityNode`, which is not a `PowerSystemResource`.

| Equipment | `wkt` |
|---|---|
| A line | `LINESTRING` from its first Terminal's bus to its last, through each Terminal's bus in order |
| Anything else with one Terminal | `POINT` at its bus |
| Anything else with more | `POINT` at its buses' centroid (a switch or transformer midway) |

cimtables makes the `Location` (`<mRID>_loc`) and one `PositionPoint` per vertex. `x` is easting or longitude.
