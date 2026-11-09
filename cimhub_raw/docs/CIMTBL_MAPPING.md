# PSS/E RAW v34 → `.cimtbl` mapping spec

**Status:** R0 approved 2026-11-08 and implemented (master, zone, area, bus with substations, busbars, voltage
limits and solved voltages; owner). Goldens: `tests/goldens/IEEE14/`; tests: `tests/test_raw_to_cimtbl.py`. Plan: [`RAW_REWRITE_PLAN.md`](../../.development/RAW_REWRITE_PLAN.md).
Format: the `cimtbl-mapping-spec` skill; contract: the `cimtbl-import-contract` skill; shapes: the `cimtbl-shapes`
skill.

The classification tables are generated with `cimhub_core.cimtbl.fields_table(..., fields=FIELDS)` from the
mapper's `FIELDS`, and `check_fields` checks them against the schema. Samples come from the committed cases,
IEEE14 and WECC240. Field names are the LinkML slots; the RAW names (I, BASKV, ...) start each note.

**Reader conventions the mappers rely on** (`raw34_reader.py`):
- A blank or missing field is `None`. The mapper fills it from the schema's `raw_default` with
  `cimhub_core.cimtbl.fill_defaults`, and lists it on the row comment (`# defaulted: ...`).
- Every bus reference is a bus number: extended names are resolved by the reader.
- Strings are trimmed of trailing blanks.

## Artifact files and order

| # | native class | artifact | shape | depends on |
|---|---|---|---|---|
| 0 | case identification + system-wide data | `<Model>.cimtbl` (master) | `common` + `line_bus_branch`'s `BasePower`: BasePower, BaseFrequency, GeographicalRegion, BaseVoltage | |
| 1 | Zone | `zone.cimtbl` | `SubGeographicalRegion` (`srgn_<I>`) | the master |
| 2 | Area | `area_interchange.cimtbl` | `ControlArea` (`ca_<I>`; new, C2/C3) | the master |
| 3 | Bus | `bus.cimtbl` | `line_bus_branch`: `Substation`s (synthesized, §bus), `TopologicalNode`s, one `BusbarSection` per bus | 0, 1 |
| – | Owner | none | untranscribed (CIM 18 gap) | |

Later slices append to this order: branch, switch, multi-section line (R1); load and shunts (R2); generator (R3);
transformer (R4); inter-area transfer (R5); substation (R6).

## Master

Orchestrator: `importer/raw_to_cimtbl.py` (`RawImporter(CimtblImporter)`, `model_cls = BusBranchModel`,
`MAPPING_ORDER`, `map_master`, `raw_to_cim`).

```
# PSS/E RAW case IEEE14: 08/19/93 UW ARCHIVE           100.0  1962 W IEEE 14 BUS TES
# Mapping: cimhub_raw/docs/CIMTBL_MAPPING.md#master
# untranscribed: GAUSS, NEWTON, ADJUST, TYSL, SOLVER (solution options)
Profile = cim18v17
Authority = https://github.com/PNNL-CIM-Tools/CIMHub
Model = IEEE14

Object BasePower: mRID=sbase, basePower (MVA)=100.0
Object BaseFrequency: mRID=bf_60hz, frequency (Hz)=60.0
Object GeographicalRegion: mRID=rgn_ieee14, name=IEEE14
Table BaseVoltage: mRID, nominalVoltage (kV)
    bv_138kv, 138.0
Table OperationalLimitType: mRID, name, durationKind, isInfiniteDuration, direction
    olt_normal_high,    normal high,    normal,    true,  high
    olt_normal_low,     normal low,     normal,    true,  low
    olt_emergency_high, emergency high, emergency, false, high
    olt_emergency_low,  emergency low,  emergency, false, low
Import zone
Import area_interchange
Import bus
```

- **Model and Authority (plan D7):** the caller names the model (`RawImporter("IEEE14")`). It is the master's file
  stem, its `Model`, and the GeographicalRegion's name. `rgn_` + the name, lowercased, is that region's mRID.
  `Authority` is the CIMHub one unless the caller passes another.
