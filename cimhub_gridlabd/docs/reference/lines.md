# Lines, conductors and switches

Everything that carries current between two buses and is not a transformer: the conductor catalogs, spacings and
configurations, lines, switching devices, and series reactors. How to read the tables is on the
[reference landing page](index.md).

| GLM | CIM (cim18v17) | Import (shape) | Export |
|---|---|---|---|
| `overhead_line_conductor` | `OverheadWireInfo` | `overhead_line_conductor.cimtbl` (`wire_info`) | `overhead_line_conductor` |
| `underground_line_conductor` | `ConcentricNeutralCableInfo`, `TapeShieldCableInfo`, or a bare `OverheadWireInfo` | `underground_line_conductor.cimtbl` (`wire_info`) | `underground_line_conductor` |
| `triplex_line_conductor` | `OverheadWireInfo` | `triplex_line_conductor.cimtbl` (`wire_info`) | `triplex_line_conductor` |
| `line_spacing` | `ConductorDistanceSpacing` (template) + `ConductorDistance` | `line_spacing.cimtbl` | `line_spacing`, one per way lines use it |
| `line_configuration`, geometry | `WireConfiguration` + `WireSequenceConfiguration` | `line_configuration.cimtbl` (`line_by_wire_configuration`) | `line_configuration` |
| `line_configuration`, matrix | `PerLengthPhaseImpedance` (template) + `PhaseImpedanceData`; a `WireConfiguration` `lc_<name>_wc` | `line_configuration.cimtbl` (`line_by_impedance`) | `line_configuration` |
| `triplex_line_configuration` | `WireConfiguration` + `WireSequenceConfiguration` on a derived `ConductorDistanceSpacing` | `triplex_line_configuration.cimtbl` | `triplex_line_configuration` |
| `overhead_line`, `underground_line`, `triplex_line` | `ACLineSegment`, `OperationalLimitSet` + `CurrentLimit` | `overhead_line.cimtbl`, `underground_line.cimtbl`, `triplex_line.cimtbl` | the three line classes |
| `switch` | `LoadBreakSwitch` | `switch.cimtbl` (`switch`) | `switch`, for every `Switch` class but the next three |
| `fuse` | `Fuse` | `fuse.cimtbl` (`switch`) | `fuse` |
| `recloser` | `Recloser` | `recloser.cimtbl` (`switch`) | `recloser` |
| `sectionalizer` | `Sectionaliser` | `sectionalizer.cimtbl` (`switch`) | `sectionalizer` |
| `series_reactor` | `SeriesCompensator` | `series_reactor.cimtbl` (`series_compensator`) | `series_reactor` |

The shapes are on the core site's [shapes page](https://pnnl-cim-tools.github.io/CIMHub/core/developer/shapes/), and the
getters the exporter reads through (`get_line_code`, `get_line_geometry`, `get_wire_info`, `get_stored_distances`,
`get_current_limits`) are on its [lines reference](https://pnnl-cim-tools.github.io/CIMHub/core/reference/lines/).

**Geometry stays geometry.** A `line_configuration` with a `line_spacing` and conductors becomes a `WireConfiguration`
that names a `ConductorDistanceSpacing` and the wires. GridLAB-D gives distances between conductors and heights above
earth, never coordinates, so the spacing keeps them as distances. No impedance is computed from geometry, on import or
export; the consumer's line constants do that. A matrix configuration is a template: its impedance has `isTemplate=true`
and sits on a `WireConfiguration` that names no spacing, and the lines that use it name that `WireConfiguration`.

**Units.** On import every length-based value keeps the deck's unit, in the column header (`gmr (ft)`,
`rAC50 (ohm/mile)`, `length (ft)`, `b (nS/mile)`); a value with an inline unit (`length 21 m`) gets its own header and its
own table. On export every value is in the unit the GLM slot declares: lengths in feet, conductor diameters in inches,
resistances and impedances per mile, capacitance in nF per mile, ratings in amperes.

**Ratings.** A link's `continuous_rating_X` and `emergency_rating_X` become the normal and emergency `CurrentLimit` of
the equipment's own `OperationalLimitSet` `<mRID>_limits`. One rating per link is mapped, so per-phase ratings that differ
raise. On export the limits are written on each of the link's phases (a triplex line's on its service letter).

