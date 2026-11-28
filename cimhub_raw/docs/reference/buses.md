# Case, buses, areas and zones

The case-level data and the network's skeleton: the case identification record with its rating sets, buses, zones,
areas, the inter-area transfers, the tie flows of devices that join two areas, and owners. How to read the tables is on
the [reference landing page](index.md).

| RAW table | CIM classes | Import | Export |
|---|---|---|---|
| [Case identification and system-wide data](#case-identification-and-system-wide-data) | `BasePower`, `BaseFrequency`, `GeographicalRegion`, `BaseVoltage` | the master document | yes |
| [Rating sets (RATING)](#rating-sets) | `OperationalLimitType` | the master document | yes |
| [Bus](#bus) | `TopologicalNode`, `BusbarSection`, `OperationalLimitSet`, `VoltageLimit`, `SvVoltage`, `Substation` | `bus.cimtbl` | yes |
| [Zone](#zone) | `SubGeographicalRegion` | `zone.cimtbl` | yes |
| [Area interchange](#area-interchange) | `ControlArea` | `area_interchange.cimtbl` | yes |
| [Inter-area transfer](#inter-area-transfer) | none | listed on the `ControlArea` comment | no |
| [Tie flows](#tie-flows) | `TieFlow` | in the artifact of each tie device | yes |
| [Owner](#owner) | none | untranscribed | no |

The importer writes one `.cimtbl` document per RAW table and a master that imports them. The master sets the
`BasePower` first, so every `(pu system)` column in a later document converts on SBASE. The shapes are on the core
site's [shapes page](https://pnnl-cim-tools.github.io/CIMHub/core/developer/shapes/).

## Case identification and system-wide data

The master document holds what applies to the whole case: one `BasePower` (mRID `sbase`), one `BaseFrequency` (mRID
`bf_<Hz>hz`, for example `bf_60hz`), the `GeographicalRegion` (mRID `rgn_<name>` in lower case, named for the model),
one `BaseVoltage` per distinct bus BASKV, the four bus voltage-limit `OperationalLimitType`s, the twelve rating-set
types, and one `Import` per document the case needs. A table with no records writes no document and no `Import`.

| field | import | export |
|---|---|---|
| IC (`new_case_flag`) | structural: 0 is a base case and maps; any other value raises | written: 0 |
| SBASE (`system_base_mva`) | copied to `BasePower.basePower` (MVA); blank takes 100, marked `# defaulted: SBASE=100` | written: `BasePower.basePower` in MVA through `get_qty`; the network must hold exactly one `BasePower`, else it raises |
| REV (`revision`) | structural: the reader accepts v34 only | written: 34 |
| XFRRAT (`transformer_ratings_units`) | mapped: 0 or less, transformer RATEn are MVA (`ApparentPowerLimit`); above 0, they are a current expressed as MVA (`CurrentLimit`, kA). Blank is MVA, noted in the master comment | written: 1 when the transformers' limits are `CurrentLimit`s, else 0 |
| NXFRAT (`branch_ratings_units`) | mapped: the same choice for branch and system switching device RATEn. Blank is MVA, noted in the master comment | written: 1 when the branch and switch limits are `CurrentLimit`s, else 0 |
| BASFRQ (`system_base_frequency`) | copied to `BaseFrequency.frequency` (Hz); blank takes 60, marked `# defaulted: BASFRQ=60` | written: the network's base frequency in Hz |
| title lines (`titles`) | untranscribed: the first line goes on the master comment | written: two blank lines |
| GENERAL (`general`) | structural: its THRSHZ (pu on the system base, default 0.0001) is the zero-impedance threshold of the [substation grouping](substations.md); the record is otherwise a solver option | not exported |
| GAUSS, NEWTON, ADJUST, TYSL, SOLVER | untranscribed: solution options have no CIM home; the master comment names the ones the case sets | not exported |
| RATING records (`ratings`) | structural: the names of the twelve rating-set types, see [Rating sets](#rating-sets) | written |

**Fail fast.** A case with no identification record, or with IC other than 0 (data added to a working case is a change
set, not a model). A case with no buses. A BASKV that is blank or not positive (the schema's default of 0.0 is no base).
Two BASKV values that give one `BaseVoltage` mRID. On export: a network with no `BasePower` or with two, ratings in
MVA on some devices and in current on others (RAW has one flag for each group), or a mix of `ApparentPowerLimit` and
`CurrentLimit` on one device.

**The master comment.** It names the case, its first title line, the solution options the case sets, `Owner <n>` when
owners exist, each unit flag the importer defaulted, and `not mapped:` followed by the record count of any RAW class
no mapper reads.

**BaseVoltage.** One row per distinct BASKV, highest first; `nominalVoltage` is BASKV copied in kV. The mRID is
`bv_<kV>kv` with `p` for a decimal point (`bv_345kv`, `bv_13p8kv`), the same rule the other CIMHub spokes use. A
two-terminal DC line also adds the valve-side voltage of each converter transformer, which is no RAW bus.

**Expected differences.** The title lines, solution options, GENERAL and the owners come back blank. A blank BASFRQ,
XFRRAT or NXFRAT comes back as the value the importer assumed. A case that sets NXFRAT to 1 but rates nothing comes
back with 0, since the flag says nothing then.

Excerpt from `cimhub_raw/tests/goldens/IEEE14/IEEE14.cimtbl`:

```
# PSS/E RAW case IEEE14: 08/19/93 UW ARCHIVE           100.0  1962 W IEEE 14 BUS TES
# Mapping: cimhub_raw/docs/CIMTBL_MAPPING.md#master
# untranscribed: GAUSS, NEWTON, ADJUST, TYSL, SOLVER (solution options)
# untranscribed: Owner 1 (ownership is a CIM 18 gap)

Profile = cim18v17
Authority = https://github.com/PNNL-CIM-Tools/CIMHub
Model = IEEE14

Object BasePower: mRID=sbase, basePower (MVA)=100.0

Object BaseFrequency: mRID=bf_60hz, frequency (Hz)=60.0

Object GeographicalRegion: mRID=rgn_ieee14, name=IEEE14

# one per distinct BASKV
Table BaseVoltage: mRID, nominalVoltage (kV)
    bv_138kv, 138.0

# ... the OperationalLimitType tables: four bus voltage limits, then RATE1 to RATE12

Import zone.cimtbl

Import area_interchange.cimtbl

Import bus.cimtbl

# ... one Import for each later document: branch, load, fixed_shunt, generator, transformer
```

To see the master and parts without building CIM, call the importer on a case:

```python
from cimhub_raw.raw34_reader import Raw34Reader
from cimhub_raw.importer.raw_to_cimtbl import RawImporter

model = Raw34Reader("cimhub_raw/tests/cases/IEEE14/IEEE_14_bus.raw").read_all()
documents = RawImporter("IEEE14").to_cimtbl(model)
print([part.name for part in documents.parts])
# ['zone', 'area_interchange', 'bus', 'branch', 'load', 'fixed_shunt', 'generator', 'transformer']
print(documents.master.comment)
```

## Rating sets

RAW names its twelve rating sets with RATING records. The master writes all twelve as `OperationalLimitType`s
`olt_rate1` to `olt_rate12`, used or not. A device's RATEn then becomes a limit of type `olt_rate<n>` in the device's
own document: see [branches](branches.md) for where the limit sets sit.

| field | import | export |
|---|---|---|
| set number (`rating_set_number`) | structural: n in the mRID `olt_rate<n>` | written: n of the type's mRID |
| name (`rating_name`) | copied to `OperationalLimitType.name`; no record or blank: `RATE<n>` | written: `OperationalLimitType.name` |
| description (`rating_description`) | copied to `OperationalLimitType.description`; no record or blank: `RATING SET <n>` | written: `OperationalLimitType.description` |

The `direction` of every type is `absoluteValue`. `durationKind` is left unset, because a rating set has no fixed
meaning in RAW. The four voltage-limit types are `olt_normal_high`, `olt_normal_low`, `olt_emergency_high` and
`olt_emergency_low`, with `direction` high or low and `durationKind` normal or emergency.

A rating of 0 is PSS/E's "no limit" and writes no row. Ratings in MVA are `ApparentPowerLimit`s; ratings flagged "in
current expressed as MVA" (NXFRAT or XFRRAT above 0) are `CurrentLimit`s in kA, `RATEn / (sqrt(3) x BASKV)`, and the
exporter inverts that on the device's `BaseVoltage`.

**Expected differences.** A case with no RATING records (WECC240) comes back with the twelve default ones.

```
Table OperationalLimitType: mRID, name, description, direction=absoluteValue
    olt_rate1,  RATE1,  RATING SET 1
    olt_rate2,  RATE2,  RATING SET 2
    ...
```

## Bus

`bus.cimtbl` writes, in this order: the `Substation`s (see [substations](substations.md) for how the buses are
grouped), one `TopologicalNode` per bus, one `BusbarSection` per bus, an `OperationalLimitSet` per busbar with four
`VoltageLimit`s, and one `SvVoltage` per node. The bus's node mRID is the bare bus number, `bb_<I>` is the busbar, and
the busbar's terminal `bb_<I>_T1` is where the bus's voltage limits and any regulation of the bus are attached.

| field | import | export |
|---|---|---|
| I (`bus_number`) | copied to `TopologicalNode.busNumber`; the node mRID is I, the busbar mRID `bb_<I>` | written: `busNumber`; a node with none is internal to a device and is not a bus; a number used twice raises |
| NAME (`name`) | copied to `TopologicalNode.name` and `BusbarSection.name`; blank: the bus number | written: `name`, left blank when it equals the bus number; more than 12 characters raises |
| BASKV (`base_voltage`) | structural: the `BaseVoltage` `bv_<kV>kv` of the node and the busbar; blank or not positive raises | written: `get_base_voltage` in kV, line to line |
| IDE (`bus_type`) | structural: 1 and 2 add nothing, the equipment says it; 3 sets `SynchronousMachine.referencePriority` on the swing machine (see [generators](generators.md)); 4 (isolated) is listed on the node table comment | written: 3 for a bus with a `referencePriority` machine, 2 for a bus whose machine or connection has an enabled control, else 1 |
| AREA (`area`) | untranscribed: a node has no `ControlArea` link in CIM 18. A bus the export trace cannot reach is listed on its node row as `untranscribed: area=<n>` | written: traced from the generating units and tie flows, see [A bus's AREA](#a-buss-area); blank when untraced |
| ZONE (`zone`) | structural: the `Region` of the bus's `Substation` is `srgn_<ZONE>`; blank ZONE is 1 | written: the zone number of the `Region` of the node's `Substation` |
| OWNER (`owner`) | untranscribed: ownership is an asset concept in CIM | not exported |
| VM (`voltage_magnitude`) | derived: `SvVoltage.v` (kV) = VM x BASKV; blank VM is 1.0 | written: `get_node_voltage` v in kV divided by BASKV; no `SvVoltage` leaves it blank |
| VA (`voltage_angle`) | copied to `SvVoltage.angle` (deg) | written: `get_node_voltage` angle in deg |
| NVHI (`normal_voltage_magnitude_high_limit`) | derived: `VoltageLimit` `bb_<I>_nvhi`, `normalValue` (kV) = NVHI x BASKV, type `olt_normal_high`; blank is 1.1 | written: `get_voltage_limits` normal high in kV, divided by BASKV |
| NVLO (`normal_voltage_magnitude_low_limit`) | derived: `bb_<I>_nvlo`, type `olt_normal_low`; blank is 0.9 | written: normal low |
| EVHI (`emergency_voltage_magnitude_high_limit`) | derived: `bb_<I>_evhi`, type `olt_emergency_high`; blank is 1.1 | written: emergency high |
| EVLO (`emergency_voltage_magnitude_low_limit`) | derived: `bb_<I>_evlo`, type `olt_emergency_low`; blank is 0.9 | written: emergency low |

The voltage values are the one place the importer multiplies by hand: a pu value in a `.cimtbl` column would need
cimtables to reach the base through the terminal's equipment, so the mapper writes kV (`kv_from_per_unit`) and the
exporter writes pu back (`per_unit_from_kv`).

A blank field the importer fills from the schema default is marked on its row (`# defaulted: ...`). The rows are in bus-number order.

**Fail fast.** BASKV blank or not positive (`bus 7: BASKV=0.0 is no base voltage`). A case with no buses. On export: a
bus number on two nodes, no node with a bus number at all, a name over 12 characters, two busbars on one node that both
hold voltage limits, and a node with no bus number that reaches no numbered node or more than one through its
transformers.

### A bus's AREA

CIM 18 has no association from a node to a `ControlArea`, so the export recovers AREA from what CIM
does place in an area. Seeds are the bus of every generating unit with its `ControlArea`, and the terminals of a
[tie](#tie-flows): the tie terminal's bus takes the area of its `positiveFlowIn = false` flow and every other terminal of
that device takes the `true` (home) area. The area spreads across every device that is not a tie. A load is not a seed,
since a load's AREA is its own (see [loads](loads.md)). Two areas meeting in one connected group raise. A group with no
seed has no area: its buses come back with AREA blank, which PSS/E reads as 1, and the importer lists them when it
writes the case (`untranscribed: area=3 (no generator or tie reaches it)`).

**Expected differences of a bus.**

- IDE 4 comes back as 1.
- AREA of an untraced bus comes back blank.
- OWNER comes back blank, which PSS/E reads as 1.
- VM and the voltage limits can differ in the last digit, because they go pu to kV to pu.
- A NAME equal to the bus number comes back blank.

Excerpt from `cimhub_raw/tests/goldens/IEEE14/bus.cimtbl`:

```
# untranscribed: area, owner; IDE 4 (isolated): none
Table TopologicalNode: mRID, name, busNumber, BaseVoltage, ConnectivityNodeContainer
    1,  BUS 1,  1,  bv_138kv, sub_1
    ...
Table BusbarSection: mRID, name, bus, BaseVoltage, EquipmentContainer
    bb_1,  BUS 1,  1,  bv_138kv, sub_1
    ...
Table OperationalLimitSet: mRID, Terminal
    bb_1_limits,  bb_1_T1
    ...
# derived: normalValue = NVHI, NVLO, EVHI, EVLO (pu) x BASKV (kv_from_per_unit)
Table VoltageLimit: mRID, OperationalLimitSet, OperationalLimitType, normalValue (kV)
    bb_1_nvhi,  bb_1_limits,  olt_normal_high,    151.8
    bb_1_nvlo,  bb_1_limits,  olt_normal_low,     124.2
    ...
# solved state; derived: v = VM (pu) x BASKV (kv_from_per_unit); angle = VA
Table SvVoltage: identifier, TopologicalNode, v (kV), angle (deg)
    1_sv,  1,  146.28,             0.0
    2_sv,  2,  144.20999999999998, -4.9826
```

## Zone

One `SubGeographicalRegion` per zone, in the case's `GeographicalRegion`: `srgn_<I>`.

| field | import | export |
|---|---|---|
| I (`zone_number`) | structural: the mRID `srgn_<I>`; `Region` is the case's `rgn_<name>` | written: the number in the mRID `srgn_<n>`; an mRID not of that form takes the next number above the largest in use, and the export logs a count |
| ZONAME (`zone_name`) | copied to `SubGeographicalRegion.name`; blank: the zone number | written: `name`, left blank when it equals the number; more than 12 characters raises |

A bus whose ZONE has no Zone record gets a synthesized `srgn_<zone>` named for its number, under the comment
`synthesized: zones that buses name but the Zone data does not`. A Zone record no bus uses is still written.

**Expected differences.** A zone the importer synthesized comes back as a Zone record. A ZONAME equal to its number
comes back blank. Two mRIDs that give one number raise.

Excerpt from `cimhub_raw/tests/goldens/IEEE14/zone.cimtbl`:

```
Table SubGeographicalRegion: mRID, name, Region=rgn_ieee14
    srgn_1, IEEE 14
```

## Area interchange

One `ControlArea` per area record: `ca_<I>`. The area's members are not listed on it: generating units, loads and the
terminals of ties join their `ControlArea` through their own documents, and a record that names an AREA with no
area-interchange record raises.

| field | import | export |
|---|---|---|
| I (`area_number`) | structural: the mRID `ca_<I>` | written: the number in `ca_<n>`, by the same rule as zones |
| ISW (`bus_number`) | untranscribed: CIM 18 has no area slack association | not exported |
| PDES (`pdes`) | derived: `ControlArea.netInterchange` (MW) = -PDES, since PDES is the desired net export and `netInterchange` is positive into the area; blank is 0 | written: PDES = -`netInterchange` in MW through `get_qty` |
| PTOL (`ptol`) | copied to `ControlArea.pTolerance` (MW); blank is 10, marked defaulted | written: `pTolerance` in MW |
| ARNAME (`name`) | copied to `ControlArea.name`; blank: the area number | written: `name`, left blank when it equals the number; more than 12 characters raises |

`ControlArea.type` is left unset: RAW does not say whether an area is used for AGC or for interchange. cim18v17 marks
`netInterchange` and `pTolerance` for deletion in favor of `AreaInterchangeController`, which has no home for the
scheduled interchange, so both stay on `ControlArea`.

**Expected differences.** ISW comes back blank. An ARNAME equal to its number comes back blank. A blank PTOL comes back as 10.

Excerpt from the artifact the importer writes for `cimhub_raw/tests/atoms/area/areas.raw` (area 1 has PDES 50, area 2 has
PDES -50 and a blank PTOL, area 3 has no name):

```
# untranscribed: bus_number
# derived: netInterchange = -PDES (net_import)
Table ControlArea: mRID, name, netInterchange (MW), pTolerance (MW)
    ca_1, WEST, -50.0, 5.0
    # defaulted: ptol=10.0
    ca_2, EAST, 50.0,  10.0
    # defaulted: name=
    ca_3, 3,    0.0,   0.0
```

## Inter-area transfer

cim18v17 has no scheduled-transfer class, so the records have no document. Each is listed on the `ControlArea` table
comment of `area_interchange.cimtbl`, as `ARFROM -> ARTO 'TRID' PTRAN MW`, in file order.

| field | import | export |
|---|---|---|
| ARFROM (`from_area`) | untranscribed: listed on the comment; no area-interchange record for it raises | not exported |
| ARTO (`to_area`) | untranscribed: as ARFROM | not exported |
| TRID (`transfer_id`) | untranscribed: listed; blank is 1, marked defaulted | not exported |
| PTRAN (`power_transfer`) | untranscribed: listed in MW, positive when ARFROM sells to ARTO; blank is 0, marked defaulted | not exported |

**Fail fast.** An ARFROM or ARTO with no area-interchange record: `inter-area transfer 1 -> 9 '1': to_area 9 has no
area-interchange record`.

**Expected differences.** The transfers are lost.

From the `areas.raw` atom:

```
# untranscribed: inter-area transfers (CIM 18 gap): 1 -> 2 '1' 30.0 MW; 1 -> 2 'A' 20.0 MW; 3 -> 2 '1' 0.0 MW
# (defaulted: transfer_id, power_transfer)
```

## Tie flows

A tie is a branch, system switching device, transformer or DC line whose terminals' buses are in more than one area.
The tie has no RAW table of its own. Its flags MET (branch), METERED (switch) and NMETR (transformer) choose the end
whose area PSS/E does not charge with the device's losses, called the home end, and CIM 18 has no field for that. The
importer records it with `TieFlow`s, and each device writes its own in its own document.

| device | flag | home end |
|---|---|---|
| branch | MET 1 (bus I is metered) | bus J |
| branch | MET 2 | bus I |
| system switching device | METERED 1 | the to bus |
| system switching device | METERED 2 | the from bus |
| transformer | NMETR 1, 2 or 3 | that winding; default 2 |

Any other MET or METERED on a tie raises. Off a tie the flag stays untranscribed, and the device's table comment says
so.

At each terminal whose bus is not in the home area, two `TieFlow`s sit on that terminal: one for the bus's own area with
`positiveFlowIn = false`, and one for the home area with `positiveFlowIn = true`. The pair sums to zero, as the
`ControlArea` rules ask of a tie seen from both areas. A three-winding transformer with two windings outside its home area
has two pairs. The mRID is `tf_<AREA>_<terminal>` and the name `<AREA>_<key>_T<k>`.

| | import | export |
|---|---|---|
| metered end | the terminal holding the pair | MET and METERED are the number of the terminal holding the pair, and a branch or switch with pairs on two of its terminals raises; NMETR is the lowest winding whose terminal holds no pair, and a transformer with a pair on every winding raises |
| a pair | two `TieFlow` rows | read to seed the [AREA trace](#a-buss-area); a pair that does not have one `false` and one `true` flow raises |

**Expected differences.** MET, METERED and NMETR of a device inside one area come back as their defaults (1, 1 and 2).

Excerpt from the artifact the importer writes for `cimhub_raw/tests/atoms/area/areas.raw` (`switch.cimtbl`, a switch
between buses 102 in area 1 and 301 in area 3, METERED 2):

```
# tie flows: two TieFlows on each tie's metered terminal, positiveFlowIn = false for the terminal's bus's area and true for the home (non-metered) end's area (METERED)
Table TieFlow: mRID, name, positiveFlowIn, ControlArea, Terminal
    tf_3_sw_102_301_1_T2, 3_102_301_1_T2, false, ca_3, sw_102_301_1_T2
    tf_1_sw_102_301_1_T2, 1_102_301_1_T2, true,  ca_1, sw_102_301_1_T2
```

## Owner

No document. CIM keeps ownership in asset management, so the Owner table and every owner field on other records (bus
OWNER, and O1 to O4 with F1 to F4 on loads, generators, branches, transformers and the rest) are untranscribed. The
master comment counts the owner records.

| field | import | export |
|---|---|---|
| I (`owner_number`) | untranscribed | not exported |
| OWNAME (`owner_name`) | untranscribed | not exported |

**Expected differences.** The Owner section comes back empty, and every owner field comes back blank, which PSS/E reads as owner 1.
