# Lines, wires and switches

Everything that carries current between two buses and is not a transformer: line codes, conductor catalogs, spacings
and geometries, lines, switches with their controls, and series reactors. How to read the tables is on the
[reference landing page](index.md).

| DSS | CIM (cim18v17) | Import (shape) | Export |
|---|---|---|---|
| `LineCode` | `PerLengthPhaseImpedance` + `PhaseImpedanceData`, or `PerLengthSequenceImpedance`; a template `WireConfiguration` `lc_<name>_wc` | `linecode.cimtbl` (`line_by_impedance`) | `LineCode`, per metre |
| `WireData`, `CNData`, `TSData` | `OverheadWireInfo`, `ConcentricNeutralCableInfo`, `TapeShieldCableInfo` | `wiredata.cimtbl`, `cndata.cimtbl`, `tsdata.cimtbl` (`wire_info`) | the same three classes, in metres |
| `LineSpacing` | `XYSpacing` (template) + `XYConductorPosition` | `linespacing.cimtbl` (`line_by_wire_configuration`) | none: positions are inline in `LineGeometry` |
| `LineGeometry` | `WireConfiguration` + `WireSequenceConfiguration` (+ `EarthResistivity`) | `linegeometry.cimtbl` (`line_by_wire_configuration`) | `LineGeometry` with `cond=` blocks |
| `Line` | `ACLineSegment`, `OperationalLimitSet` + `CurrentLimit` | `line.cimtbl` (`line_by_impedance`, `line_by_wire_configuration`) | `Line` |
| `Line` with `Switch=y`, `Fuse`, `Recloser`, `SwtControl` | `Fuse`, `Recloser` or `LoadBreakSwitch`; `RecloseSequence` | `line.cimtbl` (`switch`) | a switch `Line` and its control |
| `Reactor` (series) | `SeriesCompensator` | `reactor.cimtbl` (`series_compensator`) | `Reactor` |