## Conductors

One `WireInfo` per conductor, in one artifact per GLM class, with the values as the deck writes them. An underground
conductor with `neutral_strands` above zero is a `ConcentricNeutralCableInfo`; with `shield_thickness` above zero a
`TapeShieldCableInfo`; with neither, a bare `OverheadWireInfo`. Both set raises. A triplex conductor is an
`OverheadWireInfo`, since CIM has no triplex class and the insulation is on the configuration. A conductor that sets its
summer ratings gets `ratedCurrent` and an `OperationalLimitSet` `<mRID>_limits` on `AssetInfo`; ratings left unset are
not filled, and the row comment says so.

The three `WireInfo` mRIDs are `ohc_`, `ugc_` and `tpc_` plus the GLM name.

### overhead_line_conductor and triplex_line_conductor

| property | import | export |
|---|---|---|
| `name` | copied to `OverheadWireInfo.name` | written: Names |
| `geometric_mean_radius` | copied to `gmr` (`ft`); unset raises (GridLAB-D would take 0, and ln(1/GMR) fails) | written: `get_wire_info` `gmr` (ft); unset raises |
| `resistance` | copied to `rAC50` (`ohm/mile`), the 50 C AC value; unset raises | written: `rAC50`, else `rAC25`; neither raises |
| `diameter` (overhead only) | derived: `radius` = `diameter / 2` (`in`) | written: 2 x `radius`; unset when the radius is |
| `rating_summer_continuous` | copied to `ratedCurrent` (A); also the normal `CurrentLimit` of the wire's limit set | written: the wire's normal limit, else `ratedCurrent` |
| `rating_summer_emergency` | structural: the emergency `CurrentLimit` | written: the wire's emergency limit |
| `rating_winter_continuous`, `rating_winter_emergency` | untranscribed; a value that differs from its summer rating raises | not written |
| object header (`parent`, `groupid`, `latitude`, `longitude`, `in_svc`, `out_svc`, `rank`, `flags`) | untranscribed | not written |

### underground_line_conductor

| property | import | export |
|---|---|---|
| `name` | copied to the cable's `name` | written: Names; `<wire>_<class>` when one `WireInfo` is two GLM classes |
| `conductor_gmr` | copied to `gmr` (`ft`); unset raises | written: `gmr` |
| `conductor_resistance` | copied to `rAC50` (`ohm/mile`); unset raises | written: `rAC50`, else `rAC25` |
| `conductor_diameter` | derived: `radius` = `conductor_diameter / 2` (`in`) | written: 2 x `radius`; a buried bare wire without a radius raises |
| `outer_diameter` | copied to `diameterOverJacket` (`in`) on a cable; untranscribed on a bare wire | written: a cable's `diameterOverJacket`; a bare wire's 1.2 x its diameter (CIM has no jacket, GridLAB-D needs one) |
| `neutral_strands` | copied to `neutralStrandCount`; above zero selects `ConcentricNeutralCableInfo` | written: `neutralStrandCount` |
| `neutral_gmr` | copied to `neutralStrandGmr` (`ft`) | written |
| `neutral_diameter` | derived: `neutralStrandRadius` = `neutral_diameter / 2` (`in`) | written: 2 x `neutralStrandRadius` |
| `neutral_resistance` | copied to `neutralStrandRDC20` (`ohm/mile`), the strand's DC value | written |
| `shield_thickness` | copied to `tapeThickness` (`in`); above zero selects `TapeShieldCableInfo` | written |
| `shield_diameter` | copied to `diameterOverScreen` (`in`) | written |
| `shield_gmr`, `shield_resistance` | untranscribed: no CIM home; they follow from the screen diameter and tape thickness | written, for a tape shield only: `shield_gmr` = `diameterOverScreen` / 2, `shield_resistance` = 18.826 / (d x T) ohm/mile, d in inches and T in mils (a tape-shield cable is told by `shield_gmr` above zero) |
| `insulation_relative_permitivitty` | untranscribed: no `CableInfo` home | not written |
| `rating_summer_*`, `rating_winter_*`, object header | as the overhead conductor | as the overhead conductor |

