# Branches, switches and multi-section lines

Everything that joins two buses and is not a transformer: the Non-transformer branch (lines, series capacitors and their
line shunts), the System switching device, the Multi-section line grouping, and the RATE1..RATE12 ratings each of them
carries. Field classes, the `.cimtbl` header conventions and the full table list are on the
[reference landing page](index.md).

| RAW table | CIM (cim18v17) | Import (`.cimtbl`) | Export module |
|---|---|---|---|
| Non-transformer branch, X >= 0 | `ACLineSegment` | `branch.cimtbl` | `exporter/branch.py` |
| Non-transformer branch, X < 0 | `SeriesCompensator` (`compensatorType = capacitor`) | `branch.cimtbl` | `exporter/branch.py` |
| Branch GI, BI, GJ, BJ | `LinearShuntCompensator` | `branch.cimtbl` | `exporter/branch.py` |
| System switching device | `Switch`, `Breaker`, `Disconnector` | `switch.cimtbl` | `exporter/switch.py` |
| Multi-section line grouping | `Line` holding its sections | `multi_section_line.cimtbl` | `exporter/multi_section_line.py` |
| RATE1..RATE12, NXFRAT | `OperationalLimitSet` + `ApparentPowerLimit` or `CurrentLimit` | the three files above | `exporter/ratings.py` |

