---
name: cimtbl-shapes
description: The canonical `.cimtbl` table shapes every importer spoke emits (transformers, lines, wires, loads, shunts, switches, sources, DER, bus-branch), with their classes, mRID keys, required and optional columns and units. Use when a mapper emits rows, when choosing which CIM classes a native table becomes, or when adding a new shape.
---

# `.cimtbl` shape catalog

A shape is the one table layout for a CIM family. Spokes differ only in which optional columns they fill and in
their units, never in structure, so two formats' artifacts for the same network compare row by row.

Every shape has a loading example in `cimhub_core/src/cimhub_core/shapes/<shape>.cimtbl`;
`cimhub_core/tests/test_shapes.py` loads each one under cim18v17 and checks this catalog names every example file.
Read the example before writing the mapper: it is the spec, the table below is the index.

## Rules every shape follows

- **Units as written.** The header carries the source unit: `r (ohm/mi)`, `p (kW)`, `x (percent)`, `r (pu system)`.
  Nothing is pre-converted (I2). Any unit the cimprofiles registry parses for the quantity is allowed.
- **mRID = prefix + native ID** (D3), source case; only OpenDSS lowercases. Prefixes and child suffixes follow the
  `cimtbl-translate` prefix table; the key column below quotes them. The formatter quotes `, ( ) # "`.