**Fail fast.** A conductor without its GMR or resistance. An underground conductor with both `neutral_strands` and
`shield_thickness`. A cable property set on the wrong kind (a neutral strand on a tape shield). A winter rating that
differs from its summer one. On export, a `WireInfo` with neither `rAC50` nor `rAC25`, or without a `gmr`, and a tape
shield without `diameterOverScreen` and `tapeThickness`.

**Expected differences.** A conductor comes back in the class of the configuration that uses it: `underground_line_conductor`
where any wire of the configuration is a cable, `triplex_line_conductor` in a triplex configuration, else
`overhead_line_conductor`. Only conductors some line uses are written. A cable's `shield_gmr` and `shield_resistance` are
recomputed.

Excerpt from `cimhub_gridlabd/tests/atoms/catalog/catalog.overhead_line_conductor.cimtbl`:

```
Table OverheadWireInfo: mRID, name, gmr (ft), rAC50 (ohm/mile), ratedCurrent (A), OperationalLimitSet
    # not filled: rating.summer.emergency
    ohc_overhead_line_conductor:3, overhead_line_conductor:3, 0.00814, 0.563, 334.0, ohc_overhead_line_conductor:3_limits

# derived (radius_from_diameter): radius = diameter / 2
Table OverheadWireInfo: mRID, name, gmr (ft), rAC50 (ohm/mile), ratedCurrent (A), radius (in), OperationalLimitSet
    # untranscribed: rating_winter_continuous=730.0, rating_winter_emergency=730.0
    ohc_wire_acsr_556_5, wire_acsr_556_5, 0.0311, 0.18972, 730.0, 0.4635, ohc_wire_acsr_556_5_limits
```

## line_spacing

A `line_spacing` is a `ConductorDistanceSpacing` template, `spc_<name>`, with `isTemplate=true`, and a
`ConductorDistance` for each distance the deck writes. A distance between two conductors names both ends (`sequenceNumber1`,
`fromPhase`, `sequenceNumber2`, `toPhase`); a height is a distance to a position of kind `earth`, with no second number or
phase. The sequence numbers are 1 to n, in A, B, C, N order, over the phases the written non-zero distances name. A
distance of 0 is GridLAB-D's "no mutual term" (and its default), not two coincident conductors, so it is not written; the
spacing's comment lists it. One `ConductorDistance` table is written per unit.

| property | import | export |
|---|---|---|
| `name` | copied to `ConductorDistanceSpacing.name`; mRID `spc_` + name; `isTemplate` is true | written: Names; `<spacing>_<letters>` when lines use it on different phases |
| `distance_AB`, `distance_AC`, `distance_BC`, `distance_AN`, `distance_BN`, `distance_CN` | structural: one `ConductorDistance`, `distance` in the written unit; unset or 0 is no row | written: `get_stored_distances` between the two phases' sequence numbers; none stored: unset |
| `distance_AE`, `distance_BE`, `distance_CE`, `distance_NE` | structural: the conductor's height, a distance to earth; unset or 0 is no row | written: the stored height (an `XYSpacing`'s y; a line with a `ySpacingOffset` raises) |
| object header | untranscribed | not written |

**Fail fast.** A configuration whose conductors are not the phases its spacing names.

**Expected differences.** A spacing is written once per way the lines use it. A spacing that came from CIM coordinates
(an `XYSpacing`) is written as distances and heights, which is all GridLAB-D keeps.

Excerpt from `cimhub_gridlabd/tests/atoms/catalog/catalog.line_spacing.cimtbl`:

```
Object ConductorDistanceSpacing: mRID=spc_spc_601_ABCN, name=spc_601_ABCN, isTemplate=true

Table ConductorDistance: mRID, ConductorDistanceSpacing=spc_spc_601_ABCN, sequenceNumber1, conductorKind1, fromPhase, sequenceNumber2, conductorKind2, toPhase, distance (ft)
    spc_spc_601_ABCN_AB, 1, phase,   A, 2, phase,   B, 2.5
    spc_spc_601_ABCN_AN, 1, phase,   A, 4, neutral, N, 5.6569
    spc_spc_601_ABCN_AE, 1, phase,   A, ,  earth,   ,  28.0
    spc_spc_601_ABCN_NE, 4, neutral, N, ,  earth,   ,  24.0
```