The shapes are on the core site's [shapes page](https://pnnl-cim-tools.github.io/CIMHub/core/developer/shapes/), and the
getters the exporter reads through are on its [lines reference](https://pnnl-cim-tools.github.io/CIMHub/core/reference/lines/).

**Geometry stays geometry.** A `LineGeometry`, or a `Line` with `spacing=`, becomes a `WireConfiguration` that names an
`XYSpacing` and the wires. No impedance is computed from it, on import or export; the consumer's line constants do that.
A `LineCode` is a template that its lines share by name: its impedance has `isTemplate=true` and sits on a
`WireConfiguration` with no `WireSpacing`, and the lines name that `WireConfiguration`. A line with its own inline
impedance gets a `PerLengthImpedance` of its own, `ln_<name>_lc`, with `isTemplate=false`.

**Units.** On import every length-based value keeps the deck's unit, in the column header (`r (ohm/mi)`, `length (ft)`).
`{length}` below is the code's or line's `units`, and `{r_length}`, `{gmr_length}` and `{radius_length}` are a wire's
`Runits`, `GMRunits` and `radunits`. On export every length is in metres, so every per-length value is per metre.

## LineCode

A code that sets `rmatrix`, `xmatrix` or `cmatrix` is a matrix code; one that sets any of `r1 x1 r0 x0 C1 C0 B1 B0` is a
sequence code. DSS keeps whichever form was set last and the reader does not record the order, so a code that sets
both raises, and so does one that sets neither.

| Code | CIM | Notes |
|---|---|---|
| matrix | `PerLengthPhaseImpedance` (`conductorCount` = `nphases`) and one `PhaseImpedanceData` row per lower-triangle element, `row` and `column` the conductor indices | values in `ohm/{length}`, `b` in `nS/{length}` derived from `cmatrix` by `b_from_c`; a matrix without `cmatrix` gets the engine's default C, listed as `defaulted` |
| sequence, 3 phases | `PerLengthSequenceImpedance` | `bch`, `b0ch` in `nS/{length}` from `C1`, `C0`, or in `uS/{length}` copied from `B1`, `B0` |
| sequence, 1 or 2 phases | a derived matrix, as the engine builds the line | 1 phase: z = Z1; 2 phases: Zs = (2 Z1 + Z0)/3, Zm = (Z0 - Z1)/3 (`phase_matrix`) |

**Length unit.** DSS reads a code with no `units` per unit of each line's length. The importer takes the unit from the
lines that use the code (one template per unit, `lc_<name>_<unit>`, when they disagree). Failing that, it takes
`length_unit=` from `DssImporter`, else a magnitude gate on the median positive `r1` or `rmatrix` diagonal of the deck's
unitless codes: 0.006 to 10 per unit is `km`, 1e-5 to 0.006 is `m`, anything else raises. The row comment says which
(`units from its lines`, `units inferred`, `units given`).

**Base frequency.** `b = 2 pi f C`. A code with a nonzero `C` and no `baseFreq` takes the deck's base frequency, listed
as `defaulted: baseFreq=60.0`.

| property | import | export |
|---|---|---|
| `name` | copied to `PerLengthPhaseImpedance.name`; `PerLengthSequenceImpedance.name`; `WireConfiguration.name`; mRID = lc_ + name, lowercased; its WireConfiguration's lc_&lt;name>_wc | written: Names |
| `nphases` | copied to `PerLengthPhaseImpedance.conductorCount`; the matrix order of rmatrix/xmatrix/cmatrix; a 1- or 2-phase sequence code becomes a phase matrix as the engine builds the line (phase_matrix): 1-phase z = Z1, 2-phase Zs = (2 Z1 + Z0)/3 and Zm = (Z0 - Z1)/3 | written: phase code: conductorCount; sequence code: 3 |
| `r1` | copied to `PerLengthSequenceImpedance.r` (ohm/&#123;length&#125;) | written: sequence code: r (ohm/m) |
| `x1` | copied to `PerLengthSequenceImpedance.x` (ohm/&#123;length&#125;) | written: sequence code: x (ohm/m) |
| `r0` | copied to `PerLengthSequenceImpedance.r0` (ohm/&#123;length&#125;) | written: sequence code: r0 (ohm/m); unset raises |
| `x0` | copied to `PerLengthSequenceImpedance.x0` (ohm/&#123;length&#125;) | written: sequence code: x0 (ohm/m); unset raises |
| `C1` | derived: PerLengthSequenceImpedance bch = 2 pi baseFreq C1 (b_from_c): nF -> nS | written by rule: sequence code: c_from_b(bch) (nF/m); unset -> 0 |
| `C0` | derived: PerLengthSequenceImpedance b0ch = 2 pi baseFreq C0 (b_from_c): nF -> nS | written by rule: sequence code: c_from_b(b0ch) (nF/m); unset -> 0 |
| `units` | mapped: the length unit of every per-length header via LENGTH_UNIT; unset: the unit of the lines that use the code, else the deck's magnitude gate | written: m |
| `rmatrix` | structural: PhaseImpedanceData r, one row per lower-triangle element | written: phase code: r, lower triangle (ohm/m) |
| `xmatrix` | structural: PhaseImpedanceData x, one row per lower-triangle element | written: phase code: x, lower triangle (ohm/m) |
| `cmatrix` | derived: PhaseImpedanceData b = 2 pi baseFreq C (b_from_c): nF -> nS | written by rule: phase code: c_from_b(b), lower triangle (nF/m); unset -> zeros |
| `baseFreq` | copied to `PerLengthPhaseImpedance.calculatedFrequency` (Hz); `PerLengthSequenceImpedance.calculatedFrequency` (Hz); also the frequency of the derived b; unset with a nonzero C: the deck's base frequency, defaulted | written: network.base_frequency (Hz); a calculatedFrequency that differs raises |
| `Rg` | untranscribed: Carson earth return per length; home PerLengthImpedance.rg/xg (ohm/&lt;units>), not mapped until a deck sets it (none of the test decks do) | not written: PerLengthImpedance.rg set raises (not imported either) |
| `Xg` | untranscribed: Carson earth return per length; home PerLengthImpedance.rg/xg (ohm/&lt;units>), not mapped until a deck sets it (none of the test decks do) | not written: PerLengthImpedance.xg set raises (not imported either) |
| `B1` | copied to `PerLengthSequenceImpedance.bch` (uS/&#123;length&#125;); the alternative to C1 | not written: C1 carries the susceptance |
| `B0` | copied to `PerLengthSequenceImpedance.b0ch` (uS/&#123;length&#125;); the alternative to C0 | not written: C0 carries the susceptance |
| `like` | untranscribed: the reader resolves like= before mapping | not written: the writer never writes like= |
| `normamps`, `emergamps`, `faultrate`, `pctperm`, `repair`, `Kron`, `rho`, `neutral`, `Seasons`, `Ratings`, `LineType` | untranscribed (listed in the table comment) | not written |

**Fail fast.**

- A `units` value with no mapping, a unitless code whose lines give units on some lines only, or a gate median in no band.
- `LineCode c: sets both matrix and sequence values; DSS keeps whichever was set last, which the reader does not record`, and `LineCode c: sets no impedance; DSS would apply its defaults`.
- A 1- or 2-phase sequence code without `r1` and `x1`.
- `C1` with `B1` (or `C0` with `B0`) on one code, `B1` or `B0` on a 1- or 2-phase code, a matrix whose length fits neither the lower triangle nor the full square of `nphases`.
- On export, a `calculatedFrequency` that differs from the network's, `rg` or `xg` set, `gch` or `g0ch` nonzero, an unset `r0` or `x0` on a sequence code, and a matrix `g` that is nonzero.

**Expected differences.** The unused templates are written too. Per-length values are rescaled to per metre and
`units=m`. `baseFreq` is always written. A code's `normamps` and `emergamps` have no home on a `PerLengthImpedance`
(`untranscribed`); the lines that use the code carry them instead. A 1- or 2-phase sequence code comes back as a matrix
code. The CIM name is the mRID (`lc_mtx601`) unless `name_source="name"`.

Excerpt from `cimhub_opendss/tests/atoms/linecode/mtx601.cimtbl`:

```
Table PerLengthPhaseImpedance: mRID, name, conductorCount, calculatedFrequency (Hz), isTemplate
    # untranscribed: normamps=730.0
    lc_mtx601, mtx601, 3, 60, true

# units=mi. row/column are conductor indices of the lower triangle.
# derived: b = 2 pi baseFreq C (b_from_c), from cmatrix (nF) -> nS
Table PhaseImpedanceData: identifier, PhaseImpedance, row, column, r (ohm/mi), x (ohm/mi), b (nS/mi)
    lc_mtx601_11, lc_mtx601, 1, 1, 0.3465, 1.0179, 0.0
    lc_mtx601_21, lc_mtx601, 2, 1, 0.1535, 0.3849, 0.0
    ...

Table WireConfiguration: mRID, name, PerLengthImpedance
    lc_mtx601_wc, mtx601, lc_mtx601
```

## WireData, CNData and TSData

One catalog entry per object, in one file per DSS class. A rated wire's `normamps` and `emergamps` also become an
`OperationalLimitSet` `<mRID>_limits` with a normal and an emergency `CurrentLimit`, on `AssetInfo.OperationalLimitSet`.
The three unit selectors `Runits`, `GMRunits` and `radunits` set header units, and the mapper writes one table per
combination of them. The three classes share the conductor properties and a CNData or TSData adds its cable
construction.

**Conductor properties** (all three classes; `<Info>` is `OverheadWireInfo`, `ConcentricNeutralCableInfo` or
`TapeShieldCableInfo`):

| property | import | export |
|---|---|---|
| `name` | `<Info>.name`; mRID `wire_`, `cn_` or `ts_` plus the name, lowercased | the three catalogs share one name namespace, so a name in two catalogs raises |
| `Rdc` | copied to `rDC20` (`ohm/{r_length}`; DSS gives no temperature) | written: `r_dc20` (ohm/m); `Rdc` and `Rac` both unset raises |
| `Rac` | copied to `rAC25` (`ohm/{r_length}`; temperature unstated); unset is 1.02 x `Rdc`, the engine's rule, listed as `defaulted`; neither set raises | written when set; unset is left to the engine's 1.02 x `Rdc` |
| `Runits`, `GMRunits`, `radunits` | mapped: header units (`mi`, `kft`, `km`, `m`, `ft`, `in`, `cm`, `mm`); unset raises | written: `m` |
| `GMRac` | copied to `gmr` (`{gmr_length}`); unset raises, though the engine would take 0.7788 x radius | written when set; unset is left to the engine |
| `radius`, `diam` | one of the two, copied to `radius` (`{radius_length}`), `diam` as `diam / 2`; both or neither raises | written: `radius` (m), required; `diam` is never written |
| `normamps` | copied to `ratedCurrent` (A) and the normal `CurrentLimit` | written: the wire's normal limit, else `ratedCurrent` |
| `emergamps` | the emergency `CurrentLimit`; unset with `normamps` set is 1.5 x `normamps`, the engine's rule, listed as `defaulted` | written when set; unset is left to the engine |
| `Seasons`, `Ratings`, `Capradius` | raises when set (not mapped yet) | not written |
| `like` | resolved by the reader | never written |

**Cable properties** (CNData and TSData unless noted):

| property | import | export |
|---|---|---|
| `InsLayer` | copied to `insulationThickness` (`{radius_length}`) | written (m) |
| `DiaIns` | copied to `diameterOverInsulation` (`{radius_length}`) | written (m) |
| `DiaCable` | copied to `diameterOverJacket`; a CN cable has no jacket over its strands, so it is also `diameterOverNeutral` | TS: `diameterOverJacket`; CN: `diameterOverNeutral`, the circle of the strands, unset raises |
| `k` (CN) | copied to `neutralStrandCount` | written |
| `DiaStrand` (CN) | derived: `neutralStrandRadius = DiaStrand / 2` | written: 2 x `neutralStrandRadius` |
| `GmrStrand` (CN) | copied to `neutralStrandGmr` (`{gmr_length}`) | written |
| `Rstrand` (CN) | copied to `neutralStrandRDC20` (`ohm/{r_length}`), CIM's only strand resistance | written |
| `SemiconLayer` (CN) | raises when set (not mapped yet) | not written |
| `DiaShield` (TS) | derived: `diameterOverScreen = DiaShield - 2 TapeLayer`, because DSS measures over the tape; `DiaShield` without `TapeLayer` raises | written: `diameterOverScreen + 2 tapeThickness` |
| `TapeLayer`, `TapeLap` (TS) | copied to `tapeThickness` (`{radius_length}`), `tapeLap` (percent) | written |
| `EpsR` | untranscribed (the DSS default, 2.3, in every cable in the test decks; `InsulationInfo` has a material, not a permittivity) | not written |

**Fail fast.** A selector unit unset or unknown; both `radius` and `diam`, or neither; `GMRac` unset; neither `Rac` nor
`Rdc`; `Seasons`, `Ratings`, `Capradius` or `SemiconLayer` set. On export, a `WireInfo` with no `radius`, with neither
`rDC20` nor `rAC25`, a CN cable with no `diameterOverNeutral`, a TS cable without `diameterOverScreen` and `tapeThickness`.

**Expected differences.** Every `WireInfo` in the network is written, used or not. Everything is in metres, `Rac` and
`emergamps` come back explicit when the deck left them to the engine, and `diam` comes back as `radius`. A plain
`CableInfo` (no neutral or shield) has no DSS cable class and is written as a `WireData`, its insulation unmodelled.

Excerpt from `cimhub_opendss/tests/atoms/wire/assets_wiredata.cimtbl` is the pattern: the headers carry the units
(`rDC20 (ohm/kft)`, `gmr (in)`, `radius (in)`), and the row comment says `defaulted: Rac = 1.02 x Rdc` where it applies.

## LineSpacing

A `LineSpacing` is an `XYSpacing` template, `spc_<name>`, with `isTemplate=true`, and one `XYConductorPosition` per
conductor: `sequenceNumber` 1 to `nconds`, `xCoord` from `x` and `yCoord` from `h` in the spacing's `units`, `kind` `phase`
for conductors 1 to `nphases` and `neutral` after.

| property | import | export |
|---|---|---|
| `name` | copied to `XYSpacing.name`; mRID = spc_ + name, lowercased; isTemplate = true | - |
| `nconds` | structural: one XYConductorPosition per conductor, sequenceNumber 1..nconds; x and h must have nconds values | - |
| `nphases` | structural: kind: phase for conductors 1..nphases, neutral after | - |
| `x` | structural: XYConductorPosition.xCoord (&#123;length&#125;), one per conductor | - |
| `h` | structural: XYConductorPosition.yCoord (&#123;length&#125;), one per conductor | - |
| `units` | mapped: the length unit of xCoord and yCoord (LENGTH_UNIT); unset raises | - |
| `detailed`, `EqDistPhPh`, `EqDistPhN`, `AvgPhaseHeight`, `AvgNeutralHeight` | raises when set (not mapped yet) (the equivalent-distance form has no positions) | - |
| `like` | untranscribed (listed in the table comment) | not written |

**Fail fast.** `x` or `h` with other than `nconds` values; `units` unset; the equivalent-distance form (`detailed`,
`EqDistPhPh`, `EqDistPhN`, `AvgPhaseHeight`, `AvgNeutralHeight`).

**Export.** None. A `LineGeometry` is written with its positions inline, so a spacing that several geometries shared on
import (`spc_500` under 601 and 602) comes back as one set of positions per geometry, and a re-import gives
`wc_<name>_spc` for each. The engine sees the same line.

Excerpt from `cimhub_opendss/tests/atoms/geometry/assets_linespacing.cimtbl`:

```
Object XYSpacing: mRID=spc_500, name=500, isTemplate=true

Table XYConductorPosition: mRID, XYSpacing=spc_500, sequenceNumber, xCoord (ft), yCoord (ft), kind
    spc_500_1, 1, -4.0, 28.0, phase
    spc_500_2, 2, -1.0, 28.0, phase
    spc_500_3, 3, 3.0,  28.0, phase
    spc_500_4, 4, 0.0,  24.0, neutral
```

## LineGeometry

A geometry is a `WireConfiguration` named `wc_<name>` with one `WireSequenceConfiguration` per conductor, each naming its
`WireInfo`. The spacing is either a named `LineSpacing` (`spacing=`) or the inline positions of the `cond=` blocks, which
get a synthesized `XYSpacing` `wc_<name>_spc`. Every `WireConfiguration` names the deck's one `EarthResistivity`, `earth`
([Set options](sources.md)). A conductor name resolves to exactly one of `WireData`, `CNData` and `TSData`, and a mixed
assembly (a TS phase with a bare neutral) arrives whole.

| property | import | export |
|---|---|---|
| `name` | copied to `WireConfiguration.name`; mRID = wc_ + name, lowercased | written: Names; &lt;configuration> at offset 0, &lt;configuration>_&lt;offset>m otherwise, to the mm ('.' as 'p'); a spacing line's: &lt;line>_geometry of the first line with its spacing, offset and conductors; a coupled group's: &lt;group>_geometry |
| `nconds` | structural: one WireSequenceConfiguration per conductor, sequenceNumber 1..nconds; the conductor names and (inline) positions must have nconds values | written: the spacing's positions; a spacing line's: its phases' positions; a coupled group's: its lines' positions, a shared neutral once |
| `nphases` | copied to `WireConfiguration.numberOfPhases`; also the kind of an inline position: phase for 1..nphases, neutral after | written: WireConfiguration.numberOfPhases, required; a spacing line's: its phases other than N, a coupled group's: every line's; position kinds phase then neutral |
| `spacing` | structural: WireConfiguration.WireSpacing = spc_ + spacing; with inline positions it raises | not written: positions are written inline |
| `xs` | structural: inline positions: a synthesized XYSpacing wc_&lt;name>_spc, xCoord (&#123;length&#125;) | written: get_line_conductor_xy x (m); an unused configuration: get_spacing_xy |
| `hs` | structural: inline positions: the synthesized XYSpacing's yCoord (&#123;length&#125;) | written: get_line_conductor_xy y, above ground (m); a plain CableInfo's abs(y) |
| `units` | mapped: the length unit of the inline positions (LENGTH_UNIT); unset raises. The reader raises when the cond= blocks give different units | written: m |
| `wires` | structural: the conductor names in cond order; each resolves to exactly one of WireData, CNData, TSData (a name in two raises) and is the WireSequenceConfiguration.WireInfo. A mixed assembly (607: a TS phase, a bare neutral) arrives here whole, so the array carries no kind | written: get_configuration_wires, or a spacing line's get_line_phase_wires, by sequence number; any of the three catalogs |
| `cncables` | structural: as wires; only one of wires, cncables, tscables may be set | not written: wires carries every kind (the writer names each block's kind) |
| `tscables` | structural: as wires; only one of wires, cncables, tscables may be set | not written: wires carries every kind (the writer names each block's kind) |
| `cond` | structural: the reader folds the cond= blocks into the arrays; set alone (no cond=) it raises | not written: the writer folds wires/xs/hs into cond= blocks |
| `wire` | structural: the reader folds the cond= blocks into the arrays; set alone (no cond=) it raises | not written: the writer folds wires/xs/hs into cond= blocks |
| `cncable` | structural: the reader folds the cond= blocks into the arrays; set alone (no cond=) it raises | not written: the writer folds wires/xs/hs into cond= blocks |
| `tscable` | structural: the reader folds the cond= blocks into the arrays; set alone (no cond=) it raises | not written: the writer folds wires/xs/hs into cond= blocks |
| `x` | structural: the reader folds the cond= blocks into the arrays; set alone (no cond=) it raises | not written: the writer folds wires/xs/hs into cond= blocks |
| `h` | structural: the reader folds the cond= blocks into the arrays; set alone (no cond=) it raises | not written: the writer folds wires/xs/hs into cond= blocks |
| `reduce` | untranscribed: Kron reduction of the neutrals; a solver choice the consumer makes from the segment's phases | written: y: the neutrals grounded at both ends, as the impedance getters assume |
| `conductors` | raises when set (not mapped yet) | not written: wires carries the names |
| `like` | untranscribed: the reader resolves like= before mapping | not written: the writer never writes like= |
| `normamps`, `emergamps`, `Seasons`, `Ratings`, `LineType` | untranscribed (listed in the table comment) | not written |

**Fail fast.** `spacing=` with inline positions; a `spacing=` that is no `LineSpacing`; `wires`, `cncables` and `tscables`
set together (the order between them is not recorded); a conductor in no catalog or in two; the wrong number of names or
positions for `nconds`; `nphases` or `nconds` unset; `conductors` set; a `cond`/`wire`/`x`/`h` value without `cond=` blocks.
On export, a position whose `kind` disagrees with DSS's rule (conductors 1 to `nphases` are phases), and a
`WireConfiguration` with neither a `WireSpacing` nor a `PerLengthImpedance`.

**Export.** One `LineGeometry` per (`WireConfiguration`, `ySpacingOffset`) among the lines, named after the configuration,
with `_<offset>m` (to the mm, `.` as `p`) when the offset is not 0. A configuration no line uses is written at offset 0.
A line with a direct `WireSpacing` and a `WireInfo` on each `ACLineSegmentPhase` (a spacing line) gets a geometry
`<line>_geometry`; the lines of a coupled `MultiCircuitGroup` become one DSS line on one geometry with jumpers. Heights
are above ground, and a plain `CableInfo` below grade is mirrored above it, because DSS takes a `WireData` only above
grade. `reduce=y` is always written: the neutrals are grounded at both ends, as the impedance getters assume. On import
`reduce` is untranscribed, since it is a solver choice of the consumer.

Excerpt from `cimhub_opendss/tests/atoms/geometry/assets_linegeometry.cimtbl` (geometry 601 by spacing, 606 by inline
positions):

```
# untranscribed: reduce=true
Object WireConfiguration: mRID=wc_601, name=601, numberOfPhases=3, WireSpacing=spc_500, EarthResistivity=earth

Table WireSequenceConfiguration: mRID, WireConfiguration=wc_601, sequenceNumber, WireInfo
    wc_601_1, 1, wire_acsr_556_5
    ...
    wc_601_4, 4, wire_acsr_4/0

# synthesized: the inline positions of LineGeometry 606
Object XYSpacing: mRID=wc_606_spc, name=606, isTemplate=true
```

## Line

A `Line` becomes an `ACLineSegment` or, with `Switch=y`, a switch (next section). Exactly one source of impedance is
allowed; two raise (`Line l: gives linecode and inline; exactly one of linecode, geometry, spacing + wires, or inline
values is mapped`).

| The line gives | `ACLineSegment` references | Export |
|---|---|---|
| `linecode=` | the `WireConfiguration` of the code's template, `lc_<code>_wc` (`lc_<code>_<unit>_wc` for a code with templates per unit) | `linecode=<name>` |
| `geometry=` | `wc_<geometry>` | `geometry=<name>`, with `rho` from the `EarthResistivity` |
| `spacing=` with `wires`, `cncables` or `tscables` | a synthesized `WireConfiguration` `ln_<name>_wc` on `spc_<spacing>` | a `<line>_geometry` |
| its own `r1 x1 ...` or `rmatrix ...` | `PerLengthImpedance` `ln_<name>_lc` with `isTemplate=false`, through the LineCode rules | the values inline, per metre |
| (CIM only) lumped `r`, `x`, `bch` on the segment | not produced by this importer | inline per km, `units=km`, whole-line value / length; no length means `length=1` |

A line's own sequence values left unset take the engine's defaults, listed as `defaulted`: `r`/`x` per unit length as
they are, and `C1`/`C0` taken as nF per kft and converted to the line's `units` when the line gives them (a line with no `units` keeps the default number as it is). `phases` defaults to the code's or geometry's `nphases`, else 3.
A line's phases come from its nodes: 1, 2 and 3 are A, B and C (s1 and s2 on a split-phase island), and no nodes means
conductor k on node k. A geometry line adds an `N` for its neutral, so `ABCN`.

**Ratings.** A line's own `normamps` and `emergamps` become `ln_<name>_limits` with `CurrentLimit`s `_norm` and `_emerg`.
Where the line gives none, it copies its LineCode's, or its geometry's, or its first conductor's (emergency 1.5 x normal),
as the engine rates the line. The comment says where each came from. Nothing comes from DSS's 400 and 600 A defaults.

| property | import | export |
|---|---|---|
| `name` | `ACLineSegment.name`; mRID `ln_` plus the name, lowercased | the CIM name or mRID (`name_source`) |
| `bus1`, `bus2` | structural: `node1`, `node2` and the phases from their nodes; `bus2`'s nodes must give the same phases as `bus1`'s, else it raises as a transposition | written: the terminals' buses with the phase conductors in order; the neutral is not on the bus |
| `phases` | structural: the phase count; one that differs from the code's `nphases` raises | written: the phase conductors |
| `linecode`, `geometry`, `spacing`, `wires`, `cncables`, `tscables` | structural: see the table above | `linecode` and `geometry` written; the rest not written (the `LineGeometry` carries them) |
| `length`, `units` | copied to `length` (`{length}`); `length` unset is 1, listed as `defaulted`; `units` unset is the template's unit, and `m` for a geometry line (the engine reads a unitless geometry line in metres) | written: metres, `units=m`; a lumped line `km` |
| `r1 x1 r0 x0 C1 C0 B1 B0 rmatrix xmatrix cmatrix` | structural: the line's own `PerLengthImpedance` `ln_<name>_lc` | the line's own code inline, per metre, when its `isTemplate` is false; one that several lines use raises |
| `basefreq` | structural: the own impedance's `calculatedFrequency` and the frequency of its `b`; unset is the deck's | not written (`Options.defaultbasefreq`) |
| `normamps`, `emergamps` | structural: the `OperationalLimitSet` above | written from `get_current_limits`; unset is not written |
| `rho` | structural: `EarthResistivity.rho` (ohm-m), which every geometry line must agree on; on a line without geometry it raises | written for a geometry line, from its configuration's `EarthResistivity` |
| `Switch` | structural: a switch, next section | a `Switch` is exported by the switch module |
| `enabled` | copied to `normallyInService` | written (`get_in_service(which='normal')`) |
| `Seasons`, `Ratings`, `Rg`, `Xg`, `EpsRmedium`, `HeightOffset`, `HeightUnit`, `conductors` | raises when set (not mapped yet) | not written |
| `EarthModel`, `LineType`, `faultrate`, `pct_perm`, `repair` | untranscribed (`EarthModel` is the deck's `Set earthmodel`) | not written |
| `like` | resolved by the reader | never written |

**Fail fast.**

- `Line l: bus1 phases ABC and bus2 phases BAC differ (a transposition is not mapped)`, a phase conductor on node 0, and a bus the walk did not reach.
- `phases` that differ from the code's, geometry's or spacing's `nphases`; more than one neutral conductor in a geometry.
- `rho` on a line with no geometry.
- A `linecode`, `geometry` or `spacing` that names no such object.
- On export, a neutral conductor on a line with no geometry (`needs LineCode Kron/neutral, which is not mapped`), a `WireConfiguration` together with `ACLineSegmentPhase.WireInfo`, a phase count that differs from the configuration's `numberOfPhases`, a code with a different `conductorCount`.

**Expected differences.**

- Names are the mRIDs (`ln_l1`, `lc_mtx601`) unless `name_source="name"`.
- Lengths are in metres and per-length values per metre; a lumped line is per km. Floats are written to 15 digits.
- A line that took its ratings from its code now has them on its own `Line`.
- Lines that shared a `LineSpacing` each carry positions, as above.

## Switches: Line with Switch=y, Fuse, Recloser, SwtControl

A `Line` with `Switch=y` is a `Switch`, `sw_` plus the name. The class comes from the control that names the line as
`SwitchedObj` (or, for a Fuse or Recloser, `MonitoredObj`): a `Fuse` or a `Recloser`, else a `LoadBreakSwitch`. The
control takes the Line's name; it has no CIM object of its own. A Fuse's `RatedCurrent` becomes `ratedCurrent (A)`.

| CIM | From |
|---|---|
| `open` | an `Open Line.<name>` command, or the control's `State` (the two must agree) |
| `normalOpen` | the control's `Normal`, else `open` |
| `RecloseSequence` | one per reclosure of a Recloser: `Shots - 1` of them, `<switch>_rs<n>`, `recloseDelay (s)` = `RecloseIntervals[n]` |

A Recloser's unset `Shots` is the engine's 4 and `RecloseIntervals` its 0.5, 2, 2, listed as `defaulted`. Both given and
disagreeing raise, and so does `Shots` above 4 without intervals (the engine reads past its defaults). A switch's
impedance, `length`, `units` and ratings are not CIM and are listed on its row as `untranscribed (a switch)`.

**The `Line` of a switch, on export.** CIM has no switch impedance, so every switch is written with an invented 1 mOhm,
resistive: `r1=1e-3 r0=1e-3 x1=0 x0=0 C1=0 C0=0 length=1 units=m`. Its terminals come from `get_switch_sides`, so an open
tie between two different phases (`bus1=n2.3 bus2=n6.3`, or `.2` to `.3`) is written side by side; one that is closed in
either state raises. The class is lossy: every switch class but `Fuse` and `Recloser` is written as a `SwtControl` on a
plain switch line, and comes back a `LoadBreakSwitch`.

**Controls on export.**

| CIM | DSS | Written when |
|---|---|---|
| `Fuse` | `Fuse` with `MonitoredObj`, `RatedCurrent`, `Normal`, `State` | always; `Normal` and `State` one value per phase, because the engine sets a fuse phase by phase and `State=open` alone opens phase 1 |
| `Recloser` | `Recloser` with `MonitoredObj`, `Shots` = sequences + 1, `RecloseIntervals` | always; no sequences is `Shots=1` |
| any other switch class | `SwtControl` with `SwitchedObj`, `Normal`, `State` | the switch is open in either state |

A Fuse or Recloser is written with `enabled=No`, until CIM can carry its trip settings: cim18v17 has no home for them or
for a curve, so the engine's defaults would trip it on the first snapshot and de-energize what is behind it.
Disabled, it leaves the switch as CIM says, and the importer reads it back as the same class. `State` follows
`to_model(..., switch_state=...)`: `'actual'` (default) reads `Switch.open`, `'normal'` reads `Switch.normalOpen`, for a
model whose `open` is unset. Reclose sequences on any other protected switch raise.

**Fuse**

| property | import | export |
|---|---|---|
| `name` | untranscribed: the switch takes the Line's name; the Fuse names no CIM object | written: Names, the switch's |
| `SwitchedObj` | structural: the Line it switches: SwitchedObj, else MonitoredObj (the DSS default); not a Switch=y line raises | not written: the engine takes MonitoredObj |
| `Normal` | structural: Normal -> normalOpen, State -> open on the switch; with an Open command on the line they must agree | written: get_switch_state(which='normal'); written only when open in either state; one value per phase (the engine sets a fuse per phase) |
| `State` | structural: Normal -> normalOpen, State -> open on the switch; with an Open command on the line they must agree | written: get_switch_state(which=switch_state), 'actual' unless the caller asks 'normal'; written only when open in either state; one value per phase (the engine sets a fuse per phase) |
| `Action` | raises when set (not mapped yet) (the deprecated form of State) | not written: no home on a Switch (untranscribed on import) |
| `enabled` | untranscribed: a disabled control leaves its switch in place; no home | written by rule: no: no trip settings or curve in CIM yet, so the engine's defaults would trip it |
| `like` | untranscribed: the reader resolves like= before mapping | not written: the writer never writes like= |
| `MonitoredObj` | structural: the Line it switches: SwitchedObj, else MonitoredObj (the DSS default); not a Switch=y line raises | written: Line.&lt;the switch's Line name> |
| `RatedCurrent` | copied to `Fuse.ratedCurrent` (A) | written: Switch.ratedCurrent (A) |
| `SwitchedTerm`, `Delay`, `basefreq`, `MonitoredTerm`, `FuseCurve` | untranscribed (listed in the table comment) | not written |

**Recloser**

| property | import | export |
|---|---|---|
| `name` | untranscribed: the switch takes the Line's name; the Recloser names no CIM object | written: Names, the switch's |
| `SwitchedObj` | structural: the Line it switches: SwitchedObj, else MonitoredObj (the DSS default); not a Switch=y line raises | not written: the engine takes MonitoredObj |
| `Normal` | structural: Normal -> normalOpen, State -> open on the switch; with an Open command on the line they must agree | written: get_switch_state(which='normal'); written only when open in either state |
| `State` | structural: Normal -> normalOpen, State -> open on the switch; with an Open command on the line they must agree | written: get_switch_state(which=switch_state), 'actual' unless the caller asks 'normal'; written only when open in either state |
| `Action` | raises when set (not mapped yet) (the deprecated form of State) | not written: protection setting; no home in cim18v17's protection function blocks: the engine's default |
| `enabled` | untranscribed: a disabled control leaves its switch in place; no home | written by rule: no: no trip settings or curve in CIM yet, so the engine's defaults would trip it |
| `like` | untranscribed: the reader resolves like= before mapping | not written: the writer never writes like= |
| `MonitoredObj` | structural: the Line it switches: SwitchedObj, else MonitoredObj (the DSS default); not a Switch=y line raises | written: Line.&lt;the switch's Line name> |
| `Shots` | structural: one `RecloseSequence` per reclosure (see above) | written: the RecloseSequences + 1 (get_reclose_delays); none -> 1, no reclosure |
| `RecloseIntervals` | structural: one `RecloseSequence` per reclosure (see above) | written: each RecloseSequence's recloseDelay (s), in recloseStep order; none -> not written |
| `SwitchedTerm`, `Delay`, `basefreq`, `MonitoredTerm`, `NumFast`, `PhaseFast`, `PhaseDelayed`, `GroundFast`, `GroundDelayed`, `PhaseTrip`, `GroundTrip`, `PhaseInst`, `GroundInst`, `Reset`, `TDPhFast`, `TDGrFast`, `TDPhDelayed`, `TDGrDelayed` | untranscribed (listed in the table comment) | not written |

**SwtControl**

| property | import | export |
|---|---|---|
| `name` | untranscribed: the switch takes the Line's name; the SwtControl names no CIM object | written: Names, the switch's |
| `SwitchedObj` | structural: the Line it switches: SwitchedObj, else MonitoredObj (the DSS default); not a Switch=y line raises | written: Line.&lt;the switch's Line name> |
| `Normal` | structural: Normal -> normalOpen, State -> open on the switch; with an Open command on the line they must agree | written: get_switch_state(which='normal'); written only when open in either state |
| `State` | structural: Normal -> normalOpen, State -> open on the switch; with an Open command on the line they must agree | written: get_switch_state(which=switch_state), 'actual' unless the caller asks 'normal'; written only when open in either state |
| `Action` | raises when set (not mapped yet) (the deprecated form of State) | not written: no home on a Switch (untranscribed on import) |
| `like` | untranscribed: the reader resolves like= before mapping | not written: the writer never writes like= |
| `SwitchedTerm`, `Delay`, `basefreq`, `enabled`, `Lock`, `Reset` | untranscribed (listed in the table comment) | not written |

**Fail fast.**

- A control that switches an object other than a `Line` (`only a Line is mapped`), switches no object, or sets `Action`.
- A control or `Open` that names a `Line` that is not `Switch=y`, or one no `New` defines.
- `Normal` or `State` that is not `open` or `closed` on every phase; two controls of one line that disagree, or of different classes; a Fuse whose `Normal`/`State` give a different count than the line's phases; an `Open` on a line whose control's `State` is closed.

Excerpt from `cimhub_opendss/tests/atoms/line/codes.cimtbl` (a Fuse, a Recloser with defaulted intervals, and an open
LoadBreakSwitch):

```
Table Fuse: mRID, name, node1, node2, phases, ratedCurrent (A), open, normalOpen, BaseVoltage, EquipmentContainer=fdr_atom, normallyInService
    sw_fuse1, fuse1, n1, n4, , 100.0, false, false, bv_4p16kv,

Table LoadBreakSwitch: mRID, name, node1, node2, phases, open, normalOpen, BaseVoltage, EquipmentContainer=fdr_atom, normallyInService
    sw_sect, sect, n1, n7, ,  true,  true,  bv_4p16kv,

Table RecloseSequence: mRID, ProtectedSwitch, recloseStep, recloseDelay (s)
    # defaulted: RecloseIntervals=(0.5 2.0)
    sw_rec1_rs1, sw_rec1, 1, 0.5
    sw_rec1_rs2, sw_rec1, 2, 2.0
```

## Reactor

A series `Reactor` (`bus1` and `bus2` on different buses) is a `SeriesCompensator` between its buses: `r` and `x` per phase
in ohm, with `r0 = r` and `x0 = x` because DSS gives it no mutual coupling. `SeriesCompensator` has no per-phase class,
so a reactor of fewer than three phases gives its generated Terminals their phases in an `Update Table Terminal`. A
reactor's own `normamps` and `emergamps` are an `OperationalLimitSet`, as a line's, and nothing comes from the engine's
kvar-derived default.

| property | import | export |
|---|---|---|
| `name` | copied to `SeriesCompensator.name`; mRID = rx_ + name, lowercased | written: Names, the Reactor namespace |
| `bus1` | structural: node1 and the phases (the line rule) | written: terminal_buses (line.py): the first terminal on the phase conductors |
| `bus2` | structural: node2; unset or on bus1's bus (a shunt or neutral reactor) raises | written: terminal_buses: the second terminal |
| `phases` | structural: the conductor count; default 3 | written: the phase conductors |
| `kvar` | raises when set (not mapped yet) (X from kvar and kV) | not written: R and X carry the impedance; r0/x0 other than r/x raise |
| `Rmatrix`, `Xmatrix` | raises when set (not mapped yet) | not written: R and X carry the impedance; r0/x0 other than r/x raise |
| `Parallel` | raises when yes: raises when set (not mapped yet) | not written: R and X carry the impedance; r0/x0 other than r/x raise |
| `R` | copied to `SeriesCompensator.r` (ohm); `SeriesCompensator.r0` (ohm); per phase; r0 = r (no mutual); default 0 | written: get_series_compensator r (ohm) |
| `X` | copied to `SeriesCompensator.x` (ohm); `SeriesCompensator.x0` (ohm); per phase; x0 = x (no mutual); unset raises | written: get_series_compensator x (ohm) |
| `Rp` | raises when set (not mapped yet) (a parallel R) | not written: R and X carry the impedance; r0/x0 other than r/x raise |
| `Z1`, `Z2`, `Z0`, `Z` | raises when set (not mapped yet) | not written: R and X carry the impedance; r0/x0 other than r/x raise |
| `RCurve`, `LCurve` | raises when set (not mapped yet) | not written: untranscribed or raising on import; not in CIM |
| `LmH` | raises when set (not mapped yet) (X from an inductance) | not written: R and X carry the impedance; r0/x0 other than r/x raise |
| `normamps` | structural: instance OperationalLimitSet rx_&lt;name>_limits: CurrentLimit _norm (olt_normal); nothing from the engine's kvar-derived default | written: get_current_limits normal (A); unset -> not written |
| `emergamps` | structural: CurrentLimit _emerg (olt_emergency) in rx_&lt;name>_limits | written: get_current_limits emergency (A); unset -> not written |
| `enabled` | copied to `SeriesCompensator.normallyInService`; default true | written: get_in_service(which='normal'); unset -> not written |
| `like` | untranscribed: the reader resolves like= before mapping | not written: the writer never writes like= |
| `kv`, `conn`, `faultrate`, `pctperm`, `repair`, `basefreq` | untranscribed (listed in the table comment) | not written |

**Fail fast.** `kvar`, `Rmatrix`, `Xmatrix`, `Rp`, `Z`, `Z0`, `Z1`, `Z2`, `RCurve`, `LCurve`, `LmH` and `Parallel=yes` raise.
`bus2` unset or on `bus1`'s bus (a shunt or neutral reactor) raises, and so does an unset `X`. On export, `r0` or `x0`
different from `r` or `x`, or a varistor, raises.

Excerpt from `cimhub_opendss/tests/atoms/reactor/reactors.cimtbl`:

```
Table SeriesCompensator: mRID, name, node1, node2, r (ohm), x (ohm), r0 (ohm), x0 (ohm), normallyInService, BaseVoltage, EquipmentContainer=fdr_atom
    # defaulted: phases=3, Parallel=false, enabled=true
    rx_hvmv_sub_hsb, HVMV_Sub_HSB, sourcebus, b0, 0.0, 14.798306633595042, 0.0, 14.798306633595042, true, bv_4p16kv
```

## Run it

This imports lines by geometry and by spacing, and exports them. It runs from the repository root.

```python
from pathlib import Path

from cimhub_opendss import DssReader, cim_to_dss, dss_to_cim

deck = Path("cimhub_opendss/tests/atoms/line/geometry.dss")
network = dss_to_cim(DssReader(deck).read_all(), name="geometry")
cim_to_dss(network, "/tmp/ref-lines.dss", name_source="name")
for line in Path("/tmp/ref-lines.dss").read_text().splitlines():
    if line.startswith(("new Linegeometry.601", "new Line.")):
        print(line)
```

```
new Linegeometry.601 nconds=4 nphases=3 reduce=Yes cond=1 wire=ACSR_556_5 x=-1.2192 h=8.5344 units=m cond=2 wire=ACSR_556_5 x=-0.3048 h=8.5344 units=m cond=3 wire=ACSR_556_5 x=0.9144 h=8.5344 units=m cond=4 wire=ACSR_4/0 x=0 h=7.3152 units=m
new Line.g601 geometry=601 phases=3 bus1=sourcebus.1.2.3 bus2=n1.1.2.3 length=152.4 rho=100 units=m normamps=730 emergamps=1095
new Line.g_m geometry=601 phases=3 bus1=n1.1.2.3 bus2=n2.1.2.3 length=100 rho=100 units=m normamps=730 emergamps=1095
new Line.s510 geometry=s510 phases=1 bus1=n1.3 bus2=n3.3 length=91.44 rho=100 units=m normamps=230 emergamps=300
```

The positions are in metres (`500 ft` is `152.4 m`), the ratings the lines took from their wires are now on the lines, and
`s510`, which was `spacing=510` with wires, is a geometry of its own.
