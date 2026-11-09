# PSS/E RAW v34 → `.cimtbl` mapping spec

**Status:** R0 approved 2026-11-08 and implemented (master, zone, area, bus with substations, busbars, voltage
limits and solved voltages; owner). R1 (branch, system switching device, multi-section line, rating
sets) approved and implemented 2026-11-08; atoms in `tests/atoms/branch/`. R2 (load, fixed shunt, switched
shunt) approved and implemented 2026-11-08; atoms in `tests/atoms/load/`, `tests/atoms/shunt/`. R3 (generator) approved and
implemented 2026-11-08; atom in `tests/atoms/generator/`. R4 (transformer) approved and implemented 2026-11-08; atom in
`tests/atoms/transformer/`. R5 (tie flows, a bus's AREA, inter-area transfer, the netInterchange sign) approved
and implemented 2026-11-08; atom in `tests/atoms/area/`. R6 (node-breaker substations: nodes, substation switching
devices, equipment terminals, regulated nodes) approved and implemented 2026-11-09; case `tests/cases/IEEE118/`,
atoms in `tests/atoms/substation/`. R4b (the transformer forms R4 raised on: fixed phase shifts, phase shifters,
impedance correction tables, fixed ratios, one winding out, CONT 0 and negative, load-drop compensation) approved
and implemented 2026-11-09; atom `tests/atoms/transformer/forms_r4b.raw`. P2a (shunt FACTS devices, VSC DC lines)
and P2b (two-terminal DC lines) approved and implemented 2026-11-09; atoms in `tests/atoms/dc/`. R3b's implicit step-up transformers approved and implemented 2026-11-09; atom `tests/atoms/generator/step_up.raw`. Goldens: `tests/goldens/IEEE14/`, `tests/goldens/IEEE118/`; tests:
`tests/test_raw_to_cimtbl.py`. Plan: [`RAW_REWRITE_PLAN.md`](../../.development/RAW_REWRITE_PLAN.md).
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
| 2 | Area | `area_interchange.cimtbl` | `ControlArea` (`ca_<I>`; new, C2/C3); the inter-area transfers listed on its comment (R5) | the master |
| 3 | Bus | `bus.cimtbl` | `line_bus_branch`: `Substation`s (synthesized, §bus; a SUBSTATION block's `sub_s<IS>`, R6), `TopologicalNode`s, one `BusbarSection` per bus | 0, 1 |
| 3a | Substation (nodes, switching devices) | `substation.cimtbl` | a node-breaker `substation` (new, C2): `ConnectivityNode`s in their buses' `TopologicalNode`s, `Switch` / `Breaker` / `Disconnector` with `node1`/`node2` + `bus1`/`bus2`, a located block's `Location`, a `BusbarSection` per regulated node (R6) | 3 |
| 4 | Branch | `branch.cimtbl` | `line_bus_branch`: `ACLineSegment` (`ln_`), `SeriesCompensator` (`sc_`, X < 0), ratings on terminals, line shunts (R1), `TieFlow`s of ties (R5) | 3 |
| 5 | System switching device | `switch.cimtbl` | `switch` with `bus1`/`bus2` (R1), `TieFlow`s of ties (R5) | 3 |
| 6 | Multi-section line | `multi_section_line.cimtbl` | `Line` + `Update` rows on its sections (R1) | 4 |
| 7 | Load | `load.cimtbl` | `load` with `bus`: `LoadArea` ⊃ `SubLoadArea` ⊃ load groups, ZIP `LoadResponseCharacteristic`s, `ConformLoad` / `NonConformLoad` (R2) | 2, 3 |
| 8 | Fixed shunt | `fixed_shunt.cimtbl` | `shunt` with `bus`: `LinearShuntCompensator` (R2) | 3 |
| 9 | Switched shunt | `switched_shunt.cimtbl` | `shunt` with `bus`: `RegulatingControl`, a `LinearShuntCompensator` per block (R2) | 3 |
| 10 | Generator | `generator.cimtbl` | `synchronous_machine` (bus-branch, new, C2) and `der` with `bus`: a `RegulatingControl` per plant; `SynchronousMachine` + `GeneratingUnit` (WMOD 0) or `PowerElectronicsConnection` + `PowerElectronicsUnit` (WMOD 1), each with its control-area membership (R3) | 2, 3 |
| 11 | Transformer | `transformer.cimtbl` | `transformer_by_ends` with `bus` (2-winding r/x/g/b on end 1, cim18v17; C2) + the `regulator` shape's `RatioTapChanger` / `TapChangerControl`: `PowerTransformer`, an end per winding, a 3-winding unit's `TransformerMeshImpedance`s, ratings per winding (R4), `TieFlow`s of ties (R5) | 3 |
| 12 | Equipment terminal | `equipment_terminal.cimtbl` | `Update Table Terminal: mRID, ConnectivityNode` (R6) | 3a and every equipment artifact |
| – | Owner | none | untranscribed (CIM 18 gap) | |

Inter-area transfer has no artifact (R5: listed on `area_interchange.cimtbl`). After 11 come `vsc_dc.cimtbl`
(`DCLine`, `DCLineSegment`, `DCTopologicalNode`s, `VsConverter`s, their capability curves, ratings and the
`TieFlow`s of ties) and `facts_device.cimtbl` (`StaticSynchronousCompensator` + `RegulatingControl`), both P2a, and
before them `two_terminal_dc.cimtbl` (P2b: the same DC rows, `CsConverter`s behind their converter transformers on
internal `TopologicalNode`s, whose BaseVoltages the master writes). Impedance correction comes before 11 (R4b). The
remaining phase-2 stubs (multi-terminal DC, GNE, induction machine) write nothing yet. `equipment_terminal.cimtbl` (12) comes after them all.

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
| `branch_ratings_units` | `Optional[int]` | `0` | mapped | NXFRAT: what branch and switch RATEn are: <= 0 MVA (ApparentPowerLimit), > 0 current as MVA (CurrentLimit, kA); blank: MVA (defaulted; the spec's 'present option setting') |
| `system_base_frequency` | `Optional[float]` | `60.0` | copied | `BaseFrequency.frequency` (Hz); BASFRQ; blank: 60 (defaulted; the spec's 'present option setting', RAW-17) |
| `titles` | `Union[str, list[str], NoneType]` | `[' 08/19/93 UW ARCHIVE           100....`, `['This is a reduced WECC 240-bus powe...` | untranscribed | the two title lines go on the master's comment; no CIM home |
| `general` | `Optional[str]` | `GENERAL, THRSHZ=0.0001, PQBRAK=0.7, B...` | structural | GENERAL: its THRSHZ is the zero-impedance threshold of the substation merge (plan 3.2; default 0.0001); the record itself is a solution option |
| `gauss` | `Optional[str]` | `GAUSS, ITMX=100, ACCP=1.6, ACCQ=1.6, ...` | untranscribed | solution options; no home in the network profile parts |
| `newton` | `Optional[str]` | `NEWTON, ITMXN=20, ACCN=1.0, TOLN=0.1,...` | untranscribed | solution options; no home in the network profile parts |
| `adjust` | `Optional[str]` | `ADJUST, ADJTHR=0.005, ACCTAP=1.0, TAP...` | untranscribed | solution options; no home in the network profile parts |
| `tysl` | `Optional[str]` | `TYSL, ITMXTY=20, ACCTY=1.0, TOLTY=0.0...` | untranscribed | solution options; no home in the network profile parts |
| `solver` | `Optional[str]` | `SOLVER,     , ACTAPS=0, AREAIN=0, PHS...` | untranscribed | solution options; no home in the network profile parts |
| `ratings` | `Union[dict[Union[int, RatingRecordRatingSetNumber], Union[dict, ForwardRef('RatingRecord')]], list[Union[dict, ForwardRef('RatingRecord')]], NoneType]` | `[RatingRecord({'rating_set_number': 1...` | structural | RATING records: the names of the twelve OperationalLimitTypes olt_rate<n> in the master (RAW-9; mapping in importer/cimtbl/ratings.py) |

**Rating sets (R1; RAW-9).** The master adds one `OperationalLimitType` per rating set, all twelve whether
used or not: `olt_rate<n>`, with `name`/`description` from the `RATING` record (else `RATEn` / `RATING SET n`)
and `direction = absoluteValue`. `durationKind` is left unset, because a PSS/E rating set has no fixed meaning.

```
# rating sets RATE1..RATE12 (RAW-9)
Table OperationalLimitType: mRID, name, description, direction=absoluteValue
    olt_rate1,  RATE1,  RATING SET 1
    ...
```

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
# untranscribed: bus_number
# derived: netInterchange = -PDES (net_import)
Table ControlArea: mRID, name, netInterchange (MW), pTolerance (MW)
    ca_1, IEEE14, 0.0, 999.99
```

- Members come from the equipment (cim18v17 profile of 2026-11-08): generating units through
  `ControlAreaGeneratingUnit` (R3), loads through `ConformLoadGroup` → `SubLoadArea` → `ControlArea` (R2), and
  the metered terminals of ties through `TieFlow` (R5). A bus's own AREA is traced from them on export, and the
  slack bus ISW has no home (CIM 18 gap; [R5](#areas-tie-flows-and-inter-area-transfer-r5)).
- netInterchange = -PDES (R5): PDES is an export, netInterchange an import.
- `type` (`ControlAreaTypeKind`) is left unset: RAW does not say whether an area is used for AGC or for
  interchange.
- The `ca_` prefix and a `control_area` shape are requests C2/C3. Until then this section is the shape.

| AreaInterchangeRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `area_number` | `Union[int, AreaInterchangeRecordAreaNumber]` | `1`, `2`, `3` | structural | I: mRID = ca_ + I (prefix requested, C3); the name when ARNAME is blank |
| `bus_number` | `Optional[int]` | `2`, `0` | untranscribed | ISW, the area slack bus: no ControlArea slack association (CIM 18 gap) |
| `pdes` | `Optional[float]` | `0.0` | derived | PDES (MW, the desired net export): ControlArea.netInterchange (MW, positive into the area) = -PDES (net_import, R5); blank: 0 (defaulted) |
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
| `area` | `Optional[int]` | `1`, `4`, `2` | untranscribed | AREA: a node or BusbarSection has no ControlArea association (CIM 18 gap); the export traces it from generating units and tie flows across devices inside one area (R5); a bus the trace cannot reach (untraced_area_buses) lists untranscribed: area=AREA on its TopologicalNode row |
| `zone` | `Optional[int]` | `1`, `3`, `10` | structural | ZONE: the Region of the node's Substation (srgn_<zone>), and a substation boundary (plan 3.2) |
| `owner` | `Optional[int]` | `1` | untranscribed | OWNER: ownership is an asset concept (CIM 18 gap) |
| `voltage_magnitude` | `Optional[float]` | `1.06`, `1.05099`, `1.05691` | derived | VM (pu): SvVoltage.v (kV) = VM x BASKV (kv_from_per_unit; RAW-14) |
| `voltage_angle` | `Optional[float]` | `0.0`, `-15.0972`, `-14.7906` | copied | `SvVoltage.angle` (deg); VA (RAW-14) |
| `normal_voltage_magnitude_high_limit` | `Optional[float]` | `1.1` | derived | NVHI (pu): home VoltageLimit bb_<I>_nvhi on the BusbarSection terminal's set bb_<I>_limits (RAW-19); normalValue (kV) = pu x BASKV (kv_from_per_unit) |
| `normal_voltage_magnitude_low_limit` | `Optional[float]` | `0.9` | derived | NVLO (pu): home VoltageLimit bb_<I>_nvlo on the BusbarSection terminal's set bb_<I>_limits (RAW-19); normalValue (kV) = pu x BASKV (kv_from_per_unit) |
| `emergency_voltage_magnitude_high_limit` | `Optional[float]` | `1.1` | derived | EVHI (pu): home VoltageLimit bb_<I>_evhi on the BusbarSection terminal's set bb_<I>_limits (RAW-19); normalValue (kV) = pu x BASKV (kv_from_per_unit) |
| `emergency_voltage_magnitude_low_limit` | `Optional[float]` | `0.9` | derived | EVLO (pu): home VoltageLimit bb_<I>_evlo on the BusbarSection terminal's set bb_<I>_limits (RAW-19); normalValue (kV) = pu x BASKV (kv_from_per_unit) |

## Branch (R1)

Mapper: `importer/cimtbl/branch.py` (`map_branch`). Shape: `line_bus_branch` (`r/x/bch (pu system)` on bus I's
`BaseVoltage` and the master's `BasePower`). One row per branch, in key order:

```
# untranscribed: o1, f1, o2, f2, o3, f3, o4, f4
# untranscribed off a tie: MET (a tie's TieFlows record it; CIM 18 gap, RAW-22)
Table ACLineSegment: mRID, name, bus1, bus2, r (pu system), x (pu system), bch (pu system), length (km), inService, BaseVoltage, EquipmentContainer
    ln_1_2_1,   1_2_1,   1,  2,  0.01938, 0.05917, 0.0528, , true, bv_138kv,
    ...
    ln_7_9_1,   7_9_1,   7,  9,  -0.0,    0.11001, 0.0,    , true, bv_138kv, sub_4
    ...
# series capacitors: X < 0 (RAW-15)
Table SeriesCompensator: mRID, name, bus1, bus2, compensatorType, r (pu system), x (pu system), inService, BaseVoltage, EquipmentContainer
    sc_2404_3893_1, 2404_3893_1, 2404, 3893, capacitor, 1e-07, -0.00935, true, bv_500kv, sub_2404
    ...
```

- **Class:** X < 0 → `SeriesCompensator` (`sc_`, `compensatorType = capacitor`, r/x verbatim; RAW-15). A
  series capacitor with B ≠ 0 raises: `SeriesCompensator` has no `bch`. Every other branch is an
  `ACLineSegment` (`ln_`). `gch` is not written (RAW has no line conductance).
- **BaseVoltage:** bus I's. A branch whose buses have different BASKV raises, because its `(pu system)` base
  would be ambiguous. Neither public case has one.
- **Container:** the substation, when both buses are in one (a zero-impedance branch, a `@`/`*` circuit, a
  series capacitor, or a parallel path inside a merged substation). Otherwise none, or the multi-section `Line`
  (below).
- **Status:** `inService` = ST == 1, written on every row. WECC240 has 4 branches out of service.
- **Ratings (RAW-9, RAW-20):** each nonzero RATEn is an `ApparentPowerLimit` in one `OperationalLimitSet` on the
  branch's first terminal (`sequenceNumber` 1, bus I; user 2026-11-08):

  ```
  Table OperationalLimitSet: mRID, Terminal
      ln_2000_2202_1_ratings, ln_2000_2202_1_T1
  Table ApparentPowerLimit: mRID, OperationalLimitSet, OperationalLimitType, normalValue (MVA)
      ln_2000_2202_1_rate2, ln_2000_2202_1_ratings, olt_rate2, 986.0
      ln_2000_2202_1_rate3, ln_2000_2202_1_ratings, olt_rate3, 888.0
      ...
  ```

  A zero RATEn is "no limit" in PSS/E, so it writes no row, and a branch with no nonzero rating has no set
  (IEEE14 has none; WECC240 has 281 nonzero ratings on 192 branches). When NXFRAT > 0 the ratings are a current
  "expressed as MVA" at the bus's base voltage. They become a `CurrentLimit` with `normalValue (kA)` = RATEn /
  (√3 × BASKV), derived by `current_from_rating`. A blank NXFRAT ("the present option setting", as for BASFRQ)
  is MVA, marked `# defaulted: NXFRAT=0` on the master.
- **Line shunts (RAW-13):** GI + jBI ≠ 0 gives a `LinearShuntCompensator` `cap_<I>_<J>_<CKT>_i` on bus I, and
  GJ + jBJ ≠ 0 gives `_j` on bus J. Each has `gPerSection`/`bPerSection (pu system)`, `nomU (kV)` = BASKV, one
  section, `inService` = the branch's ST, and the end bus's substation as its container: an ordinary shunt
  (user 2026-11-08). "Switched with its line" has no CIM association in a bus-branch model, so it is carried by
  the mRID only (CIM 18 gap; in a node-breaker model the shunt would sit on the line's side of the breaker).
  Neither public case sets a line shunt; the atom `tests/atoms/branch/line_shunts.raw` covers it.
- **LEN (RAW-21):** `Conductor.length (km)`, copied: RAW's "user-selected units" are taken as km (user
  2026-11-08). LEN = 0 (the default, "not given") writes no length. A series capacitor with LEN ≠ 0 raises
  (`SeriesCompensator` is no `Conductor`). Neither public case sets one.
- **MET (RAW-22):** untranscribed, a CIM 18 gap (user 2026-11-08: power flow only, no interchange balancing).
  WECC240 has 81 branches with MET = 2, written back as MET = 1 (expected difference).
- **Owners:** untranscribed (CIM 18 gap).
- **Name:** NAME, else the key `I_J_CKT`.

| BranchRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `from_bus_number` | `int` | `1001`, `1002`, `1004` | structural | I: bus1; BaseVoltage = bus I's bv_<BASKV>; I and J with different BASKV raise ((pu system) would have two bases) |
| `to_bus_number` | `int` | `1201`, `1202`, `1004` | structural | J: bus2 |
| `r` | `float` | `0.00177`, `0.0108`, `0.0005` | copied | `ACLineSegment.r` (pu system), `SeriesCompensator.r` (pu system); R |
| `x` | `float` | `0.03169`, `0.0965`, `0.0053` | copied | `ACLineSegment.x` (pu system), `SeriesCompensator.x` (pu system); X; X < 0: a SeriesCompensator, compensatorType = capacitor, x verbatim (RAW-15) |
| `circuit` | `Optional[str]` | `1`, `9`, `2` | structural | CKT: with I and J the key, mRID ln_<I>_<J>_<CKT> (X < 0: sc_); a first character @ or * is a substation merge edge (plan 3.2) |
| `b` | `Optional[float]` | `3.3446`, `0.3296`, `0.0882` | copied | `ACLineSegment.bch` (pu system); B; blank: 0 (defaulted); a series capacitor with B != 0 raises (SeriesCompensator has no bch) |
| `name` | `Optional[str]` |  | copied | `ACLineSegment.name`, `SeriesCompensator.name`; NAME; blank: the key I_J_CKT |
| `ratings` | `Union[float, list[float], NoneType]` | `[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0...`, `[0.0, 0.0, 1630.0, 0.0, 0.0, 0.0, 0.0...`, `[0.0, 0.0, 1800.0, 0.0, 0.0, 0.0, 0.0...` | structural | RATE1..RATE12: each nonzero RATEn an ApparentPowerLimit <eq>_rate<n> (normalValue (MVA)) in the set <eq>_ratings on terminal <eq>_T1, type olt_rate<n> (RAW-9, RAW-20); NXFRAT > 0: a CurrentLimit, normalValue (kA) = RATEn / (sqrt(3) x BASKV) (ka_from_rating); 0 is no limit, no row |
| `g_from` | `Optional[float]` | `0.0` | structural | GI: with BI, a LinearShuntCompensator cap_<I>_<J>_<CKT>_i on bus I when either is nonzero (RAW-13): gPerSection (pu system), nomU (kV) = BASKV, one section, inService = ST, the bus's substation |
| `b_from` | `Optional[float]` | `0.0` | structural | BI: with GI, a LinearShuntCompensator cap_<I>_<J>_<CKT>_i on bus I when either is nonzero (RAW-13): bPerSection (pu system), nomU (kV) = BASKV, one section, inService = ST, the bus's substation |
| `g_to` | `Optional[float]` | `0.0` | structural | GJ: with BJ, a LinearShuntCompensator cap_<I>_<J>_<CKT>_j on bus J when either is nonzero (RAW-13): gPerSection (pu system), nomU (kV) = BASKV, one section, inService = ST, the bus's substation |
| `b_to` | `Optional[float]` | `0.0` | structural | BJ: with GJ, a LinearShuntCompensator cap_<I>_<J>_<CKT>_j on bus J when either is nonzero (RAW-13): bPerSection (pu system), nomU (kV) = BASKV, one section, inService = ST, the bus's substation |
| `status` | `Optional[int]` | `1`, `0` | mapped | ST: inService = (ST == 1), also on the line shunts; blank: 1 (defaulted) |
| `metered_end` | `Optional[int]` | `1`, `2` | structural | MET: on a tie (I and J in two AREAs) the home end is the non-metered one (1: J, 2: I), and both TieFlows sit on the metered terminal (R5); another code on a tie raises; elsewhere untranscribed, the loss-allocation end has no CIM home (CIM 18 gap, RAW-22); blank: 1 (defaulted) |
| `length` | `Optional[float]` | `0.0` | copied | `ACLineSegment.length` (km); LEN, 'user-selected units' taken as km (RAW-21); 0 (the default): no length; a series capacitor with LEN != 0 raises (SeriesCompensator is no Conductor) |
| `o1` | `Optional[int]` | `1` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `f1` | `Optional[float]` | `1.0` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `o2` | `Optional[int]` |  | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `f2` | `Optional[float]` |  | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `o3` | `Optional[int]` |  | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `f3` | `Optional[float]` |  | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `o4` | `Optional[int]` |  | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `f4` | `Optional[float]` |  | untranscribed | ownership is an asset concept (CIM 18 gap) |

## System switching device (R1)

Mapper: `importer/cimtbl/switch.py` (`map_switch`). Shape: `switch` with `bus1`/`bus2`. Every switch merges its
buses into one substation (§3.2), which is its container. Neither public case has one; the atom
`tests/atoms/branch/switches.raw` has one of each STYPE, one open and one normally open.

```
# untranscribed: x
# untranscribed off a tie: METERED (a tie's TieFlows record it; CIM 18 gap, RAW-22)
Table Switch: mRID, name, bus1, bus2, open, normalOpen, BaseVoltage, EquipmentContainer
    sw_101_102_1, CONNECTOR, 101, 102, false, false, bv_138kv, sub_101

Table Breaker: mRID, name, bus1, bus2, open, normalOpen, BaseVoltage, EquipmentContainer
    sw_102_103_1, BREAKER, 102, 103, true, false, bv_138kv, sub_101

Table Disconnector: mRID, name, bus1, bus2, open, normalOpen, BaseVoltage, EquipmentContainer
    sw_103_104_1, DISCONNECT, 103, 104, false, true, bv_138kv, sub_101

# NXFRAT > 0: derived, normalValue = RATEn / (sqrt(3) x BASKV) (ka_from_rating)
Table CurrentLimit: mRID, OperationalLimitSet, OperationalLimitType, normalValue (kA)
    sw_101_102_1_rate1, sw_101_102_1_ratings, olt_rate1, 0.836739520564675
```

- **Class by STYPE:** 1 (generic connector) → `Switch`, 2 → `Breaker`, 3 → `Disconnector`. The `sw_` prefix is
  shared, so a change of class keeps the mRID. A blank or unknown STYPE raises: the spec gives no default.
- **Status:** `open` = STATUS == 0 and `normalOpen` = NSTATUS == 0.
- **X** is untranscribed: it is the solver's stand-in for zero impedance (X < THRSHZ), and a `Switch` has none.
  The exporter writes THRSHZ back (expected difference).
- **Ratings** as for branches (`sw_<key>_ratings` on `sw_<key>_T1`).
- A switch across a zone boundary is not a merge edge (§3.2). Its container is bus I's substation.

| SwitchRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `from_bus_number` | `int` | `101`, `102`, `103` | structural | I: bus1; BaseVoltage = bus I's bv_<BASKV>; EquipmentContainer = bus I's substation |
| `to_bus_number` | `int` | `102`, `103`, `104` | structural | J: bus2 |
| `circuit` | `Optional[str]` | `1` | structural | CKT: with I and J the key, mRID sw_<I>_<J>_<CKT> |
| `x` | `Optional[float]` | `0.0001` | untranscribed | X: the solver's stand-in for zero impedance (X < THRSHZ); a Switch has none; the exporter writes THRSHZ back (expected difference) |
| `ratings` | `Union[float, list[float], NoneType]` | `[200.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,...`, `[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0...` | structural | RATE1..RATE12: as a branch's, the set sw_<key>_ratings on sw_<key>_T1 (RAW-9, RAW-20) |
| `status` | `Optional[int]` | `1`, `0` | mapped | STATUS: open = (STATUS == 0); blank: 1 (defaulted) |
| `nstat` | `Optional[int]` | `1`, `0` | mapped | NSTATUS: normalOpen = (NSTATUS == 0); blank: 1 (defaulted) |
| `metered_end` | `Optional[int]` | `1`, `2` | structural | METERED: as a branch's MET, the TieFlows of a tie on its metered terminal (R5); elsewhere untranscribed (CIM 18 gap, RAW-22); blank: 1 (defaulted) |
| `stype` | `Optional[int]` | `1`, `2`, `3` | mapped | STYPE: the class, 1 Switch (generic connector), 2 Breaker, 3 Disconnector; blank or another code raises (the spec gives no default) |
| `name` | `Optional[str]` | `CONNECTOR`, `BREAKER`, `DISCONNECT` | copied | `Switch.name`, `Breaker.name`, `Disconnector.name`; NAME; blank: the key I_J_CKT |

## Multi-section line (R1)

Mapper: `importer/cimtbl/multi_section_line.py` (`map_multi_section_line`), after `branch.cimtbl` (RAW-12). The
sections stay ordinary branches and the dummy buses stay nodes. The record becomes a `Line` container, and each
section is moved into it by an `Update` row:

```
# untranscribed: met
Table Line: mRID, name, Region
    # path 1, 2, 3, 4
    msl_1_4_&1, &1, srgn_1

Update Table ACLineSegment: mRID, EquipmentContainer
    ln_1_2_1, msl_1_4_&1
    ln_2_3_1, msl_1_4_&1
    ln_4_3_1, msl_1_4_&1
```

- **Members:** the path I, DUM1, …, J. Each consecutive pair must be joined by exactly one branch not already
  used, in either direction, and each dummy bus must have exactly two branches. Anything else raises with the
  record. A member already in a substation raises too, because an `Update` only adds.
- **Region:** bus I's zone. **Name:** ID.
- The `msl_` prefix is requested from the translate-table owners (C3).
- Neither public case has one; the atom `tests/atoms/branch/multi_section_line.raw` covers it.

| MultiSectionLineRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `i` | `int` | `1` | structural | I: the path's first bus; with J and ID the key, mRID msl_<I>_<J>_<ID>; the Line's Region is bus I's zone |
| `j` | `int` | `4` | structural | J: the path's last bus |
| `dum1` | `int` | `2` | structural | DUM1: the path I, DUM1, .., J names the sections, one branch per step; each section's EquipmentContainer becomes the Line (an Update row) |
| `line_id` | `Optional[str]` | `&1` | copied | `Line.name`; ID: the key |
| `met` | `Optional[int]` | `1` | untranscribed | MET: the loss-allocation end has no CIM home (CIM 18 gap, RAW-22) |
| `dum2` | `Optional[int]` | `3` | structural | as DUM1 |
| `dum3` | `Optional[int]` |  | structural | as DUM1 |
| `dum4` | `Optional[int]` |  | structural | as DUM1 |
| `dum5` | `Optional[int]` |  | structural | as DUM1 |
| `dum6` | `Optional[int]` |  | structural | as DUM1 |
| `dum7` | `Optional[int]` |  | structural | as DUM1 |
| `dum8` | `Optional[int]` |  | structural | as DUM1 |
| `dum9` | `Optional[int]` |  | structural | as DUM1 |

## Load (R2)

Mapper: `importer/cimtbl/load.py` (`map_load`). Shape: `load` with `bus` in place of `node` (C2). One row per
load, in key order, after the area hierarchy and the ZIP models it names (IEEE14):

```
Table LoadArea: mRID, name, ControlArea
    la_1, 1, ca_1
Table SubLoadArea: mRID, name, LoadArea
    sla_1_1, 1_1, la_1
Table ConformLoadGroup: mRID, name, SubLoadArea
    clg_1_1, 1_1, sla_1_1
# ZIP fractions: PL, IP, YP over p; QL, IQ, -YQ over q (zip_mix)
Table LoadResponseCharacteristic: mRID, exponentModel, pConstantPower, pConstantCurrent, pConstantImpedance, qConstantPower, qConstantCurrent, qConstantImpedance
    zip_1_0_0_1_0_0, false, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0
# untranscribed: owner, interruptible, dgenp, dgenq, dgenf
Table ConformLoad: mRID, name, bus, p (MW), q (MVAr), inService, LoadResponse, LoadGroup, BaseVoltage, EquipmentContainer
    ld_2_1,  2_1,  2,  21.7, 12.7, true, zip_1_0_0_1_0_0, clg_1_1, bv_138kv, sub_2
    ...
```

- **p, q (RAW-8):** `p (MW)` = PL + IP + YP and `q (MVAr)` = QL + IQ − YQ, the load at 1 pu voltage, CIM's
  nominal. Derived by `load_p_q`. YQ enters with a minus sign because RAW makes YQ negative for an inductive
  load. WECC240 has 118 loads with YQ < 0 and 16 with YQ > 0; the 16 have q < 0.
- **ZIP mix:** the fractions are PL/p, IP/p, YP/p and QL/q, IQ/q, −YQ/q, derived by `zip_mix`.
  - Each distinct mix is one shared row, `zip_` + its six fractions (`zip_0.5_0.3_0.2_0.25_0.25_0.5`), written
    before the loads.
  - A side whose components are all 0 counts as constant power. WECC240's mixes are `zip_0_1_0_0_0_1` and, for
    its 5 loads with q = 0, `zip_0_1_0_1_0_0`.
  - A side whose components cancel (total 0 from nonzero parts) raises.
  - The exporter recovers PL..YQ as p or q × fraction, so a mixed load can differ in the last digit (expected
    difference).
  - *Interim:* core's shared `zip_constant_pq` / `_i` / `_z` (`cimhub_core.load_response`, on `rc_1` only) take
    over the pure mixes once `raw-v34` takes `rc_1`.
- **Class from SCALE:** SCALE = 1 (scalable, the default) → `ConformLoad` in a `ConformLoadGroup`. SCALE = 0
  (fixed) → `NonConformLoad` in a `NonConformLoadGroup`. These are CIM's own "follows the system load pattern"
  split.
- **Area and zone:** the hierarchy is RAW's own totalling groups. It uses `SubLoadArea.LoadArea`, added to the
  profile 2026-11-08 by the user. Before that there was no list of sub-areas, and `ControlArea.EnergyArea` is
  0..1.
  - Each area that has loads gets one `LoadArea` `la_<area>`, with `ControlArea` = `ca_<area>`; it is the
    area's single `EnergyArea`.
  - Each (area, zone) pair with loads gets a `SubLoadArea` `sla_<area>_<zone>` in its `LoadArea`.
  - The `SubLoadArea` holds a `ConformLoadGroup` `clg_<area>_<zone>` and/or a `NonConformLoadGroup`
    `nclg_<area>_<zone>`.
  - WECC240 has 4 load areas and 14 sub-areas; IEEE14 has 1 and 1. The prefixes are requested (C3).
  - The load's own AREA and ZONE pick its group, so a load assigned elsewhere than its bus keeps both.
  - An AREA with no area-interchange record raises.
  - Blank AREA or ZONE: the bus's, defaulted (the spec's default).
  - The zone is still not an association: a `SubLoadArea` has no link to the `SubGeographicalRegion`. So the
    exporter reads a load's ZONE from its bus's substation `Region`. A load whose ZONE differs from its bus's
    sits in its own zone's sub-area, and is also listed on its row as
    `# untranscribed: zone=2 (bus 2 is in zone 1)` (CIM 18 gap, "zone of equipment"). Neither public case has
    one.
  - Not used: a `SubLoadArea` naming the `ControlArea` directly. cimtables binds a second one without error and
    overwrites the 0..1 inverse (request U-RAW-2).
- **Status:** `inService` = STATUS == 1.
- **Name:** the key `I_ID` (a v34 load has no NAME).
- **Untranscribed:** OWNER (CIM 18 gap); INTRPT; DGENP/DGENQ/DGENM. The distributed generation behind a load is
  zero in both public cases.
- **Atom:** `tests/atoms/load/loads.raw` covers a ZIP mix, SCALE 0, an area and zone other than the bus's, and
  blank AREA/ZONE.

| LoadRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `bus_number` | `int` | `10`, `11`, `12` | structural | I: bus; BaseVoltage = bus I's bv_<BASKV>; EquipmentContainer = bus I's substation |
| `load_id` | `Optional[str]` | `1` | structural | ID: with I the key, mRID ld_<I>_<ID>, name I_ID |
| `status` | `Optional[int]` | `1` | mapped | STATUS: inService = (STATUS == 1); blank: 1 (defaulted) |
| `area` | `Optional[int]` | `1`, `4`, `2` | structural | AREA: the LoadArea la_<AREA> (ControlArea ca_<AREA>) of the load's group; an AREA with no area-interchange record raises; blank: the bus's (defaulted) |
| `zone` | `Optional[int]` | `1`, `3`, `10` | structural | ZONE: the SubLoadArea sla_<AREA>_<ZONE> of the load's group; the exporter reads ZONE from the bus's substation Region, so a ZONE other than the bus's is also listed untranscribed on the row (CIM 18 gap); blank: the bus's (defaulted) |
| `constant_real_power` | `Optional[float]` | `9.0`, `3.5`, `6.1` | derived | PL: constant power; the sum is p (MW) / q (MVAr) at 1 pu (load_p_q) and its share a ZIP fraction (zip_mix) |
| `constant_imag_power` | `Optional[float]` | `5.8`, `1.8`, `1.6` | derived | QL: constant power; the sum is p (MW) / q (MVAr) at 1 pu (load_p_q) and its share a ZIP fraction (zip_mix) |
| `constant_current_real_power` | `Optional[float]` | `0.0`, `223.71`, `2212.664` | derived | IP: constant current; the sum is p (MW) / q (MVAr) at 1 pu (load_p_q) and its share a ZIP fraction (zip_mix) |
| `constant_current_imag_power` | `Optional[float]` | `0.0` | derived | IQ: constant current; the sum is p (MW) / q (MVAr) at 1 pu (load_p_q) and its share a ZIP fraction (zip_mix) |
| `constant_admittance_real_power` | `Optional[float]` | `0.0` | derived | YP: constant admittance; the sum is p (MW) / q (MVAr) at 1 pu (load_p_q) and its share a ZIP fraction (zip_mix) |
| `constant_admittance_imag_power` | `Optional[float]` | `0.0`, `583.546`, `-387.354` | derived | YQ: constant admittance, negative for an inductive load, so it enters q as -YQ; the sum is p (MW) / q (MVAr) at 1 pu (load_p_q) and its share a ZIP fraction (zip_mix) |
| `owner` | `Optional[int]` | `1` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `scale` | `Optional[int]` | `1` | mapped | SCALE: the class, 1 ConformLoad (scalable) in a ConformLoadGroup clg_<AREA>_<ZONE>, 0 NonConformLoad (fixed) in a NonConformLoadGroup nclg_<AREA>_<ZONE>; blank: 1 (defaulted) |
| `interruptible` | `Optional[int]` | `0` | untranscribed | INTRPT: no CIM home |
| `dgenp` | `Optional[float]` | `0.0` | untranscribed | DGENP: distributed generation behind the load, no CIM home |
| `dgenq` | `Optional[float]` | `0.0` | untranscribed | DGENQ: as DGENP |
| `dgenf` | `Optional[int]` | `0` | untranscribed | DGENM: as DGENP |

## Fixed shunt (R2)

Mapper: `importer/cimtbl/fixed_shunt.py` (`map_fixed_shunt`). Shape: `shunt` with `bus` and no control, like the
line shunts of R1 (IEEE14):

```
Table LinearShuntCompensator: mRID, name, bus, gPerSection (pu system), bPerSection (pu system), nomU (kV), maximumSections, normalSections, sections, inService, BaseVoltage, EquipmentContainer
    cap_9_1, 9_1, 9, 0.0, 0.19, 138.0, 1, 1, 1, true, bv_138kv, sub_4
```

- **G, B:** GL and BL are MW and Mvar at 1 pu voltage, so `gPerSection` / `bPerSection (pu system)` =
  GL / SBASE and BL / SBASE, derived by `per_unit_from_mva`.
  - cimtables converts them to siemens on `nomU` = the bus's BASKV and SBASE.
  - BL > 0 is a capacitor in RAW and in CIM, so the sign is unchanged.
  - IEEE14 has one shunt (bus 9, BL = 19.0); WECC240 has none.
- One section, always in: maximumSections = normalSections = sections = 1.
- **Status:** `inService` = STATUS == 1.
- **Container:** the bus's substation.
- **Name:** the key `I_ID`. The ID is trimmed, so IEEE14's `' 1'` gives `cap_9_1`.
- **Atom:** `tests/atoms/shunt/fixed_shunts.raw`: two shunts on one bus, a reactor out of service.

| FixedShuntRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `bus_number` | `int` | `9` | structural | I: bus; nomU (kV) = bus I's BASKV, the (pu system) base; BaseVoltage = bus I's bv_<BASKV>; EquipmentContainer = bus I's substation |
| `shunt_id` | `Optional[str]` | ` 1` | structural | ID: with I the key, mRID cap_<I>_<ID>, name I_ID |
| `status` | `Optional[int]` | `1` | mapped | STATUS: inService = (STATUS == 1); blank: 1 (defaulted) |
| `gl` | `Optional[float]` | `0.0` | derived | GL (MW at 1 pu): gPerSection (pu system) = GL / SBASE (per_unit_from_mva); blank: 0 (defaulted) |
| `bl` | `Optional[float]` | `19.0` | derived | BL (Mvar at 1 pu, > 0 a capacitor in RAW and CIM): bPerSection (pu system) = BL / SBASE (per_unit_from_mva); blank: 0 (defaulted) |

## Switched shunt (R2)

Mapper: `importer/cimtbl/switched_shunt.py` (`map_switched_shunt`). Shape: `shunt` with `bus`.
- **What a record is:** every switched bank at one bus under one controller, as up to 8 blocks of Ni identical
  steps of Bi Mvar (Bi < 0 a reactor; reactor blocks first).
- **Per block:** to match how the banks are wired and switched (user 2026-11-08), each block is its own
  `LinearShuntCompensator`, and all of them name one `RegulatingControl`.
- **Order:** the control comes first. Its terminal is a busbar's from `bus.cimtbl`, so no `Update` is needed.

WECC240:

```
# untranscribed: adjm, rmpct, rmidnt
# targetValue and targetDeadband in V
Table RegulatingControl: mRID, name, mode, discrete, enabled, targetValue, targetDeadband, Terminal
    # defaulted: nreg=0
    cc_4001, 4001, voltage, true, true, 500000.0, 500000.0, bb_4001_T1
    ...
# one per block: Ni sections of Bi; sections split from BINIT (block_sections)
Table LinearShuntCompensator: mRID, name, bus, bPerSection (pu system), nomU (kV), maximumSections, sections, inService, controlEnabled, RegulatingControl, BaseVoltage, EquipmentContainer
    swsh_4001_b1, 4001_b1, 4001, 2.0, 500.0, 5, 3.0, true, true, cc_4001, bv_500kv, sub_4001
    ...
```

- **mRIDs:**
  - each block is `swsh_<I>_b<k>`, in input order (prefix requested, C3);
  - the control is `cc_<I>`, the shunt shape's prefix;
  - the key is the bus, since a v34 switched shunt has no ID.
- **Blocks (RAW-10):** one `LinearShuntCompensator` per block, up to the first Ni or Bi that is 0 or blank (RAW's
  end of blocks):
  - maximumSections = Ni and `bPerSection (pu system)` = Bi / SBASE, derived by `per_unit_from_mva`;
  - `nomU` = the bus's BASKV;
  - the bus's substation as the container;
  - a block after the first zero raises.

  The block slots are never defaulted: a missing Ni/Bi is the end of blocks, not a value. All 7 WECC240 shunts
  have one block. `NonlinearShuntCompensator` is not used: its points hold one sequence of totals with no
  interpolation (`sections` must be one of the points), so it can say neither which bank is in nor a continuous
  state.
- **Sections:** RAW gives only the total in service, BINIT (Mvar at 1 pu). `block_sections` splits it in RAW's
  switching order (ADJM = 0):
  - BINIT < 0 fills the reactor blocks in input order, and BINIT > 0 the capacitor blocks;
  - each block in turn takes up to its Ni steps;
  - the block where BINIT runs out takes the rest as a fraction of a step (CIM allows a non-integer `sections`:
    MODSW 2, or an ADJM = 1 combination with the same total);
  - BINIT beyond the blocks' total raises;
  - `normalSections` is blank: RAW has no normal state apart from BINIT.

  The exporter's BINIT = Σ sections × Bi is exact either way. WECC240's sections are 3, 0, 4, 0, 6, 3, 1.
- **ADJM:** untranscribed: CIM has no switching-order method. The order is kept by `_b<k>`.
- **Control (MODSW).** The control is always written, so the blocks stay grouped even when locked:

  | MODSW | CIM |
  |---|---|
  | 0 locked | `enabled = false`, every block `controlEnabled = false`, `discrete` blank; the VSWHI/VSWLO target as read (unused) |
  | 1 discrete, voltage | `mode = voltage`, `discrete = true` |
  | 2 continuous, voltage | `mode = voltage`, `discrete = false` |
  | 3 plant Q, 5 another shunt's admittance | raise `NotImplementedError`: no case has one yet |
  | 4 VSC converter Q, 6 FACTS shunt Q | raise `NotImplementedError`: phase 2 (VSC DC, FACTS) |

  - **Regulated point:** `Terminal` = `bb_<SWREG>_T1`, or `bb_<I>_T1` when SWREG is 0 (RAW-11). NREG ≠ 0 names
    node NREG of the regulated bus: `bb_s<IS>_n<NREG>_T1`, that node's busbar (R6).
  - **Target:** `targetValue` = (VSWHI + VSWLO)/2 × the regulated bus's BASKV, and `targetDeadband` =
    (VSWHI − VSWLO) × BASKV. Both are in V, as the core shape writes them for mode voltage (deadband =
    the full band, target ± deadband/2). They are derived by `volts_from_per_unit`, which goes through the
    units library.
  - The subtraction can leave a last-digit float residue: the atom's 1.04 − 0.98 gives `6900.0000000000055`.
    The value is written as computed, never rounded, and the exporter's VSWHI/VSWLO can differ in the last digit
    (expected difference).
  - A cimtables `targetValue (kV)` column binds without error but drops the unit (request U-RAW-3).
  - WECC240's 1.5/0.5 pu bands give target = BASKV and deadband = BASKV.
- **Status:** `inService` = STATUS == 1 on every block.
- **Untranscribed:**
  - RMPCT: CIM has no participation share for a shunt (canonical CIM 18's `SynchronousMachine.qPercent` covers
    only machines; cim18v17 has it since 2026-11-08); CIM 18 gap; 100 everywhere in both cases;
  - RMIDNT: only used by MODSW 4 and 6, which raise.
- **Atom:** `tests/atoms/shunt/switched_shunts.raw` covers reactor + capacitor blocks with remote regulation,
  continuous mode with 2.5 steps, and a locked shunt (10 × 1.0 and 5 × 1.5 Mvar, BINIT 13 → 10 and 2 steps).

| SwitchedShuntRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `bus_number` | `int` | `4001`, `4005`, `6104` | structural | I: the key (a v34 switched shunt has no ID); every block's bus, nomU (kV) = its BASKV, BaseVoltage and EquipmentContainer (its substation) |
| `modsw` | `Optional[int]` | `1` | mapped | MODSW: 0 locked (control enabled = false), 1 voltage discrete, 2 voltage continuous; 3 and 5 raise (no case), 4 and 6 raise (phase 2); blank: 1 (defaulted) |
| `adjm` | `Optional[int]` | `0` | untranscribed | ADJM: the switching-order method has no CIM home; the block order is kept by _b<i> |
| `status` | `Optional[int]` | `1` | mapped | STATUS: inService = (STATUS == 1) on every block; blank: 1 (defaulted) |
| `vswhi` | `Optional[float]` | `1.5` | derived | VSWHI (pu): targetValue = (VSWHI + VSWLO) / 2 and targetDeadband = VSWHI - VSWLO, x the regulated bus's BASKV, in V (volts_from_per_unit); blank: 1.0 (defaulted) |
| `vswlo` | `Optional[float]` | `0.5` | derived | VSWLO (pu): as VSWHI |
| `swreg` | `Optional[int]` | `4001`, `4005`, `6104` | structural | SWREG: the regulated bus; the control's Terminal = bb_<SWREG>_T1, or bb_<I>_T1 when 0 (RAW-11); blank: 0 (defaulted) |
| `rmpct` | `Optional[float]` | `100.0` | untranscribed | RMPCT: CIM has no participation share for a shunt (CIM 18 gap) |
| `rmidnt` | `Optional[str]` |  | untranscribed | RMIDNT: only MODSW 4 and 6 use it, which raise |
| `binit` | `Optional[float]` | `600.0`, `0.0`, `400.0` | derived | BINIT (Mvar at 1 pu): split into each block's sections in RAW's switching order (block_sections); beyond the blocks' total raises; blank: 0 (defaulted) |
| `n1` | `Optional[int]` | `5`, `6` | structural | Ni / Bi: block i, a LinearShuntCompensator swsh_<I>_b<i> with maximumSections = Ni and bPerSection (pu system) = Bi / SBASE (per_unit_from_mva), up to the first Ni or Bi of 0 (RAW's end of blocks); a block after it raises; never defaulted |
| `b1` | `Optional[float]` | `200.0`, `100.0` | structural | Ni / Bi: block i, a LinearShuntCompensator swsh_<I>_b<i> with maximumSections = Ni and bPerSection (pu system) = Bi / SBASE (per_unit_from_mva), up to the first Ni or Bi of 0 (RAW's end of blocks); a block after it raises; never defaulted |
| `n2` | `Optional[int]` |  | structural | Ni / Bi: block i, a LinearShuntCompensator swsh_<I>_b<i> with maximumSections = Ni and bPerSection (pu system) = Bi / SBASE (per_unit_from_mva), up to the first Ni or Bi of 0 (RAW's end of blocks); a block after it raises; never defaulted |
| `b2` | `Optional[float]` |  | structural | Ni / Bi: block i, a LinearShuntCompensator swsh_<I>_b<i> with maximumSections = Ni and bPerSection (pu system) = Bi / SBASE (per_unit_from_mva), up to the first Ni or Bi of 0 (RAW's end of blocks); a block after it raises; never defaulted |
| `n3` | `Optional[int]` |  | structural | Ni / Bi: block i, a LinearShuntCompensator swsh_<I>_b<i> with maximumSections = Ni and bPerSection (pu system) = Bi / SBASE (per_unit_from_mva), up to the first Ni or Bi of 0 (RAW's end of blocks); a block after it raises; never defaulted |
| `b3` | `Optional[float]` |  | structural | Ni / Bi: block i, a LinearShuntCompensator swsh_<I>_b<i> with maximumSections = Ni and bPerSection (pu system) = Bi / SBASE (per_unit_from_mva), up to the first Ni or Bi of 0 (RAW's end of blocks); a block after it raises; never defaulted |
| `n4` | `Optional[int]` |  | structural | Ni / Bi: block i, a LinearShuntCompensator swsh_<I>_b<i> with maximumSections = Ni and bPerSection (pu system) = Bi / SBASE (per_unit_from_mva), up to the first Ni or Bi of 0 (RAW's end of blocks); a block after it raises; never defaulted |
| `b4` | `Optional[float]` |  | structural | Ni / Bi: block i, a LinearShuntCompensator swsh_<I>_b<i> with maximumSections = Ni and bPerSection (pu system) = Bi / SBASE (per_unit_from_mva), up to the first Ni or Bi of 0 (RAW's end of blocks); a block after it raises; never defaulted |
| `n5` | `Optional[int]` |  | structural | Ni / Bi: block i, a LinearShuntCompensator swsh_<I>_b<i> with maximumSections = Ni and bPerSection (pu system) = Bi / SBASE (per_unit_from_mva), up to the first Ni or Bi of 0 (RAW's end of blocks); a block after it raises; never defaulted |
| `b5` | `Optional[float]` |  | structural | Ni / Bi: block i, a LinearShuntCompensator swsh_<I>_b<i> with maximumSections = Ni and bPerSection (pu system) = Bi / SBASE (per_unit_from_mva), up to the first Ni or Bi of 0 (RAW's end of blocks); a block after it raises; never defaulted |
| `n6` | `Optional[int]` |  | structural | Ni / Bi: block i, a LinearShuntCompensator swsh_<I>_b<i> with maximumSections = Ni and bPerSection (pu system) = Bi / SBASE (per_unit_from_mva), up to the first Ni or Bi of 0 (RAW's end of blocks); a block after it raises; never defaulted |
| `b6` | `Optional[float]` |  | structural | Ni / Bi: block i, a LinearShuntCompensator swsh_<I>_b<i> with maximumSections = Ni and bPerSection (pu system) = Bi / SBASE (per_unit_from_mva), up to the first Ni or Bi of 0 (RAW's end of blocks); a block after it raises; never defaulted |
| `n7` | `Optional[int]` |  | structural | Ni / Bi: block i, a LinearShuntCompensator swsh_<I>_b<i> with maximumSections = Ni and bPerSection (pu system) = Bi / SBASE (per_unit_from_mva), up to the first Ni or Bi of 0 (RAW's end of blocks); a block after it raises; never defaulted |
| `b7` | `Optional[float]` |  | structural | Ni / Bi: block i, a LinearShuntCompensator swsh_<I>_b<i> with maximumSections = Ni and bPerSection (pu system) = Bi / SBASE (per_unit_from_mva), up to the first Ni or Bi of 0 (RAW's end of blocks); a block after it raises; never defaulted |
| `n8` | `Optional[int]` |  | structural | Ni / Bi: block i, a LinearShuntCompensator swsh_<I>_b<i> with maximumSections = Ni and bPerSection (pu system) = Bi / SBASE (per_unit_from_mva), up to the first Ni or Bi of 0 (RAW's end of blocks); a block after it raises; never defaulted |
| `b8` | `Optional[float]` |  | structural | Ni / Bi: block i, a LinearShuntCompensator swsh_<I>_b<i> with maximumSections = Ni and bPerSection (pu system) = Bi / SBASE (per_unit_from_mva), up to the first Ni or Bi of 0 (RAW's end of blocks); a block after it raises; never defaulted |
| `nreg` | `Optional[int]` |  | structural | NREG: a node of bus SWREG; nonzero: the control's Terminal is that node's busbar bb_s<IS>_n<NREG>_T1 (R6, RAW-11); blank: 0 (defaulted) |

## Generator (R3)

**Approved 2026-11-08 and implemented.** RAW-7, RAW-23, RAW-24, RAW-25. Atom: `tests/atoms/generator/`.

Mapper: `importer/cimtbl/generator.py` (`map_generator`). Shape: `synchronous_machine` (bus-branch), new (C2), and
the `der` shape's `PowerElectronicsConnection` with `bus`.
- **What a record is:** one machine, or several aggregated, at bus I. PSS/E treats VS, IREG and RMPCT as **plant**
  quantities: every machine at bus I shares them, and the plant's output and limits are the sums of its in-service
  machines'.
- **Class by WMOD (RAW-24):** WMOD is PSS/E's own line between a conventional machine (0) and a renewable or
  infeed one (1-4), whose reactive limits do not come from a synchronous machine.

  | WMOD | CIM, per record |
  |---|---|
  | 0 conventional | `SynchronousMachine` + `GeneratingUnit` + `ControlAreaGeneratingUnit` |
  | 1 renewable, limits QT/QB | `PowerElectronicsConnection` + `PowerElectronicsUnit` (concrete in cim18v17, no kind) + `ControlAreaPowerElectronicsUnit` |
  | 2, 3 renewable, Q limits or Q from WPF | raise `NotImplementedError`: no case has one yet |
  | 4 infeed, fixed Q | raise `NotImplementedError`: no case has one yet |

  - **CSP vs PV:** a concentrating solar thermal plant drives a synchronous generator from a steam turbine. PSS/E
    models it as a conventional machine, WMOD 0, so it lands on `SynchronousMachine` + `GeneratingUnit`.
    `SolarGeneratingUnit` is not in cim18v17, and RAW has no fuel anyway. WMOD 1 is a converter-interfaced plant
    (PV, type 3/4 wind), and `PowerElectronicsConnection` is its class.
  - WECC240's 37 WMOD 1 machines are its aggregated wind (11) and solar (26) plants. That count comes from the
    working workbook beside the old CIMHub_2_0 copy of the case, which does not say PV or CSP. The case is built
    for a study of high renewable integration.
  - What stays a gap: RAW cannot say PV or wind (so no `PhotoVoltaicUnit` / `PowerElectronicsWindUnit`). Nor can it
    say a type 1/2 wind plant, an induction machine (`AsynchronousMachine`), entered as WMOD 1.
- **Per plant:** one `RegulatingControl` for all the machines and connections at bus I. This matches the physical
  joint voltage control, and the switched shunt's form (one control, several pieces of equipment). A plant and a
  switched shunt regulating the same bus have their own controls: their setpoints differ (a VS and a band). WECC240
  has three such buses (4001, 4005, 7001).
- **Order:** `RegulatingControl`; `GeneratingUnit`, `ControlAreaGeneratingUnit`, `SynchronousMachine`;
  `PowerElectronicsConnection`, `PowerElectronicsUnit`, `ControlAreaPowerElectronicsUnit`. Each reference points
  backwards, so no `Update` is needed.

WECC240 (bus 1032: two machines and a converter plant regulating 1002; 3933: the swing plant):

```
# one per plant (bus I); targetValue in V
Table RegulatingControl: mRID, name, mode, discrete, enabled, targetValue, Terminal
    gc_1032, 1032, voltage, false, true,  349830.0,           bb_1002_T1
    gc_1333, 1333, voltage, false, true,  346724.99999999994, bb_1303_T1
    gc_3933, 3933, voltage, false, true,  20400.0,            bb_3933_T1
    ...
Table GeneratingUnit: mRID, name, maxOperatingP (MW), minOperatingP (MW), EquipmentContainer
    gu_1032_C,  1032_C,  873.0,   0.0,     sub_1032
    ...
Table ControlAreaGeneratingUnit: mRID, name, ControlArea, GeneratingUnit
    cagu_1032_C,  1032_C,  ca_1, gu_1032_C
    ...
# WMOD 0
# untranscribed: zx, o1, o2, o3, o4, f1, f2, f3, f4, wpf
Table SynchronousMachine: mRID, name, bus, p (MW), q (MVAr), maxQ (MVAr), minQ (MVAr), ratedS (MVA), r (ohm), qPercent, referencePriority, inService, controlEnabled, RegulatingControl, GeneratingUnit, BaseVoltage, EquipmentContainer
    # defaulted: wmod=0, nreg=0
    sm_1032_C,  1032_C,  1032, -712.0,    3.332,    200.0,  -200.0,  873.0,   0.0, 100.0, ,  true,  true,  gc_1032, gu_1032_C,  bv_20kv, sub_1032
    ...
    sm_3933_CG, 3933_CG, 3933, -404.88,   -88.652,  363.0,  -82.0,   865.0,   0.0, 100.0, 1, true,  true,  gc_3933, gu_3933_CG, bv_20kv, sub_3903
    ...
# WMOD 1; untranscribed here also: zr, rmpct (no qPercent)
# untranscribed: zx, o1, o2, o3, o4, f1, f2, f3, f4, wpf
Table PowerElectronicsConnection: mRID, name, bus, p (MW), q (MVAr), maxQ (MVAr), minQ (MVAr), ratedS (MVA), inService, controlEnabled, RegulatingControl, BaseVoltage, EquipmentContainer
    pec_1032_S,  1032_S,  1032, -520.0,   3.332,    360.0,  -360.0,  638.0,  true, true, gc_1032, bv_20kv, sub_1032
    ...
Table PowerElectronicsUnit: mRID, name, maxP (MW), minP (MW), PowerElectronicsConnection, EquipmentContainer
    pecu_1032_S,  1032_S,  638.0,  0.0, pec_1032_S,  sub_1032
    ...
Table ControlAreaPowerElectronicsUnit: mRID, name, ControlArea, PowerElectronicsUnit
    capu_1032_S,  1032_S,  ca_1, pecu_1032_S
    ...
```

- **mRIDs** (prefixes requested, C3), all keyed `<I>_<ID>` with name `I_ID`:
  - `sm_`, `gu_`, `cagu_` for WMOD 0, and `pec_`, `pecu_`, `capu_` for WMOD 1. The `der` shape's `pv_` and
    `<pec>_unit` assume the kind (PV) is known, and here it is not;
  - the plant control is `gc_<I>`. It cannot be `cc_<I>`, the switched shunt's, since one bus can have both.
- **Sign (RAW-14):** `p` = −PG and `q` = −QG on both classes, which use the load sign convention ("positive sign
  means flow out from a node"), so generation is negative.
  - The limits keep the generator convention, as CIM writes them, all copied: `maxQ` = QT, `minQ` = QB, and PT/PB
    → `maxOperatingP`/`minOperatingP` (unit) or `maxP`/`minP` (power-electronics unit).
  - WECC240 has 5 machines with PB < 0 (pumping), copied as is.
- **Rating:** `ratedS` = MBASE (blank: SBASE, the schema rule, defaulted). `ratedU` is blank: RAW has no machine
  voltage.
- **Plant control:**
  - `mode = voltage`, `discrete = false`, `targetValue` = VS × the regulated bus's BASKV in V
    (`volts_from_per_unit`), `targetDeadband` blank (PSS/E holds VS exactly). The product can leave a
    last-digit float residue (1.005 × 345 kV is `346724.99999999994`): written as computed, never rounded, so the
    exporter's VS can differ in the last digit (expected difference). `r (ohm)` likewise;
  - `Terminal` = `bb_<IREG>_T1`, or `bb_<I>_T1` when IREG is 0 or I (RAW-11). WECC240: 137 of 146 machines
    regulate a remote bus, and 7 regulate their own (the swing plant at 3933);
  - `enabled` = bus I's IDE is 2 or 3, and every member's `controlEnabled` follows it. An IDE 1 bus has no voltage
    control (WECC240's machine at 3432 is on one, out of service). The exporter writes IDE 2 for a bus with an
    enabled plant control and 1 otherwise, so IDE 1/2 round-trip;
  - the plant's records must agree on VS, IREG and RMPCT, as PSS/E requires. A disagreement raises with both IDs;
  - a remote IREG from a swing bus raises (PSS/E would silently regulate bus I instead), and so does an IREG that
    is no bus. NREG ≠ 0 names node NREG of the regulated bus: `bb_s<IS>_n<NREG>_T1`, that node's busbar (R6).
    NREG is a plant quantity, so the plant's records must agree on it too.
- **RMPCT:** `qPercent` on every `SynchronousMachine` of the plant (added to the profile 2026-11-08). A
  `PowerElectronicsConnection` has none, so its row lists RMPCT untranscribed, and the exporter takes the plant's
  RMPCT from one of its machines, else 100. Gap: the shunt RMPCT gap now covers power-electronics connections too.
  RMPCT is 100 everywhere in both cases.
- **Swing bus:** IDE 3 → `referencePriority = 1` on every `SynchronousMachine` at the bus (added to the profile
  2026-11-08; "1 = highest priority" for the angle-reference choice); blank elsewhere. The exporter writes IDE 3 for
  a bus with such a machine. A swing bus with no in-model `SynchronousMachine` (only WMOD 1 records) raises; no case
  has one. The 3933 swing plant has 5 machines and 2 connections.
- **Status:** `inService` = STAT == 1 on the machine or connection. The units carry no status of their own.
- **Area:** each unit's control-area membership → `ca_<AREA of bus I>`. A generator record has no AREA. A bus AREA
  with no area-interchange record raises, as for loads.
- **ZSORCE (RAW-23):** ZR/ZX are the source impedance for switching, fault and dynamic studies (pu on MBASE).
  - ZR → `r (ohm)` = ZR × BASKV² / MBASE on a `SynchronousMachine` (`ohms_from_per_unit`, through the units
    library);
  - ZX: **TODO, a new profile extension.** cim18v17's `SynchronousMachine` has no positive-sequence reactance (the
    canonical saturated `satDirect*X` were never in it). It stays untranscribed until the extension lands. The
    exporter writes the default 1.0 meanwhile, an expected difference for WECC240 (0.2);
  - on a `PowerElectronicsConnection`, both are untranscribed: a converter has no ZSORCE in CIM.
- **Step-up transformer (RAW-25, superseded by R3b below):** RT + jXT ≠ 0 (an implicit GSU) raised
  `NotImplementedError` until a case had one; both public cases model their GSUs as transformer branches (RT = XT =
  0). R3b maps it with the core shape `behind_transformer.cimtbl` (plan C8).
- **Untranscribed:** WPF (used only by WMOD 2/3), ZX (TODO extension), O1..F4 (ownership, CIM 18 gap).
- **Atom** `tests/atoms/generator/generators.raw`:
  - a plant of one WMOD 0 machine and one WMOD 1 connection regulating a remote bus, with one member out of service;
  - a swing plant;
  - a machine on an IDE 1 bus (control disabled);
  - a record with every optional field blank (all defaulted, MBASE = SBASE).
  
  Raise tests: plant records that disagree on VS, IREG, NREG or RMPCT; RT/XT ≠ 0 (until R3b); WMOD 2, 3 and 4; a remote IREG
  from a swing bus; an IREG that is no bus; a swing bus with only WMOD 1 records.
- **Checks:** all 151 records bind (IEEE14 5 machines; WECC240 109 machines and 37 connections). In SI, each p =
  −PG in W, each target = VS × BASKV in V, and each unit reaches its bus's `ControlArea`. Each plant has one
  control.

| GeneratorRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `bus_number` | `int` | `1032`, `1034`, `1131` | structural | I: the machine's bus, BaseVoltage, EquipmentContainer (its substation) and ControlArea (the bus's AREA, through ControlAreaGeneratingUnit or ControlAreaPowerElectronicsUnit); the plant key gc_<I>; IDE 2 or 3 enables the plant control, IDE 3 sets referencePriority = 1 on its SynchronousMachines |
| `gen_id` | `Optional[str]` | `C`, `G`, `S` | structural | ID: with I the key, mRIDs sm_/gu_/cagu_ or pec_/pecu_/capu_<I>_<ID>, name I_ID; blank: 1 (defaulted) |
| `p_output` | `Optional[float]` | `712.0`, `856.0`, `520.0` | derived | PG (MW): p = -PG, load sign convention (generation_p_q, RAW-14); blank: 0 (defaulted) |
| `q_output` | `Optional[float]` | `-3.332`, `262.628`, `-46.791` | derived | QG (Mvar): q = -QG, load sign convention (generation_p_q, RAW-14); blank: 0 (defaulted) |
| `max_q_output` | `Optional[float]` | `200.0`, `357.0`, `360.0` | copied | `SynchronousMachine.maxQ` (MVAr), `PowerElectronicsConnection.maxQ` (MVAr); QT, generator convention as CIM's limit; blank: 9999 (defaulted) |
| `min_q_output` | `Optional[float]` | `-200.0`, `-357.0`, `-360.0` | copied | `SynchronousMachine.minQ` (MVAr), `PowerElectronicsConnection.minQ` (MVAr); QB; blank: -9999 (defaulted) |
| `regulated_voltage_setpoint` | `Optional[float]` | `1.014`, `1.03`, `1.01` | derived | VS (pu): targetValue = VS x the regulated bus's BASKV, in V (volts_from_per_unit); a plant quantity, shared by every machine at bus I (they must agree, else raise); blank: 1.0 (defaulted) |
| `regulated_bus_number` | `Optional[int]` | `1002`, `1004`, `1101` | structural | IREG: the plant control's Terminal bb_<IREG>_T1, or bb_<I>_T1 when 0 (RAW-11), or the NREG node's busbar; a remote IREG from a swing bus raises; a plant quantity, shared by every machine at bus I (they must agree, else raise); blank: 0 (defaulted) |
| `rated_mva` | `Optional[float]` | `873.0`, `1050.0`, `638.0` | copied | `SynchronousMachine.ratedS` (MVA), `PowerElectronicsConnection.ratedS` (MVA); MBASE; blank: SBASE (defaulted) |
| `zr` | `Optional[float]` | `0.0` | derived | ZR (pu on MBASE): SynchronousMachine r (ohm) = ZR x BASKV^2 / MBASE (ohms_from_per_unit); untranscribed on a PowerElectronicsConnection; blank: 0 (defaulted) |
| `zx` | `Optional[float]` | `0.2` | untranscribed | ZX: cim18v17 has no positive-sequence machine reactance (TODO: a profile extension, RAW-23) |
| `rt` | `Optional[float]` | `0.0` | derived | RT (pu on MBASE): RT + jXT != 0 is an implicit step-up transformer <machine>_xf, the machine on its internal node <machine>_int (R3b-1); end 1 r (ohm) = RT x BASKV^2 / MBASE (ohms_from_per_unit); blank: 0 (defaulted) |
| `xt` | `Optional[float]` | `0.0` | derived | XT (pu on MBASE): as RT, end 1 x (ohm) |
| `gtap` | `Optional[float]` | `1.0` | derived | GTAP: with a step-up, a fixed RatioTapChanger <machine>_xf_tap1 on end 1, neutralU = GTAP x BASKV (R3b-1, R4b-4), none at 1; without one, PSS/E ignores it and it is listed on the machine row when not 1 (R3b-4); blank: 1.0 (defaulted) |
| `status` | `Optional[int]` | `1`, `0` | mapped | STAT: inService = (STAT == 1); blank: 1 (defaulted) |
| `rmpct` | `Optional[float]` | `100.0` | copied | `SynchronousMachine.qPercent`; RMPCT, on every SynchronousMachine of the plant; a PowerElectronicsConnection has no qPercent (CIM 18 gap); a plant quantity, shared by every machine at bus I (they must agree, else raise); blank: 100 (defaulted) |
| `max_p_output` | `Optional[float]` | `873.0`, `1050.0`, `638.0` | copied | `GeneratingUnit.maxOperatingP` (MW), `PowerElectronicsUnit.maxP` (MW); PT, by WMOD; blank: 9999 (defaulted) |
| `min_p_output` | `Optional[float]` | `0.0`, `-1006.0`, `-2841.0` | copied | `GeneratingUnit.minOperatingP` (MW), `PowerElectronicsUnit.minP` (MW); PB, by WMOD; blank: -9999 (defaulted) |
| `o1` | `Optional[int]` | `1` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `f1` | `Optional[float]` | `1.0` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `o2` | `Optional[int]` | `0` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `f2` | `Optional[float]` | `1.0` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `o3` | `Optional[int]` | `0` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `f3` | `Optional[float]` | `1.0` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `o4` | `Optional[int]` | `0` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `f4` | `Optional[float]` | `1.0` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `wmod` | `Optional[int]` | `1` | mapped | WMOD: the class (RAW-24), 0 conventional a SynchronousMachine + GeneratingUnit, 1 renewable with QT/QB limits a PowerElectronicsConnection + PowerElectronicsUnit; 2, 3 and 4 raise until a case has one; blank: 0 (defaulted) |
| `wpf` | `Optional[float]` | `1.0` | untranscribed | WPF: used only by WMOD 2 and 3, which raise |
| `nreg` | `Optional[int]` |  | structural | NREG: a node of bus IREG; nonzero: the plant control's Terminal is that node's busbar bb_s<IS>_n<NREG>_T1 (R6, RAW-11); a plant quantity, shared by every machine at bus I (they must agree, else raise); blank: 0 (defaulted) |

## Generator: the implicit step-up transformer (R3b)

**Approved 2026-11-09 (user: "bus I's base", "on the machine as written", "approve, implement") and implemented.** Extends R3 (RAW-25). Mapper: `generator.py`; the core shape `behind_transformer.cimtbl`
(plan C8), already followed by the converter transformer (P2-5). The local case set (29 cases of one network, never
committed, counted only) has 213 generators with RT + jXT ≠ 0 in every case: 212 WMOD 0 and 1 WMOD 1, 80 in
service, 8 with GTAP ≠ 1, 1 with XT = 0 (RT alone), 13 regulating a remote bus, up to 4 machines a bus. None sits in
a node-breaker substation. WMOD 2/3 (50 a case) is the other half of R3b and is not in this spec.

### The form (decision R3b-1)

The format document's figure of the implicit method puts the ideal ratio GTAP : 1 at the high-voltage bus I and
XTRAN (pu on MBASE) between it and the machine. That is an R4 2-winding transformer with CW 1, CZ 2, SBASE1-2 =
MBASE, WINDV1 = GTAP, WINDV2 = 1 and COD 0, so the step-up maps the way R4 would map that record:

- **Internal node:** `TopologicalNode` `<machine>_int` (`sm_` or `pec_<I>_<ID>_int`), named `<I>_<ID> terminal`,
  with no busNumber, in bus I's substation. The machine (`SynchronousMachine` or `PowerElectronicsConnection`) sits
  on it.
- **Transformer:** `PowerTransformer` `<machine>_xf`, named `<I>_<ID> step-up`, in bus I's substation, always in
  service (it has no status of its own in RAW, as P2-5).
  - End 1 `<machine>_xf_1` on bus I: ratedU = BASKV(I), ratedS = MBASE, r, x = RT, XT × BASKV(I)² / MBASE (ohm;
    `ohms_from_per_unit`, R4's CZ 2).
  - End 2 `<machine>_xf_2` on the internal node: ratedU = BASKV(I), ratedS = MBASE. No magnetizing branch.
- **GTAP ≠ 1:** a fixed `RatioTapChanger` `<machine>_xf_tap1` on end 1 (R4b-4: one step, neutralU = GTAP × BASKV(I)
  in kV, no control). GTAP = 1 has none (205 of 213).

### The internal node's voltage (decision R3b-2)

RAW does not give the machine's terminal voltage: XTRAN and GTAP are in per unit, on MBASE and the system base. So
the internal node, end 2 and the machine keep bus I's BaseVoltage, a per-unit equivalent. No BaseVoltage is added,
and ZR keeps its R3 conversion on BASKV(I). The machine's terminal kV is missing from RAW, not from CIM.
The exporter gets the record back: RT, XT = r, x × ratedS / ratedU1², GTAP = neutralU / ratedU1 (1 without a tap).

### Power, limits and control stay on the machine (decision R3b-3)

PG, QG, QT, QB, PT, PB and MBASE map as R3, on the machine and its unit. The plant control `gc_<I>` stays on bus
I's busbar (`bb_<I>_T1`, or IREG's): the format document makes bus I the regulated bus of the implicit method.
PSS/E's power flow injects PG + jQG at bus I and uses XTRAN only in fault analysis and dynamics. A CIM solve that
includes the step-up sees its losses (I²X of Mvar), an expected solve difference; the round trip is exact.

### GTAP without a step-up (decision R3b-4)

GTAP is used only when RT + jXT ≠ 0. 11 generators a case have GTAP ≠ 1 without one; PSS/E ignores it. It is listed
on the machine row (`untranscribed: gtap=…`) so the exporter can write it back.

### Node-breaker terminals (decision R3b-5)

An equipment terminal record (R6) naming a machine with a step-up places the transformer's end-1 terminal
`<machine>_xf_T1` on its node: the machine's own terminal is on the internal node. None in the set; the atom tests
it.

### Atom `tests/atoms/generator/step_up.raw` (hand-built)

The `generators.raw` frame (230 kV and 13.8 kV buses) with: a machine behind a step-up at GTAP 1; one at GTAP
1.025; an RT-only step-up; a WMOD 1 connection behind a step-up; a plant of two machines, one with a step-up and one
without, regulating a remote bus; a machine without a step-up with GTAP 1.02 (listed). Raise tests: none new (a
step-up no longer raises); the node-breaker placement is tested on a GSU added to `node_breaker_forms.raw` in memory.

### CIM 18 gaps

None new: the step-up is ordinary CIM. The machine's terminal kV is absent from RAW itself.

### Results

All 29 local cases map their 213 step-ups (8 with a fixed tap). One case binds whole in 66 s with only WMOD 2/3
and the R1b/R2b records set aside: its 7653 `PowerTransformer`s are 7402 transformer records, 38 converter
transformers and 213 step-ups, and its 18172 `TopologicalNode`s are 17921 buses and 251 internal nodes.

## Transformer (R4)

**Approved 2026-11-08 and implemented.** RAW-5, RAW-6. Atom: `tests/atoms/transformer/`. **R4b (below) maps the
forms this section lists as raising**, except COD ±4 and ±5, CNXA, and a 3-winding unit's TAB.
User choices 2026-11-08: impedances and admittances in ohm and S; COD 0, ±1, ±2 now; a control with CONT 0 names
the tapped winding's own terminal.

Mapper: `importer/cimtbl/transformer.py` (`map_transformer`). Shape: `transformer_by_ends` with `bus` on each end,
plus the `regulator` shape's `RatioTapChanger` + `TapChangerControl`. The core shape still puts a 2-winding x on a
`TransformerMeshImpedance`. cim18v17 no longer does that (below), so the shape needs an update (request C2).
- **What a record is:** one transformer with two windings (K = 0), or three (K ≠ 0), in one substation (§3.2).
- **cim18v17's transformer model** (user, 2026-11-08). `TransformerStarImpedance` and `TransformerStarAdmittance`
  are deleted. `TransformerCore` and `TransformerWinding` are for tanks, not for a balanced bus-branch unit:
  - **2-winding:** end 1 carries r, x, g and b, in ohm and S on its ratedU. End 2 is zero (`PowerTransformerEnd`'s
    own rule), so it carries only its ratings.
  - **3-winding:** PSS/E gives Z12, Z23 and Z31, which is already a mesh (Delta model). So three
    `TransformerMeshImpedance` rows, From 1 To 2, From 2 To 3 and From 1 To 3, each r and x in ohm seen from its
    From end. There is no star conversion and no star node. g and b go on end 1, and the ends' r and x stay blank.
- **Order:** `PowerTransformer`, `PowerTransformerEnd`, `TransformerMeshImpedance`, `TapChangerControl`,
  `RatioTapChanger`, then the rating sets. A control may name a transformer terminal, which exists only after its
  end, so the controls come after the ends. Every reference points backwards, so no `Update` is needed.

WECC240 (1001-1002: a fixed tap at ratio 1; 6103-6104: one of its two voltage controls):

```
# untranscribed: o1, o2, o3, o4, f1, f2, f3, f4, zcod, vmstar, anstar
# untranscribed off a tie: NMETR (a tie's TieFlows record it; CIM 18 gap, RAW-22)
Table PowerTransformer: mRID, name, vectorGroup, inService, EquipmentContainer
    xf_1001_1002_0_1, 1001_1002_0_1, , true, sub_1001
    xf_6103_6104_0_1, 6103_6104_0_1, , true, sub_6103
    ...
# r, x, g, b on the end's ratedU (transformer_ohms, magnetizing_siemens): a 2-winding unit's all on end 1, end 2 zero; a 3-winding unit's g, b on end 1, r, x on its mesh
Table PowerTransformerEnd: mRID, name, bus, endNumber, ratedU (kV), ratedS (MVA), r (ohm), x (ohm), g (S), b (S), BaseVoltage, PowerTransformer
    xf_1001_1002_0_1_1, 1001_1002_0_1_1, 1001, 1, 500.0, 100.0, 0.00025,  27.5,      0.0, 0.0, bv_500kv, xf_1001_1002_0_1
    xf_1001_1002_0_1_2, 1001_1002_0_1_2, 1002, 2, 345.0, 100.0, 0.0,      0.0,       0.0, 0.0, bv_345kv, xf_1001_1002_0_1
    xf_6103_6104_0_1_1, 6103_6104_0_1_1, 6103, 1, 345.0, 100.0, 0.357075, 21.543525, 0.0, 0.0, bv_345kv, xf_6103_6104_0_1
    xf_6103_6104_0_1_2, 6103_6104_0_1_2, 6104, 2, 230.0, 100.0, 0.0,      0.0,       0.0, 0.0, bv_230kv, xf_6103_6104_0_1
    ...
# targetValue and targetDeadband in V (voltage) or VAr (reactivePower); COD 0 keeps its control, disabled
Table TapChangerControl: mRID, name, mode, discrete, enabled, targetValue, targetDeadband, Terminal
    xf_1001_1002_0_1_ctrl1, 1001_1002_0_1_1, voltage, true, false, 500000.0,           100000.00000000003, bb_1001_T1
    xf_6103_6104_0_1_ctrl1, 6103_6104_0_1_1, voltage, true, true,  235749.99999999997, 34500.00000000003,  bb_6104_T1
    ...
# steps 1..NTP from RMI to RMA; neutralStep nearest ratio 1 at neutralU; stepVoltageIncrement in percent of ratedU (ratio_tap)
Table RatioTapChanger: mRID, name, lowStep, highStep, neutralStep, neutralU (kV), stepVoltageIncrement, step, ltcFlag, controlEnabled, TapChangerControl, TransformerEnd
    xf_1001_1002_0_1_tap1, 1001_1002_0_1_1, 1, 989, 495, 500.0,             0.020242914979757092, 495.0,              false, false, xf_1001_1002_0_1_ctrl1, xf_1001_1002_0_1_1
    xf_6103_6104_0_1_tap1, 6103_6104_0_1_1, 1, 30,  15,  343.8103448275862, 0.6896551724137934,   16.000249999999976, true,  true,  xf_6103_6104_0_1_ctrl1, xf_6103_6104_0_1_1
    ...
# ratings: one set per rated winding, on its terminal xf_<key>_T<k>; a zero RATEn is no limit (RAW-9, RAW-20)
Table OperationalLimitSet: mRID, Terminal
    xf_1002_1003_0_1_1_ratings, xf_1002_1003_0_1_T1
    ...
Table ApparentPowerLimit: mRID, OperationalLimitSet, OperationalLimitType, normalValue (MVA)
    xf_1002_1003_0_1_1_rate3, xf_1002_1003_0_1_1_ratings, olt_rate3, 430.0
    ...
```

The atom's 3-winding unit D (`tests/atoms/transformer/`) gives the Delta model:

```
# 3-winding Z12, Z23, Z31 (Delta model): r, x seen from the From end
Table TransformerMeshImpedance: mRID, name, FromTransformerEnd, ToTransformerEnd, r (ohm), x (ohm)
    xf_1_2_3_1_mesh_12, 1_2_3_1_12, xf_1_2_3_1_1, xf_1_2_3_1_2, 1.19025,  59.5125
    xf_1_2_3_1_mesh_23, 1_2_3_1_23, xf_1_2_3_1_2, xf_1_2_3_1_3, 1.058,    21.16
    xf_1_2_3_1_mesh_13, 1_2_3_1_13, xf_1_2_3_1_1, xf_1_2_3_1_3, 1.785375, 83.3175
```

IEEE14 4-7 has CONT 0, so its disabled control names the transformer's own terminal `xf_4_7_0_1_T1`. Its target
uses bus 4's BASKV: 138690.0 V, deadband 136620.0 V. Its tap: steps 1-159, neutral 79 at 137.825 kV, step 75.69.

- **mRIDs** (prefixes requested, C3). The key is `<I>_<J>_<K>_<CKT>`:
  - the transformer is `xf_<key>`;
  - its ends are `xf_<key>_<k>`;
  - its mesh rows are `xf_<key>_mesh_<ij>` (12, 23, 13);
  - winding k's tap changer is `xf_<key>_tap<k>` and its control `xf_<key>_ctrl<k>`;
  - cimtables generates the terminals `xf_<key>_T<k>` (sequenceNumber = endNumber).
  - NAME is the transformer's name; a blank NAME gives the key, as for a branch. An end, tap changer or control is
    named `<key>_<k>`.
- **Ends:**
  - `bus` is winding k's bus (I, J, K), and `BaseVoltage` is its BASKV's.
  - `ratedU` = NOMVk, or the bus's BASKV when NOMVk is 0 (RAW-6). Every public transformer has NOMV = BASKV,
    except IEEE14's NOMV 0. The exporter writes NOMV = ratedU back, so IEEE14's NOMV 0 comes back as 138.0
    (expected difference, the same value to PSS/E).
  - `ratedS`: on a 2-winding unit, SBASE1-2 on both ends. A 3-winding unit's SBASE1-2, 2-3 and 3-1 are bases of
    winding pairs, so no end can hold them. They enter the CZ 2/3 derivations below and are not kept otherwise.
    The exporter writes SBASE (expected difference).
  - `PowerTransformer.vectorGroup` = VECGRP when not blank (blank in both cases). `connectionKind` stays blank: a
    positive-sequence case has no winding connections.
- **Impedance (RAW-5, ohm):** one derivation, `transformer_ohms`, for each pair ij, seen from winding i:

  | CZ | RAW gives | r, x (ohm) |
  |---|---|---|
  | 1 | R, X in pu on SBASE and bus BASKVi | R, X × BASKVi² / SBASE |
  | 2 | R, X in pu on SBASEij and NOMVi | R, X × NOMVi² / SBASEij |
  | 3 | R = load loss in W, X = \|Z\| in pu on SBASEij and NOMVi | r = loss / SBASEij in pu; x = √(\|Z\|² − r²); both × NOMVi² / SBASEij |

  - PSS/E's own conversion between the codes keeps these ohms the same. So the result is one physical impedance,
    referred to winding i at its ratedU.
  - CZ 3 with \|Z\| < r raises.
  - The exporter writes CZ 1 back, so the CZ 2/3 atoms come back as CZ 1 (expected difference, the same impedance).
- **Magnetizing (RAW-5, S, end 1):** `magnetizing_siemens`, at winding 1's bus:

  | CM | RAW gives | g, b (S) |
  |---|---|---|
  | 1 | MAG1, MAG2: G, B in pu on SBASE and BASKV1 | G, B × SBASE / BASKV1² |
  | 2 | MAG1 = no-load loss in W, MAG2 = exciting current in pu on SBASE1-2 and NOMV1 | g = loss / SBASE1-2 in pu; b = −√(I² − g²); both × SBASE1-2 / NOMV1² |

  - The sign is kept: a magnetizing B is negative (inductive), and CIM's b allows either sign.
  - CM 2 with I < g raises.
  - The exporter writes CM 1 back (expected difference).
- **Turns ratio and taps (RAW-6).** A winding that has COD data gets a `RatioTapChanger` on its end: winding 1 of
  a 2-winding unit, and every winding of a 3-winding one. That covers every public transformer: WECC240 carries
  NTP, RMA and RMI even with COD 0, and IEEE14's WINDV1 is off-nominal.
  - **Winding units:** CW gives WINDV, RMA and RMI in pu of the bus's BASKV (1), in kV (2), or in pu of NOMV (3).
    `winding_kv` turns each into kV, and dividing by ratedU gives pu of the end's rating. CIM holds no CW, so the
    exporter writes CW 1 (expected difference).
  - **Steps:** lowStep = 1 and highStep = NTP, from RMI to RMA in equal steps, so `stepVoltageIncrement` =
    (RMA − RMI)/(NTP − 1), in percent of ratedU. NTP < 2 raises.
  - **Neutral:** neutralStep is the step nearest ratio 1 (a tie takes the upper), and `neutralU` = ratedU × the
    ratio at that step.
    - CIM's neutralStep is an integer, and PSS/E's ratio 1 often falls between steps: WECC240 6103-6104's RMI
      0.9, RMA 1.1 and NTP 30 put it at step 15.5.
    - A neutralU ≠ ratedU keeps it exact, and the profile allows that. A consumer that assumes neutralU =
      ratedU is off by at most half a step.
  - **Position:** `step` = neutralStep + (WINDV − the neutral ratio) / the step size. It is a float: CIM allows a
    non-integer step, and PSS/E's WINDV need not sit on a step (IEEE14's do not).
    - A WINDV outside RMI..RMA raises (CIM: lowStep ≤ step ≤ highStep).
    - The exporter's WINDV = neutralU/ratedU + (step − neutralStep) × increment, and its RMI/RMA come from
      lowStep/highStep. Each can differ in the last digit (expected difference).
  - **Winding 2 of a 2-winding unit** has only WINDV2. A ratio other than 1 (in winding units) raises until a case
    has one. The public cases all have 1.
- **Control (COD).** A tapped winding always gets its control, so VMA, VMI and CONT survive even when the tap is
  fixed (R2's locked-shunt pattern):

  | COD | RatioTapChanger | TapChangerControl |
  |---|---|---|
  | 0 fixed | `ltcFlag = false`, `controlEnabled = false` | `mode = voltage`, `enabled = false`; the target as read (unused by PSS/E) |
  | 1 / −1 voltage | `ltcFlag = true`, `controlEnabled = (COD > 0)` | `mode = voltage`, `enabled = (COD > 0)` |
  | 2 / −2 reactive power | as ±1 | `mode = reactivePower`, `enabled = (COD > 0)` |
  | ±3 phase shift, ±5 asymmetric phase shift | raise `NotImplementedError`: no case has one yet (a `PhaseTapChanger`) | |
  | ±4 DC line control | raise `NotImplementedError`: phase 2 (two-terminal DC) | |

  - **The exporter's COD:** 0 when `ltcFlag` is false; otherwise ±1 or ±2 by mode, signed by `enabled`. That makes
    it a round trip.
  - **Regulated point:** `Terminal` = `bb_<CONT>_T1` (RAW-11). CONT 0 names the tapped winding's own terminal
    `xf_<key>_T<k>` (user 2026-11-08). The exporter writes CONT 0 back for an own terminal.
    - COD ±1 with CONT 0 raises: PSS/E needs a controlled bus.
    - COD ±2 measures the flow through the winding, so CONT 0 is its usual form.
    - A negative CONT raises.
    - NODk ≠ 0 names node NODk of bus CONTk: `bb_s<IS>_n<NODk>_T1`, that node's busbar (R6). NODk with CONT 0
      raises.
  - **Target:** `discrete = true` (taps step).
    - Voltage: `targetValue` = (VMA + VMI)/2 × the regulated bus's BASKV and `targetDeadband` = (VMA − VMI) ×
      BASKV, in V (`volts_from_per_unit`, as the switched shunt).
    - Reactive power: the same, in VAr from Mvar, through the units library.
    - CONT 0 uses the winding's own bus's BASKV.
  - **Raise until a case has one:** CRk/CXk ≠ 0 (load-drop compensation, which `TapChangerControl.lineDropR/X`
    could take) and CNXAk ≠ 0 (only COD ±5 uses it).
  - TABk ≠ 0 (an impedance correction table) raises until phase 2.
- **Status:** STAT 1 → `inService = true` and 0 → false. STAT 2, 3 and 4 (one winding of a 3-winding unit out)
  raise until a case has one.
- **Ratings:** each winding's nonzero RATEk-n go on terminal `xf_<key>_T<k>`, in the set `xf_<key>_<k>_ratings`
  (RAW-20, through `RatingRows`). They are `ApparentPowerLimit`s in MVA, or `CurrentLimit`s in kA when XFRRAT > 0
  (RAW-9; blank → MVA). WECC240 has 42 units with RATE1-3.
- **Untranscribed:**
  - NMETR off a tie: the non-metered end, a CIM 18 gap as branch MET (RAW-22); on a tie its TieFlows record it (R5);
  - O1..F4: ownership (CIM 18 gap);
  - ZCOD: the zero-sequence data is in the sequence file, not the RAW;
  - VMSTAR/ANSTAR: the solved voltage of the star point, which the Delta model omits;
  - CW, CZ, CM: unit codes, applied above; the exporter writes 1.
- **Defaults:** RAW's rules apply per record. SBASEij defaults to SBASE. WINDV defaults to 1.0, or to the bus's
  BASKV under CW 2. RMA/RMI default to 1.1/0.9 under CW 1 or 3 when \|COD\| is not 3 or 5. VMA/VMI default to
  1.1/0.9 when \|COD\| is 1, and the mapper applies the same to COD 0, whose band PSS/E ignores. A blank with no
  default raises. A 2-winding unit's 3-winding slots (the schema's `serialize_if: k != 0`) are never defaulted.
- **Atom:** `tests/atoms/transformer/transformers.raw` holds five units:
  - A: CW 2 + CZ 2 + CM 2, with NOMV1 340 on a 345 kV bus, COD 1 on a remote bus, and two ratings;
  - B: CW 3 + CZ 3, with COD −1;
  - C: COD 2 with CONT 0;
  - D: 3-winding with CZ 1 + CM 1, COD 1 on winding 2, and ratings on windings 1 and 3;
  - E: 3-winding with CZ 2 on pair bases, every winding's tap data defaulted.

  It survives a RAW read → write → read with nothing lost, and binds. Every value is checked in SI against PSS/E's
  conversion. Nineteen raise cases are tested; R0's substation merge already rejects a winding bus that is no bus.

| TransformerRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `i` | `int` | `4`, `5`, `1001` | structural | I: winding 1's bus (end 1's bus and BaseVoltage); the transformer's EquipmentContainer is its substation |
| `j` | `int` | `7`, `9`, `6` | structural | J: winding 2's bus |
| `x1_2` | `float` | `0.20912`, `0.55618`, `0.25202` | derived | X1-2: as R1-2, x (ohm) |
| `k` | `Optional[int]` | `0` | structural | K: winding 3's bus; 0 is a 2-winding unit; blank: 0 (defaulted) |
| `circuit` | `Optional[str]` | `1`, `2`, `3` | structural | CKT: with I, J and K the key, mRID xf_<I>_<J>_<K>_<CKT>; blank: 1 (defaulted) |
| `cw` | `Optional[int]` | `1` | mapped | CW: the unit of WINDV, RMA and RMI (winding_unit_kv); CIM keeps kV, so the exporter writes CW 1; blank: 1 (defaulted) |
| `cz` | `Optional[int]` | `1` | mapped | CZ: the code of R/X (transformer_ohms); CIM keeps ohm, so the exporter writes CZ 1; blank: 1 (defaulted) |
| `cm` | `Optional[int]` | `1` | mapped | CM: the code of MAG1/MAG2 (magnetizing_siemens); the exporter writes CM 1; blank: 1 (defaulted) |
| `mag1` | `Optional[float]` | `0.0` | derived | MAG1: end 1's g (S) (magnetizing_siemens, by CM); blank: 0 (defaulted) |
| `mag2` | `Optional[float]` | `0.0` | derived | MAG2: end 1's b (S), negative inductive; blank: 0 (defaulted) |
| `nmetr` | `Optional[int]` | `2` | structural | NMETR: the non-metered (home) winding; on a tie (windings' buses in two or more AREAs) each other winding outside the home area carries both TieFlows on its terminal (R5); a code outside 1..windings on a tie raises; elsewhere untranscribed, as branch MET (CIM 18 gap, RAW-22); blank: 2 (defaulted) |
| `name` | `Optional[str]` |  | copied | `PowerTransformer.name`; NAME; blank: the key I_J_K_CKT |
| `status` | `Optional[int]` | `1` | mapped | STAT: inService = (STAT != 0); 2, 3 and 4 (a 3-winding unit's winding 2, 3 or 1 out): that winding's terminal connected = false, an Update row (R4b-6); blank: 1 (defaulted) |
| `o1` | `Optional[int]` | `1` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `f1` | `Optional[float]` | `1.0` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `o2` | `Optional[int]` | `0` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `f2` | `Optional[float]` | `1.0` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `o3` | `Optional[int]` | `0` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `f3` | `Optional[float]` | `1.0` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `o4` | `Optional[int]` | `0` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `f4` | `Optional[float]` | `1.0` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `vecgrp` | `Optional[str]` |  | copied | `PowerTransformer.vectorGroup`; VECGRP; blank: none |
| `zcod` | `Optional[int]` |  | untranscribed | ZCOD: zero-sequence data is in the sequence file, not the RAW |
| `r1_2` | `Optional[float]` | `0.0`, `1e-07`, `0.00028` | derived | R1-2: with X1-2, r (ohm) seen from winding 1 (transformer_ohms, by CZ); 2-winding: on end 1, 3-winding: on the mesh row; blank: 0 (defaulted) |
| `sbase1_2` | `Optional[float]` | `100.0` | derived | SBASE1-2 (MVA): the pair's base for CZ 2 and 3 (and CM 2 on 1-2); a 2-winding unit's SBASE1-2 is also both ends' ratedS; a 3-winding unit's pair bases have no end to go on; blank: SBASE (defaulted) |
| `r2_3` | `Optional[float]` |  | derived | R2-3: with X2-3, r (ohm) seen from winding 2 (transformer_ohms, by CZ); 2-winding: on end 1, 3-winding: on the mesh row; blank: 0 (defaulted) |
| `x2_3` | `Optional[float]` |  | derived | X2-3: as R2-3, x (ohm) |
| `sbase2_3` | `Optional[float]` |  | derived | SBASE2-3 (MVA): the pair's base for CZ 2 and 3 (and CM 2 on 1-2); a 2-winding unit's SBASE1-2 is also both ends' ratedS; a 3-winding unit's pair bases have no end to go on; blank: SBASE (defaulted) |
| `r3_1` | `Optional[float]` |  | derived | R3-1: with X3-1, r (ohm) seen from winding 1 (transformer_ohms, by CZ); 2-winding: on end 1, 3-winding: on the mesh row; blank: 0 (defaulted) |
| `x3_1` | `Optional[float]` |  | derived | X3-1: as R3-1, x (ohm) |
| `sbase3_1` | `Optional[float]` |  | derived | SBASE3-1 (MVA): the pair's base for CZ 2 and 3 (and CM 2 on 1-2); a 2-winding unit's SBASE1-2 is also both ends' ratedS; a 3-winding unit's pair bases have no end to go on; blank: SBASE (defaulted) |
| `vmstar` | `Optional[float]` |  | untranscribed | VMSTAR: the solved voltage of the star point, which the Delta model omits |
| `anstar` | `Optional[float]` |  | untranscribed | ANSTAR: as VMSTAR |
| `windv1` | `Optional[float]` | `0.978`, `0.969`, `0.932` | derived | WINDV1: the ratio, in CW units: RatioTapChanger step (ratio_tap) on winding 1, or any winding of a 3-winding unit; a fixed RatioTapChanger (neutralU = WINDV in kV, R4b-4) on an off-nominal winding 2 of a 2-winding unit, a COD 0 winding without a usable RMI..RMA, or an off-nominal phase shifter winding; blank: 1.0, or the bus's BASKV for CW 2 (defaulted) |
| `nomv1` | `Optional[float]` | `0.0`, `500.0`, `345.0` | derived | NOMV1 (kV): PowerTransformerEnd ratedU, or the bus's BASKV when 0 (RAW-6); blank: 0 (defaulted) |
| `ang1` | `Optional[float]` | `0.0` | derived | ANG1 (deg): phaseShift = cim_angle(ANG) on end 1 (R4b-2), or, with |COD1| 3, the PhaseTapChangerLinear's step (phase_tap, R4b-3); blank: 0 (defaulted) |
| `rate1_1` | `Optional[float]` | `0.0` | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate1_2` | `Optional[float]` | `0.0` | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate1_3` | `Optional[float]` | `0.0`, `430.0`, `2000.0` | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate1_4` | `Optional[float]` | `0.0` | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate1_5` | `Optional[float]` | `0.0` | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate1_6` | `Optional[float]` | `0.0` | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate1_7` | `Optional[float]` | `0.0` | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate1_8` | `Optional[float]` | `0.0` | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate1_9` | `Optional[float]` | `0.0` | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate1_10` | `Optional[float]` | `0.0` | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate1_11` | `Optional[float]` | `0.0` | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate1_12` | `Optional[float]` | `0.0` | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `cod1` | `Optional[int]` | `0`, `1` | mapped | COD1: 0 ltcFlag false, control disabled; +-1 voltage, +-2 reactivePower, +-3 activePower (a PhaseTapChangerLinear, R4b-3), ltcFlag true, controlEnabled and enabled = (COD > 0); +-5 raises (no case), +-4 raises (phase 2); blank: 0 (defaulted) |
| `cont1` | `Optional[int]` | `0`, `1001`, `1002` | structural | CONT1: the TapChangerControl Terminal bb_<|CONT|>_T1, or the winding's own xf_<key>_T<k> when 0 (user 2026-11-08; COD +-1 too, R4b-7) and for COD +-3; a negative CONT's sign is listed on the control row (R4b-8); blank: 0 (defaulted) |
| `rma1` | `Optional[float]` | `1.5`, `1.1` | derived | RMA1: highStep's ratio, in CW units (ratio_tap: steps 1..NTP from RMI to RMA, stepVoltageIncrement), or angle (deg) for COD +-3 (phase_tap); listed on the row where CIM cannot hold it (R4b-3, -4, -5); blank: 1.1 for CW 1 or 3 and |COD| not 3 (defaulted), else raises |
| `rmi1` | `Optional[float]` | `0.51`, `0.9` | derived | RMI1: lowStep's ratio or angle; as RMA1; blank: 0.9 (defaulted) as RMA1 |
| `vma1` | `Optional[float]` | `1.5`, `1.1` | derived | VMA1: targetValue = (VMA + VMI) / 2 and targetDeadband = VMA - VMI, in V x the regulated bus's BASKV (volts_from_per_unit) for voltage, in VAr from Mvar (vars_from_mvar) for reactivePower, in W from MW (watts_from_mw) for activePower; blank: 1.1 for COD 0 or +-1 (defaulted), else raises |
| `vmi1` | `Optional[float]` | `0.51`, `0.9`, `0.95` | derived | VMI1: as VMA1; blank: 0.9 for COD 0 or +-1 (defaulted) |
| `ntp1` | `Optional[int]` | `159`, `989`, `30` | derived | NTP1: highStep = NTP, lowStep = 1 (the steps of a phase shifter too); below 2 raises; blank: 33 (defaulted) |
| `tab1` | `Optional[int]` | `0` | structural | TAB1: an ImpedanceTapChangerTabular xf_<key>_ztab<k> on end 1, naming table ict_<TAB> (R4b-10); a 3-winding unit's raises; blank: 0 (defaulted) |
| `cr1` | `Optional[float]` | `0.0` | derived | CR1 (pu on SBASE): lineDropR = CR x BASKV^2 / SBASE ohm (ohms_from_per_unit, the regulated bus's BASKV), lineDropCompensation true (R4b-9); nonzero off COD +-1 raises; blank: 0 (defaulted) |
| `cx1` | `Optional[float]` | `0.0` | derived | CX1: lineDropX, as CR1 |
| `cnxa1` | `Optional[float]` | `0.0` | structural | CNXA1: only COD +-5 uses it; nonzero raises; blank: 0 (defaulted) |
| `nod1` | `Optional[int]` | `0` | structural | NOD1: a node of bus CONT1; nonzero: the TapChangerControl Terminal is that node's busbar bb_s<IS>_n<NOD>_T1 (R6, RAW-11); with CONT1 0 it raises; blank: 0 (defaulted) |
| `windv2` | `Optional[float]` | `1.0` | derived | WINDV2: the ratio, in CW units: RatioTapChanger step (ratio_tap) on winding 1, or any winding of a 3-winding unit; a fixed RatioTapChanger (neutralU = WINDV in kV, R4b-4) on an off-nominal winding 2 of a 2-winding unit, a COD 0 winding without a usable RMI..RMA, or an off-nominal phase shifter winding; blank: 1.0, or the bus's BASKV for CW 2 (defaulted) |
| `nomv2` | `Optional[float]` | `0.0`, `345.0`, `230.0` | derived | NOMV2 (kV): PowerTransformerEnd ratedU, or the bus's BASKV when 0 (RAW-6); blank: 0 (defaulted) |
| `ang2` | `Optional[float]` |  | derived | ANG2 (deg): phaseShift = cim_angle(ANG) on end 2 (R4b-2), or, with |COD2| 3, the PhaseTapChangerLinear's step (phase_tap, R4b-3); blank: 0 (defaulted) |
| `rate2_1` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate2_2` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate2_3` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate2_4` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate2_5` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate2_6` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate2_7` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate2_8` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate2_9` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate2_10` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate2_11` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate2_12` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `cod2` | `Optional[int]` |  | mapped | COD2: 0 ltcFlag false, control disabled; +-1 voltage, +-2 reactivePower, +-3 activePower (a PhaseTapChangerLinear, R4b-3), ltcFlag true, controlEnabled and enabled = (COD > 0); +-5 raises (no case), +-4 raises (phase 2); blank: 0 (defaulted) |
| `cont2` | `Optional[int]` |  | structural | CONT2: the TapChangerControl Terminal bb_<|CONT|>_T1, or the winding's own xf_<key>_T<k> when 0 (user 2026-11-08; COD +-1 too, R4b-7) and for COD +-3; a negative CONT's sign is listed on the control row (R4b-8); blank: 0 (defaulted) |
| `rma2` | `Optional[float]` |  | derived | RMA2: highStep's ratio, in CW units (ratio_tap: steps 1..NTP from RMI to RMA, stepVoltageIncrement), or angle (deg) for COD +-3 (phase_tap); listed on the row where CIM cannot hold it (R4b-3, -4, -5); blank: 1.1 for CW 1 or 3 and |COD| not 3 (defaulted), else raises |
| `rmi2` | `Optional[float]` |  | derived | RMI2: lowStep's ratio or angle; as RMA2; blank: 0.9 (defaulted) as RMA2 |
| `vma2` | `Optional[float]` |  | derived | VMA2: targetValue = (VMA + VMI) / 2 and targetDeadband = VMA - VMI, in V x the regulated bus's BASKV (volts_from_per_unit) for voltage, in VAr from Mvar (vars_from_mvar) for reactivePower, in W from MW (watts_from_mw) for activePower; blank: 1.1 for COD 0 or +-1 (defaulted), else raises |
| `vmi2` | `Optional[float]` |  | derived | VMI2: as VMA2; blank: 0.9 for COD 0 or +-1 (defaulted) |
| `ntp2` | `Optional[int]` |  | derived | NTP2: highStep = NTP, lowStep = 1 (the steps of a phase shifter too); below 2 raises; blank: 33 (defaulted) |
| `tab2` | `Optional[int]` |  | structural | TAB2: an ImpedanceTapChangerTabular xf_<key>_ztab<k> on end 2, naming table ict_<TAB> (R4b-10); a 3-winding unit's raises; blank: 0 (defaulted) |
| `cr2` | `Optional[float]` |  | derived | CR2 (pu on SBASE): lineDropR = CR x BASKV^2 / SBASE ohm (ohms_from_per_unit, the regulated bus's BASKV), lineDropCompensation true (R4b-9); nonzero off COD +-1 raises; blank: 0 (defaulted) |
| `cx2` | `Optional[float]` |  | derived | CX2: lineDropX, as CR2 |
| `cnxa2` | `Optional[float]` |  | structural | CNXA2: only COD +-5 uses it; nonzero raises; blank: 0 (defaulted) |
| `nod2` | `Optional[int]` |  | structural | NOD2: a node of bus CONT2; nonzero: the TapChangerControl Terminal is that node's busbar bb_s<IS>_n<NOD>_T1 (R6, RAW-11); with CONT2 0 it raises; blank: 0 (defaulted) |
| `windv3` | `Optional[float]` |  | derived | WINDV3: the ratio, in CW units: RatioTapChanger step (ratio_tap) on winding 1, or any winding of a 3-winding unit; a fixed RatioTapChanger (neutralU = WINDV in kV, R4b-4) on an off-nominal winding 2 of a 2-winding unit, a COD 0 winding without a usable RMI..RMA, or an off-nominal phase shifter winding; blank: 1.0, or the bus's BASKV for CW 2 (defaulted) |
| `nomv3` | `Optional[float]` |  | derived | NOMV3 (kV): PowerTransformerEnd ratedU, or the bus's BASKV when 0 (RAW-6); blank: 0 (defaulted) |
| `ang3` | `Optional[float]` |  | derived | ANG3 (deg): phaseShift = cim_angle(ANG) on end 3 (R4b-2), or, with |COD3| 3, the PhaseTapChangerLinear's step (phase_tap, R4b-3); blank: 0 (defaulted) |
| `rate3_1` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate3_2` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate3_3` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate3_4` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate3_5` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate3_6` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate3_7` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate3_8` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate3_9` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate3_10` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate3_11` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `rate3_12` | `Optional[float]` |  | structural | RATEk-n: winding k's ratings, an ApparentPowerLimit (MVA) or CurrentLimit (kA, XFRRAT > 0) xf_<key>_<k>_rate<n> in the set xf_<key>_<k>_ratings on terminal xf_<key>_T<k>; 0 is no limit, no row; blank: 0 (defaulted) |
| `cod3` | `Optional[int]` |  | mapped | COD3: 0 ltcFlag false, control disabled; +-1 voltage, +-2 reactivePower, +-3 activePower (a PhaseTapChangerLinear, R4b-3), ltcFlag true, controlEnabled and enabled = (COD > 0); +-5 raises (no case), +-4 raises (phase 2); blank: 0 (defaulted) |
| `cont3` | `Optional[int]` |  | structural | CONT3: the TapChangerControl Terminal bb_<|CONT|>_T1, or the winding's own xf_<key>_T<k> when 0 (user 2026-11-08; COD +-1 too, R4b-7) and for COD +-3; a negative CONT's sign is listed on the control row (R4b-8); blank: 0 (defaulted) |
| `rma3` | `Optional[float]` |  | derived | RMA3: highStep's ratio, in CW units (ratio_tap: steps 1..NTP from RMI to RMA, stepVoltageIncrement), or angle (deg) for COD +-3 (phase_tap); listed on the row where CIM cannot hold it (R4b-3, -4, -5); blank: 1.1 for CW 1 or 3 and |COD| not 3 (defaulted), else raises |
| `rmi3` | `Optional[float]` |  | derived | RMI3: lowStep's ratio or angle; as RMA3; blank: 0.9 (defaulted) as RMA3 |
| `vma3` | `Optional[float]` |  | derived | VMA3: targetValue = (VMA + VMI) / 2 and targetDeadband = VMA - VMI, in V x the regulated bus's BASKV (volts_from_per_unit) for voltage, in VAr from Mvar (vars_from_mvar) for reactivePower, in W from MW (watts_from_mw) for activePower; blank: 1.1 for COD 0 or +-1 (defaulted), else raises |
| `vmi3` | `Optional[float]` |  | derived | VMI3: as VMA3; blank: 0.9 for COD 0 or +-1 (defaulted) |
| `ntp3` | `Optional[int]` |  | derived | NTP3: highStep = NTP, lowStep = 1 (the steps of a phase shifter too); below 2 raises; blank: 33 (defaulted) |
| `tab3` | `Optional[int]` |  | structural | TAB3: an ImpedanceTapChangerTabular xf_<key>_ztab<k> on end 3, naming table ict_<TAB> (R4b-10); a 3-winding unit's raises; blank: 0 (defaulted) |
| `cr3` | `Optional[float]` |  | derived | CR3 (pu on SBASE): lineDropR = CR x BASKV^2 / SBASE ohm (ohms_from_per_unit, the regulated bus's BASKV), lineDropCompensation true (R4b-9); nonzero off COD +-1 raises; blank: 0 (defaulted) |
| `cx3` | `Optional[float]` |  | derived | CX3: lineDropX, as CR3 |
| `cnxa3` | `Optional[float]` |  | structural | CNXA3: only COD +-5 uses it; nonzero raises; blank: 0 (defaulted) |
| `nod3` | `Optional[int]` |  | structural | NOD3: a node of bus CONT3; nonzero: the TapChangerControl Terminal is that node's busbar bb_s<IS>_n<NOD>_T1 (R6, RAW-11); with CONT3 0 it raises; blank: 0 (defaulted) |


## Transformer: the forms R4 raised on (R4b)

**Approved 2026-11-09 (user) and implemented.** Extends R4 (RAW-5, RAW-6). Mappers: `transformer.py`,
`impedance_correction.py`; derived functions `cim_angle`, `phase_tap`, `usable_tap_range`, `watts_from_mw`,
`impedance_deviation_percent`, `is_angle_table` (`derived.py`). R4 raised `NotImplementedError` on each form below
"until a case has one". A local case set now has them: 29 cases of one network, never committed, reported here by
count only. Profile additions (user, 2026-11-09): `PowerTransformerEnd.phaseShift` (AngleDegrees) and
`ImpedanceTapChangerTabular.TransformerEnd`. Atom (new, hand-built): `tests/atoms/transformer/forms_r4b.raw`.

What one case of the set holds, each condition counted on its own (a record can have several):

| form | windings | R4 today | R4b |
|---|---|---|---|
| fixed phase shift ANGk ≠ 0, \|CODk\| not 3 or 5 | ~765 (~730 at a multiple of 30°, 35 not) | raises | `phaseShift` on end k |
| phase shifter COD ±3 | 66 | raises | `PhaseTapChangerLinear` + an activePower `TapChangerControl` |
| impedance correction table TABk | 49 (all 2-winding: 48 on COD ±3, 1 on COD −2), 32 tables | raises | `ImpedanceTapChangerTable` + `ImpedanceTapChangerTabular` |
| off-nominal winding 2 of a 2-winding unit | 1226 | raises | a fixed `RatioTapChanger` on end 2 |
| COD 0 with RMA ≤ RMI (99) or WINDV outside RMI..RMA (694) | 793 | raises | a fixed `RatioTapChanger` |
| a phase shifter's winding off nominal | 9 | (behind the COD raise) | a fixed `RatioTapChanger` |
| COD ±1 with WINDV outside RMI..RMA | 1 | raises | the step range extended to the step |
| STAT 2 / 3 (one winding of a 3-winding unit out) | 6 / 124 (no STAT 4) | raises | that end's Terminal `connected = false` |
| COD ±1 with CONT 0 | 90 | raises | control on the winding's own terminal |
| CONT < 0 | 11 | raises | control on bus \|CONT\|; the sign listed |
| load-drop compensation CRk/CXk ≠ 0 | 14 (all COD 1) | raises | `lineDropR`/`lineDropX` |

Still raising: COD ±4 (two-terminal DC, phase 2), COD ±5 and CNXA (none in the set), a 3-winding unit's TAB, a
complex impedance factor (Im F ≠ 0; none in the set), CR/CX on a winding that is not a voltage control.

### Angles: one sign for CIM (decision R4b-1)

CIM's `PhaseTapChanger` angles are positive "from the Terminal at the PowerTransformerEnd into the transformer":
the voltage inside leads the terminal's. PSS/E's ANGk is positive when winding k's bus leads the transformer's
internal (star point) voltage, so a PSS/E angle is the CIM angle with its sign turned: `cim_angle(ang) = −ang`, a
named derived function. The new `phaseShift` takes the `PhaseTapChanger` sign (user, 2026-11-09). Its UML
text: "Fixed phase angle displacement, in degrees, of the positive-sequence voltage between this end's terminal and
the transformer's internal reference, positive from the terminal into the transformer as for PhaseTapChanger
angles. It holds only the fixed shift from the winding connection or construction, not any shift from a tap
changer; only the differences between a transformer's ends are physically meaningful." So a fixed shift and a tap
changer's shift on one end add.

### Fixed phase shift (decision R4b-2)

- `PowerTransformerEnd.phaseShift` = `cim_angle(ANGk)` on end k, for each winding whose \|CODk\| is not 3 or 5. A
  2-winding unit has only ANG1, so end 2 stays blank (0).
- Each end's shift is against the transformer's internal reference, as PSS/E's ANGk is against the star point, so
  a 3-winding unit's ANG1..3 go on as they are. Only the differences between ends are physical. In the Delta model
  each mesh impedance joins two ends' internal points, which is where PSS/E's star-point shifts act, so per-end
  shifts are exact.
- No `windingConfiguration`: a positive-sequence case does not say which winding is the delta. VECGRP is still
  copied to `vectorGroup`; it is blank on 513 shifted units of the set, so nothing is derived from it.
- Exporter: ANGk = −phaseShift.

### Phase shifters, COD ±3 (decision R4b-3)

- A `PhaseTapChangerLinear` `xf_<key>_ptap<k>` on end k. PSS/E's angle is continuous (NTP is used only for COD ±1
  and ±2), but CIM's needs steps, so NTPk sets the grid as written: lowStep 1, highStep NTP, from RMI to RMA (in
  PSS/E's angle) in equal steps. `stepPhaseShiftIncrement` = `cim_angle((RMA − RMI)/(NTP − 1))`.
- `neutralStep` is the step nearest PSS/E angle 0 (a tie takes the upper), and `step` = neutralStep + ANG / ((RMA −
  RMI)/(NTP − 1)), a float. ANG itself is exact.
- CIM has no neutral angle (a ratio tap has `neutralU`), so when 0° falls between steps, the end steps' angles move
  by that offset. In the set, 56 of 66 have 0° on the grid; the other 10 are off by 0.3°–1.9°. Those rows list
  `untranscribed: rma=…, rmi=…`, and the exporter's RMA/RMI differ by the offset (expected difference).
- `ltcFlag` true, `controlEnabled` = (COD > 0). `xMax` stays blank: PSS/E's impedance does not move with the angle
  unless TABk says so (below).
- Its control `xf_<key>_ctrl<k>`: `mode = activePower`, `discrete = true`, `enabled = (COD > 0)`, on the winding's
  own terminal `xf_<key>_T<k>` (PSS/E measures the flow into the transformer at winding k's bus, and CIM's terminal
  flow is positive into the equipment, so there is no sign change). `targetValue` = (VMA + VMI)/2 and
  `targetDeadband` = VMA − VMI, in W from MW through the units library. CONTk is not used.
- The winding's ratio WINDVk is fixed (RMA/RMI are angles here): ratio 1 gets no `RatioTapChanger`, an off-nominal
  ratio a fixed one (next).
- Exporter: COD ±3 from a `PhaseTapChangerLinear` with an activePower control, signed by `enabled`.

### Fixed ratios (decision R4b-4)

A winding whose ratio has no usable tap range gets a **fixed** `RatioTapChanger` `xf_<key>_tap<k>`: lowStep =
highStep = neutralStep = step = 1, `neutralU` = WINDVk in kV (`winding_kv`), `stepVoltageIncrement` blank,
`ltcFlag` false, `controlEnabled` false. Its ratio is neutralU / ratedU, exact. Three cases:
- **Winding 2 of a 2-winding unit**, off nominal: end 2's tap changer. It has no COD data, so it has no control.
- **COD 0 with RMA ≤ RMI, or WINDV outside RMI..RMA.** The format document says RMA/RMI are not used at COD 0, so
  this data is valid. The winding keeps R4's disabled control (R4: COD 0 keeps its control). RMA, RMI and NTP are
  listed on the row, `untranscribed: rma=…, rmi=…, ntp=…`, and the exporter writes their defaults (PSS/E ignores
  them at COD 0). A COD 0 winding with a usable range keeps R4's stepped tap changer.
- **A phase shifter's winding, off nominal:** no control (the phase tap changer has it).

Exporter: WINDVk = neutralU / the winding unit; no `RatioTapChanger` → WINDV 1.

### A voltage control's WINDV outside its range (decision R4b-5)

COD ±1 with WINDV outside RMI..RMA (1 winding in the set): CIM needs lowStep ≤ step ≤ highStep. R4's grid and
increment stay, and lowStep extends below 1 or highStep above NTP to the first whole step past the position
(`ratio_tap`). The same holds for COD ±2, the other stepped control (none in the set). RMA and RMI are listed on the
row, and the exporter's RMA/RMI come from the extended steps (expected difference).

### One winding out, STAT 2 / 3 / 4 (decision R4b-6)

`PowerTransformer.inService = true`, and the out winding's terminal gets `connected = false` through an `Update
Table Terminal: mRID, connected` row (R6's pattern) after the ends: STAT 2 → `xf_<key>_T2`, 3 → `_T3`, 4 → `_T1`.
The exporter reads STAT 2/3/4 from the one disconnected terminal and STAT 0 from `inService`.

### Voltage-control terminals (decisions R4b-7, R4b-8)

- **COD ±1 with CONT 0:** the control names the winding's own terminal `xf_<key>_T<k>`, as COD 0 and ±2 already do.
  `enabled` stays as written (COD > 0). The row comment says `CONT 0: regulates its own terminal`. The exporter
  writes CONT 0 back for an own terminal (R4), so this round-trips.
- **CONT < 0:** the control names `bb_<|CONT|>_T1`. The sign tells PSS/E to adjust the ratio as if bus |CONT| were
  on winding 1's side; CIM has no home for it. The control row lists `untranscribed: cont=-<CONT>`, and the gap is
  logged. The exporter writes CONT positive (expected difference). It matters to PSS/E only when |CONT| is not I, J
  or K.

### Load-drop compensation (decision R4b-9)

CRk/CXk (pu on system base) → `TapChangerControl.lineDropCompensation = true`, `lineDropR` = CR × BASKV² / SBASE
and `lineDropX` = CX × BASKV² / SBASE in ohm (`ohms_from_per_unit`). BASKV is that of the regulated bus (|CONT|, or
the winding's own bus at CONT 0). CR/CX on a winding that is not COD ±1 raise (PSS/E uses them only for COD 1; none
in the set).

### Impedance correction tables (decision R4b-10)

- **Artifact:** `impedance_correction.cimtbl` moves before `transformer.cimtbl` in `MAPPING_ORDER`, because each
  winding's tabular names its table.
- **One `ImpedanceTapChangerTable` per RAW table:** `ict_<I>`, name `<I>`. Its points are
  `ImpedanceTapChangerTablePoint` rows with identifier `ict_<I>_<n>` (n = 1.. in file order).
- **Angle or ratio** follows PSS/E's own rule: a table whose first T is below 0.5 or last T above 1.5 is in degrees,
  otherwise a ratio. In the set, 31 tables are angle tables and 1 is a ratio table.
  - Angle: `angle` = `cim_angle(T)`.
  - Ratio: T is in pu of the controlling winding's bus base. CIM's `ratio` is in pu of the end's ratedU, so `ratio`
    = T × BASKV / ratedU. Every user of a ratio table must have the same BASKV / ratedU, otherwise it raises. The
    set's ratio table has one user, with NOMV 230 on a 220 kV bus, so ratio = T × 220/230. A ratio table with no
    user raises (no base to convert with).
  - `step` stays blank: PSS/E looks a table up by ratio or angle, not by step.
- **Factor:** F scales the impedance, so `rEnd1` = `xEnd1` = 100 × (Re F − 1), in percent (a 2-winding unit's r and
  x are on end 1). Im F ≠ 0 raises. rEnd2/3 and xEnd2/3 stay blank.
- **Each winding with TABk:** an `ImpedanceTapChangerTabular` `xf_<key>_ztab<k>`, with `TransformerEnd` = end k and
  `ImpedanceTapChangerTable` = `ict_<TABk>`. Its own step fields stay blank: the winding's `PhaseTapChanger` or
  `RatioTapChanger` holds the position, and the table is looked up by its angle or ratio.
- A 3-winding unit's TAB raises. PSS/E applies it to the T-model's Z_k (ZCOD 0) or to Z_ij (ZCOD 1), and the Delta
  model needs a rule for that; none in the set.
- **Exporter:** TABk from the tabular's table; F = 1 + rEnd1/100. A point with rEnd1 ≠ xEnd1 has no PSS/E form and
  raises.

Field classification (samples from the R4b atom):

| ImpedanceCorrectionRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `table_number` | `Union[int, ImpedanceCorrectionRecordTableNumber]` | `1`, `2` | structural | I: the key, ImpedanceTapChangerTable ict_<I>, named <I>; a winding's TABk names it (transformer.cimtbl) |
| `points` | `list[ImpedanceCorrectionPoint]` | 7 and 3 points | structural | the points (T, F), each an ImpedanceTapChangerTablePoint ict_<I>_<n> (n = 1.. in file order); the 0, 0, 0 point that ends the table is not a point |

| ImpedanceCorrectionPoint field | type | samples | kind | target |
|---|---|---|---|---|
| `t` | `float` | `-30.0`, `-10.0`, `0.0` | derived | Ti: an angle table's (first T < 0.5 or last T > 1.5, is_angle_table) angle = cim_angle(T) (deg); else a ratio table's ratio = T x BASKV / ratedU of its users' winding (users that disagree, or none, raise); step blank (PSS/E looks a table up by angle or ratio) |
| `f_real` | `float` | `1.2`, `1.05`, `1.0` | derived | Re(Fi): rEnd1 = xEnd1 = 100 x (F - 1) percent of the nominal impedance (impedance_deviation_percent; a 2-winding unit's r and x are on end 1) |
| `f_imag` | `float` | `0.0` | structural | Im(Fi): a complex factor has no CIM form (rEnd and xEnd are real); nonzero raises |

### mRIDs (prefixes requested, C3)

`xf_<key>_ptap<k>` (phase tap changer), `xf_<key>_ztab<k>` (impedance tabular), `ict_<I>` and `ict_<I>_<n>` (the
table and its points). A fixed ratio tap reuses `xf_<key>_tap<k>`, so winding 2's is `xf_<key>_tap2`.

### Atom `tests/atoms/transformer/forms_r4b.raw` (hand-built)

One unit per form:
- a 2-winding unit with ANG1 30 and COD 1;
- a 3-winding unit with ANG2 −13.5 and STAT 3;
- a 3-winding unit with STAT 2, and one with STAT 4;
- a COD 3 shifter with 0° on its grid, and a COD −3 shifter with 0° off its grid, an off-nominal WINDV1 and an angle
  table;
- a COD −2 unit with NOMV ≠ BASKV and a ratio table;
- an off-nominal WINDV2 (CW 1 and CW 2);
- COD 0 with RMA = RMI, and COD 0 with WINDV outside RMI..RMA;
- COD 1 with WINDV outside RMI..RMA;
- COD 1 with CONT 0; COD 1 with a negative CONT; COD 1 with CR/CX;
- and the impedance correction section with two tables, one of them running onto a second line.

It survives a RAW read → write → read with nothing lost, and binds. Each value is checked in SI against the formulas
above, and the raise list is tested form by form.

### Expected export differences

- A shifter's RMA/RMI, when 0° falls between its steps (by that offset).
- COD 0 RMA/RMI/NTP that PSS/E ignores come back as their defaults.
- A negative CONT comes back positive.
- An extended voltage-control range comes back as its extended steps.

### CIM 18 gaps and profile notes

- **Gap:** which side of a voltage-controlling winding its controlled bus is on (CONT's sign).
- **Profile note:** the inverse of `ImpedanceTapChangerTabular.TransformerEnd` is spelled
  `TransformerEnd.ImpedanceTabChanger`.
- **Profile note:** `phaseShift`'s sign is the `PhaseTapChanger` sign (R4b-1), stated in its UML text.

### Results

The atom binds, and each form is checked value by value (`tests/test_raw_to_cimtbl.py`, R4b). On the local case
set, every transformer and impedance correction table maps; one case binds whole once the records still blocked
in other slices are set aside (R1b, R2b, R3b, phase 2): 7402 transformers, 9927 ratio and 66 phase tap changers,
32 tables with 303 points, 49 tabulars.

## Areas, tie flows and inter-area transfer (R5)

**Approved 2026-11-08 and implemented.** RAW-2 (the open part: how a bus's AREA is recorded). Atom:
`tests/atoms/area/`. User choices 2026-11-08: a bus's AREA traced on export (no profile extension); inter-area
transfers listed untranscribed (no profile class).

Code: `importer/cimtbl/tie_flow.py` (`TieFlowRows`, used by `branch.py`, `switch.py` and `transformer.py`),
`importer/topology.py` (`untraced_area_buses`), `importer/cimtbl/interarea_transfer.py` (`transfer_lines`) and
`derived.net_import`.

There is no new artifact. Each device's tie flows go in its own artifact, because MET and NMETR are its fields.
The transfers have no CIM home, so they are listed on `area_interchange.cimtbl`.

### netInterchange sign (an R0 fix)

PDES is the area's desired net **export**. CIM's `ControlArea.netInterchange` is positive **into** the area
(ControlArea's rule 1: import positive). So `netInterchange = -PDES` (`net_import`, written `0.0 - PDES` so that 0
stays `0.0`). Both public cases have PDES 0, so no golden value changes. The field becomes derived.

cim18v17 marks `netInterchange`, `pTolerance` and `type` *ToBeDeleted*. Their successor, `AreaInterchangeController`,
carries only `pTolerance` and an `enabled` that RAW does not give (area interchange control is a solution option).
So both values stay on `ControlArea` until the profile has a home for the scheduled interchange.

### Tie flows

A **tie** is a branch, switching device or transformer whose terminals' buses are in more than one AREA.
- **Its home end** is the non-metered end, whose area PSS/E charges with the device's losses:
  - branch MET or switch METERED 1 (bus I metered): J;
  - MET 2: I;
  - a transformer's NMETR names the home winding directly (1, 2 or 3; default 2).
  On a tie, any other value raises. Elsewhere, MET and NMETR stay untranscribed, as before (RAW-22).
- **At each terminal whose bus is not in the home area**, two `TieFlow`s sit on that terminal:
  - one for the bus's own area, `positiveFlowIn = false` (flow into the terminal leaves that area);
  - one for the home area, `positiveFlowIn = true`.

  They sum to zero, as ControlArea's rule 3 asks of a tie seen from both areas. A 3-winding transformer with two
  windings outside its home area has two pairs.
- **mRID** `tf_<AREA>_<terminal>`, name `<AREA>_<key>_T<k>` (prefix requested, C3). The `TieFlow` table comes last
  in the device's artifact. It refers back to the terminal and to `ca_<AREA>`; an AREA with no area-interchange
  record raises, as it does for loads and generators.
- **What it recovers:** a tie's metered end (the terminal holding the pair). That narrows the MET/NMETR gap to
  devices inside one area.

WECC240: 23 tie branches give 46 TieFlows. No transformer or switch there spans two areas, and IEEE14 has one area
and no tie flows. Branch 1002-6506 has MET 2; branch 1201-2901 has MET 1:

```
# tie flows: two TieFlows on each tie's metered terminal, positiveFlowIn = false for the terminal's bus's area and true for the home (non-metered) end's area (MET)
Table TieFlow: mRID, name, positiveFlowIn, ControlArea, Terminal
    tf_3_ln_1002_6506_1_T2, 3_1002_6506_1_T2, false, ca_3, ln_1002_6506_1_T2
    tf_1_ln_1002_6506_1_T2, 1_1002_6506_1_T2, true,  ca_1, ln_1002_6506_1_T2
    ...
    tf_1_ln_1201_2901_1_T1, 1_1201_2901_1_T1, false, ca_1, ln_1201_2901_1_T1
    tf_2_ln_1201_2901_1_T1, 2_1201_2901_1_T1, true,  ca_2, ln_1201_2901_1_T1
```

The atom's 3-winding tie 101-202-302 has NMETR 3, so winding 3 (area 3) is home and windings 1 and 2 are metered:

```
Table TieFlow: mRID, name, positiveFlowIn, ControlArea, Terminal
    tf_1_xf_101_202_302_1_T1, 1_101_202_302_1_T1, false, ca_1, xf_101_202_302_1_T1
    tf_3_xf_101_202_302_1_T1, 3_101_202_302_1_T1, true,  ca_3, xf_101_202_302_1_T1
    tf_2_xf_101_202_302_1_T2, 2_101_202_302_1_T2, false, ca_2, xf_101_202_302_1_T2
    tf_3_xf_101_202_302_1_T2, 3_101_202_302_1_T2, true,  ca_3, xf_101_202_302_1_T2
```

The device tables now say where MET/NMETR are still untranscribed:

```
# untranscribed: o1, f1, o2, f2, o3, f3, o4, f4
# untranscribed off a tie: MET (a tie's TieFlows record it; CIM 18 gap, RAW-22)
Table ACLineSegment: ...
```

### A bus's AREA (RAW-2)

A node or `BusbarSection` has no `ControlArea` association (CIM 18 gap). The area is recorded by what CIM already
places in an area: generating units (R3) and tie flows. On export the bus's AREA is traced:
- **Seeds:**
  - a generator's bus has its unit's `ControlArea`;
  - a tie terminal's bus has its pair's `false` area;
  - each other terminal of a tie has the home area.
- **Propagation:** across every device whose ends are in one area (branch, switch, transformer).

Loads are not seeds, since a load's AREA is its own (R2). The importer runs the same trace on the RAW records. Any
bus the trace cannot reach (a component with no generator and no tie) gets `untranscribed: area=<AREA>` on its
`TopologicalNode` row. In IEEE14 and WECC240, every bus is reached. In the atom, isolated bus 303 is not:

```
    # untranscribed: area=3 (no generator or tie reaches it)
    303, NORTH ISOL, 303, bv_115kv, sub_303
```

### Area slack bus (ISW)

Unchanged: untranscribed (CIM 18 gap). `SynchronousMachine.referencePriority` is the angle reference (R3), not an
area's interchange slack.

### Inter-area transfer

Mapper: `importer/cimtbl/interarea_transfer.py` (`transfer_lines`). It writes no artifact.
- **No home:** cim18v17 has no scheduled-transfer class. cim17v40's `InterchangeSchedule` and its market classes are
  gone, and `TieCorridor` / `PowerTransferCorridor` group ties but carry no schedule.
- **What is written:** each record is listed verbatim on the `ControlArea` table comment of
  `area_interchange.cimtbl`, so the master no longer lists the table as not mapped.
- **Checks:** ARFROM and ARTO must have area-interchange records, else it raises.
- **Recorded as a CIM 18 gap,** with a profile extension as the candidate (the user's).

The atom:

```
# untranscribed: bus_number
# derived: netInterchange = -PDES (net_import)
# untranscribed: inter-area transfers (CIM 18 gap): 1 -> 2 '1' 30.0 MW; 1 -> 2 'A' 20.0 MW; 3 -> 2 '1' 0.0 MW
# (defaulted: transfer_id, power_transfer)
Table ControlArea: mRID, name, netInterchange (MW), pTolerance (MW)
    ca_1, WEST, -50.0, 5.0
    # defaulted: ptol=10.0
    ca_2, EAST, 50.0,  10.0
    # defaulted: name=
    ca_3, 3,    0.0,   0.0
```

| InterareaTransferRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `from_area` | `int` |  | untranscribed | ARFROM: listed on area_interchange.cimtbl's ControlArea comment (no scheduled-transfer class, CIM 18 gap); with no area-interchange record raises |
| `to_area` | `int` |  | untranscribed | ARTO: as ARFROM |
| `transfer_id` | `Optional[str]` |  | untranscribed | TRID: as ARFROM; blank: 1 (defaulted) |
| `power_transfer` | `Optional[float]` |  | untranscribed | PTRAN (MW, positive = ARFROM selling to ARTO): as ARFROM; blank: 0 (defaulted) |

### Atom `tests/atoms/area/areas.raw`

Three areas:

| area | name | ISW | PDES | PTOL |
|---|---|---|---|---|
| 1 | WEST | 101 | 50 | 5 |
| 2 | EAST | 0 | -50 | blank |
| 3 | blank | 0 | 0 | 0 |

**Buses:** 101 (swing, generator) and 102 in area 1; 201 (generator) and 202 (load) in area 2; 301 (generator), 302
(115 kV) and 303 (115 kV, isolated, no equipment: the untraced bus) in area 3.

**Ties:**
- branch 102-201 circuit 1, MET 1 (pair at T1);
- branch 102-201 circuit 2, MET 2 (pair at T2);
- branch 202-301, MET blank (defaults to 1);
- switch 102-301, METERED 2;
- 2-winding transformer 202-302, NMETR 1 (pair at T2);
- 3-winding transformer 101-202-302, NMETR 3 (pairs at T1 and T2).

**Inside one area:** branch 101-102 with MET 2 (stays untranscribed) and transformer 301-302.

**Transfers:** 1→2 '1' 30 MW, 1→2 'A' 20 MW, and 3→2 with TRID and PTRAN blank.

**Exit (met 2026-11-08; 181 tests):**
- the atom binds;
- each tie's two flows sit on one terminal with opposite signs;
- MET and NMETR on a tie are recovered from the pair's terminal;
- in IEEE14, WECC240 and the atom, the trace over the bound CIM gives every bus's RAW AREA, except bus 303,
  which carries the comment (the test's `_traced_areas` is the export rule's first draft);
- the master lists nothing as not mapped.

Also fixed: the schema's NMETR description said "metered end"; NMETR is the non-metered end code. Its default 2
names the same end as MET's default 1.

## Node-breaker substations (R6)

**Approved 2026-11-09 and implemented** (drafted 2026-11-08, checked against the RAW v34 format document 2026-11-09).
RAW-16, RAW-11 (regulated nodes), §3.2's node-breaker rule. User choices 2026-11-09: LATI = LONG = 0 writes no
Location; a busbar only on a node a control regulates (the IEEE118 layouts give no safe busbar rule, below); node
STATUS 0 listed on its row.

Code: `importer/node_breaker.py` (`NodeBreaker`: the blocks, nodes and bus → block index, and
`regulated_terminal`), `importer/topology.py` (block edges in `substation_groups`; substation switching devices in
the area trace), `importer/cimtbl/substation.py`, `importer/cimtbl/equipment_terminal.py`, and `regulated_nodes` in
`generator.py`, `switched_shunt.py` and `transformer.py`.

Cases: `tests/cases/IEEE118/IEEE118_all_hydro_25_clean_4_subs.raw` (written by PSS/E 34.9 2026-11-09: IEEE 118
with four buses expanded to node-breaker, below). Atoms: `tests/atoms/substation/` (the PSS/E-built two-bus atom,
and the hand-built `node_breaker_forms.raw`). IEEE14 and WECC240 have no SUBSTATION data. Goldens:
`tests/goldens/IEEE118/` (`substation.cimtbl`, `equipment_terminal.cimtbl`).

### Load path (RAW-16, resolved)

cimtables already loads a mixed model, so nothing is filed upstream (checked 2026-11-08 on the two-bus atom):
- a row with `node1` and `bus1` puts one Terminal on both its `ConnectivityNode` and its `TopologicalNode`
  (`connectivity.add_connectivity`; its docstring names PSS/E's substation node data as the case);
- a `ConnectivityNode` row binds `TopologicalNode`, `BaseVoltage` and `ConnectivityNodeContainer` as ordinary
  associations, and the inverses (`TopologicalNode.ConnectivityNodes`, `ConnectivityNode.Terminals`) are filled;
- `Update Table Terminal: mRID, ConnectivityNode` adds a node to a Terminal that already has its TopologicalNode.

An in-memory `BusBranchModel` and `NodeBreakerModel` behave the same (they differ only in database loading), so
`RawImporter.model_cls` stays `BusBranchModel`. A bus outside any SUBSTATION block keeps its bare
`TopologicalNode`; a bus inside one also gets its block's `ConnectivityNode`s.

### Artifacts

The SUBSTATION section's four record classes land in three places, because of bind order:

| native class | artifact | position | why there |
|---|---|---|---|
| `SubstationRecord` | `bus.cimtbl`, its `Substation` table | 3 | the bus's `TopologicalNode` names its substation as `ConnectivityNodeContainer`, so the substation binds first |
| `SubstationRecord` (coordinates), `SubstationNodeRecord`, `StationSwitchingDeviceRecord` | `substation.cimtbl` | 3a, after `bus.cimtbl` | a node names its bus's `TopologicalNode`; a regulated node's busbar must exist before the generator, switched shunt and transformer controls that name it |
| `EquipmentTerminalRecord` | `equipment_terminal.cimtbl` | last, after the phase-2 stubs | `Update` rows on Terminals, which exist only once every equipment artifact is written; the mapper matches each record against the equipment those artifacts wrote |

So the equipment mappers stay as they are: they still write `bus` / `bus1` / `bus2`, and the placement on a node is
one reviewable file.

### Substations: the block takes precedence (plan §3.2)

`topology.substation_groups` gains the blocks (`NodeBreaker.block_of_bus`):
- **Block edges:** every bus a block's nodes name is joined to the block's other buses, alongside the §3.2 merge
  equipment.
- **Identity:** a group holding a block is `sub_s<IS>` (prefix C3; `bus.block_mrid`), named the block's NAME
  (blank: IS). Its row comment says `SUBSTATION block IS: bus(es) ...`, plus any merge equipment. A group with no
  block keeps `sub_<lowest bus>`.
- A free bus merged into a block's group (by a transformer) joins `sub_s<IS>`: IEEE118's buses 5 and 38.
- **Raises:** a bus with nodes in two blocks; a group holding two blocks (merge equipment between them); a block
  whose buses are in two zones (a `Substation` has one `Region`).

```
# synthesized: substations, buses merged across switching devices, zero-impedance branches (R = 0, |X| <= THRSHZ
# 0.0001), series capacitors and transformers, within a zone (108 substations, 4 from SUBSTATION blocks (R6))
Table Substation: mRID, name, Region
    ...
    # SUBSTATION block 8: buses 5, 8; xf_8_5_0_1
    sub_s8,   STATION_8, srgn_1
```

**Coordinates** follow the OpenDSS spoke's `LatLongCoords` form: one `CoordinateSystem` `crs_latlong` (crsUrn
`urn:ogc:def:crs:OGC:1.3:CRS84`, x = longitude, y = latitude), a `Location` `sub_s<IS>_loc` with one
`PositionPoint` `sub_s<IS>_loc_1`, and `Update Table Substation: mRID, Location`. A block with LATI = LONG = 0 (the
default, as every block of the two-bus atom and IEEE118 writes) gets no Location, and the document comment lists
them (user, 2026-11-09). The exporter writes 0, 0 back, so the round trip holds either way.

| SubstationRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `substation_number` | `Union[int, SubstationRecordSubstationNumber]` | `100`, `37`, `49` | structural | IS: the key, Substation sub_s<IS> (in bus.cimtbl, R6); the scope of its node numbers |
| `name` | `Optional[str]` | `GLEN L`, `EASTLI`, `PHILO` | structural | NAME: the Substation's name (bus.cimtbl); blank: IS |
| `latitude` | `Optional[float]` | `0.0`, `46.2` | copied | `PositionPoint.yPosition`; LATI (deg): the point sub_s<IS>_loc_1 of Location sub_s<IS>_loc; LATI = LONG = 0 (the default) writes no Location (user, 2026-11-09) |
| `longitude` | `Optional[float]` | `0.0`, `-119.1` | copied | `PositionPoint.xPosition`; LONG (deg): as LATI |
| `grounding_resistance` | `Optional[float]` | `0.1`, `0.2` | untranscribed | SGR (ohm): a substation's DC grounding resistance (GIC) has no CIM 18 home (gap) |

### Nodes

One `ConnectivityNode` `sub_s<IS>_n<NI>` per node, in its bus's `TopologicalNode` and its block's substation, with
its bus's `BaseVoltage`. `NodeBreaker` raises on a node number twice in a block, a node on no bus, and a bus with
nodes in two blocks.

| SubstationNodeRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `node_number` | `int` | `1`, `10`, `11` | structural | NI: with IS the key, ConnectivityNode sub_s<IS>_n<NI>; a node number twice in one block raises |
| `bus_number` | `int` | `100`, `37`, `49` | structural | I: TopologicalNode = I (bare), BaseVoltage = bus I's; a bus with nodes in two blocks raises |
| `name` | `Optional[str]` | `GLEN L_100_1`, `GLEN L_100_10`, `GLEN L_100_11` | copied | `ConnectivityNode.name`; NAME; blank: <IS>_<NI> |
| `status` | `Optional[int]` | `1`, `0` | untranscribed | STATUS: a ConnectivityNode has no in-service flag (CIM 18 gap); 0 is listed on the row |
| `vm` | `Optional[float]` | `1.02` | untranscribed | VM (pu): SvVoltage attaches only to a TopologicalNode (the bus's VM); a VM other than the default -1.0 (not given) is listed on the row |
| `va` | `Optional[float]` | `-2.5` | untranscribed | VA (deg): as VM; listed when not 0.0 |
| `substation_number` | `Optional[int]` | `100`, `37`, `49` | structural | IS: the enclosing block (filled by the reader); ConnectivityNodeContainer = sub_s<IS> |

STATUS has no home (a `ConnectivityNode` has no in-service flag). IEEE118's transfer bus is out of service:

```
# untranscribed: status, vm, va
Table ConnectivityNode: mRID, name, TopologicalNode, BaseVoltage, ConnectivityNodeContainer
    ...
    sub_s100_n1,  GLEN L_100_1,  100, bv_138kv, sub_s100
    # untranscribed: status=0
    sub_s100_n2,  GLEN L_100_2,  100, bv_138kv, sub_s100
```

### Substation switching devices

Each record becomes a `Switch`, `Breaker` or `Disconnector` by TYPE, with the system switching device's code tables
(`switch.SWITCH_CLASS`, `switch.OPEN`), `node1`/`node2` on its nodes and `bus1`/`bus2` on their buses, in
`sub_s<IS>`. A device whose nodes' buses are in two AREAs raises (a tie inside a substation: no case). The R5 area
trace spreads across these devices like any same-area device; one between two nodes of one bus joins nothing.

| StationSwitchingDeviceRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `from_node` | `int` | `1`, `2`, `3` | structural | NI: node1 = sub_s<IS>_n<NI>, bus1 = that node's bus; BaseVoltage = its bus's |
| `to_node` | `int` | `10`, `11`, `12` | structural | NJ: node2, bus2; NI = NJ raises |
| `device_type` | `int` | `2`, `3`, `1` | mapped | TYPE: the class, as a system switching device's STYPE: 1 Switch (generic connector), 2 Breaker, 3 Disconnector; another code raises |
| `circuit` | `Optional[str]` | `1` | structural | CKT: with IS, NI and NJ the key, mRID sw_s<IS>_<NI>_<NJ>_<CKT>; blank: 1 (defaulted) |
| `name` | `Optional[str]` | `SHUNT BREAKER OPEN`, `GEN BREAKER`, `LINE DISCONNECT` | copied | `Switch.name`, `Breaker.name`, `Disconnector.name`; NAME; blank: the key <IS>_<NI>_<NJ>_<CKT> |
| `status` | `Optional[int]` | `1`, `0` | mapped | STATUS: open = (STATUS == 0); blank: 1 (defaulted) |
| `normal_status` | `Optional[int]` | `1`, `0` | mapped | NSTAT: normalOpen = (NSTAT == 0); blank: 1 (defaulted) |
| `reactance` | `Optional[float]` | `0.0001` | untranscribed | X: as a system switching device's (a Switch has no impedance); the exporter writes the default 0.0001 back |
| `rate1` | `Optional[float]` | `0.0`, `250.0` | structural | RATE1..RATE3: as a system switching device's ratings (RatingRows, units by NXFRAT), the set sw_s<key>_ratings on terminal 1; zero is no limit |
| `rate2` | `Optional[float]` | `0.0` | structural | RATE2: as RATE1 |
| `rate3` | `Optional[float]` | `0.0` | structural | RATE3: as RATE1 |
| `substation_number` | `Optional[int]` | `100`, `37`, `49` | structural | IS: EquipmentContainer = sub_s<IS> |

```
# untranscribed: reactance
Table Breaker: mRID, name, node1, node2, bus1, bus2, open, normalOpen, BaseVoltage, EquipmentContainer
    ...
    sw_s100_1_2_1,  100_1_2_1,  sub_s100_n1, sub_s100_n2,  100, 100, true,  true,  bv_138kv, sub_s100

Table Disconnector: mRID, name, node1, node2, bus1, bus2, open, normalOpen, BaseVoltage, EquipmentContainer
    sw_s100_2_3_1,  100_2_3_1,  sub_s100_n2, sub_s100_n3,  100, 100, true, true, bv_138kv, sub_s100
    ...
```

### Regulated nodes (RAW-11: NREG, NOD1..NOD3)

A nonzero generator NREG, switched-shunt NREG or transformer NODk names node NI of the regulated bus (IREG / SWREG /
CONTk, or the device's own bus when IREG or SWREG is 0). The control's `Terminal` is `bb_s<IS>_n<NI>_T1`
(`NodeBreaker.regulated_terminal`), the terminal of a `BusbarSection` `bb_s<IS>_n<NI>` on that node (`node` +
`bus`, in `sub_s<IS>`, named the node's NAME). `substation.cimtbl` writes one such busbar per node some control
names (`regulated_nodes` of the three mappers), and no others. The bus's own `bb_<I>` stays as it is, on the bus
only, holding the limits and any bus-level regulation. NREG is a plant quantity: a plant's records must agree on it.
**Raises:** the regulated bus has no block, the block has no node NI of that bus, or NODk ≠ 0 with CONTk = 0.

**Which nodes are busbars** (user, 2026-11-09: none inferred). In IEEE118's four PSS/E-generated layouts the
busbars are exactly the nodes with no equipment terminal (double bus double breaker 8: nodes 1, 2; breaker and a
half 49: 1, 2; main and transfer 100: 1, 2; ring 37: none), each joined to 5-11 devices. That rule fails on a bay's
internal node (a breaker between two disconnectors leaves a terminal-free node too), and the two-bus atom's block 2
has two terminal-free nodes on one breaker each; a degree threshold misses block 1's two-feeder busbars (degree 2).

```
# one per node a control regulates (NREG, NODk; RAW-11); RAW does not say which nodes are busbars
Table BusbarSection: mRID, name, node, bus, BaseVoltage, EquipmentContainer
    bb_s10_n1,  HV BUS, sub_s10_n1,  1, bv_230kv, sub_s10
    bb_s10_n11, LV BUS, sub_s10_n11, 2, bv_115kv, sub_s10
```

### Equipment terminals

Each record puts the equipment's terminal at bus I on node `sub_s<IS>_n<NI>`, as an `Update Table Terminal: mRID,
ConnectivityNode` row in `equipment_terminal.cimtbl`, in (IS, NI) order. The node's bus must be I, and its block
IS. The equipment is matched against the mRIDs the earlier artifacts wrote (`written_equipment`), so the mapper
derives no mRID rule of its own: equipment that no mapper wrote, a key that matches two, and a Terminal placed twice
raise. A terminal with no record stays on its bus only.

**NI = 0** is the format's "bus I has no node-breaker model": the record writes no row, and the table comment counts
such records. NI = 0 at a bus that has nodes raises, as does a nonzero NI at a bus that has none.

| TYP | equipment (key) | Terminal(s) updated |
|---|---|---|
| `L` | load (I, ID) | `ld_<I>_<ID>_T1` |
| `F` | fixed shunt (I, ID) | `cap_<I>_<ID>_T1` |
| `M` | generator (I, ID) | `sm_<I>_<ID>_T1` (WMOD 0) or `pec_<I>_<ID>_T1` (WMOD 1) |
| `B` or `2` (one form) | a branch or a 2-winding transformer (I, J, CKT) | a branch: `ln_` / `sc_<key>_T1` when I is its from bus, `_T2` when its to bus, and that end's line shunt `cap_<key>_i` / `_j` on the same node (RAW-13: a node-breaker model says "switched with its line" by placement); a transformer: `xf_<key>_T1` or `_T2`, by which winding I is |
| `3` | 3-winding transformer (I, J, K, CKT) | `xf_<key>_T<k>`, the winding at I; the buses in any order |
| `S` | switched shunt (I; no ID in v34) | every block's `swsh_<I>_b<k>_T1` |
| `I`, `D`, `V`, `N`, `A` | phase-2 equipment | raise (phase 2) |

The key is matched in either bus order: I is the end at this record, so the record at a branch's to bus lists it
first (IEEE118's `ln_9_8_1_T2` at block 8, the two-bus atom's SUB_2). A system switching device is no
terminal-record form: a `B` key that matches only one raises, and the switch stays on its buses.

| EquipmentTerminalRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `bus_number` | `int` | `100`, `37`, `49` | structural | I: which terminal of the equipment; node NI's bus must be I |
| `node_number` | `int` | `3`, `4`, `5` | structural | NI: the Terminal's ConnectivityNode sub_s<IS>_n<NI> (an Update row); 0: bus I has no node-breaker model, no row |
| `terminal_type` | `str` | `B`, `L`, `M` | structural | TYP: the equipment form, L F M B/2 3 S; B and 2 are one form (a branch or a two-winding transformer); I D V N A raise (phase 2) |
| `j_bus` | `Optional[int]` | `101`, `103`, `104` | structural | J: the other end of a B / 2 / 3 key, in either order |
| `k_bus` | `Optional[int]` | `4`, `1`, `2` | structural | K: the third winding of a 3 key |
| `identifier` | `Optional[str]` | `1`, `2`, `T` | structural | ID / CKT: the rest of the key; blank: 1 for L F M I B 2 3 (defaulted) |
| `substation_number` | `Optional[int]` | `100`, `37`, `49` | structural | IS: the block whose node NI is meant (filled by the reader) |

```
# each named equipment terminal on its node; 1 record with NI 0 (no node-breaker model) places nothing
Update Table Terminal: mRID, ConnectivityNode
    sm_1_G_T1,      sub_s10_n2
    pec_1_PV_T1,    sub_s10_n2
    ln_1_3_A_T1,    sub_s10_n3
    cap_1_3_A_i_T1, sub_s10_n3
    ...
```

### Cases and atoms

- **`two_bus_node_breaker.raw`** (PSS/E-built, committed in R0): `sub_s1`, `sub_s2`; 8 nodes; 7 breakers; the four
  line ends on nodes 3 and 4 of each block (`ln_1_2_1_T1` on `sub_s1_n3`, `ln_1_2_1_T2` on `sub_s2_n3`, ...).
- **IEEE118** (PSS/E-written; the whole case mapped before R6 apart from its SUBSTATION data):
  - block 8 (OLIVE 345 kV, double bus double breaker): 7 nodes, 10 breakers; terminals `L`, `M`, two `B`, and a
    `2` to bus 5, which the transformer merges into `sub_s8`;
  - block 37 (EASTLI 138 kV, ring): 7 nodes, 7 breakers; `S`, five `B`, and a `2` to bus 38 (merged into
    `sub_s37`);
  - block 49 (PHILO 138 kV, breaker and a half): 16 nodes, 21 breakers; `L`, `M`, twelve `B` (two pairs of
    parallel lines);
  - block 100 (GLEN L 138 kV, main and transfer): 12 nodes, 11 breakers (1-2 open, normally open) and 10 open
    disconnectors to the out-of-service transfer bus (node 2, STATUS 0); `L`, `M`, eight `B`.

  No NREG, NODk, `F` or `3`; every block at 0, 0. 36 terminals placed, 42 nodes, 108 substations.
- **`node_breaker_forms.raw`** (hand-built, its content in the folder's README): one block 10 at 46.2 N, 119.1 W
  holding buses 1 (230 kV) and 2 (115 kV), every TYPE, open and normally-open devices, a rated device, an unnamed
  node with VM/VA; terminal records for `L`, `F`, `M` (WMOD 0 and 1), `B` (a line with its line shunt), `2` (a
  transformer, and a line written as `2`), `3` (once with its buses reordered), `S`, and one with NI = 0 at the free
  bus 4, which the 3-winding transformer merges into `sub_s10`; a generator NREG, a switched-shunt NREG and a
  transformer NOD1 (two controls on one node, so one busbar each for nodes 1 and 11).

  Raise tests on it: a bus in two blocks, two blocks in one substation, a block across zones, NI = NJ, a device
  node outside its block, a terminal on another bus's node, unknown equipment, a Terminal placed twice, NI 0 at a
  bus with nodes, a phase-2 and an unknown TYP, a `B` record naming a system switching device, an NREG with no node,
  NOD1 with CONT1 0.

**Exit (met 2026-11-09; 216 tests):**
- IEEE118 and both atoms bind; every placed Terminal's `ConnectivityNode.TopologicalNode` is its own
  `TopologicalNode`, and every node is in its bus's substation;
- the master lists nothing as not mapped for any of them;
- IEEE14 and WECC240 output is unchanged (their goldens and counts pass as before);
- NREG / NODk no longer raise, except as above;
- IEEE118 and the forms atom read → write → read losslessly.

### Expected export differences

SGR comes back as the default 0.1; a node's STATUS 0 as 1, and its VM/VA as the defaults (-1.0, 0.0); a terminal
record with NI = 0 is not written back (it places nothing); a `B`/`2` record comes back as `2` for a transformer and
`B` for a branch; a substation switching device's X as 0.0001; a block at 0, 0 as 0, 0. A free bus merged into a
block's substation (by a transformer) stays outside the block's node data, as it was.

## FACTS devices and DC lines (phase 2, P2a / P2b)

**P2a approved 2026-11-09 (user: "profiles fixed, continue") and implemented**: `facts_device.py`, `vsc_dc.py`,
`dc_topology.py`; atom `tests/atoms/dc/facts_vsc.raw`. **P2b approved 2026-11-09 (user: "go ahead and build the
converter transformer") and implemented**: `two_terminal_dc.py`, derived `converter_transformer_ohms`,
`converter_tap`; atom `tests/atoms/dc/two_terminal.raw`; the converter transformer follows the new core shape
`behind_transformer.cimtbl` (C8, on the core branch `c8-behind-transformer`). Profile additions (user, 2026-11-09): `ACDCConverter.PccTerminal`, and `VsCapabilityCurve` is a `Curve`. The local case set holds the following, the same in each of its 29 cases (counts only):

| table | per case | forms | P2 |
|---|---|---|---|
| FACTS device | 25 | all shunt only (J = 0, MODE 0 or 1); 24 regulate a remote bus; PDES, QDES, SET1, SET2, IMX 0, MNAME blank | P2a |
| VSC DC line | 2 | both are area ties; converter TYPE 1 + 2, MODE 1; 3 of the 4 converters regulate a remote bus | P2a |
| two-terminal DC line | 19 | MDC 0 or 1; every converter transformer implicit (IFR = ITR = 0); no capacitor commutation (XCAP 0); 2 are area ties; 3 name a commutating bus ICR | P2b |
| multi-terminal DC, GNE, induction machine | 0 | | stubs stay |

The set has no node-breaker substations, so equipment terminal records of TYP A, D and V still raise. Switched
shunts with MODSW 6 (they control a FACTS device's shunt output) go with MODSW 3 in R2b: both convert VSWHI/VSWLO
from pu of the controlled device's reactive range.

### DC topology (decision P2-1)

- **Bus-branch, so `DCTopologicalNode`s**, as AC buses are `TopologicalNode`s. Each DC line has two:
  `<line>_n1` (converter 1 or the rectifier) and `<line>_n2`.
- **A `DCLine` container per line**, holding the nodes and one `DCLineSegment` `<line>_seg`. Its `resistance`
  is RDC (ohm), and its `DCTerminal`s `<line>_seg_DC1`/`_DC2` sit on n1/n2.
- **Each converter has one `ACDCConverterDCTerminal`** `<converter>_DC1` (`polarity` positive) on its node. RAW
  gives one equivalent pole, so the return path is not modeled. CIM's monopole has a negative terminal as well.
- **RDC = 0 is still a segment, with resistance 0.** About 3 lines per case have it; it looks like back-to-back,
  but no topology is inferred from it.
- **Converters sit in their AC bus's `Substation`**, as all AC equipment does. No `DCConverterUnit`: RAW says
  nothing of poles or operating mode.
- **cimtables binds these rows as they are:** the DC terminals are explicit rows, and the converters' AC
  terminals come from the `bus` column. This was checked on a scratch document, so no core or cimtables request
  is needed. mRIDs: two-terminal lines `dc2_<NAME>`, VSC lines `vsc_<NAME>` (prefixes requested, C3).

### FACTS device: shunt only (decision P2-2)

**Equipment.** `StaticSynchronousCompensator` `fd_<NAME>` (a `FACTSEquipment`, so a `RegulatingCondEq`), on bus
I, in bus I's substation and BaseVoltage. J ≠ 0 raises: series FACTS (SSSC, UPFC, IPFC); there are none in the
set, and UPFC/IPFC have no CIM class.

| field | target |
|---|---|
| MODE | 0: `inService` false; 1: true; 2..8 need J ≠ 0 and raise |
| VSET | a `RegulatingControl` `fdc_<NAME>`: mode voltage, discrete false, enabled true, targetValue = VSET × BASKV(FCREG) (V) |
| FCREG, NREG | the control's Terminal: `bb_<FCREG>_T1`, or the node busbar (R6, RAW-11); FCREG 0 is bus I |
| SHMX (MVA at unity voltage) | `ratedI` = SHMX / (√3 × BASKV(I)) kA (`ka_from_rating`, RAW-9); 0 (5 devices: shunt disabled) stays 0 |
| PDES, QDES, TRMX, VTMN, VTMX, VSMX, IMX, LINX, SET1, SET2, VSREF, MNAME | the series element's; a shunt device does not use them; untranscribed, listed on the row when not the default (5 rows in the set) |
| RMPCT | untranscribed, as the switched shunt's (gap); listed when not 100 (3 devices) |
| OWNER | untranscribed (gap) |

### VSC DC line (decision P2-3)

**Line.** A `DCLine` `vsc_<NAME>` with segment `resistance` = RDC. MDC 0 sets `inService` false on the segment and
both converters. O1..F4 are untranscribed (ownership gap).

**Converters.** `VsConverter` `vsc_<NAME>_c1` and `_c2` on IBUS. Converter k:

| field | target |
|---|---|
| TYPE | 0: `inService` false, DCSET listed; 1: `pPccControl` udc, `targetUdc` = DCSET (kV); 2: `pPccControl` pPcc, `targetPpcc` = −DCSET (MW; RAW's + feeds the AC network, CIM uses the load sign) |
| MODE, ACSET | 1: `qPccControl` voltagePcc, `targetUpcc` = ACSET × BASKV(VSREG or IBUS) (kV); 2: `qPccControl` powerFactorPcc, `targetPowerFactorPcc` = ACSET |
| ALOSS, BLOSS | `idleLoss` (kW) and `switchingLoss` (kW/A): PSS/E's loss = ALOSS + Idc × BLOSS |
| MINLOSS | no CIM home (gap); listed when not 0 |
| SMAX, IMAX | an `OperationalLimitSet` `<converter>_ratings` on T1, typed as RATE1: `ApparentPowerLimit` SMAX (MVA) and `CurrentLimit` IMAX (A); 0 (unlimited) writes no limit |
| PWF | no CIM home (gap); listed when not 1.0 (all 4 converters are 0.5) |
| MAXQ, MINQ | MODE 1: a `VsCapabilityCurve` `<converter>_qcurve` (curveStyle constantYValue, x in MW, y in MVAr) with one `CurveData` point: x 0, y1 MINQ, y2 MAXQ, so the limits hold at every P. MODE 2 does not use them; listed when not the default |
| VSREG, NREG | MODE 1: `PccTerminal` = `bb_<VSREG>_T1` (`bb_<IBUS>_T1` when 0, RAW-11), or the NREG node's busbar (R6); MODE 2: `bb_<IBUS>_T1`, with VSREG and NREG listed when not 0 |
| RMPCT | `qShare` (PerCent), copied |

**Ties (both lines).** PSS/E makes the DC-voltage (TYPE 1) converter the non-metered home end. The `TieFlow` pair
goes on the other converter's terminal, through R5's `TieFlowRows`. Its `add` takes the terminals' mRIDs, since a
DC line's two terminals belong to two converters. A tie without exactly one TYPE 1 converter raises.

### Two-terminal DC line (decision P2-4)

**Line.** A `DCLine` `dc2_<NAME>`, the segment, and `CsConverter`s `dc2_<NAME>_r` (`operatingMode` rectifier,
behind IPR) and `_i` (inverter, behind IPI), each on its internal node (P2-5).

| field | target |
|---|---|
| MDC 0 (blocked) | `inService` false on the segment and both converters (the transformers stay in service); the rectifier has no `pPccControl`; SETVL listed on the `DCLine` row, since its unit (A or MW) depends on the MDC it was blocked from |
| MDC 1, SETVL | rectifier `pPccControl` activePower. SETVL > 0 is `targetPpcc` on the rectifier; SETVL < 0 (most of the set) is `targetPpcc` on the inverter, as given: the load sign already makes an inverter's injection negative |
| MDC 2, SETVL | rectifier `pPccControl` dcCurrent, `targetIdc` = SETVL (A) |
| VSCHD | inverter `pPccControl` dcVoltage, `targetUdc` = VSCHD (kV). RCOMP 0 (all the set) puts the compounding point at the inverter; a nonzero RCOMP is listed |
| VCMOD, RCOMP, DELTI, DCVMIN, CCCITMX, CCCACC | no CIM home (gap); listed on the `DCLine` row when not the default (DELTI is on every line of the set) |
| METER | on a tie, the `TieFlow` pair sits on the metered converter's transformer terminal at the AC bus (`<converter>_xf_T1`); the other converter is home (R5) |
| NBR / NBI | `numberOfValves` = 6 × NB (six valves per bridge) |
| ANMXR, ANMNR / ANMXI, ANMNI | `maxAlpha`, `minAlpha` / `maxGamma`, `minGamma` (deg) |
| RC, XC, EBAS, TR, TAP, TMX, TMN, STP | the converter transformer (P2-5) |
| ICR, NDR | the firing-angle measuring bus has no CIM home (gap); listed on the converter row when nonzero |
| IFR, ITR, IDR ≠ 0 | raise: an AC transformer used as the converter transformer (COD ±4; none in the set) |
| XCAPR, XCAPI ≠ 0 | raise: capacitor commutated (none in the set) |

### The converter transformer (decision P2-5)

Every two-terminal converter has a transformer that RAW describes implicitly (EBAS, TR, TAP and its range, RC/XC
per bridge). Each becomes the core shape `behind_transformer.cimtbl` (plan C8, widened to "equipment behind its own
transformer"; it serves the step-up generators of R3b too):

- **Internal node:** `TopologicalNode` `<converter>_int`, with no busNumber. It sits in the AC bus's substation,
  with the BaseVoltage of EBAS × TR (the valve side). The master's BaseVoltage table adds these voltages
  (`two_terminal_dc.valve_kv`). The `CsConverter` sits on this node.
- **Transformer:** a 2-winding `PowerTransformer` `<converter>_xf`, always in service.
  - End 1 is on the AC bus, with ratedU = EBAS.
  - End 2 is on the internal node, with ratedU = EBAS × TR.
  - **One equivalent per converter.** RAW gives RC/XC per bridge on the valve side and does not say how the NB
    bridges' transformers are built (two 2-winding units or one 3-winding unit). Their AC sides are in parallel,
    so end 1 r, x = RC, XC / (NB × TR²) (ohm; `converter_transformer_ohms`). The exporter gets RC/XC back with NB =
    numberOfValves / 6 and TR = ratedU2 / ratedU1.
  - No ratedS (RAW gives none) and no magnetizing branch.
- **Tap:** a `RatioTapChanger` `<converter>_xf_tap1` on end 1, with `ltcFlag` true, built by `ratio_tap` (R4) over
  the STP grid from TMN (`converter_tap`).
  - stepVoltageIncrement is exactly STP. Step 1 is TMN; highStep is the last whole step at or below TMX. A third of
    the set's ends have a TMX - TMN that is not a whole number of STP steps, and their TMX is listed on the tap row.
  - neutralStep is the step nearest ratio 1, and the step comes from TAP (a float, since TAP is often off the grid).
  - No `TapChangerControl`: PSS/E moves TAP to hold the firing angle within ANMN..ANMX, and no CIM mode says that.

### Profile requests

- **P2-R1 `ACDCConverter.PccTerminal` → `Terminal`**: added by the user. It is the AC point a converter's
  `targetUpcc` refers to; 3 of the 4 VSC converters in the set name a remote bus.
- **P2-R2 `VsCapabilityCurve` as a `Curve`**: added by the user. It holds MAXQ / MINQ.
- **P2-R3 `qPercent` on `RegulatingCondEq`**: not taken. FACTS RMPCT stays a gap, as the switched shunt's does,
  and is listed on the row when it is not 100.

### Atom `tests/atoms/dc/facts_vsc.raw` (hand-built)

Built on the R5 areas atom's buses and areas (3 areas):
- **FACTS:** `STATCOM-LOC`, local FCREG; `STATCOM-REM`, FCREG 301 with TRMX 0 and RMPCT 75 (listed);
  `STATCOM-OUT`, MODE 0 with SHMX 0.
- **`VSC-TIE`:** an area tie. Converter 1 is TYPE 2, MODE 1, with SMAX/IMAX and PWF 0.5; converter 2 is TYPE 1,
  MODE 2, with MINLOSS.
- **`VSC-OUT`:** MDC 0. Converter 1 is MODE 1 with remote VSREG 201 and RMPCT 60; converter 2 is TYPE 0.

It survives a read → write → read losslessly and binds. Each value is checked in SI, and the raises are tested
form by form (`tests/test_raw_to_cimtbl.py`, P2a).

### Atom `tests/atoms/dc/two_terminal.raw` (hand-built)

On the same frame:
- **`DC-TIE`** 102-201, an area tie: MDC 1, SETVL −250 (inverter power), METER I. The rectifier's TMX is off its
  STP grid.
- **`DC-B2B`** 202-201: RDC 0, SETVL 150 (rectifier power), ICR 201 (listed).
- **`DC-CURRENT`** 301-302: MDC 2, SETVL 1000 A, VCMOD 118.1. The inverter's EBAS is 120 kV, on a 115 kV bus.
- **`DC-BLOCKED`** 101-102: MDC 0.

Every line has DELTI ≠ 0, which is listed. The atom survives a read → write → read losslessly and binds, with
values checked in SI and its raises tested (`tests/test_raw_to_cimtbl.py`, P2b).

Field classification (samples from the P2a atom):

| FactsDeviceRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `str` | `STATCOM-LOC`, `STATCOM-OUT`, `STATCOM-REM` | structural | NAME: the key, mRID fd_<NAME> (control fdc_<NAME>), name NAME |
| `ibus` | `int` | `202`, `102`, `302` | structural | I: the device's bus, BaseVoltage and EquipmentContainer (its substation) |
| `jbus` | `Optional[int]` | `0` | structural | J: 0 is a shunt-only device; nonzero (a series element: SSSC, UPFC, IPFC) raises |
| `mode` | `Optional[int]` | `1`, `0` | mapped | MODE: inService = (MODE == 1); 2..8 need J != 0; blank: 1 (defaulted) |
| `pdes` | `Optional[float]` | `0.0` | untranscribed | PDES: the series element's; a shunt-only device does not use it: listed on the row when not the default |
| `qdes` | `Optional[float]` | `0.0` | untranscribed | QDES: the series element's; a shunt-only device does not use it: listed on the row when not the default |
| `vset` | `Optional[float]` | `1.02`, `1.0`, `1.01` | derived | VSET (pu): the control's targetValue = VSET x BASKV(FCREG), in V (volts_from_per_unit); blank: 1.0 (defaulted) |
| `shmx` | `Optional[float]` | `100.0`, `0.0`, `50.0` | derived | SHMX (MVA at unity voltage): ratedI = SHMX / (sqrt(3) x BASKV(I)) kA (ka_from_rating); 0 (no shunt) stays 0; blank: 9999 (defaulted) |
| `trmx` | `Optional[float]` | `9999.0`, `0.0` | untranscribed | TRMX: the series element's; a shunt-only device does not use it: listed on the row when not the default |
| `vtmn` | `Optional[float]` | `0.9` | untranscribed | VTMN: the series element's; a shunt-only device does not use it: listed on the row when not the default |
| `vtmx` | `Optional[float]` | `1.1` | untranscribed | VTMX: the series element's; a shunt-only device does not use it: listed on the row when not the default |
| `vsmx` | `Optional[float]` | `1.0` | untranscribed | VSMX: the series element's; a shunt-only device does not use it: listed on the row when not the default |
| `imx` | `Optional[float]` | `0.0` | untranscribed | IMX: the series element's; a shunt-only device does not use it: listed on the row when not the default |
| `linx` | `Optional[float]` | `0.05` | untranscribed | LINX: the series element's; a shunt-only device does not use it: listed on the row when not the default |
| `rmpct` | `Optional[float]` | `100.0`, `75.0` | untranscribed | RMPCT: a shunt's share of a coordinated voltage control has no CIM home (qPercent is SynchronousMachine's; CIM 18 gap); listed when not 100 |
| `owner` | `Optional[int]` | `1` | untranscribed | OWNER: ownership is an asset concept (CIM 18 gap) |
| `set1` | `Optional[float]` | `0.0` | untranscribed | SET1: the series element's; a shunt-only device does not use it: listed on the row when not the default |
| `set2` | `Optional[float]` | `0.0` | untranscribed | SET2: the series element's; a shunt-only device does not use it: listed on the row when not the default |
| `vsref` | `Optional[int]` | `0` | untranscribed | VSREF: the series element's; a shunt-only device does not use it: listed on the row when not the default |
| `remot` | `Optional[int]` | `0`, `301` | structural | FCREG: the control's Terminal bb_<FCREG>_T1, or bb_<I>_T1 when 0 (RAW-11), or the NREG node's busbar; blank: 0 (defaulted) |
| `mname` | `Optional[str]` |  | untranscribed | MNAME: the series element's; a shunt-only device does not use it: listed on the row when not the default |
| `nreg` | `Optional[int]` | `0` | structural | NREG: a node of bus FCREG; nonzero: the control's Terminal is that node's busbar bb_s<IS>_n<NREG>_T1 (R6, RAW-11); blank: 0 (defaulted) |


| VscDcRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, VscDcRecordName]` | `VSC-OUT`, `VSC-TIE` | structural | NAME: the key; DCLine vsc_<NAME>, its segment, nodes and converters |
| `rdc` | `float` | `16.0`, `1.58` | copied | `DCLineSegment.resistance` (ohm); RDC |
| `ibus_1` | `int` | `202`, `102` | structural | IBUS (converter 1): VsConverter vsc_<NAME>_c1 on this bus, its BaseVoltage and EquipmentContainer (its substation) |
| `converter_type_1` | `int` | `1`, `2` | mapped | TYPE (converter 1): 0 inService false, 1 pPccControl udc, 2 pPccControl pPcc; on a tie the TYPE 1 converter is the home end (R5) |
| `dcset_1` | `float` | `450.0`, `96.0` | derived | DCSET (converter 1): TYPE 1 targetUdc (kV); TYPE 2 targetPpcc = -DCSET (MW: RAW's + feeds the AC network, CIM's load sign); TYPE 0 listed |
| `ibus_2` | `int` | `201`, `202` | structural | IBUS (converter 2): VsConverter vsc_<NAME>_c2 on this bus, its BaseVoltage and EquipmentContainer (its substation) |
| `converter_type_2` | `int` | `0`, `1` | mapped | TYPE (converter 2): 0 inService false, 1 pPccControl udc, 2 pPccControl pPcc; on a tie the TYPE 1 converter is the home end (R5) |
| `dcset_2` | `float` | `100.0`, `300.0` | derived | DCSET (converter 2): TYPE 1 targetUdc (kV); TYPE 2 targetPpcc = -DCSET (MW: RAW's + feeds the AC network, CIM's load sign); TYPE 0 listed |
| `mdc` | `Optional[int]` | `0`, `1` | mapped | MDC: inService = (MDC == 1) on the segment and both converters; blank: 1 (defaulted) |
| `o1` | `Optional[int]` | `1` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `f1` | `Optional[float]` | `1.0` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `o2` | `Optional[int]` | `0` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `f2` | `Optional[float]` | `1.0` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `o3` | `Optional[int]` | `0` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `f3` | `Optional[float]` | `1.0` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `o4` | `Optional[int]` | `0` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `f4` | `Optional[float]` | `1.0` | untranscribed | ownership is an asset concept (CIM 18 gap) |
| `mode_1` | `Optional[int]` | `1` | mapped | MODE (converter 1): 1 qPccControl voltagePcc, 2 qPccControl powerFactorPcc; blank: 1 (defaulted) |
| `acset_1` | `Optional[float]` | `1.0`, `1.02` | derived | ACSET (converter 1): MODE 1 targetUpcc = ACSET x BASKV(VSREG or IBUS) (kv_from_per_unit); MODE 2 targetPowerFactorPcc = ACSET; blank: 1.0 (defaulted) |
| `aloss_1` | `Optional[float]` | `0.0`, `1600.0` | copied | `VsConverter.idleLoss` (kW); ALOSS (converter 1); blank: 0 (defaulted) |
| `bloss_1` | `Optional[float]` | `0.0`, `3.4` | copied | `VsConverter.switchingLoss` (kW/A); BLOSS (converter 1): loss = ALOSS + Idc x BLOSS; blank: 0 (defaulted) |
| `minloss_1` | `Optional[float]` | `0.0` | untranscribed | MINLOSS (converter 1): no CIM home (CIM 18 gap); listed when not 0 |
| `smax_1` | `Optional[float]` | `0.0`, `360.0` | structural | SMAX (converter 1): ApparentPowerLimit <converter>_smax (MVA) in the set <converter>_ratings on its T1, typed RATE1; 0 (unlimited) writes no limit |
| `imax_1` | `Optional[float]` | `0.0`, `1032.0` | structural | IMAX (converter 1): CurrentLimit <converter>_imax (A), as SMAX |
| `pwf_1` | `Optional[float]` | `1.0`, `0.5` | untranscribed | PWF (converter 1): no CIM home (CIM 18 gap); listed when not 1.0 |
| `maxq_1` | `Optional[float]` | `50.0`, `200.0` | copied | `CurveData.y2value` (MVAr); MAXQ (converter 1): MODE 1: the VsCapabilityCurve <converter>_qcurve's one point (P 0, constantYValue), y2 = MAXQ (MVAr); MODE 2 does not use it (listed when not the default) |
| `minq_1` | `Optional[float]` | `-50.0`, `-100.0` | copied | `CurveData.y1value` (MVAr); MINQ (converter 1): as MAXQ, y1 = MINQ |
| `vsreg_1` | `Optional[int]` | `201`, `0` | structural | VSREG (converter 1): MODE 1: PccTerminal bb_<VSREG>_T1, or bb_<IBUS>_T1 when 0 (RAW-11), or the NREG node's busbar; MODE 2: bb_<IBUS>_T1 |
| `rmpct_1` | `Optional[float]` | `60.0`, `100.0` | copied | `VsConverter.qShare`; RMPCT (converter 1); blank: 100 (defaulted) |
| `nreg_1` | `Optional[int]` | `0` | structural | NREG (converter 1): a node of bus VSREG; nonzero: PccTerminal is that node's busbar bb_s<IS>_n<NREG>_T1 (R6) |
| `mode_2` | `Optional[int]` | `1`, `2` | mapped | MODE (converter 2): 1 qPccControl voltagePcc, 2 qPccControl powerFactorPcc; blank: 1 (defaulted) |
| `acset_2` | `Optional[float]` | `1.0`, `0.95` | derived | ACSET (converter 2): MODE 1 targetUpcc = ACSET x BASKV(VSREG or IBUS) (kv_from_per_unit); MODE 2 targetPowerFactorPcc = ACSET; blank: 1.0 (defaulted) |
| `aloss_2` | `Optional[float]` | `0.0`, `615.0` | copied | `VsConverter.idleLoss` (kW); ALOSS (converter 2); blank: 0 (defaulted) |
| `bloss_2` | `Optional[float]` | `0.0`, `2.527` | copied | `VsConverter.switchingLoss` (kW/A); BLOSS (converter 2): loss = ALOSS + Idc x BLOSS; blank: 0 (defaulted) |
| `minloss_2` | `Optional[float]` | `0.0`, `1110.0` | untranscribed | MINLOSS (converter 2): no CIM home (CIM 18 gap); listed when not 0 |
| `smax_2` | `Optional[float]` | `0.0` | structural | SMAX (converter 2): ApparentPowerLimit <converter>_smax (MVA) in the set <converter>_ratings on its T1, typed RATE1; 0 (unlimited) writes no limit |
| `imax_2` | `Optional[float]` | `0.0` | structural | IMAX (converter 2): CurrentLimit <converter>_imax (A), as SMAX |
| `pwf_2` | `Optional[float]` | `1.0` | untranscribed | PWF (converter 2): no CIM home (CIM 18 gap); listed when not 1.0 |
| `maxq_2` | `Optional[float]` | `9999.0` | copied | `CurveData.y2value` (MVAr); MAXQ (converter 2): MODE 1: the VsCapabilityCurve <converter>_qcurve's one point (P 0, constantYValue), y2 = MAXQ (MVAr); MODE 2 does not use it (listed when not the default) |
| `minq_2` | `Optional[float]` | `-9999.0` | copied | `CurveData.y1value` (MVAr); MINQ (converter 2): as MAXQ, y1 = MINQ |
| `vsreg_2` | `Optional[int]` | `0` | structural | VSREG (converter 2): MODE 1: PccTerminal bb_<VSREG>_T1, or bb_<IBUS>_T1 when 0 (RAW-11), or the NREG node's busbar; MODE 2: bb_<IBUS>_T1 |
| `rmpct_2` | `Optional[float]` | `100.0` | copied | `VsConverter.qShare`; RMPCT (converter 2); blank: 100 (defaulted) |
| `nreg_2` | `Optional[int]` | `0` | structural | NREG (converter 2): a node of bus VSREG; nonzero: PccTerminal is that node's busbar bb_s<IS>_n<NREG>_T1 (R6) |


Two-terminal DC field classification (samples from the P2b atom):

| TwoTerminalDCRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, TwoTerminalDCRecordName]` | `DC-B2B`, `DC-BLOCKED`, `DC-CURRENT` | structural | NAME: the key; DCLine dc2_<NAME>, its segment, nodes, converters and their transformers |
| `rdc` | `float` | `0.0`, `15.4`, `1.78` | copied | `DCLineSegment.resistance` (ohm); RDC; 0 is still a segment |
| `setvl` | `float` | `150.0`, `-413.1`, `1000.0` | derived | SETVL: MDC 1 targetPpcc (MW, load sign as given): > 0 on the rectifier, < 0 on the inverter; MDC 2 the rectifier's targetIdc (A); MDC 0 listed (its unit depends on the MDC it was blocked from) |
| `vschd` | `float` | `80.0`, `450.0`, `150.0` | copied | `CsConverter.targetUdc` (kV); VSCHD: the inverter's targetUdc, pPccControl dcVoltage |
| `ipr` | `int` | `202`, `101`, `301` | structural | IPR: the rectifier's AC bus: end 1 of its converter transformer dc2_<NAME>_r_xf, its substation; the CsConverter dc2_<NAME>_r sits on the internal node dc2_<NAME>_r_int |
| `nbr` | `int` | `2` | derived | NBR: numberOfValves = 6 x NB; the transformer's r, x divide by NB (converter_transformer_ohms) |
| `anmxr` | `float` | `17.0`, `21.0`, `24.0` | copied | `CsConverter.maxAlpha` (deg); ANMXR |
| `anmnr` | `float` | `13.0`, `15.0`, `22.0` | copied | `CsConverter.minAlpha` (deg); ANMNR |
| `rcr` | `float` | `0.0`, `0.042`, `0.012` | derived | RCR (ohm per bridge, valve side): end 1 r = RC / (NB x TR^2) (converter_transformer_ohms) |
| `xcr` | `float` | `1.779`, `2.796`, `2.1202` | derived | XCR: end 1 x, as RC |
| `ebasr` | `float` | `230.0` | copied | `PowerTransformerEnd.ratedU` (kV); EBASR: end 1 ratedU; end 2 ratedU = EBAS x TR (valve side), the internal node's BaseVoltage |
| `ipi` | `int` | `201`, `102`, `302` | structural | IPI: the inverter's AC bus: end 1 of its converter transformer dc2_<NAME>_i_xf, its substation; the CsConverter dc2_<NAME>_i sits on the internal node dc2_<NAME>_i_int |
| `nbi` | `int` | `2` | derived | NBI: numberOfValves = 6 x NB; the transformer's r, x divide by NB (converter_transformer_ohms) |
| `anmxi` | `float` | `18.0`, `21.0`, `29.0` | copied | `CsConverter.maxGamma` (deg); ANMXI |
| `anmni` | `float` | `15.0`, `18.0`, `25.0` | copied | `CsConverter.minGamma` (deg); ANMNI |
| `rci` | `float` | `0.0`, `0.042`, `0.012` | derived | RCI (ohm per bridge, valve side): end 1 r = RC / (NB x TR^2) (converter_transformer_ohms) |
| `xci` | `float` | `1.779`, `2.796`, `2.1197` | derived | XCI: end 1 x, as RC |
| `ebasi` | `float` | `230.0`, `120.0` | copied | `PowerTransformerEnd.ratedU` (kV); EBASI: end 1 ratedU; end 2 ratedU = EBAS x TR (valve side), the internal node's BaseVoltage |
| `mdc` | `Optional[int]` | `1`, `0`, `2` | mapped | MDC: 0 blocked (inService false on the segment and both converters), 1 the rectifier's pPccControl activePower, 2 dcCurrent; blank: 0 (defaulted) |
| `vcmod` | `Optional[float]` | `0.0`, `118.1` | untranscribed | VCMOD: no CIM home (CIM 18 gap); listed on the DCLine row when not the default |
| `rcomp` | `Optional[float]` | `0.0` | untranscribed | RCOMP: no CIM home (CIM 18 gap); listed on the DCLine row when not the default (0 puts the compounding point at the inverter) |
| `delti` | `Optional[float]` | `0.1`, `0.17`, `0.15` | untranscribed | DELTI: no CIM home (CIM 18 gap); listed on the DCLine row when not the default |
| `meter` | `Optional[str]` | `R`, `I` | structural | METER: on a tie, the metered converter (R rectifier, I inverter); the other is the home end (R5); blank: I (defaulted) |
| `dcvmin` | `Optional[float]` | `0.0` | untranscribed | DCVMIN: no CIM home (CIM 18 gap); listed on the DCLine row when not the default |
| `cccitmx` | `Optional[int]` | `20` | untranscribed | CCCITMX: no CIM home (CIM 18 gap); listed on the DCLine row when not the default |
| `cccacc` | `Optional[float]` | `1.0` | untranscribed | CCCACC: no CIM home (CIM 18 gap); listed on the DCLine row when not the default |
| `trr` | `Optional[float]` | `0.1905`, `1.0`, `0.3143` | derived | TRR: end 2 ratedU = EBAS x TR; blank: 1.0 (defaulted) |
| `tapr` | `Optional[float]` | `1.0`, `1.09`, `1.024` | derived | TAPR: the RatioTapChanger dc2_<NAME>_r_xf_tap1 on end 1: step from TAP over the STP grid from TMN (converter_tap), ltcFlag true; PSS/E adjusts it to hold the firing angle in range, which no TapChangerControl mode says; blank: 1.0 (defaulted) |
| `tmxr` | `Optional[float]` | `1.06`, `1.12`, `1.1875` | derived | TMXR: highStep = the last whole STP step at or below TMX; a TMX off the grid is listed on the tap row; blank: 1.5 (defaulted) |
| `tmnr` | `Optional[float]` | `0.94`, `0.88`, `0.9375` | derived | TMNR: step 1; blank: 0.51 (defaulted) |
| `stpr` | `Optional[float]` | `0.012`, `0.005`, `0.0125` | derived | STPR: stepVoltageIncrement = STP in percent of EBAS; blank: 0.00625 (defaulted) |
| `icr` | `Optional[int]` | `201`, `0` | untranscribed | ICR: the firing-angle measuring bus has no CIM home (CIM 18 gap); listed on the converter row when not 0 |
| `ifr` | `Optional[int]` | `0` | structural | IFR: nonzero (an AC transformer as the converter transformer, COD +-4) raises |
| `itr` | `Optional[int]` | `0` | structural | ITR: as IFR |
| `idr` | `Optional[str]` | `1` | untranscribed | IDR: used only with IFR / ITR, which raise |
| `xcapr` | `Optional[float]` | `0.0` | structural | XCAPR: nonzero (capacitor commutated) raises |
| `ndr` | `Optional[int]` | `0` | untranscribed | NDR: a node of ICR, as ICR |
| `tri` | `Optional[float]` | `0.1905`, `1.0`, `0.529` | derived | TRI: end 2 ratedU = EBAS x TR; blank: 1.0 (defaulted) |
| `tapi` | `Optional[float]` | `1.0`, `1.01`, `0.9875` | derived | TAPI: the RatioTapChanger dc2_<NAME>_i_xf_tap1 on end 1: step from TAP over the STP grid from TMN (converter_tap), ltcFlag true; PSS/E adjusts it to hold the firing angle in range, which no TapChangerControl mode says; blank: 1.0 (defaulted) |
| `tmxi` | `Optional[float]` | `1.06`, `1.12`, `1.0875` | derived | TMXI: highStep = the last whole STP step at or below TMX; a TMX off the grid is listed on the tap row; blank: 1.5 (defaulted) |
| `tmni` | `Optional[float]` | `0.94`, `0.88`, `0.925` | derived | TMNI: step 1; blank: 0.51 (defaulted) |
| `stpi` | `Optional[float]` | `0.012`, `0.005`, `0.0125` | derived | STPI: stepVoltageIncrement = STP in percent of EBAS; blank: 0.00625 (defaulted) |
| `ici` | `Optional[int]` | `0` | untranscribed | ICI: the firing-angle measuring bus has no CIM home (CIM 18 gap); listed on the converter row when not 0 |
| `ifi` | `Optional[int]` | `0` | structural | IFI: nonzero (an AC transformer as the converter transformer, COD +-4) raises |
| `iti` | `Optional[int]` | `0` | structural | ITI: as IFI |
| `idi` | `Optional[str]` | `1` | untranscribed | IDI: used only with IFI / ITI, which raise |
| `xcapi` | `Optional[float]` | `0.0` | structural | XCAPI: nonzero (capacitor commutated) raises |
| `ndi` | `Optional[int]` | `0` | untranscribed | NDI: a node of ICI, as ICI |


### Expected export differences

- A listed field comes back from its row note only if the exporter reads notes; otherwise it comes back as the
  default.
- A MODE 2 converter's unused VSREG, NREG, MAXQ and MINQ come back the same way.
- A TYPE 0 converter's DCSET comes back the same way.
- P2b: SETVL of a blocked line comes back from its row note, and no MDC beyond 0 is recovered. RC/XC come
  back exactly from r, x, NB and TR. A TMX off the STP grid comes back from its note, or else as the grid's
  top.

### CIM 18 gaps (in the register and the table under CIM 18 gaps)

- A FACTS device's series element, UPFC and IPFC (no class; SSSC has `StaticSynchronousSeriesCompensator`).
- VSC MINLOSS and PWF.
- Two-terminal VCMOD, DELTI, RCOMP, DCVMIN, CCCITMX, CCCACC and ICR.
- RMPCT of a FACTS shunt (P2-R3 not taken).

## Owner


No artifact. The Owner table and every owner field on other records (bus OWNER, O1/F1..O4/F4) are untranscribed:
CIM keeps ownership in asset management (CIM 18 gap). The master comment counts the owners.

| OwnerRecord field | type | samples | kind | target |
|---|---|---|---|---|
| `owner_number` | `Union[int, OwnerRecordOwnerNumber]` | `1` | untranscribed | ownership is an asset concept (CIM 18 gap); no owner.cimtbl is written |
| `owner_name` | `Optional[str]` | `1`, `OWNER1` | untranscribed | as I |

## Code tables

IDE and IC are checked in the mapper (above). They are not CIM enums.

| STYPE (R1) | class |
|---|---|
| 1 generic connector | `Switch` |
| 2 circuit breaker | `Breaker` |
| 3 disconnect switch | `Disconnector` |
| blank or other | raises |

MODSW (R2): the table in [Switched shunt](#switched-shunt-r2). WMOD (R3): the table in
[Generator](#generator-r3). CZ, CM and COD (R4): the tables in [Transformer](#transformer-r4); CW is
`winding_unit_kv` (1 pu of BASKV, 2 kV, 3 pu of NOMV).

## CIM 18 gaps

Each is logged in the shared register (`CIMTBL-Models/distribution/CIM18_GAPS.md`) and in the plan's §6a:

| gap | RAW fields | R0 approximation |
|---|---|---|
| zone membership of a bus | ZONE | substations never span two zones |
| a bus's own control area, and the area slack (equipment is covered: `ControlAreaGeneratingUnit`, `LoadGroup` → `SubLoadArea`, `TieFlow`) | bus AREA, area ISW | bus AREA traced on export from generating units and tie flows (R5), a bus the trace cannot reach listed `untranscribed: area=`; ISW untranscribed |
| area/zone of machines and DC equipment; zone of a load (the `SubLoadArea` → `LoadArea` hierarchy was added to the profile 2026-11-08) | induction machine, MTDC bus AREA/ZONE; load ZONE ≠ bus ZONE | loads in `LoadArea` ⊃ `SubLoadArea` per (area, zone) (R2); the rest untranscribed |
| ownership of network equipment | Owner, OWNER, O1..F4 | untranscribed |
| the metered (loss-allocation) end of a branch (R1) | branch, switch and multi-section line MET; transformer NMETR (R4) | on a tie, recorded by its TieFlows' terminal (R5); elsewhere, and multi-section line MET, untranscribed |
| a scheduled transfer between two control areas (R5; cim17v40's `InterchangeSchedule` is gone, `TieCorridor` has no schedule) | inter-area transfer ARFROM, ARTO, TRID, PTRAN | listed on the `ControlArea` table comment |
| a shunt switched with its line, in a bus-branch model (R1) | branch GI/BI/GJ/BJ | a `LinearShuntCompensator` per end, linked by its mRID only; in a node-breaker substation it sits on its line end's node (R6) |
| a node's in-service status (R6; a `ConnectivityNode` has no `inService`) | substation node STATUS | 0 listed on the node row (`untranscribed: status=0`) |
| a substation's DC grounding resistance, for GIC studies (R6) | substation SGR | untranscribed |
| a solved voltage per node of a split bus (R6; `SvVoltage` attaches only to a `TopologicalNode`) | substation node VM, VA | listed on the node row when given |
| a shunt's or converter's share of a coordinated voltage control (R2, R3) | switched shunt RMPCT; generator RMPCT on WMOD 1 | untranscribed |
| the kind of a renewable bus-branch generator: PV, wind, or an induction machine (R3) | generator WMOD 1 | a `PowerElectronicsConnection` + `PowerElectronicsUnit` (no kind) |
| a machine's positive-sequence reactance: TODO, a profile extension (R3) | generator ZX | untranscribed |
| which side of a voltage-controlling winding its controlled bus is on (R4b) | transformer CONTk's sign | \|CONT\| regulated; the sign listed on the control row |
| a FACTS device's series element; UPFC and IPFC have no class (P2a) | FACTS J ≠ 0, MODE 2..8 | raises (none in a case yet); a shunt-only device's series fields are listed when not the default |
| a FACTS shunt's share of a coordinated voltage control (P2a) | FACTS RMPCT | listed on the row when not 100 |
| a VSC converter's minimum loss and its power weighting factor (P2a) | VSC MINLOSS, PWF | listed on the row when not the default |
| a two-terminal line's mode-switch voltage, margin, compounding, minimum DC voltage, CCC solution settings and commutating bus; its tap control's aim (hold the firing angle) (P2b) | VCMOD, DELTI, RCOMP, DCVMIN, CCCITMX, CCCACC, ICR, NDR; TAP's control | listed on the `DCLine` / converter row when not the default; the tap has no `TapChangerControl` |

Not gaps: a bus's voltage limits and its regulation sit on its `BusbarSection`'s terminal. CIM puts limits and
regulating controls on terminals by design (RAW-11, RAW-19). RAW not saying which nodes are busbars is a gap in
RAW, not CIM: R6 adds a `BusbarSection` only where a control regulates a node.

## Decisions this spec applies

- **RAW-14** (user, 2026-11-08): VM/VA → `SvVoltage`; generator PG/QG → `RotatingMachine.p`/`q` (R3).
- **RAW-17** (recommended): a blank BASFRQ → 60 Hz, defaulted.
- **RAW-18** (recommended): bare bus numbers as node mRIDs, per the translate table (the shape example writes
  `bus_<I>`; request C2).
- **RAW-19** (user, 2026-11-08): a `BusbarSection` per bus; voltage limits in kV on its terminal.
- **R1** (user, 2026-11-08): RAW-9 (rating sets, NXFRAT), RAW-12 (multi-section `Line` with `Update` rows),
  RAW-13 (line shunts as ordinary shunts), RAW-20 (one rating set on terminal 1), RAW-21 (LEN in km), RAW-22
  (MET untranscribed, a gap).
- **R2** (user, 2026-11-08): RAW-8 (loads: SCALE → Conform/NonConformLoad; `LoadArea` ⊃ `SubLoadArea` per (area,
  zone)); RAW-10 (a switched shunt's blocks as one `LinearShuntCompensator` each, under one `RegulatingControl`).
- **R3** (user, 2026-11-08): RAW-7 (one `RegulatingControl` per plant), RAW-23
  (`referencePriority` and `qPercent` added to the profile; ZX a TODO extension), RAW-24 (WMOD 0 a
  `SynchronousMachine`, WMOD 1 a `PowerElectronicsConnection`), RAW-25 (an implicit step-up transformer raised; the
  builder shape a TODO for an owner).
- **R3b** (user, 2026-11-09): R3b-1..R3b-5 (an implicit step-up is the core shape `behind_transformer.cimtbl`: the
  machine on an internal node at bus I's base behind an R4-form 2-winding transformer, GTAP a fixed tap on end 1; PG
  and QG as written on the machine).
- **R4** (user, 2026-11-08): RAW-5 (every CZ/CM code derived to ohm/S; a 2-winding r/x/g/b on end 1; a 3-winding
  unit's Z12/Z23/Z31 as `TransformerMeshImpedance` rows with g/b on end 1, no star conversion; cim18v17 has no
  `TransformerStarImpedance`/`TransformerStarAdmittance`); RAW-6 (a `RatioTapChanger` per tapped winding over steps
  1..NTP, neutralStep nearest ratio 1 at an exact neutralU; COD 0/±1/±2 mapped, ±3/±4/±5 raise; CONT 0 names the
  winding's own terminal).
- **R4b** (user, 2026-11-09): angles in CIM's sign (`cim_angle`; `PowerTransformerEnd.phaseShift` added to the
  profile with the `PhaseTapChanger` sign); fixed shifts on `phaseShift`, never `windingConfiguration`; COD ±3 a
  `PhaseTapChangerLinear` over NTP steps with an activePower control; fixed ratios as one-step `RatioTapChanger`s;
  an out-of-range controlled WINDV extends the steps; STAT 2/3/4 a disconnected terminal; CONT 0 the own terminal,
  a negative CONT's sign listed; CR/CX as `lineDropR`/`lineDropX`; impedance tables as `ImpedanceTapChangerTable`
  + `ImpedanceTapChangerTabular` (its `TransformerEnd` link added to the profile).
- **R5** (user, 2026-11-08): RAW-2's open part (a bus's AREA traced on export from generating units and tie flows;
  no profile extension); tie flows as a pair on each tie's metered terminal; inter-area transfers listed
  untranscribed (no profile class); netInterchange = -PDES.
- **R6** (user, 2026-11-09): RAW-16 (a mixed model loads through cimtables as it is: `node1` + `bus1`, and
  `Update` rows on Terminals); a SUBSTATION block's substation takes precedence over the §3.2 merge; LATI = LONG = 0
  writes no Location; a `BusbarSection` only on a node a control regulates (RAW-11), none inferred from the layout;
  node STATUS 0 listed on its row; `B` and `2` one terminal form, as the format document has it.

## Reference model and expected differences

The golden artifact directory is IEEE14's (`tests/goldens/IEEE14/`), generated by the orchestrator and reviewed by
hand. WECC240 is the bind and round-trip case.

There is no hand translation to differ from. CIMHub_2_0's old converter differs by design:
- it made one `VoltageLevel` per bus;
- it read none of the transformer controls past RATE1-12, and replaced them with schema defaults (§reader);
- it lost 1e-7 values on writing.

Expected export differences from R5:
- MET, METERED and NMETR of a device inside one area come back as their defaults (1, 1, 2);
- a bus the trace cannot reach (listed `untranscribed: area=`) needs the exporter's rule (slice E);
- inter-area transfers and ISW are lost.

Expected export differences from R6: SGR comes back as 0.1; a node's STATUS 0 as 1 and its VM/VA as the defaults;
an equipment terminal record with NI = 0 is not written back; a `B`/`2` record comes back as `2` for a transformer
and `B` for a branch; a substation switching device's X as 0.0001.