(rows abridged) The spacing's own name is `spc_601_ABCN`, so its mRID reads `spc_spc_601_ABCN`.

## line_configuration

A configuration is geometry (`spacing` with `conductor_A` to `conductor_N`) or a matrix (`z11` to `z33`, `c11` to `c33`),
never both. A record with both raises, as does one with neither, because GridLAB-D would use the matrix.

**Geometry.** A `WireConfiguration` `wc_<name>`, `numberOfPhases` the A, B, C conductors set, `WireSpacing` the
spacing, and a `WireSequenceConfiguration` per conductor, numbered 1 to n in A, B, C, N order, as its spacing's positions
are. The conductors must be the phases the spacing names.

**Matrix.** A template `PerLengthPhaseImpedance` `lc_<name>` (`isTemplate=true`, `calculatedFrequency` the base frequency),
a `PhaseImpedanceData` row per lower-triangle element, and a `WireConfiguration` `lc_<name>_wc` that holds it and names no
spacing. The rows and columns are compacted to 1 to n over the phases whose `z_ii` is set and non-zero, so a matrix on A and
C has two rows. `r` and `x` are the real and imaginary parts of `z`, in the written unit (`ohm/mile`). `b` is derived from
`c` as `2 pi f c` (`b_from_c`, nF to nS) at the base frequency, in `nS/mile`. A mutual term left unset is GridLAB-D's 0 and
the row comment says `defaulted`. GridLAB-D's matrix is the Kron-reduced A, B, C one and has no neutral terms, so it is
written as given.

| property | import | export |
|---|---|---|
| `name` | copied to `WireConfiguration.name` and `PerLengthPhaseImpedance.name`; mRID `wc_` or `lc_` + name | written: Names; `<template>_<letters>` when lines use it on different phases |
| `spacing` | structural: geometry, `WireConfiguration.WireSpacing` = `spc_` + spacing; without conductors raises | written: the `line_spacing` of the configuration |
| `conductor_A`, `conductor_B`, `conductor_C`, `conductor_N` | structural: geometry, one `WireSequenceConfiguration` each, `WireInfo` the conductor's mRID; must be a conductor of the line's class | written: the wire at the line's phase's sequence number |
| `z11` to `z33` | structural: matrix, `PhaseImpedanceData.r` and `x`; `z_ij` must equal `z_ji`; an off-diagonal term without both diagonals raises | written: r + jx (`ohm/mile`) by phase letter, a neutral row Kron-reduced out; a sequence code is expanded by the getter |
| `c11` to `c33` | derived: `PhaseImpedanceData.b` = `b_from_c(c)` (`nS/mile`); in nF per length only | written: `c_from_b(b)` (`nF/mile`) at the base frequency; `b` unset: unset |
| `rating_summer_*`, `rating_winter_*` | structural: not on the template; the line mapper puts the configuration's on each line that sets none | unset: ratings are each line's own |
| object header | untranscribed | not written |

