# Transformers and impedance correction

Two- and three-winding transformers, with their windings, ratings, tap changers and controls, and the impedance correction
tables that windings name. Field classes, the `.cimtbl` header conventions and the full table list are on the
[reference landing page](index.md).

| RAW table | CIM (cim18v17) | Import (`.cimtbl`) | Export module |
|---|---|---|---|
| Transformer | `PowerTransformer`, a `PowerTransformerEnd` per winding, `TransformerMeshImpedance` (three windings) | `transformer.cimtbl` | `exporter/transformer.py` |
| Transformer tap data, COD 0, +-1, +-2 | `RatioTapChanger` + `TapChangerControl` | `transformer.cimtbl` | `exporter/transformer.py` |
| Transformer tap data, COD +-3 | `PhaseTapChangerLinear` + `TapChangerControl` (mode `activePower`) | `transformer.cimtbl` | `exporter/transformer.py` |
| ANG | `PowerTransformerEnd.phaseShift` | `transformer.cimtbl` | `exporter/transformer.py` |
| RATEk-1..RATEk-12 | `OperationalLimitSet` per winding | `transformer.cimtbl` | `exporter/transformer.py`, `exporter/ratings.py` |
| Impedance correction | `ImpedanceTapChangerTable` + `ImpedanceTapChangerTablePoint`; `ImpedanceTapChangerTabular` per winding | `impedance_correction.cimtbl`, `transformer.cimtbl` | `exporter/impedance_correction.py` |