The shapes are on the core site's [shapes page](https://pnnl-cim-tools.github.io/CIMHub/core/developer/shapes/). The
getters the exporter reads through (`get_line_sequence_impedance`, `get_series_compensator`, `get_shunt_admittance`,
`get_switch_state`, `get_limits_by_type`) are described in the core
[getters guide](https://pnnl-cim-tools.github.io/CIMHub/core/guide/getters/).

## Try it

```python
from cimhub_raw.raw34_reader import Raw34Reader
from cimhub_raw.importer.raw_to_cimtbl import raw_to_cim
from cimhub_raw.exporter.cim_to_raw import RawExporter
import cimhub_raw.schema.raw_v34.raw34_schema as schema

model = Raw34Reader("cimhub_raw/tests/atoms/branch/mixed_base.raw").read_all()
network = raw_to_cim(model, name="mixed_base", artifact_dir="/tmp/raw-branches")  # branch.cimtbl, ...
back = RawExporter().to_model(network)
for branch in sorted(back.list_by_class(schema.BranchRecord), key=lambda b: b.ID):
    print(branch.ID, branch.r, branch.x, branch.b, branch.length, branch.b_to)
```

```
1_2_1 0.001 0.01 0.02 None None
2_3_1 0.0 -0.005 None None None
3_4_1 0.001 0.01 0.02 None None
4_5_1 0.002 0.02 0.02 None 0.01
```

Branch `2_3_1` has X < 0, so it is a `SeriesCompensator` and comes back with no B and no length. Branch `4_5_1` joins
a 230 kV bus to a 240 kV bus.

## Units

RAW states a branch's R, X and B in per unit on the case's SBASE and the bus base voltage. The importer copies the numbers
and names the base in the column header:

| header | meaning |
|---|---|
| `r (pu system)`, `x (pu system)`, `bch (pu system)` | pu on the master's `BasePower` (SBASE) and the equipment's `BaseVoltage`, which is bus I's `bv_<BASKV>` |
| `gPerSection (pu system)`, `bPerSection (pu system)` | a line shunt: pu on SBASE and its own bus's BASKV |
| `length (km)` | LEN, copied; RAW's "user-selected units" are taken as km |
| `normalValue (MVA)` | a rating in MVA, copied |
| `normalValue (kA)` | a rating "in current expressed as MVA" (NXFRAT > 0): kA = RATEn / (sqrt(3) x BASKV) |

cimtables turns `(pu system)` into ohm and S when it binds the table, so the mapper does no impedance arithmetic. The
exporter asks the getter for pu on the same two bases (SBASE and the equipment's `BaseVoltage`) and writes R, X and B as
RAW states them.

**A branch between two base voltages.** CIM gives an `ACLineSegment` one `BaseVoltage`, and a RAW branch whose buses I and J
have different BASKV is still one line. It keeps bus I's base for R, X and B and for a current rating, and its row lists bus
J's base in a comment (`# BASKV 240.0 at bus J`). The exporter reads pu on the line's own base, so R, X and B round-trip
exactly. A line shunt keeps its own bus's base, so GJ + jBJ stays on bus J's BASKV. No transformer is inserted for the step
between the bases: a solver that works in kV sees that step at bus J.

## Branch

One row per branch, in (I, J, CKT) order. A branch with X < 0 is a series capacitor and goes to a `SeriesCompensator`
table, with `compensatorType = capacitor` and R and X copied as written (X stays negative). Every other branch is an
`ACLineSegment`. The mRID is `ln_<I>_<J>_<CKT>` (a capacitor: `sc_<I>_<J>_<CKT>`), and the name is NAME, or the key
`I_J_CKT` when NAME is blank.

The container is the substation when both buses are in one (a zero-impedance branch, a series capacitor, a circuit whose ID
starts with `@` or `*`, or a parallel path inside a merged substation). Otherwise the cell is blank, or the multi-section
`Line` that holds the branch (below). A blank field that the schema gives a default is filled, and the row says so
(`# defaulted: ...`).

| field | import | export |
|---|---|---|
| I (`from_bus_number`) | structural: `bus1`; `bv_<BASKV>` of bus I is the row's `BaseVoltage` | terminal 1's `busNumber` |
| J (`to_bus_number`) | structural: `bus2` | terminal 2's `busNumber` |
| CKT (`circuit`) | structural: with I and J the mRID key | the mRID key when its buses are I and J in order, else the next free `1`, `2`, ... on the pair |
| R (`r`) | `ACLineSegment.r`, `SeriesCompensator.r` (pu system) | `get_line_sequence_impedance` or `get_series_compensator`, in pu |
| X (`x`) | `ACLineSegment.x`, `SeriesCompensator.x` (pu system); X < 0 selects the capacitor | the same getters, in pu |
| B (`b`) | `ACLineSegment.bch` (pu system); blank: 0. A series capacitor with B != 0 raises (`SeriesCompensator` has no `bch`) | the line's b in pu; blank for a series capacitor |
| NAME (`name`) | `name`; blank: the key | blank when the name is the key; longer than 40 characters raises |
| ST (`status`) | mapped: `inService` = (ST == 1), also on the line shunts; blank: 1 | 0 when `inService` is false, else 1 |
| LEN (`length`) | `ACLineSegment.length` (km); 0 or blank writes no length. A series capacitor's LEN != 0 is listed on its row (`SeriesCompensator` is no conductor) | `length` in km; blank when unset, and blank for a series capacitor |
| GI, BI (`g_from`, `b_from`) | structural: a `LinearShuntCompensator` `cap_<key>_i` on bus I when either is nonzero | the shunt `cap_<key>_i`: g and b in pu on its bus's base |
| GJ, BJ (`g_to`, `b_to`) | structural: `cap_<key>_j` on bus J when either is nonzero | the shunt `cap_<key>_j` |
| RATE1..RATE12 (`ratings`) | structural: [Ratings](#ratings) | the limits of types `olt_rate1`..`olt_rate12` |
| MET (`metered_end`) | structural on a tie (below); elsewhere untranscribed. Blank: 1 | on a tie, the terminal that holds the TieFlow pair; off a tie, blank |
| O1..O4, F1..F4 | untranscribed: ownership is an asset concept (CIM 18 gap) | not exported |

**Line shunts.** GI + jBI and GJ + jBJ are admittances at 1 pu of their bus's BASKV. Each becomes an ordinary
`LinearShuntCompensator` with one section, `nomU` = the bus's BASKV, the bus's `BaseVoltage` and substation, and
`inService` = the branch's ST. CIM 18 has no association from a shunt to its line, so the pairing is carried by the mRID
alone: `cap_<I>_<J>_<CKT>_i` and `_j`. The exporter takes a shunt with such an mRID, on the matching branch's node, as that
branch's GI/BI or GJ/BJ. The shunt tables skip it.

**Ties.** When I and J are in two AREAs, MET names the metered end, and the other end is the home end whose area PSS/E
charges with the losses. The importer writes two `TieFlow`s on the metered terminal: the bus's area with
`positiveFlowIn = false` and the home area with `true`. The exporter reads MET back from the terminal that holds the pair.
Off a tie MET has no CIM home.

Excerpt from `cimhub_raw/tests/goldens/IEEE14/branch.cimtbl` (all 17 branches of IEEE 14 are lines with no length and no
rating):

```
Table ACLineSegment: mRID, name, bus1, bus2, r (pu system), x (pu system), bch (pu system), length (km), inService, BaseVoltage, EquipmentContainer
    ln_1_2_1,   1_2_1,   1,  2,  0.01938, 0.05917, 0.0528, , true, bv_138kv,
    ln_1_5_1,   1_5_1,   1,  5,  0.05403, 0.22304, 0.0492, , true, bv_138kv,
```

The rows the importer wrote for the atom `cimhub_raw/tests/atoms/branch/mixed_base.raw` (a series capacitor with a length,
a line between two base voltages, and the shunt at its bus J):

```
Table ACLineSegment: mRID, name, bus1, bus2, r (pu system), x (pu system), bch (pu system), length (km), inService, BaseVoltage, EquipmentContainer
    ln_1_2_1, 1_2_1, 1, 2, 0.001, 0.01, 0.02, , true, bv_230kv,
    ln_3_4_1, 3_4_1, 3, 4, 0.001, 0.01, 0.02, , true, bv_230kv,
    # BASKV 240.0 at bus J
    ln_4_5_1, 4_5_1, 4, 5, 0.002, 0.02, 0.02, , true, bv_230kv,

Table SeriesCompensator: mRID, name, bus1, bus2, compensatorType, r (pu system), x (pu system), inService, BaseVoltage, EquipmentContainer
    # untranscribed: length=1.0
    sc_2_3_1, 2_3_1, 2, 3, capacitor, 0.0, -0.005, true, bv_230kv, sub_2

Table LinearShuntCompensator: mRID, name, bus, gPerSection (pu system), bPerSection (pu system), nomU (kV), sections, normalSections, maximumSections, inService, BaseVoltage, EquipmentContainer
    cap_4_5_1_j, 4_5_1_j, 5, 0.0, 0.01, 240.0, 1, 1, 1, true, bv_240kv, sub_5
```

**Fail fast, import.** A series capacitor (X < 0) with B != 0. An ST that is not 0 or 1. On a tie, a MET that is not 1 or 2,
or an AREA with no area-interchange record.

**Fail fast, export.** A line with `gch` set (RAW has no line conductance). A branch on a node with no
`busNumber`. A line shunt whose `inService` differs from its line's, or whose `nomU` is not its `BaseVoltage` (RAW states a
shunt at 1 pu of its bus voltage). A NAME longer than 40 characters. Two branches with one key. TieFlow pairs on both
terminals of one branch. Ratings of both kinds (see [Ratings](#ratings)). The exporter reads a line's own lumped r, x and b, so a line with only a per-length impedance raises.

**Expected differences.** MET 2 off a tie comes back blank, which reads as the default 1. A series capacitor's LEN comes back blank. A `SeriesCompensator`
with X >= 0 is written as a branch and would import as an `ACLineSegment`. Owners are not exported.

## System switching device

`switch.cimtbl` has one table per class, with the same columns. STYPE picks the class, and the mRID prefix `sw_` is the same
for all three, so a change of class keeps the mRID. The switch's `BaseVoltage` is bus I's and its container is bus I's
substation, since a switch merges its two buses into one substation. A switch across a zone boundary is not a merge edge,
and its container is still bus I's substation.

| field | import | export |
|---|---|---|
| I, J (`from_bus_number`, `to_bus_number`) | structural: `bus1`, `bus2` | terminals 1 and 2's `busNumber` |
| CKT (`circuit`) | structural: mRID `sw_<I>_<J>_<CKT>` | as a branch's |
| STYPE (`stype`) | mapped: 1 `Switch`, 2 `Breaker`, 3 `Disconnector`. Blank or another code raises: no default | by class, the same numbers |
| STATUS (`status`) | mapped: `open` = (STATUS == 0); blank: 1 | `get_switch_state` actual: open is 0, closed 1 |
| NSTATUS (`nstat`) | mapped: `normalOpen` = (NSTATUS == 0); blank: 1 | `get_switch_state` normal |
| X (`x`) | untranscribed: the solver's stand-in for zero impedance; a switch has none | always 0.0001 (the format gives X no default) |
| METERED (`metered_end`) | structural on a tie, as a branch's MET; elsewhere untranscribed. Blank: 1 | on a tie the terminal that holds the TieFlows, else 1 |
| NAME (`name`) | `name`; blank: the key | as a branch's |
| RATE1..RATE12 (`ratings`) | structural: [Ratings](#ratings) | as a branch's |

Excerpt from `cimhub_raw/tests/atoms/branch/switches.raw` (one switch of each STYPE, the first rated in current):

```
Table Breaker: mRID, name, bus1, bus2, open, normalOpen, BaseVoltage, EquipmentContainer
    sw_102_103_1, BREAKER, 102, 103, true, false, bv_138kv, sub_101

Table Disconnector: mRID, name, bus1, bus2, open, normalOpen, BaseVoltage, EquipmentContainer
    sw_103_104_1, DISCONNECT, 103, 104, false, true, bv_138kv, sub_101

Table CurrentLimit: mRID, OperationalLimitSet, OperationalLimitType, normalValue (kA)
    sw_101_102_1_rate1, sw_101_102_1_ratings, olt_rate1, 0.836739520564675
```

**Fail fast.** On import, a blank STYPE, and an STYPE, STATUS or NSTATUS outside its codes (a blank STATUS or NSTATUS is 1). On export, a switch with a `ConnectivityNode` on one
terminal only, and any switch class other than `Switch`, `Breaker` and `Disconnector` (a fuse or a recloser has no RAW form,
and the exporter raises on any conducting equipment it has no module for).

**Expected differences.** A switch's X other than 0.0001 comes back 0.0001. METERED 2 off a tie comes back 1. A switch with
a `ConnectivityNode` on both terminals belongs to a node-breaker substation (see [Substations](substations.md)); this
exporter leaves it out, and the exporter has no module for node-breaker substations yet, so such switches are not in the
exported case.

## Multi-section line

A multi-section line record names a path of buses: I, then the dummy buses DUM1..DUM9 that are set, then J. The sections
stay ordinary branches in `branch.cimtbl`, and the dummy buses stay buses. The record becomes a `Line` (mRID
`msl_<I>_<J>_<ID>`, name ID, `Region` = bus I's zone), and an `Update` row moves each section into it.

| field | import | export |
|---|---|---|
| I, J (`i`, `j`) | structural: the key and the path's ends | the path's ends: from the mRID key when it names them in order, else the lower bus first |
| ID (`line_id`) | copied to `Line.name`; part of the key | the mRID key, else the next free `&1`, `&2`, ... |
| DUM1..DUM9 (`dum1`..`dum9`) | structural: the path I, DUM1, ..., J names the sections, one branch per step | the path's dummy buses in order, blank past the end |
| MET (`met`) | untranscribed: the loss-allocation end has no CIM home | not exported |

Each step of the path must be joined by exactly one branch that no earlier record has used, in either direction (a section
may be entered 4-3 for a path from 3 to 4), and each dummy bus must have exactly two branches. A section whose two buses
are in one substation (a series capacitor merges its buses) stays contained by that substation and joins the Line through
the second container association, `AdditionalEquipmentContainer`. The Line's row lists it:
`# path 1, 2, 3, 4; in substations: sc_2_3_1`.

Excerpt from `cimhub_raw/tests/atoms/branch/mixed_base.raw`, a line `&1` of three sections through buses 2 and 3, the middle
one a series capacitor:

```
Table Line: mRID, name, Region
    # path 1, 2, 3, 4; in substations: sc_2_3_1
    msl_1_4_&1, &1, srgn_1

Update Table ACLineSegment: mRID, EquipmentContainer
    ln_1_2_1, msl_1_4_&1
    ln_3_4_1, msl_1_4_&1

Update Table SeriesCompensator: mRID, AdditionalEquipmentContainer
    sc_2_3_1, msl_1_4_&1
```

**Fail fast, import.** A dummy bus with other than two branches. A step of the path with no unused branch, or with more than
one (parallel branches between two path buses are ambiguous).

**Fallback, export.** A `Line` whose sections are not one path of one to nine dummy buses, each joining exactly two
branches, writes no multi-section record and raises nothing: its sections are still written as branches, and the count of
such lines is logged.

**Expected differences.** MET is not exported. A record with no dummy bus (I and J joined by one branch) is read by the
importer but not written back.

## Ratings

RATE1..RATE12 are the twelve rating sets of the case. The master table writes twelve `OperationalLimitType`s,
`olt_rate1`..`olt_rate12`, named from the RATING records (a set with no record is named `RATEn` and described
`RATING SET n`).

A device's nonzero ratings go into one `OperationalLimitSet` `<mRID>_ratings` on its first terminal `<mRID>_T1` (bus I),
one limit per rating, mRID `<mRID>_rate<n>`, of type `olt_rate<n>`. A zero rating is PSS/E's "no limit", so it writes no
row, and a device with no nonzero rating has no set. A transformer's ratings are one set per winding; see
[Transformers](transformers.md).

| NXFRAT | limit class | `normalValue` | value |
|---|---|---|---|
| 0 or less | `ApparentPowerLimit` | MVA | RATEn, copied |
| > 0 | `CurrentLimit` | kA | RATEn / (sqrt(3) x BASKV), the rating being a current "expressed as MVA" at bus I's BASKV |

A blank NXFRAT is the present option setting, which the importer reads as MVA and notes on the master
(`# defaulted: NXFRAT=0`). One flag holds for every branch and switch of the case.

The exporter reads RATEn from the limit whose type is `olt_rate<n>`, with 0 where there is none. A current limit becomes MVA
= sqrt(3) x BASKV x kA on the device's `BaseVoltage`. It writes NXFRAT 1 when the case's branch and switch ratings are
`CurrentLimit`s, and 0 when they are `ApparentPowerLimit`s or there are none.

**Fail fast, export.** A limit whose type is not one of `olt_rate1`..`olt_rate12`. A device with both
`ApparentPowerLimit`s and `CurrentLimit`s, or a case that holds both kinds among its branches and switches.

**Expected differences.** A case with no rated branch or switch comes back NXFRAT 0, whatever it was.

Excerpt from `cimhub_raw/tests/atoms/branch/line_shunts.raw` (RATE1 100 and RATE2 120 MVA on branch 1-2):

```
Table OperationalLimitSet: mRID, Terminal
    ln_1_2_1_ratings, ln_1_2_1_T1

Table ApparentPowerLimit: mRID, OperationalLimitSet, OperationalLimitType, normalValue (MVA)
    ln_1_2_1_rate1, ln_1_2_1_ratings, olt_rate1, 100.0
    ln_1_2_1_rate2, ln_1_2_1_ratings, olt_rate2, 120.0
```

## Where the rules are specified

The per-field classification with its reasons is in the [import mapping](../CIMTBL_MAPPING.md) (sections Branch, System
switching device, Multi-section line) and the [export mapping](../EXPORT_MAPPING.md) (section E1).