**Fail fast.** A matrix and geometry together, or neither. `spacing` without conductors or the reverse. Conductors that
are not the spacing's phases. A conductor or spacing that names no object, or an object of the wrong class (a triplex
conductor on a `line_configuration`). A `z_ij` that differs from `z_ji`. Every `z_ii` unset or 0. A `c` written in other
than nF per length. A matrix whose `z` values are in different units. On export, a `WireConfiguration` that has neither a
`WireSpacing` nor a `PerLengthImpedance` (its own or the line's); a `PerLengthImpedance` and a different `WireConfiguration`
impedance on one line.

**Expected differences.** A template that lines use on different phases is one GLM configuration per use,
`<template>_<letters>`; a template no line uses is not written. A sequence code (`PerLengthSequenceImpedance`) comes back
as a matrix, since GridLAB-D has no sequence form. A neutral row of a matrix is Kron-reduced out. Geometry lines are not
reduced to impedance in either direction, so each engine computes its own line constants.

Excerpt from `cimhub_gridlabd/tests/atoms/catalog/catalog.line_configuration.cimtbl` (geometry `lcon_601`, matrix
`lcon_mtx604_AC`):

```
Object WireConfiguration: mRID=wc_lcon_601, name=lcon_601, numberOfPhases=3, WireSpacing=spc_spc_601_ABCN

Table WireSequenceConfiguration: mRID, WireConfiguration=wc_lcon_601, sequenceNumber, WireInfo
    wc_lcon_601_A, 1, ohc_wire_acsr_556_5
    wc_lcon_601_N, 4, ohc_overhead_line_conductor:3

Object PerLengthPhaseImpedance: mRID=lc_lcon_mtx604_AC, name=lcon_mtx604_AC, conductorCount=2, calculatedFrequency (Hz)=60.0, isTemplate=true

# derived: b = 2 pi f c (b_from_c)
Table PhaseImpedanceData: identifier, PhaseImpedance=lc_lcon_mtx604_AC, row, column, r (ohm/mile), x (ohm/mile), b (nS/mile)
    # z31 (CA); defaulted: c = 0
    lc_lcon_mtx604_AC_21, 2, 1, 0.2066, 0.4591, 0.0
```

(rows abridged)

## triplex_line_configuration

A triplex configuration is geometry too, but GridLAB-D computes its spacing from `diameter` and `insulation_thickness`:
the two insulated phase conductors touch, and the bare neutral touches both. The importer writes that spacing as a derived
`ConductorDistanceSpacing` `wc_<name>_spc` with positions `s1`, `s2`, `N` (1, 2, 3), and a `WireConfiguration`
`wc_<name>` with `numberOfPhases` 2 and a `WireSequenceConfiguration` per conductor.

| property | import | export |
|---|---|---|
| `name` | copied to `WireConfiguration.name`; mRID `wc_` + name | written: Names, as `line_configuration` |
| `conductor_1`, `conductor_2`, `conductor_N` | structural: `WireSequenceConfiguration` 1, 2, 3 (spacing phases `s1`, `s2`, `N`); required | written: the wire at `s1`, `s2`, `N` |
| `diameter`, `insulation_thickness` | derived: the spacing's distances, D12 = `diameter` + 2 `insulation_thickness`, D1N = D2N = `diameter` + `insulation_thickness` (`in`); both required, in one unit | written: `insulation_thickness` = D12 - D1N, `diameter` = 2 D1N - D12 |
| `spacing`, `conductor_A`, `conductor_B`, `conductor_C` | raises when set: GridLAB-D's triplex line does not read them | unset |
| `z11` to `z33`, `c11` to `c33` | raises when set (no readable deck sets a triplex matrix) | written, for a line whose impedance is a matrix: `z11`, `z12`, `z21`, `z22` on `s1`, `s2`, with `N` Kron-reduced out; `c` is never written |
| `rating_summer_*`, `rating_winter_*` | structural: as `line_configuration` | unset: ratings are each line's own |
| object header | untranscribed | not written |

**Fail fast.** A conductor, `diameter` or `insulation_thickness` unset. A D12 or D1N that is not positive. A conductor of
a class other than `triplex_line_conductor`. On export, a triplex spacing without `s1`, `s2` and `N` positions, or whose
D1N and D2N differ by more than a relative 1e-5: GridLAB-D's triplex spacing is symmetric.

**Expected differences.** A triplex matrix's susceptance is not written, and is logged once per configuration:
GridLAB-D's `triplex_line` has no shunt admittance, so no slot holds it. IEEE 8500's triplex codes carry about 0.1 VAr
per kft at 240 V. The importer in turn raises on any `z` or `c` of a triplex configuration, so a deck exported from a CIM triplex matrix is not read back.

Excerpt from `cimhub_gridlabd/tests/atoms/catalog/catalog.triplex_line_configuration.cimtbl`:

```
# derived (triplex_spacing): D12 = diameter + 2 insulation_thickness, D1N = D2N = diameter + insulation_thickness; diameter=0.522, insulation_thickness=0.08 in
Object ConductorDistanceSpacing: mRID=wc_triplex_line_configuration:1_spc, name=triplex_line_configuration:1, isTemplate=true

Table ConductorDistance: mRID, ConductorDistanceSpacing=wc_triplex_line_configuration:1_spc, sequenceNumber1, conductorKind1, fromPhase, sequenceNumber2, conductorKind2, toPhase, distance (in)
    wc_triplex_line_configuration:1_spc_12, 1, phase, s1, 2, phase,   s2, 0.682
    wc_triplex_line_configuration:1_spc_1N, 1, phase, s1, 3, neutral, N,  0.602
```

## overhead_line, underground_line, triplex_line

A line is an `ACLineSegment` `ln_<name>`, in `EquipmentContainer` `fdr_<feeder>`, that names its configuration's
`WireConfiguration` (`wc_<configuration>`, or `lc_<configuration>_wc` for a matrix) and the walk's `BaseVoltage`. Its
`node1` and `node2` are the root buses of `from` and `to`. The `phases` cell is written in the configuration's own order
(A, B, C, then N, and `s1s2N` on a triplex line) because the per-phase objects are numbered in that order, and it must
name the configuration's phases: a geometry line's must equal its conductors, a matrix line's its diagonal (a matrix
line never reads `N`, so it is dropped from the cell). A table is written per length unit, then the limit sets.