- **BasePower comes first** (G13), so every later `(pu system)` column converts on SBASE.
- **BaseFrequency:** BASFRQ. It is blank in WECC240; a blank becomes 60 Hz, marked `# defaulted: BASFRQ=60` (RAW-17:
  the spec's default is "the present option setting", and PSS/E ships 60).
- **OperationalLimitType:** the four bus voltage-limit types (RAW-19). R1 adds one per RATING record (RAW-9).
- **BaseVoltage:** one row per distinct BASKV, highest first. The mRID comes from `cimtopology.core.voltage.base_voltage_mrid`
  (`bv_345kv`, `bv_13p8kv`), as DSS uses, so two spokes name a voltage the same way. `nominalVoltage (kV)` is
  BASKV copied.
- **Comment:** the case name and its first title line, the untranscribed system-wide records, and `not mapped:`
  with the record count of every RAW class no mapper reads yet, so a class never disappears silently.
- **Fail fast:** IC ≠ 0 (a change case); a model with no buses; a BASKV that is blank or ≤ 0 (the spec defaults it
  to 0.0, which is no base).

| CaseIdentificationRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `new_case_flag` | `Union[int, CaseIdentificationRecordNewCaseFlag]` | `0` | structural | IC: 0 (base case) maps; 1 (add to the working case) raises, a change case is not a model |
| `system_base_mva` | `Optional[float]` | `100.0` | copied | `BasePower.basePower` (MVA); SBASE; blank: 100 (defaulted) |
| `revision` | `Optional[float]` | `34.0` | structural | REV: the reader reads 34 only |
| `transformer_ratings_units` | `Optional[int]` | `0` | mapped | XFRRAT: selects what transformer RATEn-k are (<= 0 MVA; > 0 current as MVA at 1 pu voltage); read by R4 |
| `branch_ratings_units` | `Optional[int]` | `0` | mapped | NXFRAT: the same for branch RATEn; read by R1 |
| `system_base_frequency` | `Optional[float]` | `60.0` | copied | `BaseFrequency.frequency` (Hz); BASFRQ; blank: 60 (defaulted; the spec's 'present option setting', RAW-17) |
| `titles` | `Union[str, list[str], NoneType]` | `[' 08/19/93 UW ARCHIVE           100....`, `['This is a reduced WECC 240-bus powe...` | untranscribed | the two title lines go on the master's comment; no CIM home |
| `general` | `Optional[str]` | `GENERAL, THRSHZ=0.0001, PQBRAK=0.7, B...` | structural | GENERAL: its THRSHZ is the zero-impedance threshold of the substation merge (plan 3.2; default 0.0001); the record itself is a solution option |
| `gauss` | `Optional[str]` | `GAUSS, ITMX=100, ACCP=1.6, ACCQ=1.6, ...` | untranscribed | solution options; no home in the network profile parts |
| `newton` | `Optional[str]` | `NEWTON, ITMXN=20, ACCN=1.0, TOLN=0.1,...` | untranscribed | solution options; no home in the network profile parts |
| `adjust` | `Optional[str]` | `ADJUST, ADJTHR=0.005, ACCTAP=1.0, TAP...` | untranscribed | solution options; no home in the network profile parts |
| `tysl` | `Optional[str]` | `TYSL, ITMXTY=20, ACCTY=1.0, TOLTY=0.0...` | untranscribed | solution options; no home in the network profile parts |
| `solver` | `Optional[str]` | `SOLVER,     , ACTAPS=0, AREAIN=0, PHS...` | untranscribed | solution options; no home in the network profile parts |
| `ratings` | `Union[dict[Union[int, RatingRecordRatingSetNumber], Union[dict, ForwardRef('RatingRecord')]], list[Union[dict, ForwardRef('RatingRecord')]], NoneType]` | `[RatingRecord({'rating_set_number': 1...` | structural | RATING records: one OperationalLimitType olt_rate<n> each, written with R1 (RAW-9) |

## Zone

Mapper: `importer/cimtbl/zone.py` (`map_zone`). One `SubGeographicalRegion` per zone, in the case's region:

```
Table SubGeographicalRegion: mRID, name, Region=rgn_ieee14
    srgn_1, IEEE 14
```

- A bus whose ZONE has no Zone record (RAW allows it; the Zone section is optional) gets a synthesized
  `srgn_<zone>` named by the number, under `# synthesized: zones that buses name but the Zone data does not`.
- A Zone record that no bus uses is still written.

| ZoneRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `zone_number` | `Union[int, ZoneRecordZoneNumber]` | `1`, `10`, `11` | structural | I: mRID = srgn_ + I, Region = the case's rgn_; the name when ZONAME is blank |
| `zone_name` | `Optional[str]` | `IEEE 14`, `ALBERTA`, `NEW MEXI` | copied | `SubGeographicalRegion.name`; ZONAME; blank: the zone number |

## Area interchange

Mapper: `importer/cimtbl/area_interchange.py` (`map_area_interchange`). One `ControlArea` per area:

```
Table ControlArea: mRID, name, netInterchange (MW), pTolerance (MW)
    ca_1, IEEE14, 0.0, 999.99
```

- Members come from the equipment (cim18v17 profile of 2026-11-08): generating units through
  `ControlAreaGeneratingUnit` (R3), loads through `ConformLoadGroup` → `SubLoadArea` → `ControlArea` (R2), and
  terminals of branches between areas through `TieFlow` (R5). A bus's own AREA and the slack bus ISW have no home
  (CIM 18 gap).
- `type` (`ControlAreaTypeKind`) is left unset: RAW does not say whether an area is used for AGC or for
  interchange.
- The `ca_` prefix and a `control_area` shape are requests C2/C3. Until then this section is the shape.

| AreaInterchangeRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `area_number` | `Union[int, AreaInterchangeRecordAreaNumber]` | `1`, `2`, `3` | structural | I: mRID = ca_ + I (prefix requested, C3); the name when ARNAME is blank |
| `bus_number` | `Optional[int]` | `2`, `0` | untranscribed | ISW, the area slack bus: no ControlArea slack association (CIM 18 gap) |
| `pdes` | `Optional[float]` | `0.0` | copied | `ControlArea.netInterchange` (MW); PDES; blank: 0 (defaulted) |
| `ptol` | `Optional[float]` | `999.99`, `5.0` | copied | `ControlArea.pTolerance` (MW); PTOL; blank: 10 (defaulted) |
| `name` | `Optional[str]` | `IEEE14`, `SOUTH`, `CALIFORNIA` | copied | `ControlArea.name`; ARNAME; blank: the area number |

## Bus

Mapper: `importer/cimtbl/bus.py` (`map_bus(native, merge_threshold)`). It writes the substations, then one
`TopologicalNode` per bus.

### Substations (plan §3.2, RAW-2)

Every bus lands in a `Substation`. Buses joined by equipment that sits inside a substation share one, but never
across a zone boundary:
- **Merge equipment:**
  - every system switching device;
  - a zero-impedance branch: R = 0 and \|X\| ≤ THRSHZ (from `GENERAL`, default 0.0001);
  - a branch whose CKT starts with `@` or `*`;
  - a series capacitor (X < 0; RAW-15, R1);
  - every transformer, all of its windings' buses.
- **Zone boundary:** a merge edge between two zones is skipped, so the equipment sits on the substation boundary.
  This is the interim form of the zone gap (§CIM 18 gaps).
- **Grouping:** `cimtopology.core.Topology(Network(branches=<one Branch per merge edge>, nodes=<every bus>)).islands()`.
  No local union-find.
- **Identity:** `sub_` + the lowest bus number of the group. Its name is that bus's NAME, and its `Region` is its
  zone's `srgn_`. The row comment lists the group's buses and the equipment that merged them.

```
# synthesized: substations, buses merged across switching devices, zero-impedance branches (|X| <= THRSHZ 0.0001),
# series capacitors and transformers, within a zone (11 substations)
Table Substation: mRID, name, Region
    sub_1, BUS 1, srgn_1
    sub_4, BUS 4, srgn_1  # buses 4, 7, 9; xf_4_7_0_1, xf_4_9_0_1
    sub_5, BUS 5, srgn_1  # buses 5, 6; xf_5_6_0_1
    ...
```

The result on the committed cases is 11 substations for IEEE14 (two of several buses: {4, 7, 9}, {5, 6}) and
134 for WECC240 (79 of several buses, the largest 7). Without the zone boundary, WECC240 would have 131.

### Nodes and busbars

The tables after the substations, in file order: TopologicalNode, BusbarSection, OperationalLimitSet,
VoltageLimit, SvVoltage.

```
Table TopologicalNode: mRID, name, busNumber, BaseVoltage, ConnectivityNodeContainer
    1, BUS 1, 1, bv_138kv, sub_1
    ...
# IDE 4 (isolated): none

# one BusbarSection per bus: its terminal holds the bus's voltage limits and any regulation of the bus
Table BusbarSection: mRID, name, bus, BaseVoltage, EquipmentContainer
    bb_1, BUS 1, 1, bv_138kv, sub_1
    ...
```

- **BusbarSection (RAW-19, RAW-11):** `bb_` + I (prefix requested, C3), on the bus's node, in its substation.
  cimtables generates its terminal `bb_<I>_T1`. That terminal is where every limit and control of the bus goes:
  - **Voltage limits:** an `OperationalLimitSet` `bb_<I>_limits` (`Terminal = bb_<I>_T1`) with
    `VoltageLimit`s `bb_<I>_nvhi`, `_nvlo`, `_evhi`, `_evlo`. The limit types (in the master) are
    `olt_normal_high`, `olt_normal_low`, `olt_emergency_high` and `olt_emergency_low`: `direction` high/low,
    `durationKind` normal/emergency. A blank limit takes its spec default (1.1 / 0.9), listed as defaulted.
    `normalValue (kV)` = pu × BASKV is derived by `kv_from_per_unit` (user, 2026-11-08). A pu cell would need
    cimtables to reach the base through `Terminal.ConductingEquipment.BaseVoltage`, one hop too many.
  - **Solved voltage (RAW-14):** one `SvVoltage` per node (identity-only: `identifier` = `<I>_sv`). `v (kV)` = VM
    × BASKV (`kv_from_per_unit`) and `angle (deg)` = VA.
  - **Regulation (R2, R3):** a generator, switched shunt or transformer that regulates bus I names
    `bb_<I>_T1` as its control's `Terminal`.

- **Identity (RAW-18):** the bare bus number. The `cimtbl-translate` prefix table gives nodes no prefix. The core
  shape example (`line_bus_branch.cimtbl`) writes `bus_1`; that example should follow the table (request to the
  core owner).
- `name` = NAME, else the bus number. `busNumber` = I.
- Rows in bus-number order.

| BusRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `bus_number` | `Union[int, BusRecordBusNumber]` | `1`, `10`, `11` | copied | `TopologicalNode.busNumber`; I; node mRID = I (bare, the cimtbl-translate rule for nodes; RAW-18); BusbarSection mRID = bb_ + I (RAW-19) |
| `name` | `Optional[str]` | `BUS 1`, `BUS 10`, `BUS 11` | copied | `TopologicalNode.name`, `BusbarSection.name`; NAME; blank: the bus number |
| `base_voltage` | `Optional[float]` | `138.0`, `500.0`, `345.0` | structural | BASKV: the node's and the busbar's BaseVoltage bv_<kv>; the master writes one BaseVoltage per distinct BASKV, nominalVoltage (kV) copied; the base of every pu voltage of the bus |
| `bus_type` | `Optional[int]` | `3`, `1`, `2` | structural | IDE: 1 and 2 add nothing (the equipment says it); 3 (swing) is the angle reference, written with R3 (SynchronousMachine.referencePriority); 4 (isolated) is listed on the table comment |
| `area` | `Optional[int]` | `1`, `4`, `2` | untranscribed | AREA: a node or BusbarSection has no ControlArea association (CIM 18 gap); the bus's generators, loads and tie terminals carry the area (R2, R3, R5) |
| `zone` | `Optional[int]` | `1`, `3`, `10` | structural | ZONE: the Region of the node's Substation (srgn_<zone>), and a substation boundary (plan 3.2) |
| `owner` | `Optional[int]` | `1` | untranscribed | OWNER: ownership is an asset concept (CIM 18 gap) |
| `voltage_magnitude` | `Optional[float]` | `1.06`, `1.05099`, `1.05691` | derived | VM (pu): SvVoltage.v (kV) = VM x BASKV (kv_from_per_unit; RAW-14) |
| `voltage_angle` | `Optional[float]` | `0.0`, `-15.0972`, `-14.7906` | copied | `SvVoltage.angle` (deg); VA (RAW-14) |
| `normal_voltage_magnitude_high_limit` | `Optional[float]` | `1.1` | derived | NVHI (pu): home VoltageLimit bb_<I>_nvhi on the BusbarSection terminal's set bb_<I>_limits (RAW-19); normalValue (kV) = pu x BASKV (kv_from_per_unit) |
| `normal_voltage_magnitude_low_limit` | `Optional[float]` | `0.9` | derived | NVLO (pu): home VoltageLimit bb_<I>_nvlo on the BusbarSection terminal's set bb_<I>_limits (RAW-19); normalValue (kV) = pu x BASKV (kv_from_per_unit) |
| `emergency_voltage_magnitude_high_limit` | `Optional[float]` | `1.1` | derived | EVHI (pu): home VoltageLimit bb_<I>_evhi on the BusbarSection terminal's set bb_<I>_limits (RAW-19); normalValue (kV) = pu x BASKV (kv_from_per_unit) |
| `emergency_voltage_magnitude_low_limit` | `Optional[float]` | `0.9` | derived | EVLO (pu): home VoltageLimit bb_<I>_evlo on the BusbarSection terminal's set bb_<I>_limits (RAW-19); normalValue (kV) = pu x BASKV (kv_from_per_unit) |

## Owner

No artifact. The Owner table and every owner field on other records (bus OWNER, O1/F1..O4/F4) are untranscribed:
CIM keeps ownership in asset management (CIM 18 gap). The master comment counts the owners.

| OwnerRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `owner_number` | `Union[int, OwnerRecordOwnerNumber]` | `1` | untranscribed | ownership is an asset concept (CIM 18 gap); no owner.cimtbl is written |
| `owner_name` | `Optional[str]` | `1`, `OWNER1` | untranscribed | as I |

## Code tables

None in R0. IDE and IC are checked in the mapper (above). They are not CIM enums.

## CIM 18 gaps

Each is logged in the shared register (`CIMTBL-Models/distribution/CIM18_GAPS.md`) and in the plan's §6a:

| gap | RAW fields | R0 approximation |
|---|---|---|
| zone membership of a bus | ZONE | substations never span two zones |
| a bus's own control area, and the area slack (equipment is covered: `ControlAreaGeneratingUnit`, `LoadGroup` → `SubLoadArea`, `TieFlow`) | bus AREA, area ISW | untranscribed |
| the load-area hierarchy (`SubLoadArea` → `LoadArea` missing); area/zone of machines and DC equipment | induction machine, MTDC bus AREA/ZONE | loads per (area, zone) `SubLoadArea` (R2); the rest untranscribed |

Not gaps: a bus's voltage limits and its regulation sit on its `BusbarSection`'s terminal. CIM puts limits and
regulating controls on terminals by design (RAW-11, RAW-19).
| ownership of network equipment | Owner, OWNER, O1..F4 | untranscribed |

## Decisions this spec applies

- **RAW-14** (user, 2026-11-08): VM/VA → `SvVoltage`; generator PG/QG → `RotatingMachine.p`/`q` (R3).
- **RAW-17** (recommended): a blank BASFRQ → 60 Hz, defaulted.
- **RAW-18** (recommended): bare bus numbers as node mRIDs, per the translate table (the shape example writes
  `bus_<I>`; request C2).
- **RAW-19** (user, 2026-11-08): a `BusbarSection` per bus; voltage limits in kV on its terminal.

## Reference model and expected differences

The golden artifact directory is IEEE14's (`tests/goldens/IEEE14/`), generated by the orchestrator and reviewed by
hand. WECC240 is the bind and round-trip case.

There is no hand translation to differ from. CIMHub_2_0's old converter differs by design:
- it made one `VoltageLevel` per bus;
- it read none of the transformer controls past RATE1-12, and replaced them with schema defaults (§reader);
- it lost 1e-7 values on writing.