- **Generated, never written:** Terminals `<equipment>_T<n>` (a TransformerEnd's is `<xf>_T<endNumber>`), phase
  children `<mRID>_<phase>`, ConnectivityNodes from `node`/`node1`/`node2`, TopologicalNodes from `bus`/`bus1`/`bus2`.
  Refer to a generated Terminal by that mRID.
- **Declare before reference.** Templates, catalogs and controls come before the rows that name them. The master's
  `Import` order is the dependency order.
- **Catalog vs instance.** Templates (`TransformerTankConfiguration`, `WireConfiguration`, `XYSpacing`,
  `PerLengthImpedance`, wire infos) hold no container, node or BaseVoltage. Instances hold those and point at the
  template. CIM 18 has no catalog-level ratings: a catalog rating becomes an instance `OperationalLimitSet` or is
  untranscribed (D9).
- **Transformer ratings.** `ratedU`/`ratedS` are nameplate values (IEEE C57.12.00-2021): `ratedU` phase-to-phase
  (s1-s2 on a split-phase secondary), `ratedS` the normal kVA, the same on both sides of a two-winding unit.
  `baseU`/`baseS` are only the percent → ohm basis, z = baseU²/baseS: `baseU` is the coil voltage (LL for delta,
  LN for wye: `12470GY/7200` gives 12470 / 7200); `baseS` is the per-phase kVA (a 3-phase tank's kVA / 3; a
  single-phase unit's kVA on every coil, split-phase halves included).
- **Identity-only classes** (`PhaseImpedanceData`) have no mRID: write `identifier` = `<parent>_<row><column>`.
- **No `*Info` network templates.** `WireSpacingInfo` is gone; `TransformerTankInfo`/`TransformerEndInfo`/
  `ShortCircuitTest` are asset-only.
- **`TapChanger.step` is a tap position,** never a turns ratio.

## Shapes

Columns: **required** / *optional*.

| shape | example | classes (key) | columns | from |
|---|---|---|---|---|
| shared prerequisites | `common.cimtbl` | `Substation` (`sub_`), `Feeder` (`fdr_`), `BaseVoltage` (`bv_`), `LoadResponseCharacteristic` (`zip_`) | BaseVoltage: **nominalVoltage** (kV, LL). Zip: **exponentModel**, **p/qConstant{Power,Current,Impedance}** | every master |
| transformer template, 3-phase | `transformer_template.cimtbl` | `TransformerTankConfiguration` (`xc_`), `TransformerTankEnd` (`<xc>_end_<n>`), `TransformerWinding` (`<xc>_wdg_<n>`), `TransformerCore` (`<xc>_core`), `TransformerMeshImpedance` (`<xc>_mesh_<ij>`) | TankEnd: **endNumber**, **phases**, **connectionKind**, *grounded*, *rground/xground (ohm)*. Winding: **ratedU** (kV, LL), **baseU** (the coil), **ratedS**, **baseS** (per-phase kVA), **FromTransformerEnd**. Mesh: **FromWinding**, **ToWinding**, **r/x** (percent on the From winding's baseU²/baseS), *r0/x0*. Config: *percentImpedance*, *percentMagnetizingCurrent*, *noLoadLoss/loadLoss* (W, kW) | DSS XfmrCode (3-phase), GLM transformer_configuration |
| transformer template, single-phase / center-tap | `transformer_template_1ph.cimtbl` | as above, with `TransformerPhaseEnd` (`<xc>_<suffix>`) instead of TankEnd; *TransformerLug* | PhaseEnd: **endNumber**, **sequenceNumber**, **phase**, **phaseNeutralU** (V). Winding: **ratedS/baseS**, **ratedU/baseU**, *r (percent)*, **From/ToTransformerEnd** | DSS XfmrCode (1-phase, center tap), GLM split-phase |
| open delta | pending (D14) | `TransformerLug` + `TransformerPhaseEnd` | the user supplies the template; until then open-delta banks fail fast | DSS open-delta banks |
| transformer instance by template | `transformer_by_template.cimtbl` | `PowerTransformer` (`xf_`), `TransformerTank` (`<xf>_tank`), `PowerTransformerEnd` (`<xf>_<n>`) | Tank: **PowerTransformer**, **TankConfiguration**. End: **node**, **phases**, **endNumber**, **BaseVoltage**, *connectionKind*, *grounded*. PowerTransformer: *vectorGroup* | DSS Transformer with XfmrCode, GLM transformer |
| transformer by balanced ends | `transformer_by_ends.cimtbl` | `PowerTransformer`, `PowerTransformerEnd`, `TransformerMeshImpedance` (`<xf>_mesh_<ij>`) | End: **node**, **phases**, **endNumber**, **connectionKind**, **ratedU** (kV), **ratedS** (kVA), **r** (percent on the end's ratedU²/ratedS, or ohm), **BaseVoltage**, *grounded*, *rground/xground*. Mesh: **From/ToTransformerEnd**, **x** (percent on the From end), *r* | DSS Transformer without XfmrCode (3-phase), RAW, MATPOWER |
| single-phase transformer by phase ends | `transformer_by_phase_ends.cimtbl` | `PowerTransformer` (`xf_`), `PowerTransformerEnd` (`<xf>_<n>`, one per bus), `TransformerTank` (`<xf>_tank`), `TransformerPhaseEnd` (`<xf>_<endNumber>_<phase>`), `TransformerWinding` (`<xf>_wdg_<n>`), `TransformerMeshImpedance` | End: **node**, **phases** (terminal phases: `AN`, `AB`, `s1s2N`), **endNumber**, **BaseVoltage**. PhaseEnd: **endNumber**, **sequenceNumber** (unique in the transformer, end 1 first, terminal phase order), **phase**, *phaseNeutralU*. Winding: **ratedU** (LL), **baseU** (coil), **ratedS**, **baseS**, *r (percent)*, **From/ToTransformerEnd** (phase ends). Tank: *percentMagnetizingCurrent*, *noLoadLoss*. No TransformerTankEnd | DSS Transformer without XfmrCode (1-phase) |
| regulator | `regulator.cimtbl` | transformer by ends + `RatioTapChanger` (`<xf>_tap`) + `TapChangerControl` (`<xf>_ctrl`) | Tap: **lowStep**, **highStep**, **neutralStep**, **normalStep**, **step**, **stepVoltageIncrement** (percent), **TransformerEnd**, *neutralU*, *ptRatio*, *ctRating*, *ctRatio*, *initialDelay/subsequentDelay (s)*. Control: **mode**, **Terminal** (generated `<xf>_T<n>`), **targetValue**, **targetDeadband**, *monitoredPhase*, *lineDropCompensation*, *lineDropR/X (ohm)* | DSS RegControl, GLM regulator |
| line by PerLengthImpedance | `line_by_impedance.cimtbl` | `PerLengthPhaseImpedance` (`lc_`) + `PhaseImpedanceData` (identifier `<lc>_<row><col>`), or `PerLengthSequenceImpedance` (`lc_`); `ACLineSegment` (`ln_`); `OperationalLimitSet` (`<ln>_limits`) + `CurrentLimit` (`<ln>_normal`) | Phase: **conductorCount**, *calculatedFrequency (Hz)*; data: **row**, **column** (conductor indices, lower triangle), **r**, **x**, *b* (ohm/<len>, nS or uS/<len>). Sequence: **r, x, r0, x0** (ohm/<len>), *bch, b0ch*. Segment: **node1**, **node2**, **phases**, **length** (its own unit), **PerLengthImpedance**, **BaseVoltage** | DSS LineCode + Line, GLM line_configuration with z11..z33 |
| wire and cable catalog | `wire_info.cimtbl` | `OverheadWireInfo` (`wire_`), `TapeShieldCableInfo` / `ConcentricNeutralCableInfo` (`cable_`) | **radius**, **gmr** (in, ft, mm), one resistance (*rDC20*, *rAC25/50/75* per length), *ratedCurrent (A)*; cables: insulation and screen diameters, *tapeThickness*, *tapeLap*, *neutralStrand{Count,Radius,Gmr,RDC20}* | DSS WireData/TSData/CNData, GLM conductors |
| line by geometry | `line_by_wire_configuration.cimtbl` | `XYSpacing` (`spc_`) + `XYConductorPosition` (`<spc>_<n>`), `WireConfiguration` (`wc_`) + `WireSequenceConfiguration` (`<wc>_<n>`), `ACLineSegment` | Position: **sequenceNumber**, **xCoord**, **yCoord** (ft, m), **kind** (phase, neutral). WireConfiguration: **WireSpacing**, *numberOfPhases*; per conductor: **sequenceNumber**, **WireInfo**. Segment: **WireConfiguration** instead of PerLengthImpedance | DSS LineSpacing/LineGeometry, GLM line_spacing |
| line lumped in per unit (bus-branch) | `line_bus_branch.cimtbl` | `BasePower` (first), `TopologicalNode` (`bus_`), `ACLineSegment` | **bus1**, **bus2**, **r**, **x** (pu system, ohm), *bch* (pu system, S), **BaseVoltage**. Load with `load_model(..., model_cls=BusBranchModel)` | RAW, MATPOWER |
| load | `load.cimtbl` | `EnergyConsumer` (`ld_`) | **node**, **phases**, **p** (kW, W), **q** (kVAr), **BaseVoltage**, *phaseConnection* (Y, D, I), *grounded*, *LoadResponse* (`zip_`). Consumption is positive p | every distribution format |
| shunt with control | `shunt.cimtbl` | `LinearShuntCompensator` (`cap_`), `RegulatingControl` (`<cap>_ctrl`) | Compensator: **node**, **phases**, **nomQ** (kVAr), **nomU** (kV), *bPerSection (S)*, *sections*, *normalSections*, *maximumSections*, *phaseConnection*, *grounded*, *aVRDelay (s)*, *RegulatingControl*. Control: **mode**, **Terminal**, *targetValue/targetDeadband (V)*, *monitoredPhase* | DSS Capacitor + CapControl, GLM capacitor |
| switch | `switch.cimtbl` | `Breaker`, `Fuse`, `LoadBreakSwitch`, `Recloser`, `Disconnector`, `Sectionaliser` (all `sw_`) | **node1**, **node2**, **phases**, **open**, **normalOpen**, **BaseVoltage**, *ratedCurrent (A)* | every distribution format |
| source | `source.cimtbl` | `EnergySource` (`src_`) | **node**, **phases**, **nominalVoltage**, **voltageMagnitude** (kV), *voltageAngle (deg)*, *r/x/r0/x0 (ohm)*, **BaseVoltage** | DSS Vsource/Circuit, GLM swing node |
| inverter-based DER | `der.cimtbl` | `PowerElectronicsConnection` (`pv_`, `storage_`), `PhotoVoltaicUnit` / `BatteryUnit` (`<pec>_unit`) | Connection: **node**, **phases**, **ratedS** (kVA), **ratedU**, **p**, **q** (negative p = generation), **BaseVoltage**. PV: *maxP*. Battery: *ratedE*, *storedE* (kWh), *batteryState* | DSS PVSystem/Storage, GLM inverter + solar/battery |

## Not yet catalogued

Added here first, by the wave that needs them: synchronous machines and their bus-branch generator form (RAW,
MATPOWER), per-phase load and shunt rows (`EnergyConsumerPhase`, `LinearShuntCompensatorPhase`), series compensators,
FACTS, protection beyond switches, measurements, the open-delta template (D14).

## Adding a shape

1. Write `cimhub_core/src/cimhub_core/shapes/<shape>.cimtbl`: `Profile = cim18v17`, `Import common.cimtbl` for
   shared context, and a comment block naming the shape and its sources.
2. Add its row here (classes with keys, required/*optional* columns, units, sources).
3. Make sure it loads (`uv run pytest cimhub_core/tests/test_shapes.py`). Add a value check in SI if the shape uses a
   unit or base word no other example covers.
4. Only then let a mapper emit it. A mapper never invents a layout locally.

## Anti-patterns

- A matrix (`PerLengthPhaseImpedance`) written for a line whose source has spacing + wires: emit the geometry shape
  (skill `conductor-geometry`).
- Writing Terminals or ConnectivityNodes as rows; giving a template a node, container or BaseVoltage.
- Pre-converting units to SI in cells; writing a ratio into `step`; the same series R on both windings and the mesh.
- Two spokes emitting different classes for the same equipment family.