| property | import | export |
|---|---|---|
| `name` | copied to `ACLineSegment.name`; mRID `ln_` + name | written: Names |
| `phases` | structural: the `phases` cell as above; `D` on any line, `S` on a non-triplex line, or a triplex line other than `AS`, `BS`, `CS` raises | written: the line's A, B, C, then `N` when it has a neutral conductor; a triplex line its buses' service letter, then `S` |
| `from`, `to` | structural: `node1`, `node2`, the root bus of the object named | written: terminal 1's and terminal 2's bus |
| `length` | copied to `length` (`ft`, or the unit the deck writes); unset raises (GridLAB-D's 0 is a line of no impedance) | written: `ACLineSegment.length` (ft); unset raises |
| `configuration` | structural: the `WireConfiguration`; must be this line class's configuration (a `triplex_line_configuration` on a `triplex_line`, a `line_configuration` on the others); unset raises | written: the configuration of the line's template |
| `continuous_rating_A` to `_C`, `emergency_rating_A` to `_C` | structural: the normal and emergency `CurrentLimit` of `ln_<name>_limits`; else the configuration's, noted `ratings: from ...` | written: `get_current_limits` on each of the line's phases |
| `status` | structural: unset or `CLOSED`; `OPEN` raises (a line is not a switch) | not written |
| `nominal_voltage`, `mean_repair_time`, `pdispatch`, `pdispatch_offset`, `set_pdispatch`, solver outputs (`power_*`, `current_*`, `fault_*`, `flow_direction`, `overloaded_status`), `inrush_*`, object header | untranscribed | not written |

A line's own rating that differs from its configuration's raises.

The exporter picks the GLM class from the line. A split-phase line (`s1`, `s2`) is a `triplex_line`; a geometry line whose
wires include a cable is an `underground_line`; every other line is an `overhead_line`. A line is geometry when its
`WireConfiguration` names a `WireSpacing`, whatever else it has; otherwise its impedance (the line's own
`PerLengthImpedance`, else its `WireConfiguration`'s) is a matrix configuration; neither raises.

**Fail fast.** A line without `configuration`, `length` or `phases`. A configuration of the wrong class. An overhead line on
underground conductors, or the reverse, and an underground line whose phase cables are not one kind. A geometry line
whose phases are not its configuration's conductors, or a matrix line whose phases are not its diagonal. A triplex line
whose ends the walk does not put on a split-phase system. A `status OPEN`. Ratings that differ across a link's phases.

**Expected differences.** The configuration's ratings come back on each line. A line length is written in feet, so a
`21 m` line comes back as 68.8976 ft. A line keeps its name; the configuration it names may be renamed (`line_configuration:18`
returns as `line_configuration_18`). Phases come back in A, B, C, N order (`CA` returns as `AC`).

Excerpt from `cimhub_gridlabd/tests/atoms/line/line.overhead_line.cimtbl`:

```
Table ACLineSegment: mRID, name, node1, node2, phases, length (ft), WireConfiguration, BaseVoltage, EquipmentContainer=fdr_line
    ln_l1,      l1,      src, n1, ABCN, 500.0, wc_lcon_601,          bv_4p16kv
    ln_line_l2, line_l2, n1,  n4, AC,   300.0, lc_lcon_mtx604_AC_wc, bv_4p16kv

Table ACLineSegment: mRID, name, node1, node2, phases, length (m), WireConfiguration, BaseVoltage, EquipmentContainer=fdr_line
    ln_overhead_line:3, overhead_line:3, n1, n5, AN, 21.0, wc_line_configuration:18, bv_4p16kv
```

The steps from a deck to this table, and back to a deck:

```python
from cimtables.document import format_document
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.importer.glm_to_cimtbl import GlmImporter, glm_to_cim
from cimhub_gridlabd.exporter.cim_to_glm import GlmExporter

model = GlmReader("cimhub_gridlabd/tests/atoms/line/line.glm").read_all()
documents = GlmImporter("line").to_cimtbl(model)
lines = next(part for part in documents.parts if part.name == "overhead_line")
print("\n".join(format_document(lines).splitlines()[6:9]))

network = glm_to_cim(model, name="line")
exported = GlmExporter().to_model(network, name_source="name")
cls = next(c for c in exported.graph if c.class_name == "line_configuration")
print(sorted(record.name for record in exported.graph[cls].values()))
```

## switch, fuse, recloser, sectionalizer

A switching device is a `LoadBreakSwitch`, `Fuse`, `Recloser` or `Sectionaliser` `sw_<name>`, in one artifact per GLM
class. A `sectionalizer` adds no properties to `switch`, so it maps the same way. GLM gives a
device one state, `status`, so it becomes both `open` and `normalOpen`. The `phases` cell is the switched conductors with
`N` dropped, and blank when they are A, B and C. A switching device `OPEN` between laterals on different phases (a tie from
an A lateral to a B one) takes `phaseSide1`, the switched conductors, and `phaseSide2`, its `to` end's, instead of
`phases`, with a row note. GridLAB-D cannot load that deck, but CIM holds it.

| property | import | export |
|---|---|---|
| `name` | copied to the device's `name`; mRID `sw_` + name | written: Names |
| `phases` | structural: the switched conductors A, B, C, `N` dropped; blank when ABC; none of A, B, C raises | written: side 1's A, B, C |
| `from`, `to` | structural: `node1`, `node2`, root buses | written: terminal 1's and terminal 2's bus |
| `status` | structural: `OPEN` is `open` and `normalOpen` true; unset is `CLOSED`, listed as `defaulted` | written: `OPEN` or `CLOSED` from `get_switch_state`, by the caller's `switch_state`: `"actual"` (`Switch.open`, the default) or `"normal"` (`normalOpen`) |
| `phase_A_state`, `phase_B_state`, `phase_C_state` (`switch`, `recloser`) | structural: must equal `status` on a phase the device has, else raises; on a phase it lacks, listed on the row | not written |
| `phase_A_status`, `phase_B_status`, `phase_C_status` (`fuse`) | structural: unset or `GOOD`; `BLOWN` on a phase the fuse has raises | not written |
| `current_limit` (`fuse`) | copied to `Fuse.ratedCurrent` (A); unset: not filled, the row says so | written: `Fuse.ratedCurrent` |
| `continuous_rating_A` to `_C`, `emergency_rating_A` to `_C` | structural: the device's `<mRID>_limits` | written: `get_current_limits`, on side 1's phases |
| `operating_mode`, `switch_impedance`, `switch_resistance`, `switch_reactance`, `fuse_resistance` | untranscribed: a numerical stand-in for a closed device, or the operating mode (with every phase state equal to `status` the modes act alike) | not written |
| `retry_time`, `max_number_of_tries`, `number_of_tries` (`recloser`) | untranscribed: protection settings and state | not written |
| `repair_dist_type`, `mean_replacement_time` (`fuse`), `mean_repair_time` | untranscribed: reliability data | not written |
| `nominal_voltage`, solver outputs, object header | untranscribed | not written |

**Fail fast.** A phase state that differs from `status` on a phase the device has; a `BLOWN` fuse phase; phases other
than A, B, C and N; an end that is no bus object; phases that are not on both end objects (only an `OPEN` device between laterals on different phases may differ).

**Expected differences.** On export a CIM `Sectionaliser` is a `sectionalizer`, a `Fuse` a `fuse`, a `Recloser` a `recloser`, and every other switch class a
`switch`: GridLAB-D has no breaker. A recloser's retry settings, a fuse's resistance and all per-phase states are lost.
A tie across phases is written on side 1's phases.

Excerpt from `cimhub_gridlabd/tests/atoms/line/line.switch.cimtbl` and `line.fuse.cimtbl`:

```
Table LoadBreakSwitch: mRID, name, node1, node2, phases, open, normalOpen, BaseVoltage, EquipmentContainer=fdr_line
    sw_swt_s1, swt_s1, n1, n2, ,  false, false, bv_4p16kv
    sw_swt_s2, swt_s2, n5, n7, A, true,  true,  bv_4p16kv

Table Fuse: mRID, name, node1, node2, phases, ratedCurrent (A), open, normalOpen, BaseVoltage, EquipmentContainer=fdr_line
    # untranscribed: mean_replacement_time=3600.0
    sw_fuse_1, fuse_1, n4, n8, C, 50000.0, false, false, bv_4p16kv
    # not filled: current_limit
    sw_fuse_2, fuse_2, n5, n9, A, ,        false, false, bv_4p16kv
```

## series_reactor

A `series_reactor` is a `SeriesCompensator` `rx_<name>`. GridLAB-D's reactor is one impedance per phase with no coupling
between phases, while CIM's `SeriesCompensator` is one `r` + j`x` for every phase, so the phases' `phase_X_impedance` must
be equal. `r0` and `x0` are written equal to `r` and `x`. `SeriesCompensator` has no per-phase class, so a reactor on fewer
than three phases gives its two Terminals those phases in an `Update Table Terminal`.

| property | import | export |
|---|---|---|
| `name` | copied to `SeriesCompensator.name`; mRID `rx_` + name | written: Names |
| `phases` | structural: A, B, C, `N` dropped; fewer than three also sets the Terminals' phases | written: the compensator's A, B, C |
| `from`, `to` | structural: `node1`, `node2`, root buses | written: terminal 1's and terminal 2's bus |
| `phase_A_impedance`, `phase_B_impedance`, `phase_C_impedance` | copied to `r`, `x`, `r0`, `x0` (`ohm`): the real and imaginary parts, `r0` = `r`, `x0` = `x`; the reactor's phases must agree, and one unset raises (GridLAB-D's 0 is a switch stand-in under NR, not a reactor) | written: `get_series_compensator` r + jx (ohm) on each of its phases; `r0` or `x0` that differ from `r` or `x` raise, and so does a varistor |
| `phase_A_resistance`, `phase_A_reactance`, and the B and C pairs | raises when set: GridLAB-D's aliases of the impedance's parts | not mapped: `phase_X_impedance` is written |
| `continuous_rating_A` to `_C`, `emergency_rating_A` to `_C` | structural: the reactor's `<mRID>_limits` | written: `get_current_limits` |
| `status` | structural: unset or `CLOSED`; `OPEN` raises | not written |
| object header, solver outputs | untranscribed | not written |

**Fail fast.** Phases whose impedances differ, or an impedance unset or in different units; `phase_X_resistance` or
`phase_X_reactance` set; `status OPEN`. On export, `r0` or `x0` that differ from `r` or `x`; a varistor.

**Expected differences.** Impedances are written in ohms on every phase of the compensator. A reactor on one phase comes
back with that phase's impedance only.

Excerpt from `cimhub_gridlabd/tests/atoms/series_reactor/series_reactor.series_reactor.cimtbl`:

```
# r0 = r, x0 = x: GridLAB-D's reactor has no coupling between phases
Table SeriesCompensator: mRID, name, node1, node2, r (ohm), x (ohm), r0 (ohm), x0 (ohm), BaseVoltage, EquipmentContainer=fdr_atom
    rx_hsb, hsb, n2,  rb1, 0.0, 14.798307, 0.0, 14.798307, bv_4p16kv
    rx_r1,  r1,  rb1, rb2, 0.5, 2.0,       0.5, 2.0,       bv_4p16kv

# SeriesCompensator has no per-phase class: a reactor on fewer than three phases gives its Terminals their phases here
Update Table Terminal: mRID, phases
    rx_r1_T1, B
    rx_r1_T2, B
```