The CIM 18 transformer model has no star impedance, so a two-winding unit keeps r, x, g and b on end 1 and a
three-winding unit keeps its three pair impedances as a mesh. The core getter the exporter reads is
`get_transformer_model`, with `get_tap_changer_control`, `get_tap_steps`, `get_tap_voltage`, `get_phase_tap_steps` and
`get_impedance_table`; see the core [transformers reference](https://pnnl-cim-tools.github.io/CIMHub/core/reference/transformers/)
and [shapes page](https://pnnl-cim-tools.github.io/CIMHub/core/developer/shapes/). Generator step-up transformers belong to
[Generators](generators.md) and DC converter transformers to [DC lines and FACTS devices](dc.md); the transformer exporter
skips both.

## Try it

```python
from cimhub_raw.raw34_reader import Raw34Reader
from cimhub_raw.importer.raw_to_cimtbl import raw_to_cim
from cimhub_raw.exporter.cim_to_raw import RawExporter
import cimhub_raw.schema.raw_v34.raw34_schema as schema

model = Raw34Reader("cimhub_raw/tests/atoms/transformer/forms_r4b.raw").read_all()
network = raw_to_cim(model, name="forms_r4b", artifact_dir="/tmp/raw-transformers")  # transformer.cimtbl, ...
back = RawExporter().to_model(network)
for xf in sorted(back.list_by_class(schema.TransformerRecord), key=lambda t: t.ID)[:4]:
    print(xf.ID, xf.cw, xf.cz, xf.cm, xf.r1_2, xf.x1_2, xf.ang1, xf.cod1)
```

```
1_2_0_F 1 1 1 0.002 0.08 30.0 1
1_2_3_G 1 1 1 0.001 0.05 0.0 0
1_2_4_H 1 1 1 0.001 0.05 0.0 0
1_3_4_I 1 1 1 0.001 0.05 0.0 0
```

The exporter always writes CW = CZ = CM = 1 (pu on SBASE and the bus base), whatever codes the case used.

## Units and codes

A transformer's values are in units that depend on three codes. The importer converts them, and
the `.cimtbl` carries ohm and S on each winding's `ratedU`, not per unit:

| code | value | meaning |
|---|---|---|
| CW 1 | WINDV, RMA, RMI | pu of the bus's BASKV |
| CW 2 | WINDV, RMA, RMI | kV |
| CW 3 | WINDV, RMA, RMI | pu of the winding's NOMV (BASKV when NOMV is 0) |
| CZ 1 | R, X | pu on SBASE and bus i's BASKV |
| CZ 2 | R, X | pu on the pair's SBASEij and NOMVi |
| CZ 3 | R, X | R is the load loss in W and X is \|Z\| in pu on SBASEij and NOMVi; r = loss / SBASEij and x = sqrt(\|Z\|^2 - r^2) |
| CM 1 | MAG1, MAG2 | G and B in pu on SBASE and bus 1's BASKV |
| CM 2 | MAG1, MAG2 | the no-load loss in W and the exciting current in pu on SBASE1-2 and NOMV1; g = loss / SBASE1-2 and b = -sqrt(I^2 - g^2) (inductive) |

The ohm is the same whichever code the case used. The table headers say so: `r (ohm)`, `x (ohm)`, `g (S)`, `b (S)`,
`ratedU (kV)`, `ratedS (MVA)`. The impedance of a pair is "seen from" winding i (the lower-numbered winding of the pair),
on that winding's `ratedU`.

The exporter inverts only CZ 1, CM 1 and CW 1. The getter reads each value in pu on SBASE and the winding's `ratedU`, and the
exporter moves it to the bus's BASKV by the voltage ratio alone: an impedance times (ratedU / BASKV)^2, an admittance
times (BASKV / ratedU)^2. That is the identity when NOMV = BASKV.

**Blank fields take the schema's defaults**, and the row lists each one it filled (`# defaulted: ...`). The ones that
matter here: CW, CZ, CM 1; WINDV 1.0, or the bus's BASKV for CW 2; SBASEij the case SBASE; RMA 1.1 and RMI 0.9 for CW 1 or 3
unless COD is +-3 or +-5; VMA 1.1 and VMI 0.9 for COD 0 and +-1; NTP 33; COD, CONT, TAB, CR, CX and NOD 0; NMETR 2. A
blank RMA or RMI at CW 2 or COD +-3, or a blank VMA or VMI at COD +-2 or +-3, has no default and raises.

## Transformer

One `PowerTransformer` per record, mRID `xf_<I>_<J>_<K>_<CKT>` (K is 0 for two windings), name NAME or the key, in the
substation of bus I. Each winding is a `PowerTransformerEnd` `xf_<key>_<k>` with `endNumber` k, the winding's bus and that
bus's `BaseVoltage`. Its `ratedU` is NOMVk, or the bus's BASKV when NOMVk is 0.

| Form | `PowerTransformerEnd` values | Other rows |
|---|---|---|
| two windings (K = 0) | end 1: r, x (ohm), g, b (S) and `ratedS` = SBASE1-2; end 2: r, x, g, b all 0, `ratedS` = SBASE1-2 | none |
| three windings | end 1: g, b (S); r, x and `ratedS` blank on every end | `TransformerMeshImpedance` rows From 1 To 2, From 2 To 3, From 1 To 3: r, x (ohm) seen from the From end |

There is no star node: PSS/E's three pair impedances Z12, Z23 and Z31 are already a mesh. The three-winding pair bases
(SBASE2-3, SBASE3-1) have no end to sit on, so on export they come back as SBASE.

| field | import | export |
|---|---|---|
| I, J, K (`i`, `j`, `k`) | structural: windings 1, 2, 3's buses; K = 0 is a two-winding unit | the buses of ends 1, 2, 3; K = 0 for two ends |
| CKT (`circuit`) | structural: with I, J, K the mRID key; blank: 1 | the mRID key, else the next free ID on the buses |
| NAME (`name`) | `PowerTransformer.name`; blank: the key | blank when the name is the key; longer than 40 characters raises |
| STAT (`status`) | mapped: `inService` = (STAT != 0). STAT 2, 3, 4 (winding 2, 3, 1 of a three-winding unit out) keep the unit in service and set that end's terminal `connected = false` through an `Update Table Terminal` row. STAT 2, 3, 4 on a two-winding unit raises | 0 when `inService` is false; 2, 3, 4 when exactly winding 2, 3, 1 of a three-winding unit is disconnected; else 1. Two windings out raises |
| VECGRP (`vecgrp`) | `PowerTransformer.vectorGroup`; blank: none | `vectorGroup`, blank when unset |
| CW, CZ, CM (`cw`, `cz`, `cm`) | mapped: the code of WINDV/RMA/RMI, R/X, MAG1/MAG2; any other value raises | rule: always 1 |
| R1-2, X1-2 (`r1_2`, `x1_2`) | derived: end 1's r, x (ohm) for two windings; the mesh row's r, x for three | r of both ends plus the mesh r, in pu on SBASE, moved to bus 1's BASKV |
| R2-3, X2-3, R3-1, X3-1 (`r2_3`, `x2_3`, `r3_1`, `x3_1`) | derived: the mesh rows 2-3 and 1-3 | the same, from winding 2 (2-3) and winding 1 (3-1) |
| SBASE1-2, SBASE2-3, SBASE3-1 | derived: the pair's base for CZ 2 and 3 and for CM 2 on 1-2; a two-winding unit's SBASE1-2 is also both ends' `ratedS`; blank: SBASE | a two-winding unit's `ratedS` (both ends must agree, else raises); three windings: SBASE |
| MAG1, MAG2 (`mag1`, `mag2`) | derived: end 1's g, b (S), by CM; blank: 0 | the core's g, b, moved to bus 1's BASKV, sign kept |
| NMETR (`nmetr`) | structural on a tie (windings in two or more AREAs): the non-metered home winding; each other winding outside the home area carries the TieFlow pair. A code outside 1..windings on a tie raises. Elsewhere untranscribed. Blank: 2 | on a tie, the winding whose terminal holds no TieFlow (the lower of two); off a tie, blank |
| NOMVk (`nomv1`..`nomv3`) | derived: `ratedU` of end k (kV); 0: the bus's BASKV | the end's `ratedU` |
| ZCOD, VMSTAR, ANSTAR | untranscribed: zero-sequence data is in the sequence file; the star point's solved voltage, which the mesh omits | not exported |
| O1..O4, F1..F4 | untranscribed: ownership is an asset concept (CIM 18 gap) | not exported |
| RATEk-1..RATEk-12 (`rate1_1`..`rate3_12`) | structural: [Ratings](#ratings) | the limits of types `olt_rate<n>` on winding k's terminal |

## Tap changers and controls

Each winding that has COD data (winding 1 of a two-winding unit, every winding of a three-winding unit) gets a
`TapChangerControl` `xf_<key>_ctrl<k>` and one tap changer on its end. Winding 2 of a two-winding unit has only WINDV2 and
NOMV2.

| COD | tap changer | control mode | enabled |
|---|---|---|---|
| 0 | `RatioTapChanger`, `ltcFlag` false | `voltage` | false: the control is kept, disabled |
| +-1 | `RatioTapChanger`, `ltcFlag` true | `voltage` | COD > 0 |
| +-2 | `RatioTapChanger`, `ltcFlag` true | `reactivePower` | COD > 0 |
| +-3 | `PhaseTapChangerLinear`, `ltcFlag` true | `activePower` | COD > 0 |
| +-4, +-5 | none: raises (two-terminal DC phase 2; asymmetric phase shift) | | |

`discrete` is true on every control.

| field | import | export |
|---|---|---|
| CODk (`cod1`..`cod3`) | mapped: the table above; `controlEnabled` = (COD > 0). Another value raises | from the controlled tap changer: a ratio tap with `ltcFlag` false 0; `ltcFlag` true +-1 (`voltage`) or +-2 (`reactivePower`); a `PhaseTapChangerLinear` under `activePower` +-3; sign + when the control is enabled (the tap's `controlEnabled` must agree). No controlled tap: 0 |
| WINDVk (`windv1`..`windv3`) | derived: the ratio, in CW units, as the tap's `step` (below), or a fixed tap's `neutralU` = WINDV in kV | the tap's voltage at its `step` / bus k's BASKV; with no ratio tap, `ratedU` / BASKV |
| RMAk, RMIk, NTPk | derived: the ratio tap's `highStep` ratio, `lowStep` ratio and number of steps, or for COD +-3 the angles | the tap's `highStep` and `lowStep` voltages / BASKV, and `highStep` - `lowStep` + 1; for a shifter the larger and smaller end angle. A fixed or missing tap: blank |
| CONTk (`cont1`..`cont3`) | structural: the control's `Terminal`, below | 0 for the winding's own terminal, else the busNumber of the control's node; blank for COD +-3 |
| NODk | structural: with CONTk, the busbar of that node of the regulated bus; NODk with CONTk 0 raises | not exported (node-breaker data) |
| VMAk, VMIk | derived: `targetValue` = (VMA + VMI) / 2, `targetDeadband` = VMA - VMI, in V (voltage, times the regulated bus's BASKV), VAr (reactivePower, from Mvar) or W (activePower, from MW) | `targetValue` +- `targetDeadband` / 2, as pu of the regulated bus's BASKV, Mvar or MW; blank with no control |
| CRk, CXk | derived: `lineDropCompensation` true, `lineDropR`, `lineDropX` (ohm) = CR, CX x BASKV^2 / SBASE, with the regulated bus's BASKV; nonzero on a COD other than +-1 raises | `lineDropR`, `lineDropX` as pu on SBASE and the regulated bus's BASKV, when `lineDropCompensation` is true; else blank |
| CNXAk | structural: nonzero raises (only COD +-5 uses it) | not exported |
| ANGk (`ang1`..`ang3`) | derived: see [Angles](#angles-and-phase-shifters) | see below |
| TABk (`tab1`..`tab3`) | structural: an `ImpedanceTapChangerTabular` `xf_<key>_ztab<k>` on end k, naming `ict_<TAB>`; TAB names no table, or TAB on a three-winding unit, raises | the table's number from the end's tabular; none: blank |

### Ratio taps

A stepped `RatioTapChanger` `xf_<key>_tap<k>` runs from step 1 at RMI to step NTP at RMA in equal steps:

| column | value |
|---|---|
| `lowStep`, `highStep` | 1 and NTP; widened to the first whole step past WINDV when WINDV lies outside RMI..RMA |
| `stepVoltageIncrement` | (RMA - RMI) / (NTP - 1), in percent of `ratedU` |
| `neutralStep`, `neutralU` | the step nearest ratio 1 (a tie takes the upper), and that step's voltage in kV: CIM's neutral step is an integer and PSS/E's ratio 1 often falls between steps |
| `step` | `neutralStep` + (WINDV - the neutral ratio) / the step size, a float; a WINDV exactly at RMA or RMI is step NTP or 1 |

NTP below 2, or RMA <= RMI, raises. When WINDV is outside RMI..RMA the row lists RMA and RMI.

A **fixed** `RatioTapChanger` has one step: `lowStep` = `highStep` = `neutralStep` = `step` = 1, `neutralU` = WINDV in kV, no
increment, `ltcFlag` and `controlEnabled` false. It is written for:

- winding 2 of a two-winding unit whose WINDV2 is off its NOMV2 (no control);
- a COD 0 winding whose RMI..RMA is not a range holding WINDV (RMA <= RMI, or WINDV outside it); the row lists RMA, RMI
  and NTP, and the winding keeps its disabled control;
- the winding of a phase shifter whose ratio is off nominal (no control; the phase tap holds it).

Winding 2 of a two-winding unit and the winding of a phase shifter, at their nominal ratio, get no ratio tap changer; the
exporter then writes WINDV = `ratedU` / BASKV.

### Control terminal

| CONTk | the control's `Terminal` |
|---|---|
| 0 | the winding's own terminal `xf_<key>_T<k>` (the row says `CONT 0: regulates its own terminal` for COD +-1) |
| a bus | that bus's busbar terminal `bb_<CONT>_T1` |
| a bus and NODk | that node's busbar terminal, in a node-breaker substation (see [Substations](substations.md)) |
| negative | as the bus; the sign tells PSS/E to treat the bus as on winding 1's side, which CIM has no place for, so the row lists `untranscribed: cont1=-2`. The exporter writes CONT positive |
| COD +-3 | always the winding's own terminal |

A CONT that names no bus raises.

### Angles and phase shifters

PSS/E's ANGk is positive when winding k's bus leads the transformer's internal voltage. CIM's `phaseShift` and phase tap
angles are positive from the terminal into the transformer, the opposite sign, so the importer writes the negated angle
and the exporter turns it back.

- **Fixed shift.** For every winding whose \|COD\| is not 3, a nonzero ANGk is `PowerTransformerEnd.phaseShift` (deg) on
  end k. A two-winding unit has only ANG1, so end 2 stays blank. Only the differences between ends are physical, so the
  exporter writes a two-winding unit's ANG1 as -(`phaseShift` of end 1 - that of end 2). The `phaseShift` column appears
  in `PowerTransformerEnd` only when some end has one.
- **Phase shifter, COD +-3.** A `PhaseTapChangerLinear` `xf_<key>_ptap<k>` from step 1 at RMI to step NTP at RMA, in
  PSS/E angles, with `stepPhaseShiftIncrement` = the negated (RMA - RMI) / (NTP - 1), `neutralStep` the step nearest 0
  degrees, and `step` = `neutralStep` + ANG / the step size, so ANG itself is exact. CIM has no neutral angle, so when 0
  degrees falls between steps the end steps' angles move by that offset; the row lists RMA and RMI and says by how far. An
  ANG outside RMI..RMA raises. The control is on the winding's own terminal; its `targetValue` and `targetDeadband` are VMA
  and VMI in MW converted to W. The exporter writes ANGk as -(`phaseShift` + (`step` - `neutralStep`) x the increment),
  RMA and RMI from the end steps, and a stepped ratio tap beside a phase tap changer raises.

### Impedance correction tables

TABk makes the winding's tabular `xf_<key>_ztab<k>` name the table. The table side is `impedance_correction.cimtbl`, which
comes before the transformer file because the tabular names it.

| field | import | export |
|---|---|---|
| I (`table_number`) | structural: `ImpedanceTapChangerTable` `ict_<I>`, named I | the number from the mRID `ict_<I>`, else the next free number |
| Ti (`t`) | derived. An angle table (first T below 0.5 or last T above 1.5) gives `angle` (deg) = the negated T. A ratio table gives `ratio` = T x BASKV / `ratedU` of its users' winding; `step` stays blank | an angle point's T is the negated angle; a ratio point's T = ratio x `ratedU` / BASKV of its users' winding |
| Re(Fi) (`f_real`) | derived: `rEnd1` = `xEnd1` = 100 x (F - 1), in percent | F = 1 + `rEnd1` / 100 |
| Im(Fi) (`f_imag`) | structural: nonzero raises (CIM's deviations are real) | rule: 0 |
| the closing 0, 0, 0 point | not a point | not written |

Points are numbered `ict_<I>_<n>` in file order, and the exporter returns them in ascending T. Excerpt from the atom
`cimhub_raw/tests/atoms/transformer/forms_r4b.raw`, whose table 1 is an angle table on a phase shifter and whose table 2 is
a ratio table on a 240 kV winding at a 230 kV bus:

```
Table ImpedanceTapChangerTabular: mRID, name, TransformerEnd, ImpedanceTapChangerTable
    xf_2_5_0_K_ztab1, 2_5_0_K_1, xf_2_5_0_K_1, ict_1
    xf_2_6_0_L_ztab1, 2_6_0_L_1, xf_2_6_0_L_1, ict_2

Table ImpedanceTapChangerTable: mRID, name
    # angle table
    ict_1, 1
    # ratio table
    ict_2, 2

Table ImpedanceTapChangerTablePoint: identifier, ImpedanceTapChangerTable, ratio, rEnd1, xEnd1
    ict_2_1, ict_2, 0.8625,             -5.000000000000004, -5.000000000000004
    ict_2_2, ict_2, 0.9583333333333334, 0.0,                0.0
    ict_2_3, ict_2, 1.0541666666666667, 8.000000000000007,  8.000000000000007
```

**Fail fast, import (impedance correction).** A table with fewer than two points. A complex factor (Im F != 0). A ratio table
that no winding uses, or whose users have different BASKV / `ratedU` (one table cannot hold both).

**Fail fast, export (impedance correction).** A point with both or neither of ratio and angle, or a table that mixes them. A
point whose `rEnd1` differs from `xEnd1`, or that sets `rEnd2`, `rEnd3`, `xEnd2` or `xEnd3`. A ratio table with no user, or
whose users' `ratedU` / BASKV differ. A tabular that names no table.

### Ratings

A transformer's ratings are per winding. Each nonzero RATEk-n is a limit `xf_<key>_<k>_rate<n>` of type `olt_rate<n>` in the
set `xf_<key>_<k>_ratings` on winding k's terminal `xf_<key>_T<k>`. A two-winding unit has ratings on winding 1 only, and the
exporter raises on a rating on winding 2. As for branches, a zero rating is no limit, and the flag XFRRAT decides the class:
0 gives `ApparentPowerLimit` in MVA, and XFRRAT > 0 gives `CurrentLimit` in kA = RATEn / (sqrt(3) x BASKV), the BASKV of that
winding's bus. The exporter writes XFRRAT 1 when the transformer ratings are `CurrentLimit`s, reading each winding's
terminal on its own, and raises when both kinds occur. See [Branches](branches.md) for the branch flag.

## Excerpts

From `cimhub_raw/tests/goldens/IEEE14/transformer.cimtbl`, the first of three two-winding units (CW = CZ = CM = 1, COD 0).
End 1 holds x and end 2 is zero; the control is kept, disabled, and the tap has 159 steps:

```
Table PowerTransformer: mRID, name, vectorGroup, inService, EquipmentContainer
    xf_4_7_0_1, 4_7_0_1, , true, sub_4

Table PowerTransformerEnd: mRID, name, bus, endNumber, ratedU (kV), ratedS (MVA), r (ohm), x (ohm), g (S), b (S), BaseVoltage, PowerTransformer
    xf_4_7_0_1_1, 4_7_0_1_1, 4, 1, 138.0, 100.0, 0.0, 39.8248128,         0.0, 0.0, bv_138kv, xf_4_7_0_1
    xf_4_7_0_1_2, 4_7_0_1_2, 7, 2, 138.0, 100.0, 0.0, 0.0,                0.0, 0.0, bv_138kv, xf_4_7_0_1

Table TapChangerControl: mRID, name, mode, discrete, enabled, targetValue, targetDeadband, Terminal
    xf_4_7_0_1_ctrl1, 4_7_0_1_1, voltage, true, false, 138690.0, 136620.0, xf_4_7_0_1_T1

Table RatioTapChanger: mRID, name, lowStep, highStep, neutralStep, neutralU (kV), stepVoltageIncrement, step, ltcFlag, controlEnabled, TapChangerControl, TransformerEnd
    xf_4_7_0_1_tap1, 4_7_0_1_1, 1, 159, 79, 137.8253164556962, 0.6265822784810127, 75.69090909090909, false, false, xf_4_7_0_1_ctrl1, xf_4_7_0_1_1
```

From the atom `cimhub_raw/tests/atoms/transformer/transformers.raw`, unit D, a three-winding unit (1-2-3) with CZ 1: g and b
on end 1, the pair impedances as a mesh, and a rating on windings 1 and 3:

```
Table PowerTransformerEnd: mRID, name, bus, endNumber, ratedU (kV), ratedS (MVA), r (ohm), x (ohm), g (S), b (S), BaseVoltage, PowerTransformer
    xf_1_2_3_1_1, 1_2_3_1_1, 1, 1, 345.0, ,      ,                    ,                  4.2007981516488137e-07, -1.6803192606595255e-06, bv_345kv,  xf_1_2_3_1
    xf_1_2_3_1_2, 1_2_3_1_2, 2, 2, 230.0, ,      ,                    ,                  ,                       ,                        bv_230kv,  xf_1_2_3_1
    xf_1_2_3_1_3, 1_2_3_1_3, 3, 3, 69.0,  ,      ,                    ,                  ,                       ,                        bv_69kv,   xf_1_2_3_1

Table TransformerMeshImpedance: mRID, name, FromTransformerEnd, ToTransformerEnd, r (ohm), x (ohm)
    xf_1_2_3_1_mesh_12, 1_2_3_1_12, xf_1_2_3_1_1, xf_1_2_3_1_2, 1.19025,             59.5125
    xf_1_2_3_1_mesh_23, 1_2_3_1_23, xf_1_2_3_1_2, xf_1_2_3_1_3, 1.058,               21.16
    xf_1_2_3_1_mesh_13, 1_2_3_1_13, xf_1_2_3_1_1, xf_1_2_3_1_3, 1.785375,            83.3175

Table OperationalLimitSet: mRID, Terminal
    xf_1_2_3_1_1_ratings, xf_1_2_3_1_T1
    xf_1_2_3_1_3_ratings, xf_1_2_3_1_T3
```

From the atom `cimhub_raw/tests/atoms/transformer/forms_r4b.raw`, unit K, a phase shifter (COD -3, 0 degrees off the step
grid) with a fixed off-nominal ratio and an impedance correction table. The row lists the RMA and RMI that CIM cannot hold:

```
Table TapChangerControl: mRID, name, mode, discrete, enabled, targetValue, targetDeadband, Terminal, lineDropCompensation, lineDropR (ohm), lineDropX (ohm)
    xf_2_5_0_K_ctrl1, 2_5_0_K_1, activePower,   true, false, 70000000.0,  20000000.0,         xf_2_5_0_K_T1, ,     ,

Table RatioTapChanger: mRID, name, lowStep, highStep, neutralStep, neutralU (kV), stepVoltageIncrement, step, ltcFlag, controlEnabled, TapChangerControl, TransformerEnd
    # fixed: a phase shifter's off-nominal ratio
    xf_2_5_0_K_tap1, 2_5_0_K_1, 1, 1,  1,  234.6,              ,                   1,                  false, false, ,                 xf_2_5_0_K_1

Table PhaseTapChangerLinear: mRID, name, lowStep, highStep, neutralStep, stepPhaseShiftIncrement (deg), step, ltcFlag, controlEnabled, TapChangerControl, TransformerEnd
    # untranscribed: rma1=40.0, rmi1=-30.0 (0 deg lies 0.6451612903225765 deg off the step grid)
    xf_2_5_0_K_ptap1, 2_5_0_K_1, 1, 32, 14, -2.2580645161290325, 9.571428571428573, true, false, xf_2_5_0_K_ctrl1, xf_2_5_0_K_1
```

## Fail fast and expected differences

**Fail fast, import.**

- STAT 2, 3 or 4 on a two-winding unit.
- COD +-4 or +-5, and a nonzero CNXA.
- TAB on a three-winding unit, or a TAB that names no impedance correction table.
- CR or CX nonzero on a COD other than +-1.
- A blank RMA, RMI, VMA or VMI that has no default.
- NOD without CONT, and a CONT that is no bus.
- CW, CZ or CM outside its codes; CZ 3 with \|Z\| below r; CM 2 with an exciting current below g.
- NTP below 2, RMA <= RMI on a stepped tap, and an ANG outside RMI..RMA on a phase shifter.
- On a tie, an NMETR that names no winding.

**Fail fast, export.**

- A transformer that is not two or three ends, a model not given by ends, or an end on a node with no busNumber (that is
  neither a generator step-up nor a converter transformer).
- Ends whose `ratedS` differ on a two-winding unit; a rating on winding 2 of a two-winding unit.
- Winding 2 of a two-winding unit with a moving tap, a control, or a phase or impedance tap changer.
- A phase tap changer that is not linear; both tap changers controlled; a stepped ratio tap beside a phase tap changer.
- A control mode other than voltage, reactive power or active power; a ratio tap under an active power control, or a phase
  tap under another mode; a `controlEnabled` that disagrees with the control's `enabled`.
- A control whose terminal is on a node with no busNumber.
- TAB on a three-winding unit.
- More than one winding disconnected, or one disconnected on a two-winding unit.
- TieFlows on every winding.
- Ratings in MVA and in current in one case.

**Expected differences.**

- CW, CZ and CM come back 1, and R, X, MAG1, MAG2, WINDV, RMA, RMI are in pu on SBASE and the bus base, which are the same
  physical values. A three-winding unit's SBASE2-3 and SBASE3-1 come back as SBASE.
- A blank that was defaulted comes back as its default value.
- A COD 0 winding with an unusable tap range (a fixed tap) comes back with RMA, RMI and NTP blank, and a COD +-1 winding whose WINDV
  was outside RMI..RMA comes back with RMA and RMI from the widened steps.
- A phase shifter whose 0 degrees was off the step grid comes back with RMA and RMI moved by the listed offset.
- A negative CONT comes back positive.
- A two-winding unit's ANG1 comes back as the difference of the two ends' shifts.
- NMETR off a tie comes back blank (RAW's default is 2); on a tie it is the lowest-numbered home winding.
- Impedance correction points come back in ascending T.
- NODk is not exported (the node-breaker export is not written yet), and owners, ZCOD, VMSTAR and ANSTAR are not exported.

## Where the rules are specified

The per-field classification with its reasons is in the [import mapping](../CIMTBL_MAPPING.md) (sections Transformer and
Transformer: the forms it raises on) and the [export mapping](../EXPORT_MAPPING.md) (section E4).
