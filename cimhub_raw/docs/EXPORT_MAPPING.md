# cim18v17 → PSS/E RAW v34 export spec

Plan and decisions: `.development/RAW_REWRITE_PLAN.md` §9 (X1-X7, approved 2026-11-09). One section per sub-slice,
each approved before its code. The exporter reads values only through the core getters (skill `export-getters`).
The model it returns has the shape `Raw34Reader.read_all()` returns, so `Raw34Writer` writes a case that the reader
and the importer read back. The import spec is `CIMTBL_MAPPING.md`; its "the exporter writes ..." notes are
settled here, sub-slice by sub-slice.

## E0: framework, case data, bus, zone, area (spec approved 2026-11-09; done 2026-11-09)

### Layout

```
cimhub_raw/src/cimhub_raw/exporter/
    cim_to_raw.py           RawExporter(FormatExporter), EXPORT_ORDER, export_tables, cim_to_raw(network, path)
    identity.py             bus numbers, keyed IDs and numbers (X2), names (X2)
    area_trace.py           a bus's AREA from generating units and tie flows (R5, X5)
    case_identification.py  BasePower, BaseFrequency, rating-set OperationalLimitTypes -> the case record
    zone.py                 SubGeographicalRegion -> Zone
    area_interchange.py     ControlArea -> Area
    bus.py                  TopologicalNode (+ its BusbarSection, SvVoltage) -> Bus
```

- **`RawExporter().to_model(network) -> GraphModel`**, which `Raw34Writer` writes. It checks that every conducting
  equipment class is exported, then calls `export_tables(network, EXPORT_ORDER)`. A class with no module raises
  with the counts (`no RAW export yet for {'ACLineSegment': 20, ...}`), so nothing is dropped silently while the
  sub-slices land. The tests call `export_tables` with the modules that have landed so far.
- Each module has `NATIVE_CLASS`, `SLOTS` and `export(context) -> list[record]` over the whole network. A module
  works over the whole network rather than object by object, because IDs are allocated per bus and AREA is a trace.
- **`SLOTS` moves to core.** The DSS exporter's `slots.py` (`Slot`, `KINDS`, `check_slots`, `with_default`,
  `slots_table`) has nothing DSS-specific in it, so it moves to `cimhub_core/export_slots.py`, and DSS imports it
  from there (a second consumer, not a copy). The kinds:
  - `written`: from a getter;
  - `rule`: a CIM `None` that RAW needs;
  - `unset`: no CIM home, left `None` and written blank, so PSS/E applies its default (X1);
  - `not mapped`.

  A test checks that `SLOTS` lists every schema slot, and the tables below are generated from it.
- **Consistency test:** every field the importer's `FIELDS` marks untranscribed is `unset` here, unless this spec
  recovers it. The one recovered so far is bus AREA, through the R5 trace.
- `context` (`ExportContext`) holds the network, the bus numbers, the per-unit bases (SBASE; each node's BASKV)
  and the AREA trace. Nothing else is shared between modules.
- The records are sorted by key (X6). `ID` is the reader's `composite_id`, so a record compares by key.

### Identity and names (X2)

- **Bus number:** `TopologicalNode.busNumber`. A node without one is internal to a device (see Bus). A number used
  twice raises, and so does a model where no node has one (numbering a model from another format waits for a
  consumer).
- **A keyed ID** (load, machine and shunt ID; branch and transformer CKT) comes from the importer's mRID,
  `<prefix>_<buses>_<ID>`. It is accepted only when the prefix is the module's and the bus numbers are the
  equipment's own, in order. Otherwise the ID is the next free `1`, `2`, ... on that bus (or bus pair). This is
  the one fallback, and each use is logged once per module with a count. The keyed modules arrive in E1-E4.
- **Zone and area numbers:** `srgn_<n>` / `ca_<n>`, by the same rule. Otherwise the next number above the largest
  one taken.
- **NAME** = the CIM `name`. It is written blank when it equals the importer's blank-NAME key (the bus number, the
  zone or area number), so a blank comes back blank. A NAME written as its own number comes back blank too
  (IEEE118's areas and zones). A name longer than its field raises: 12 characters for a bus, zone or area. The
  `name_source` switch (DSS E1) does not apply, because RAW's identity is the number.

### Case identification

The RATING records come from `olt_rate<n>` (`name`, `description`); the importer writes all twelve. A blank
BASFRQ, XFRRAT or NXFRAT on import is the importer's 60 Hz and MVA, so writing them is no difference.

WECC240 writes no RATING records, so it gains the twelve default ones. That is an expected difference, the same
values after defaults.

### Zone, area, owner

- **Zone:** one per `SubGeographicalRegion`: I by X2; ZONAME = `name`.
- **Area:** one per `ControlArea`: I by X2; ARNAME = `name`; PDES = −netInterchange (MW, the inverse of
  `net_import`; a `derived.net_export`); PTOL = pTolerance (MW). ISW is unset (no ControlArea slack association,
  CIM 18 gap).
- **Owner:** none written. Owner is untranscribed on import, so the section is empty and every OWNER/O1 field is
  blank (PSS/E's default is owner 1).

### Bus

One Bus per `TopologicalNode` with a `busNumber`. A node that is internal to a mapped device (the R3b step-up's
`<machine>_int`, P2b's valve-side nodes) has none, and is folded back by its device's sub-slice (E3, E6); the
`TopologicalNode`s without a number are counted on the log line.

- **IDE:** 3 when a `SynchronousMachine` on the bus has `referencePriority` set (import R3). Otherwise 2 when the
  `RegulatingControl` of a machine or connection on the bus is enabled, in any mode (import R3: enabled = IDE 2/3; a
  WMOD 3 plant's control is powerFactor). Otherwise 1. A device on an internal node counts for the one numbered
  node across its transformers (`bus.raw_bus`). IDE 4 (isolated) has no CIM home on import and comes back as 1.
- **ZONE:** the zone number of the `Region` of the node's `Substation` (`ConnectivityNodeContainer`).
- **VM, VA:** **`get_node_voltage(node, "kV", "deg")`** (new core getter, `getters/voltage.py`: the node's one
  balanced `SvVoltage`, `None` without one). VM = v / BASKV (`derived.per_unit_from_kv`). With no SvVoltage they are
  blank (PSS/E's 1.0, 0.0).
- **NVHI..EVLO:** **`get_voltage_limits(equipment, "kV")`** (new core getter, the pattern of `get_current_limits`,
  whose set-finding and agreement helpers it shares: `VoltageLimits(normal_high, normal_low, emergency_high,
  emergency_low)`, kind by the limit type's `durationKind` and `direction`; two that disagree raise; a seasonal or
  short-term voltage limit raises), in pu as for VM.

**The bus's limits** are those of the one `BusbarSection` on the node that holds any: the importer's `bb_<I>`. A
node-breaker block's node busbars (R6: `bb_s<IS>_n<NI>`) carry none. Two busbars with limits on one bus raise.

### A bus's AREA (`area_trace.py`, R5)

The importer's `untraced_area_buses` runs over RAW records. Here, the same rule runs over the bound CIM:
- **Seeds:**
  - the bus of every `SynchronousMachine` or `PowerElectronicsConnection`, with its unit's `ControlArea`
    (`ControlAreaGeneratingUnit`, `ControlAreaPowerElectronicsUnit`);
  - each terminal that holds a `TieFlow` pair, with its bus taking the pair's `positiveFlowIn = false` area;
  - every other terminal of that device, which takes the pair's `true` (home) area.
- **Spreading:** across every device with two or more terminals and no `TieFlow` (a device that R5 found inside
  one area), using `cimtopology.core.Topology(...).islands()` as the importer does. There is no union-find here.
- Two areas meeting in one island raise, naming both seeds. An island with no seed is untraced, and its buses'
  AREA is left blank. That is an expected difference, the row the importer listed (`untranscribed: area=`). In
  the area atom it is isolated bus 303.

### Tests (E0)

- `export_tables(network, (case_identification, zone, area_interchange, bus))` on IEEE14, WECC240, IEEE118 and
  every committed atom. Each is compared with the RAW as read: the case record, the RATING records, Zone, Area and
  Bus, by key. `unset` slots are skipped. Both sides are filled with `fill_defaults` (blank = default), and floats
  are compared at rel 1e-9. The expected differences are one dict in the test, mirroring the list below.
- `RawExporter().to_model(IEEE14)` raises, naming the classes not yet exported.
- New getters: `get_node_voltage` and `get_voltage_limits`, tested on the core `line_bus_branch` shape with hand
  numbers. `export_slots` covers DSS as before; the DSS suite must stay green.
- The writer writes the E0 model, and the reader reads it back with the same records.

### Expected differences (E0)

`tests/test_cim_to_raw.py` `EXPECTED` mirrors this list, fixture by fixture:
- IEEE14 ISW 2 comes back blank (0): unset, not compared.
- An untraced bus's AREA comes back blank (1): isolated bus 303 in three atoms; the loads atom's bus 3 (area 2),
  one of the three buses the importer lists `untranscribed: area=`.
- IDE 4 comes back as 1: bus 303.
- WECC240 gains the twelve default RATING records.
- A zone that buses name without a Zone record comes back as a record (import synthesized it): every atom.
- NXFRAT > 0 (current ratings) came back 0 until E1, which settles it (see E1).
- An area or zone NAME equal to its number comes back blank: IEEE118's three areas and three zones.
- The Owner section comes back empty (not compared: no Owner module).
- VM and the voltage limits can differ in the last digit (pu → kV → pu); compared at rel 1e-9.

### Results

IEEE14, WECC240, IEEE118 and all 18 atoms: every compared slot of the case record, the RATING records, Zone, Area
and Bus equals the RAW as read, except the list above. The written E0 tables read back unchanged.
`RawExporter().to_model` raises on IEEE14, naming the 17 ACLineSegments and the other classes not yet exported.

### Slots (generated from `SLOTS`)

#### CaseIdentificationRecord

| RAW slot | kind | from / why |
|---|---|---|
| new_case_flag | rule | IC 0: a base case |
| system_base_mva | written | SBASE: BasePower.basePower (MVA), the one BasePower |
| revision | rule | REV 34 |
| transformer_ratings_units | rule | XFRRAT 1 when the transformer ratings are CurrentLimits, else 0 |
| branch_ratings_units | rule | NXFRAT 1 when the branch and switch ratings are CurrentLimits, else 0 |
| system_base_frequency | written | BASFRQ: the network's base frequency (Hz) |
| titles | unset | two blank lines: the importer lists the titles on the master's comment |
| general | unset | solution options; THRSHZ only steered the import's substation merge |
| gauss | unset | solution options: no home in the network profile parts |
| newton | unset | solution options: no home in the network profile parts |
| adjust | unset | solution options: no home in the network profile parts |
| tysl | unset | solution options: no home in the network profile parts |
| solver | unset | solution options: no home in the network profile parts |
| ratings | written | a RATING record per olt_rate<n> OperationalLimitType |

#### RatingRecord

| RAW slot | kind | from / why |
|---|---|---|
| rating_set_number | written | n of the type's mRID olt_rate<n> |
| rating_name | written | OperationalLimitType.name |
| rating_description | written | OperationalLimitType.description |

#### ZoneRecord

| RAW slot | kind | from / why |
|---|---|---|
| zone_number | written | I: the srgn_<n> key (X2) |
| zone_name | written | ZONAME: name; blank when it is the number |

#### AreaInterchangeRecord

| RAW slot | kind | from / why |
|---|---|---|
| area_number | written | I: the ca_<n> key (X2) |
| bus_number | unset | ISW: no ControlArea slack association (CIM 18 gap) |
| pdes | written | PDES = -netInterchange (MW, net_export) |
| ptol | written | PTOL: pTolerance (MW) |
| name | written | ARNAME: name; blank when it is the number |

#### BusRecord

| RAW slot | kind | from / why |
|---|---|---|
| bus_number | written | I: busNumber |
| name | written | NAME: name; blank when it is the bus number |
| base_voltage | written | BASKV: get_base_voltage (kV, LL) |
| bus_type | rule | IDE: 3 with a referencePriority machine, 2 with an enabled plant control, else 1 |
| area | written | AREA: the R5 trace; blank when untraced |
| zone | written | ZONE: the number of its Substation's Region |
| owner | unset | OWNER: ownership is an asset concept (CIM 18 gap) |
| voltage_magnitude | written | VM: get_node_voltage v / BASKV |
| voltage_angle | written | VA: get_node_voltage angle (deg) |
| normal_voltage_magnitude_high_limit | written | NVHI: normal high on the bus's BusbarSection (get_voltage_limits), pu of BASKV |
| normal_voltage_magnitude_low_limit | written | NVLO: normal low on the bus's BusbarSection (get_voltage_limits), pu of BASKV |
| emergency_voltage_magnitude_high_limit | written | EVHI: emergency high on the bus's BusbarSection (get_voltage_limits), pu of BASKV |
| emergency_voltage_magnitude_low_limit | written | EVLO: emergency low on the bus's BusbarSection (get_voltage_limits), pu of BASKV |

## E1: branch, series capacitor, switch, multi-section line, ratings (spec approved 2026-11-09: E1-1 grouped sections (amended from "close the gap"), E1-2 line shunts by mRID; done 2026-11-09)

Modules: `branch.py` (`ACLineSegment`, `SeriesCompensator` → Non-transformer branch, with its line shunts),
`switch.py` (`Switch`, `Breaker`, `Disconnector` → System switching device), `multi_section_line.py` (`Line` →
Multi-section line), `ratings.py` (shared: RATE1..RATE12 and the units flag). `EXPORT_ORDER` gains them after
`bus`. Import spec: `CIMTBL_MAPPING.md#branch`, `#system-switching-device`, `#multi-section-line`, R1b, R5.

### Buses and keys

- **I, J:** the `busNumber` of terminal 1's and terminal 2's `TopologicalNode` (`get_terminal_nodes(...,
  topological=True)`), in that order. A terminal on an unnumbered node raises.
- **CKT** (X2): from the mRID `ln_<I>_<J>_<CKT>` / `sc_` / `sw_` when I and J are the terminals' buses in order;
  otherwise the next free `1`, `2`, ... on the bus pair, in either order (PSS/E's key). Two branches with one key
  raise.
- **NAME:** `name`, blank when it is the importer's key `I_J_CKT`; longer than 40 characters raises.

### Branch

| RAW | from |
|---|---|
| R, X, B | `ACLineSegment`: **`get_line_sequence_impedance(line, "pu", base_power=...)`**, lumped values only (`derive` LUMPED: a per-length or matrix line waits for a consumer, E7); pu on the line's BaseVoltage, bus I's on import (R1b-1). A set `gch` raises (RAW has no line conductance). `SeriesCompensator`: **`get_series_compensator(compensator, "pu", base_power=...)`** (the getter gains the line getter's `unit` / `base_power`; ohm stays its default); B blank. A compensator with X ≥ 0 is written as is and comes back an `ACLineSegment` (none on import). |
| ST | `get_in_service(which="actual")`: 1 when true or unset, 0 when false |
| MET | on a tie: the terminal holding its `TieFlow` pair, 1 or 2 (R5); pairs on both terminals raise. Off a tie: blank (1): the loss end has no CIM home (RAW-22) |
| LEN | `ACLineSegment.length` in km; blank when unset. A series capacitor's is lost (R1b-2 listed it on the row) |
| GI, BI, GJ, BJ | the branch's line shunts (decision E1-2) |
| RATE1..12 | ratings, below |
| O1..F4 | unset (CIM 18 gap) |

**Line shunts (decision E1-2):** a `LinearShuntCompensator` whose mRID is
`cap_<I>_<J>_<CKT>_i` / `_j` of an exported branch, on that end's bus, is the branch's GI + jBI / GJ + jBJ: the same
mRID key rule as X2, and the only link the importer could give it (RAW-13, CIM 18 gap). G and B come from a new core
getter **`get_shunt_admittance(shunt, unit, *, sections, base_power=None)`** (total g, b of the `sections` in
service; `"pu"` on the shunt's `nomU` and `base_power`, `nomU` checked against its BaseVoltage since E2; E2 reads fixed and switched shunts with it too). One
section is read (`sections='actual'`). Its `inService` must equal the branch's, else it raises. E2 skips the shunts
claimed here (`branch.line_shunts(network)`). The alternative, every line shunt a fixed shunt, solves the same while
the line is in service but loses the pairing and "switched with its line".

### Series capacitor in the branch table

Only R, X, ST, MET, the key, NAME and the ratings: `SeriesCompensator` has no `bch`, `length` or shunts.

### System switching device

- **Which switches:** a `Switch`, `Breaker` or `Disconnector` with no `ConnectivityNode` on either terminal. One
  on two `ConnectivityNode`s is a substation switching device (R6), exported by E5; one on a node at only one
  terminal raises. Another `Switch` subclass (fuse, recloser, load-break switch, ...) has no module, so `to_model`
  raises on it: RAW has STYPE 1-3 only.
- **STYPE** by class: `Switch` 1, `Breaker` 2, `Disconnector` 3 (the importer's `SWITCH_CLASS` inverted).
- **STATUS / NSTAT:** `get_switch_state(which="actual")` / `"normal"`: open is 0, closed 1; unset raises
  (semantic rule 1).
- **X** and **METERED** have no default in the format, so neither is left blank (amended at implementation):
  - X is 0.0001 (a rule: a `Switch` has no impedance; the substation switching device's default). The import
    spec's "the exporter writes THRSHZ back" now says so (THRSHZ is an unset solution option, E0).
  - METERED is a branch's MET on a tie, and 1 off a tie.
- **Ratings** as a branch's.

### Multi-section line

One record per `Line` whose sections form one path I, DUM1, ..., J:
- **Sections:** the `ACLineSegment`s and `SeriesCompensator`s the `Line` contains (`Equipments`) or groups
  (`AdditionalGroupedEquipment`). Each dummy bus joins exactly two branches, as on import; one to nine dummy buses.
- **A section in one substation (decision E1-1, amended at implementation):** R1b-3 kept such a section (every
  series-capacitor section of the local set, 44) contained by its substation. The approved rule closed the gap it
  left in the Line through the one branch joining two loose ends. The local set showed the case it misses: a
  capacitor at an end of the path leaves no gap, so the Line held one section and the record lost its DUM1. The
  user chose CIM's own association instead ("AdditionalGrouped"): the importer now groups the section in its Line
  (`AdditionalEquipmentContainer`, import R1b-3 amended), and the exporter reads both lists. No gap rule remains.
- **I, J and ID (X2):** from the mRID `msl_<I>_<J>_<ID>` when it names the path's ends; otherwise I is the lower
  end bus, and ID is the next free `&1`, `&2`, ... on the pair (the draft's "`name` when it is `&` and one more
  character" was dropped at implementation: X2's one fallback).
- A `Line` that is still not one path (a branching or a CGMES-style line) writes no record and is counted on the
  log line: a multi-section line is a grouping, and its sections are written as branches either way. This is the
  one fallback.
- MET is unset (RAW-22).

### Ratings (`ratings.py`)

- New core getter **`get_limits_by_type(equipment, limit_class, unit) -> {OperationalLimitType: value}`**
  (`getters/limits_by_type.py`): every `limit_class` limit in the equipment's sets (`equipment_limit_sets`), one
  value per type (`agreed_limit`), `normalValue` required.
- RATEn = the limit whose type's mRID is `olt_rate<n>` (E0's rule); 0 where there is none. A limit of another type
  raises: mapping `durationKind` types onto rating sets waits for a consumer.
- **NXFRAT:** 1 when the case's branch and switch ratings (every `ACLineSegment`, `SeriesCompensator` and `Switch`,
  E5's included) are `CurrentLimit`s, 0 when they are `ApparentPowerLimit`s or there are none. Both kinds in one
  case raise, and so do both on one device. A `CurrentLimit` is written as RATEn = kA × √3 × the device's BaseVoltage
  in kV (new `derived.rating_from_ka`, the inverse of `ka_from_rating`). `ExportContext` gains
  `branch_ratings_in_current`, read by the case record and the rated modules.

### Tests (E1)

`tests/test_cim_to_raw.py`: the round trip over every fixture with the E1 modules added (Branch, System switching
device, Multi-section line compared by key and slot, RATE1..RATE12 value by value at rel 1e-9), and:
- the switches atom's NXFRAT 1 comes back;
- the mixed-base atom's `&1` comes back whole, its capacitor grouped (`AdditionalGroupedEquipment`); a grouped
  section at the end of the path (the multi-section atom's 1-2 moved to the grouped list); a Line made a loop (that
  atom's `&1` with its parallel 1-4 `2` added) writes no record;
- `keyed_ids`: a keyed ID, a reversed pair, a fallback, an ID too long for the field, two devices with one key;
- raises: a NAME of 41 characters, a `gch`, a line shunt out of service with its line in, a switch on one
  `ConnectivityNode`, ratings in MVA and in current in one case;
- the written WECC240, mixed-base and switches models read back with the same records;
- core (`test_getters_bus_branch_units.py`, an inline atom with hand numbers): `get_limits_by_type`,
  `get_shunt_admittance`, and `get_series_compensator` in pu.

### Expected differences (E1)

- **MET / METERED 2 off a tie comes back 1** (RAW-22): computed in the test from the RAW as read (a device whose
  buses share an AREA, `_metered_off_a_tie`): WECC240 74 of its 81 MET 2, IEEE118 77 of 83, one branch in each of the
  areas, FACTS/VSC, two-terminal and line-shunt atoms, and the switches atom's disconnector. The ties' MET comes back.
- The mixed-base atom's series capacitor LEN 1.0 comes back 0 (R1b-2 listed it on the row).
- A system switching device's X other than 0.0001 comes back 0.0001 (untranscribed; one a local case; none in the
  committed fixtures).
- The two-bus node-breaker atom's NXFRAT 1 comes back 0: nothing in it is rated, so the flag says nothing.
- Owners and the multi-section line's MET: unset, not compared.

### Results

IEEE14, WECC240, IEEE118 and all 18 atoms: every compared slot of Branch, System switching device and
Multi-section line equals the RAW as read, except the list above, and the E0 tables are as before. The switches
atom's NXFRAT 1 now comes back. The written WECC240, mixed-base and switches models read back unchanged.

**Local case set** (29 v34 cases of one network, never committed; 3 run, counts only): every branch (about 14450 a
case), system switching device (6 or 7) and multi-section line (35 of 35, their 44 grouped capacitor sections
included) comes back keyed as on import, each case in about 70 s. Per case the E1 differences are: MET 2 off a tie
(about 6150), the one series capacitor's LEN, and one switch's X ≠ 0.0001. The bus table shows only E0's: untraced
AREA (about 179) and IDE 4 → 1 (615 to 827, all IDE 4).

### Slots (generated from `SLOTS`)

#### BranchRecord

| RAW slot | kind | from / why |
|---|---|---|
| from_bus_number | written | I: terminal 1's busNumber |
| to_bus_number | written | J: terminal 2's busNumber |
| r | written | R: get_line_sequence_impedance / get_series_compensator r (pu) |
| x | written | X: get_line_sequence_impedance / get_series_compensator x (pu) |
| circuit | written | CKT: the ln_ / sc_<I>_<J>_<CKT> key, else the next free (X2) |
| b | written | B: get_line_sequence_impedance b (pu); blank for a series capacitor |
| name | written | NAME: name; blank when it is the key I_J_CKT |
| ratings | written | RATE1..RATE12: the olt_rate<n> limits (ratings.device_ratings) |
| g_from | written | GI: the line shunt cap_<key>_i (mRID key, E1-2): get_shunt_admittance g (pu) |
| b_from | written | BI: the line shunt cap_<key>_i (mRID key, E1-2): get_shunt_admittance b (pu) |
| g_to | written | GJ: the line shunt cap_<key>_j (mRID key, E1-2): get_shunt_admittance g (pu) |
| b_to | written | BJ: the line shunt cap_<key>_j (mRID key, E1-2): get_shunt_admittance b (pu) |
| status | rule | ST: 0 when inService is false, else 1 |
| metered_end | written | MET: on a tie, the terminal holding its TieFlow pair (R5); else blank (RAW-22) |
| length | written | LEN: ACLineSegment.length (km); blank for a series capacitor (R1b-2) |
| o1 | unset | ownership is an asset concept (CIM 18 gap) |
| f1 | unset | ownership is an asset concept (CIM 18 gap) |
| o2 | unset | ownership is an asset concept (CIM 18 gap) |
| f2 | unset | ownership is an asset concept (CIM 18 gap) |
| o3 | unset | ownership is an asset concept (CIM 18 gap) |
| f3 | unset | ownership is an asset concept (CIM 18 gap) |
| o4 | unset | ownership is an asset concept (CIM 18 gap) |
| f4 | unset | ownership is an asset concept (CIM 18 gap) |

#### SwitchRecord

| RAW slot | kind | from / why |
|---|---|---|
| from_bus_number | written | I: terminal 1's busNumber |
| to_bus_number | written | J: terminal 2's busNumber |
| circuit | written | CKT: the sw_<I>_<J>_<CKT> key, else the next free (X2) |
| x | rule | X 0.0001: a Switch has no impedance, and the format gives X no default |
| ratings | written | RATE1..RATE12: the olt_rate<n> limits (ratings.device_ratings) |
| status | written | STATUS: get_switch_state actual, open 0 |
| nstat | written | NSTATUS: get_switch_state normal, open 0 |
| metered_end | rule | METERED: on a tie, the terminal holding its TieFlow pair (R5); else 1 (no default in the format; RAW-22) |
| stype | written | STYPE by class: Switch 1, Breaker 2, Disconnector 3 |
| name | written | NAME: name; blank when it is the key I_J_CKT |

#### MultiSectionLineRecord

| RAW slot | kind | from / why |
|---|---|---|
| i | written | I: the path's first bus (by the msl_<I>_<J>_<ID> key, else the lower end) |
| j | written | J: the path's last bus |
| dum1 | written | DUM1: the path's first dummy bus |
| line_id | written | ID: the msl_<I>_<J>_<ID> key, else the next free &1, &2, ... (X2) |
| met | unset | MET: the loss-allocation end has no CIM home (CIM 18 gap, RAW-22) |
| dum2 | written | the path's next dummy bus, blank past its end |
| dum3 | written | the path's next dummy bus, blank past its end |
| dum4 | written | the path's next dummy bus, blank past its end |
| dum5 | written | the path's next dummy bus, blank past its end |
| dum6 | written | the path's next dummy bus, blank past its end |
| dum7 | written | the path's next dummy bus, blank past its end |
| dum8 | written | the path's next dummy bus, blank past its end |
| dum9 | written | the path's next dummy bus, blank past its end |

## E2: load, fixed shunt, switched shunt (spec approved 2026-11-09: E2-1 bus's Region, E2-2 SWREG I; done 2026-11-09)

Modules: `load.py` (`ConformLoad`, `NonConformLoad`, `EnergyConsumer` → Load), `fixed_shunt.py` and
`switched_shunt.py` (`LinearShuntCompensator` → Fixed shunt or Switched shunt, split by control). `EXPORT_ORDER`
gains them after `multi_section_line`. Import spec: `CIMTBL_MAPPING.md#load-r2`, `#fixed-shunt-r2`,
`#switched-shunt-r2`, R2b. A `NonlinearShuntCompensator` has no module, so `to_model` raises on it (the import never
writes one).

### Which shunt is which

Every `LinearShuntCompensator` goes to exactly one record:
1. a line shunt of an exported branch (`branch.line_shunts`, E1-2): the branch's GI/BI/GJ/BJ;
2. one with a `RegulatingControl`: a block of the Switched shunt of that control;
3. any other: a Fixed shunt.

**Per unit on the bus base.** RAW's GL, BL and Bi are MW / Mvar at 1 pu of the bus's BASKV. The pu admittance of
`get_shunt_admittance(..., "pu", base_power=...)` is on the shunt's `nomU`, so a shunt whose `nomU` differs from its
BaseVoltage raises (the importer writes `nomU` = BASKV; a shunt rated off its bus voltage waits for a consumer).
The same check now guards E1's line shunts (E1's text said "on the shunt's BaseVoltage": it is `nomU`). MW / Mvar =
pu × SBASE through a new `derived.mva_from_per_unit`, the inverse of `per_unit_from_mva`.

### Load

| RAW | from |
|---|---|
| I, ID | the terminal's bus; ID from the mRID `ld_<I>_<ID>`, else the next free `1`, `2`, ... on the bus (X2) |
| STATUS | `get_in_service(which="actual")`: 1 when true or unset, 0 when false |
| AREA | the load's group: `LoadGroup` → `SubLoadArea` → `LoadArea` → `ControlArea` → its number. No group: blank (PSS/E: the bus's). A group whose chain breaks raises |
| ZONE | its bus's substation `Region` (E2-1), as the bus's ZONE |
| PL, IP, YP | p × the p fractions: `get_phase_loads(load, "MW", "MVAr").total` and `get_load_response` (constant power, current, impedance) |
| QL, IQ, YQ | q × the q fractions; YQ = −(q × the impedance fraction), RAW's sign (import RAW-8) |
| SCALE | by class: `ConformLoad` 1, `NonConformLoad` 0, a plain `EnergyConsumer` blank (PSS/E: 1) |
| OWNER, INTRPT, DGENP, DGENQ, DGENM | unset (no CIM home) |

An exponent response (`exponentModel` true) raises: a v34 load is ZIP only. A load without a `LoadResponse` raises
(the getter's rule). A zero side comes back 0, 0, 0 whatever its fractions.

### Fixed shunt

| RAW | from |
|---|---|
| I, ID | the terminal's bus; ID from the mRID `cap_<I>_<ID>`, else the next free (X2) |
| STATUS | `get_in_service(which="actual")`, as a load's |
| GL, BL | `get_shunt_admittance(shunt, "pu", sections="actual")` × SBASE |

### Switched shunt

**One record per `RegulatingControl`** over the shunts that name it; they must sit on one bus (else it raises), and
two records on one bus raise (a v34 switched shunt's key is its bus).

| RAW | from |
|---|---|
| I | the blocks' bus |
| N1, B1 .. N8, B8 | one block per shunt, in the order of the mRID `swsh_<I>_b<k>`; otherwise reactors first, then capacitors, each by mRID. Ni = maximumSections; Bi = `get_shunt_admittance(block, "pu", sections="maximum")`'s b per section × SBASE. More than 8 blocks raise; a block with g ≠ 0 raises (RAW has no G here) |
| BINIT | Σ over the blocks of sections × Bi (`sections="actual"`): the import's `block_sections` split, inverted exactly |
| STATUS | the blocks' `inService`, which must agree (else it raises) |
| MODSW | from the control (below) |
| VSWHI, VSWLO | from the control's target and deadband (below) |
| SWREG | the busNumber of the control's terminal (decision E2-2); MODSW 6: unset |
| RMIDNT | MODSW 6: the name of the FACTS device at the control's terminal; else unset |
| NREG | unset in E2: a terminal on a node of a node-breaker block is E5's (node numbers) |
| ADJM, RMPCT | unset (no CIM home) |

**MODSW** (the import's `CONTROL_MODE` inverted):

| control | MODSW |
|---|---|
| mode voltage, locked (`enabled` false, or every block's `controlEnabled` false) | 0 |
| mode voltage, `discrete` true or unset | 1 |
| mode voltage, `discrete` false | 2 |
| mode reactivePower on a `SynchronousMachine` or `PowerElectronicsConnection` terminal, or disabled on any other (R2b-1's no-plant case) | 3 |
| mode reactivePower on a `StaticSynchronousCompensator` terminal | 6 |
| any other mode | raises (MODSW 4 and 5 have no import either) |

Blocks whose `controlEnabled` disagree raise.

**VSWHI, VSWLO** from `get_regulating_control` (target ± deadband / 2; an unset deadband is 0):
- mode voltage: in kV, as pu of the regulated bus's BASKV (`per_unit_from_kv`).
- MODSW 3: the band low..high in Mvar under the output sign (−target ∓ deadband / 2) as fractions of the machine's
  QB..QT, its `minQ`..`maxQ` (generation sign as stored): VSWLO = (low − QB) / (QT − QB). A new
  `derived.band_fractions`, the inverse of `reactive_band`. QT = QB raises, and so does a target on equipment that is
  no machine. *Amended at implementation:* the draft named `get_machine_rating` / `get_inverter_rating`, but both
  require `ratedU`, which the RAW import does not write (a RAW machine has no rated kV), so the two limits are read
  with `get_qty`. *Undone by E3-1:* the importer now writes ratedU = BASKV, and QT..QB are read through
  `get_machine_rating` / `get_inverter_rating`.
- MODSW 6: the same over −SHMX..SHMX, SHMX = `rating_from_ka(ratedI, BASKV)` of the FACTS device.
- A disabled control with no target (R2b-1's no-plant case): blank (PSS/E: 1.0, 1.0).

### Decisions

- **E2-1. A load's ZONE: the bus's substation `Region`** (user 2026-11-09), as the import spec planned. A
  `SubLoadArea` is one (area, zone) pair with no link to a zone. `EnergyArea` holds only `ControlArea`. The new
  `ConnectedArea` has no link to a zone or a `ControlArea`, and a zone `ConnectedArea` would duplicate each zone's
  `SubGeographicalRegion`. A load whose ZONE differs from its bus's comes back as the bus's (none in the committed
  cases; the loads atom 1; 2505 to 5090 a local case). This goes to the IEC committee with the rest of the
  `ControlArea` family's gaps (plan §6a). A bus's AREA from a `transmissionArea` `ConnectedArea` is a later slice
  (plan §9.1).
- **E2-2. SWREG of a shunt regulating its own bus: I, always** (user 2026-11-09): the busNumber of the control's
  terminal. RAW writes 0 or I for the same meaning, and CIM keeps neither. WECC240's 7 and the local set's (about
  1100 a case, none 0) come back; IEEE118's 13 and 4 atom shunts' 0 come back I.

### Tests (E2)

`tests/test_cim_to_raw.py`: the round trip with the E2 modules added, and:
- the loads atom (a ZIP mix, SCALE 0 and blank, an area and zone off the bus's, blank AREA/ZONE), the fixed-shunts
  atom (GL ≠ 0, a reactor out of service), the switched-shunts atom (reactor + capacitor blocks with remote
  regulation, MODSW 2 with 2.5 steps, a locked shunt), the plant-and-facts atom (MODSW 3 with and without a plant,
  MODSW 6);
- the line-shunts atom's shunts stay on their branches (no Fixed shunt);
- raises: a `NonlinearShuntCompensator`, an exponent load, a shunt with `nomU` off its BaseVoltage, blocks of one
  control on two buses, two controls on one bus, more blocks than the record holds, a block with g ≠ 0, blocks in
  and out of service;
- the written loads, switched-shunts and plant-and-facts models read back with the same records;
- `derived`: `mva_from_per_unit`, `band_fractions` against `reactive_band`.

### Expected differences (E2)

- PL..YQ of a mixed load can differ in the last digit (p × fraction; rel 1e-9).
- VSWHI/VSWLO in the last digit (the import's float residue).
- A blank load AREA or ZONE comes back filled: AREA its group's (the importer gives every load one), ZONE its
  bus's, the same meaning (the loads atom's `3 1`).
- A load ZONE off its bus's comes back as the bus's (E2-1): the loads atom's `2 A`.
- SWREG 0 comes back I (E2-2), computed in the test (`_own_bus_swreg`; MODSW 6 keeps its blank): IEEE118 13, the
  switched-shunts atom 2, the plant-and-facts atom 1 (no plant), the node-breaker forms atom 1.
- ADJM and RMPCT are unset, not compared: ADJM 1 (the switched-shunts atom 1, 115 a local case) and RMPCT ≠ 100
  (46 a local case) come back as the defaults 0 and 100.
- The no-plant MODSW 3 shunt's VSWLO 0 comes back 1.0 (R2b-1 listed it).
- NREG is unset until E5, not compared: the node-breaker forms atom's 11 comes back blank.
- OWNER, INTRPT, DGEN* of a load: unset, not compared.

### Results

IEEE14, WECC240, IEEE118 and all 18 atoms: every compared slot of Load, Fixed shunt and Switched shunt equals the RAW
as read, except the list above; the E0 and E1 tables are as before. The written loads, switched-shunts and
plant-and-facts models read back unchanged.

**Local case set** (29 v34 cases of one network, never committed; 3 run, counts only): every load (6980 to 9566 a
case, 755 SCALE 0), fixed shunt (806 to 811) and switched shunt (1387 to 1389: MODSW 0, 1, 2, 3 and 6, up to 8
blocks) comes back keyed as on import, each case in about 72 s. Every PL..YQ, GL, BL, Ni, Bi, BINIT, MODSW, VSWHI,
VSWLO and RMIDNT matches at rel 1e-9. Per case the E2 differences are only: load ZONE off its bus's (E2-1: 2505,
5055, 5090, each exactly the case's count of such loads), SWREG 0 → I where present, and in one case the no-plant
MODSW 3 shunt's VSWLO (R2b-1). The E0 and E1 differences are unchanged.

### Slots (generated from `SLOTS`)

#### LoadRecord

| RAW slot | kind | from / why |
|---|---|---|
| bus_number | written | I: the terminal's busNumber |
| load_id | written | ID: the ld_<I>_<ID> key, else the next free (X2) |
| status | rule | STATUS: 0 when inService is false, else 1 |
| area | written | AREA: LoadGroup -> SubLoadArea -> LoadArea -> ControlArea; blank without a group |
| zone | written | ZONE: its bus's (E2-1; a SubLoadArea has no link to a zone, CIM 18 gap) |
| constant_real_power | written | PL: p (get_phase_loads total, MW) x the constant power fraction (get_load_response) |
| constant_imag_power | written | QL: q (get_phase_loads total, Mvar) x the constant power fraction (get_load_response) |
| constant_current_real_power | written | IP: p (get_phase_loads total, MW) x the constant current fraction (get_load_response) |
| constant_current_imag_power | written | IQ: q (get_phase_loads total, Mvar) x the constant current fraction (get_load_response) |
| constant_admittance_real_power | written | YP: p (get_phase_loads total, MW) x the constant impedance fraction (get_load_response) |
| constant_admittance_imag_power | written | YQ: -(q (get_phase_loads total, Mvar) x the constant impedance fraction (get_load_response)), RAW's sign |
| owner | unset | ownership is an asset concept (CIM 18 gap) |
| scale | written | SCALE by class: ConformLoad 1, NonConformLoad 0, EnergyConsumer blank |
| interruptible | unset | no CIM home |
| dgenp | unset | no CIM home |
| dgenq | unset | no CIM home |
| dgenf | unset | no CIM home |

#### FixedShuntRecord

| RAW slot | kind | from / why |
|---|---|---|
| bus_number | written | I: the terminal's busNumber |
| shunt_id | written | ID: the cap_<I>_<ID> key, else the next free (X2) |
| status | rule | STATUS: 0 when inService is false, else 1 |
| gl | written | GL (MW at 1 pu): get_shunt_admittance g of the sections in service (pu on the bus base) x SBASE |
| bl | written | BL (Mvar at 1 pu): get_shunt_admittance b of the sections in service (pu on the bus base) x SBASE |

#### SwitchedShuntRecord

| RAW slot | kind | from / why |
|---|---|---|
| bus_number | written | I: the blocks' busNumber (a v34 switched shunt's key) |
| modsw | written | MODSW from the control: voltage 0 locked, 1 discrete, 2 continuous; reactivePower 3 on a machine (or disabled elsewhere), 6 on a FACTS device |
| adjm | unset | ADJM: the switching-order method has no CIM home |
| status | rule | ST: 0 when the blocks' inService is false, else 1 |
| vswhi | written | VSWHI: the band's top from get_regulating_control target +- deadband / 2: voltage in kV over the regulated bus's BASKV; MODSW 3 and 6 as fractions of the machine's minQ..maxQ or the FACTS device's -SHMX..SHMX (band_fractions); blank for a disabled control with no target |
| vswlo | written | VSWLO: the band's bottom from get_regulating_control target +- deadband / 2: voltage in kV over the regulated bus's BASKV; MODSW 3 and 6 as fractions of the machine's minQ..maxQ or the FACTS device's -SHMX..SHMX (band_fractions); blank for a disabled control with no target |
| swreg | written | SWREG: the busNumber of the control's terminal, its own bus included (E2-2); blank for MODSW 6 |
| rmpct | unset | RMPCT: a shunt's participation share has no CIM home (CIM 18 gap) |
| rmidnt | written | RMIDNT: MODSW 6: the name of the FACTS device at the control's terminal |
| binit | written | BINIT: the sum over the blocks of get_shunt_admittance b of the sections in service (pu on the bus base) x SBASE |
| n1 | written | Ni / Bi: block i, maximumSections and get_shunt_admittance b per section (pu on the bus base) x SBASE; in the swsh_<I>_b<i> order, else reactors first, each by mRID |
| b1 | written | Ni / Bi: block i, maximumSections and get_shunt_admittance b per section (pu on the bus base) x SBASE; in the swsh_<I>_b<i> order, else reactors first, each by mRID |
| n2 | written | Ni / Bi: block i, maximumSections and get_shunt_admittance b per section (pu on the bus base) x SBASE; in the swsh_<I>_b<i> order, else reactors first, each by mRID |
| b2 | written | Ni / Bi: block i, maximumSections and get_shunt_admittance b per section (pu on the bus base) x SBASE; in the swsh_<I>_b<i> order, else reactors first, each by mRID |
| n3 | written | Ni / Bi: block i, maximumSections and get_shunt_admittance b per section (pu on the bus base) x SBASE; in the swsh_<I>_b<i> order, else reactors first, each by mRID |
| b3 | written | Ni / Bi: block i, maximumSections and get_shunt_admittance b per section (pu on the bus base) x SBASE; in the swsh_<I>_b<i> order, else reactors first, each by mRID |
| n4 | written | Ni / Bi: block i, maximumSections and get_shunt_admittance b per section (pu on the bus base) x SBASE; in the swsh_<I>_b<i> order, else reactors first, each by mRID |
| b4 | written | Ni / Bi: block i, maximumSections and get_shunt_admittance b per section (pu on the bus base) x SBASE; in the swsh_<I>_b<i> order, else reactors first, each by mRID |
| n5 | written | Ni / Bi: block i, maximumSections and get_shunt_admittance b per section (pu on the bus base) x SBASE; in the swsh_<I>_b<i> order, else reactors first, each by mRID |
| b5 | written | Ni / Bi: block i, maximumSections and get_shunt_admittance b per section (pu on the bus base) x SBASE; in the swsh_<I>_b<i> order, else reactors first, each by mRID |
| n6 | written | Ni / Bi: block i, maximumSections and get_shunt_admittance b per section (pu on the bus base) x SBASE; in the swsh_<I>_b<i> order, else reactors first, each by mRID |
| b6 | written | Ni / Bi: block i, maximumSections and get_shunt_admittance b per section (pu on the bus base) x SBASE; in the swsh_<I>_b<i> order, else reactors first, each by mRID |
| n7 | written | Ni / Bi: block i, maximumSections and get_shunt_admittance b per section (pu on the bus base) x SBASE; in the swsh_<I>_b<i> order, else reactors first, each by mRID |
| b7 | written | Ni / Bi: block i, maximumSections and get_shunt_admittance b per section (pu on the bus base) x SBASE; in the swsh_<I>_b<i> order, else reactors first, each by mRID |
| n8 | written | Ni / Bi: block i, maximumSections and get_shunt_admittance b per section (pu on the bus base) x SBASE; in the swsh_<I>_b<i> order, else reactors first, each by mRID |
| b8 | written | Ni / Bi: block i, maximumSections and get_shunt_admittance b per section (pu on the bus base) x SBASE; in the swsh_<I>_b<i> order, else reactors first, each by mRID |
| nreg | unset | NREG: a node of a node-breaker block, written by E5 |

## E3: generator (spec approved 2026-11-09: E3-1 ratedU = BASKV, E3-2 the getter reads a star x, E3-3 a fixed tap's increment None, E3-4 IREG I; E3-5 at implementation, reversed P limits as stored; done 2026-11-09)

Module: `generator.py` (`SynchronousMachine`, `PowerElectronicsConnection` → Generator). `EXPORT_ORDER` gains it
after `switched_shunt`. Import spec: `CIMTBL_MAPPING.md#generator-r3`, R3b (step-ups), R3c (WMOD 2, 3), R6 (NREG).
`PowerTransformer` stays E4's class: E3 exposes `step_ups(context)` (step-up → machine), which E4 leaves out, as E1's
`branch.line_shunts` is for E2.

### Machines, plants and keys

| RAW | from |
|---|---|
| I, ID | the machine's bus: its terminal's node, or for a machine behind a step-up the node across it (`raw_bus`); ID from the mRID `sm_<I>_<ID>` / `pec_<I>_<ID>`, else the next free (X2) |
| PG, QG | `get_der_output(machine, "MW", "MVAr", sign="generation").total` |
| QT, QB | `get_machine_rating` / `get_inverter_rating(..., sign="generation")` max_q, min_q; unset: blank (PSS/E: ±9999) |
| MBASE | their rated_s (MVA) |
| PT, PB | **`get_unit_limits(unit, "MW", sign="generation")`** (new, `getters/der.py`): a `GeneratingUnit`'s `maxOperatingP`/`minOperatingP` or a `PowerElectronicsUnit`'s `maxP`/`minP`, as `(min, max)`, as stored even when the minimum is above the maximum (E3-5); the unit is the machine's `GeneratingUnit` or the connection's one unit (`get_inverter_unit`); none: blank |
| ZR | a `SynchronousMachine`: `get_machine_impedance(machine, "pu").r`, on its ratedU and ratedS (BASKV, MBASE; E3-1); a connection: blank (R3c-3 listed it; X1) |
| ZX | untranscribed (no machine reactance in cim18v17, UPSTREAM U13) |
| RT, XT, GTAP | the step-up, below; without one: 0, 0, blank (R3b-4's listed GTAP is lost, X1) |
| STAT | `get_in_service(which="actual")`: 1 when true or unset, 0 when false |
| RMPCT | the `qPercent` of the plant's `SynchronousMachine`s (`get_machine_rating`), on every record of the plant, so a connection beside machines gets it back; a plant of connections only: blank (R3c-3, X1). *Refined at implementation:* the draft blanked every connection's |
| WMOD | `SynchronousMachine` 0; `PowerElectronicsConnection` 3 when its control is mode `powerFactor`, else 1 (WMOD 2 comes back 1, X1) |
| WPF | WMOD 3: the control's targetValue (signed, R3c-2); else blank |
| IREG | the busNumber of `raw_bus` of the control's terminal node, its own bus included (E3-4, as E2-2); blank without a control and for WMOD 3 |
| VS | mode `voltage`: `get_regulating_control(control, "kV")` target as pu of the regulated bus's BASKV (`per_unit_from_kv`); blank for WMOD 3 and without a control |
| NREG | unset in E3: E5's (node numbers), as the switched shunt's |
| O1..O4, F1..F4 | unset (no CIM home) |

**A plant** is the machines whose bus is I. As on import, IREG, VS and RMPCT are plant quantities: machines of one
plant that disagree on them raise. A control in any mode but `voltage` and `powerFactor` raises, and so does a
`powerFactor` control on a `SynchronousMachine` (the import writes none). The bus's IDE (E0) is unchanged.

### The step-up folded back (R3b inverted)

A machine whose terminal node has no busNumber sits behind a step-up. The node must hold only the machine and one
2-winding `PowerTransformer` whose other end is on a numbered bus; anything else raises (two machines behind one
step-up, a third terminal, a converter). The transformer must be in service (RAW gives it no status) and have no
core admittance. With `model = get_transformer_model(step_up, "pu", base_power=machine.ratedS)` and winding 1 the
end on bus I (else it raises):
- RT = r₁ + r₂, XT = the mesh (1, 2) x (pu on MBASE). Both ends' ratedU must equal their nodes' BaseVoltage (R3b-2's
  per-unit form; another raises until a consumer has one).
- GTAP = neutralU / ratedU₁ of the fixed `RatioTapChanger` on end 1 (`get_tap_steps`, E3-3); 1 without a tap; a tap
  that moves (lowStep ≠ highStep) or a tap on end 2 raises.

### Decisions

- **E3-1. A RAW machine's `ratedU`: the importer writes BASKV(I)** (user 2026-11-09) on every `SynchronousMachine`
  and `PowerElectronicsConnection`, amending R3 (`CIMTBL_MAPPING.md#generator-r3`). `get_machine_rating`,
  `get_inverter_rating` and `get_machine_impedance("pu")` require it, and RAW has no machine kV. R3b-2 already puts
  the machine at bus I's base, and the step-up's ends carry ratedU = BASKV. ZR comes back through the getter (pu on
  BASKV, MBASE), and E2's switched shunt reads QT/QB through `get_machine_rating` / `get_inverter_rating` again (its
  `get_qty` amendment is undone). The IEEE14 generator golden gains the column. Not chosen: an optional `ratedU` in
  the getters (a core contract change for DSS, GDM, GLM), or RAW reading `get_qty` beside the getters.
- **E3-2. A star impedance on a `PowerTransformerEnd`: the getter reads it** (user 2026-11-09).
  `get_transformer_model` refused `PowerTransformerEnd.x` (G6b), but the RAW import writes every 2-winding unit's
  r, x on end 1, step-ups (R3b-1) and transformer records (R4) alike, as the core shape `behind_transformer` and
  CGMES do. Now, with no mesh impedance, the ends' x add by pair: (i, j) x = xᵢ + xⱼ (an unset end x is 0), each on
  its own end's base moved to the model's; the mesh r is None, since r is per winding either way. A unit with both
  an end x and a mesh impedance raises. E4 reads every RAW transformer this way. Not chosen: the importer writing a
  `TransformerMeshImpedance`.
- **E3-3. A fixed tap's increment: None** (user 2026-11-09). `get_tap_steps` and `get_tap_ratio` require
  `stepVoltageIncrement` except on a fixed tap (lowStep = highStep, R4b-4), which has no step to increment; its ratio
  at its one position is 1 (its voltage is its neutralU). E4's fixed taps read the same.
- **E3-4. IREG of a plant regulating its own bus: I, always** (approved with the spec), as E2-2's SWREG. RAW writes
  0 or I for the same meaning. The local set writes I (about 2400 a case, none 0); 20 atom generators' 0 come back
  I (WMOD 3's excepted).
- **E3-5. P limits reversed: as stored** (user 2026-11-09, found at implementation). One local case has 2 WMOD 0
  records out of service with PB above PT. The import copies them, and the draft's `get_unit_limits` raised through
  the shared order check (`der._limits`: a minimum above its maximum is a producer that wrote the load sign).
  `get_unit_limits` now returns a unit's active power limits as stored; the reactive limits keep the check. Not
  chosen: raising in the exporter (that case could not be exported) or at import.

### Tests (E3)

`tests/test_cim_to_raw.py`: the round trip with E3 added, and:
- the generators atom (a machine and a connection in one plant, a remote IREG, a machine out of service, blank
  MBASE/QT/PT, a plant on an IDE 1 bus), the renewables atom (WMOD 2 and 3, a connection with ZR and RMPCT listed),
  the step-up atom (GTAP 1 and 1.025, RT only, a WMOD 1 connection behind one, a plant of three, GTAP without a
  step-up), the plant-and-facts atom (a WMOD 1 plant of a MODSW 3 shunt);
- `step_ups(context)` holds exactly the 4 step-ups of the step-up atom;
- raises: plant members that disagree on (IREG, VS), a mode `reactivePower` plant control, two machines behind one
  step-up, a step-up out of service, a step-up tap that moves, a step-up end rated off its node's BaseVoltage;
- reversed PT/PB come back as written (E3-5);
- the written generators, renewables and step-up models read back with the same records;
- core (`cimhub_core/tests`): `get_unit_limits`, the star impedance (2 and 3 windings, star + mesh raises), the
  fixed tap, against hand numbers.

### Expected differences (E3)

- IREG 0 comes back I (E3-4), computed in the test (`_own_bus_ireg`, as `_own_bus_swreg`): 20 atom generators; none
  in IEEE14, IEEE118, WECC240 or the local set.
- A blank MBASE comes back SBASE, the same meaning (the generators atom's `5 1`).
- WMOD 2 comes back 1 (R3c-1, X1): the renewables atom's `2 W` (with its WPF, and its RMPCT: a plant of one
  connection) and `4 W1` (WPF 1.0 already).
- WMOD 3's listed IREG and VS are not written (R3c-2): the renewables atom's `5 S`.
- A connection's ZR comes back blank (R3c-3, X1): the renewables atom's `6 S2`.
- A WMOD 1 record's WPF other than 1 comes back blank: PSS/E uses WPF only for WMOD 2 and 3, and the import carries
  it nowhere (R3c, "unused otherwise"). None in the committed cases; 18 a local case.
- GTAP without a step-up comes back blank (R3b-4, X1): the step-up atom's `2 G2`.
- NREG is unset until E5, not compared: the node-breaker forms atom's 2.
- RT, XT, GTAP of a step-up and ZR, VS: rel 1e-9 (per unit → ohm, V → per unit).
- ZX, O1..O4, F1..F4: unset, not compared.

### Results

IEEE14, WECC240, IEEE118 and all 18 atoms: every compared Generator slot equals the RAW as read, except the list
above; the E0, E1 and E2 tables are as before. The written generators, renewables and step-up models read back
unchanged. The 4 step-ups of the step-up atom (GTAP 1 and 1.025, RT only, a connection behind one) come back RT, XT,
GTAP at rel 1e-9. IEEE14's `to_model` now names only its 3 `PowerTransformer`s as not yet exported (E4).

**Local case set** (29 v34 cases of one network, never committed; 3 run, counts only): every generator (2997 to
2998 a case: WMOD 0, 1, 2 and 3, plants of up to 8, 213 step-ups with 8 fixed taps) comes back keyed as on import,
each case in about 70 s. Every PG, QG, QT, QB, MBASE, PT, PB, ZR (machines), RT, XT, GTAP (step-ups), STAT, IREG,
VS and RMPCT (plants with a machine) matches at rel 1e-9. Per case the E3 differences are only the X1 and R3c ones:
GTAP without a step-up 11, WMOD 2 → 1 24, WPF 39 (WMOD 2's 21, WMOD 1's 18), RMPCT of a connection-only plant 45,
a connection's ZR 73 or 74, and WMOD 3's listed IREG 26 and VS 12. No IREG 0 in the set. The E0, E1 and E2
differences are unchanged.

### Slots (generated from `SLOTS`)

#### GeneratorRecord

| RAW slot | kind | from / why |
|---|---|---|
| bus_number | written | I: the busNumber of the machine's node, or of the bus across its step-up (raw_bus) |
| gen_id | written | ID: the sm_<I>_<ID> / pec_<I>_<ID> key, else the next free (X2) |
| p_output | written | PG: get_der_output(sign='generation').total p (MW) |
| q_output | written | QG: get_der_output(sign='generation').total q (Mvar) |
| max_q_output | written | QT: get_machine_rating / get_inverter_rating(sign='generation').max_q (Mvar) |
| min_q_output | written | QB: get_machine_rating / get_inverter_rating(sign='generation').min_q (Mvar) |
| regulated_voltage_setpoint | written | VS: a voltage control's get_regulating_control target as pu of the regulated bus's BASKV; blank for WMOD 3; a plant quantity: the machines at bus I must agree, else it raises |
| regulated_bus_number | written | IREG: the busNumber of raw_bus of the voltage control's terminal, its own bus included (E3-4); blank for WMOD 3; a plant quantity: the machines at bus I must agree, else it raises |
| rated_mva | written | MBASE: the rating's rated_s (MVA) |
| zr | written | ZR: a SynchronousMachine's get_machine_impedance('pu').r, on its ratedU and ratedS (BASKV, MBASE; E3-1); a connection's has no CIM home (R3c-3) |
| zx | unset | ZX: cim18v17 has no positive-sequence machine reactance (UPSTREAM U13) |
| rt | written | RT: the step-up's winding r summed, pu on MBASE (get_transformer_model); 0 without one |
| xt | written | XT: the step-up's mesh (1, 2) x, pu on MBASE (get_transformer_model); 0 without one |
| gtap | written | GTAP: neutralU / ratedU1 of the step-up's fixed tap (get_tap_steps), 1 without a tap; blank without a step-up (R3b-4's GTAP has no CIM home) |
| status | rule | STAT: 0 when inService is false, else 1 |
| rmpct | written | RMPCT: the qPercent of the plant's SynchronousMachines (get_machine_rating), on every record of the plant; a plant of connections only has no CIM home (R3c-3); a plant quantity: the machines at bus I must agree, else it raises |
| max_p_output | written | PT: get_unit_limits(sign='generation').max_p of the GeneratingUnit or the connection's PowerElectronicsUnit (MW) |
| min_p_output | written | PB: get_unit_limits(sign='generation').min_p (MW) |
| o1 | unset | ownership is an asset concept (CIM 18 gap) |
| f1 | unset | ownership is an asset concept (CIM 18 gap) |
| o2 | unset | ownership is an asset concept (CIM 18 gap) |
| f2 | unset | ownership is an asset concept (CIM 18 gap) |
| o3 | unset | ownership is an asset concept (CIM 18 gap) |
| f3 | unset | ownership is an asset concept (CIM 18 gap) |
| o4 | unset | ownership is an asset concept (CIM 18 gap) |
| f4 | unset | ownership is an asset concept (CIM 18 gap) |
| wmod | written | WMOD: SynchronousMachine 0; PowerElectronicsConnection 3 under a powerFactor control, else 1 (WMOD 2 has no CIM home, R3c-1) |
| wpf | written | WPF: WMOD 3: the powerFactor control's target, as stored (signed, R3c-2); else blank |
| nreg | unset | NREG: a node of a node-breaker bus, written by E5 |

## E4: transformer, impedance correction (spec approved 2026-11-09: E4-1 the getter reads on base_power, E4-2 a zero end holds no core, E4-3 `get_tap_voltage`; done 2026-11-09)

Modules: `transformer.py` (`PowerTransformer` → Transformer) and `impedance_correction.py` (`ImpedanceTapChangerTable`
→ Impedance correction). `EXPORT_ORDER` gains them after `generator`. Import spec: `CIMTBL_MAPPING.md#transformer-r4`,
R4b (the forms R4 raised on), R5 (NMETR on a tie), R6 (NODk), P2-5 (converter transformers). CW = CZ = CM = 1 (plan
§9.1).

### Which transformers

- Every `PowerTransformer` whose ends are all on numbered buses is one record, in the BY_ENDS form with 2 or 3
  windings (`get_transformer_model`); tanks, 1 or 4+ windings raise.
- E3's step-ups (`generator.step_ups`) are left out, as are converter transformers (P2-5: an end on an internal
  node holding an `ACDCConverter`), which are E6's. Any other end on a node without a busNumber raises.

### Keys, status, names

| RAW | from |
|---|---|
| I, J, K | the busNumbers of ends 1, 2, 3 (by `endNumber`); K 0 for a 2-winding unit |
| CKT | from the mRID `xf_<I>_<J>_<K>_<CKT>`, else the next free (X2) |
| NAME | X2; blank when it equals the key `<I>_<J>_<K>_<CKT>` |
| STAT | 0 when inService is false; else 2, 3 or 4 when exactly winding 2, 3 or 1 of a 3-winding unit has its terminal `connected = false` (R4b-6); else 1. Two windings out, or one out of a 2-winding unit, raise |
| VECGRP | `vectorGroup`, blank when unset |
| NMETR | on a tie (R5): the winding whose terminal holds no TieFlow; of two such (a 3-winding unit with two windings in the home area) the lower-numbered. Off a tie: blank (RAW-22, as branch MET) |
| CW, CZ, CM | 1 |
| O1..F4, ZCOD, VMSTAR, ANSTAR | unset (no CIM home; R4) |
| NODk | unset in E4: E5's, as NREG |

### Impedance and magnetizing (X4)

`model = get_transformer_model(unit, "pu", base_power=SBASE, voltage_unit="kV")` gives each value in pu on SBASE
and the winding's `ratedU` (a mesh impedance on its From end's; per-unit values on rated bases are the same seen
from either end). RAW's CZ 1 and CM 1 are on the bus BASKV, so each moves by the voltage only, with new named
derived functions: an impedance × (ratedU / BASKV)², an admittance × (BASKV / ratedU)². This is the importer's
`transformer_ohms` / `magnetizing_siemens` (CZ 1, CM 1) inverted, and it is the identity when NOMV = BASKV.

- R_ij, X_ij for each pair (1-2; 2-3 and 3-1 on a 3-winding unit), seen from winding i as on import (`MESH_PAIRS`:
  1-2 and 3-1 from winding 1, 2-3 from winding 2): R = rᵢ + rⱼ + the mesh r (unset 0), X = the mesh x. This covers
  the importer's two forms, a 2-winding unit's r, x on end 1 (E3-2's star reading) and a 3-winding unit's mesh,
  and a CGMES-style star.
- MAG1, MAG2: `model.core` g, b on winding 1 (RAW's only place), sign kept.
- SBASE1-2: a 2-winding unit's ratedS (MVA; the two ends must agree). A 3-winding unit's SBASE1-2, 2-3, 3-1: SBASE,
  since no end holds a pair base (R4). *Amended at implementation:* the draft left them blank, but RAW's blank is
  SBASE only by a rule the comparison's static defaults cannot hold, so SBASE is written.
- NOMVk: winding k's `ratedU` (kV).

### Taps and control (per winding)

Each winding has at most one controlled tap changer (one with a `TapChangerControl`), and may have a fixed
`RatioTapChanger` beside a phase tap changer (R4b-3).

| RAW | from |
|---|---|
| WINDVk | the winding's `RatioTapChanger` voltage at its `step` (**`get_tap_voltage`**, below) / bus k's BASKV (CW 1); no ratio tap: ratedU / BASKV. *Amended at implementation:* the draft (and R4b-4's note) had 1, which holds only when NOMV = BASKV; the import writes no tap at ratio NOMV, so such a winding is at its ratedU (about 600 local windings a case with NOMV ≠ BASKV) |
| ANGk | −(phaseShift + the phase tap changer's angle at its step): `Winding.phase_shift` (new) plus **`get_phase_tap_steps`** (step − neutral) × increment (R4b-1, -2, -3). A 2-winding unit has only ANG1: −(θ₁ − θ₂), only the difference being physical (R4b-1's UML text) |
| CODk | the controlled tap changer: a `RatioTapChanger` with ltcFlag false 0; ltcFlag true ±1 (voltage) or ±2 (reactivePower); a `PhaseTapChangerLinear` under an activePower control ±3; + when the control is enabled (tap `controlEnabled` must agree). Any other pairing raises; no controlled tap: 0 |
| CONTk | the control's terminal: the winding's own terminal 0; else its node's busNumber (none raises). COD ±3: blank (unused). A negative CONT comes back positive (R4b-8) |
| RMAk, RMIk | ratio: the voltages at highStep and lowStep / BASKV; phase shifter: the larger and smaller PSS/E angle at the end steps; a fixed tap (lowStep = highStep, R4b-4) or none: blank |
| NTPk | highStep − lowStep + 1 of the stepped tap; a fixed tap or none: blank |
| VMAk, VMIk | `get_tap_changer_control` target ± deadband / 2: voltage in kV / the regulated bus's BASKV (CONT 0: the winding's own bus); reactivePower in Mvar; activePower in MW. No control: blank |
| CRk, CXk | `line_drop` r, x (ohm) as pu on SBASE and the regulated bus's BASKV (a new `per_unit_from_ohms`, `ohms_from_per_unit` inverted), when lineDropCompensation is true; else blank |
| CNXAk | blank (0; COD ±5 is not mapped) |
| TABk | the number of the table of the end's `ImpedanceTapChangerTabular` (below); a 3-winding unit's raises (as on import); none: blank |
| RATEk-n | winding k's limits on its own terminal (ratings.py, per terminal); a 2-winding unit's only on winding 1 (a rating on winding 2 raises). XFRRAT (E0's `transformer_ratings_units`) 1 when the transformer ratings are CurrentLimits, each winding's terminal read on its own (`ratings_in_current(per_terminal=True)`) |

Winding 2 of a 2-winding unit has only WINDV2: a fixed `RatioTapChanger` (neutralU / BASKV₂) or none (ratedU / BASKV₂). A tap
that moves, a control, or a phase tap changer on it raises.

### Impedance correction

One record per `ImpedanceTapChangerTable`: I from the mRID `ict_<I>`, else the next free. The points, by T
ascending (PSS/E's order), from **`get_impedance_table`**:
- an angle point: T = −angle (`cim_angle` inverted); a ratio point: T = ratio × ratedU / BASKV of its users' winding
  (users that disagree raise; a ratio table without a user raises, as on import);
- F = 1 + rEnd1 / 100. rEnd1 ≠ xEnd1, a set rEnd2/3 or xEnd2/3, a point with both or neither of ratio and angle, and
  a table mixing them raise. Im F is 0.

### Getter changes (core, on this branch)

- `get_transformer_model`: with a declared `base_power`, an impedance or admittance is read on that power directly
  (`get_qty(power_base=)`), so an end needs no `ratedS` (E4-1); an end whose g and b are zero holds no core (E4-2);
  `Winding.phase_shift` (deg) from `PowerTransformerEnd.phaseShift`.
- **`get_tap_voltage(tap, *, which, voltage_unit)`** (`tap_changer.py`, E4-3): a `RatioTapChanger`'s voltage at a
  position: neutralU + (position − neutralStep) × stepVoltageIncrement / 100 × the end's ratedU; a fixed tap's is
  its neutralU. `get_tap_ratio` keeps its meaning (the ratio about the neutral).
- **`get_phase_tap_steps(tap, angle_unit="deg")`**: a `PhaseTapChangerLinear`'s low, high, neutral, normal, step
  and `stepPhaseShiftIncrement` (all required but normal).
- **`get_impedance_table(table)`**: each point's step, ratio, angle, rEnd1..3, xEnd1..3 (percent).
- `get_limits_by_type(..., terminal=)`: the limits on one terminal (a transformer's are per winding).

### Decisions

- **E4-1. A 3-winding unit's ends have no ratedS** (R4: the pair bases fit no end), and `get_transformer_model`
  required one. **User 2026-11-09:** the getter reads on the declared `base_power` directly, needing only ratedU (the
  ohms and siemens are on the end's ratedU, and the power is the caller's). Not recommended: the importer writing
  ratedS = SBASE on 3-winding ends (a nameplate the case does not give).
- **E4-2. End 2's zeros.** The import writes end 2's r, x, g, b as 0 (R4, CIM's "the secondary end is zero"), and
  the getter counted two ends holding a core. **User 2026-11-09:** an end whose g and b are zero holds no core (zeros on
  several ends are one zero core). Not recommended: the importer leaving end 2 blank (an R4 change; the goldens
  change).
- **E4-3. A tap's voltage when neutralU ≠ ratedU** (R4: the neutral nearest ratio 1, e.g. WECC240 6103-6104).
  `get_tap_ratio` is 1 + (position − neutral) × increment, the ratio about the neutral. **User 2026-11-09:** a new core
  `get_tap_voltage` (above), as CIM defines the increment in percent of the end's ratedU. Not recommended: the
  exporter computing it from `get_tap_steps`.

### Tests (E4)

`tests/test_cim_to_raw.py`: the round trip with E4 added, over every fixture, and:
- the transformers atom (A to E: CW/CZ/CM 2 and 3, a 3-winding unit, COD ±1 and 2, CONT 0, ratings on windings 1
  and 3), the R4b atom (F to T and tables 1 and 2), IEEE14 (NOMV 0, off-nominal WINDV1), WECC240 (122 units with
  ratings), IEEE118;
- the step-up atom's 4 step-ups and the two-terminal atom's 8 converter transformers are left out;
- the R4b atom's L (NOMV1 240 on a 230 kV bus, CZ 1): its end holds the ohms on 240 kV, and X1-2 comes back on 230 kV;
- `to_model` exports IEEE14 whole, and raises on the two-terminal atom's `CsConverter`s (E6);
- raises: an end off a numbered bus that is neither, two windings out, a moving tap on a 2-winding unit's winding 2,
  a control on a phase tap changer in voltage mode, a 3-winding unit's tabular, a table point with rEnd1 ≠ xEnd1;
- the written transformers and R4b models read back with the same records;
- core: each getter change against hand numbers on the core shapes.

### Expected differences (E4)

- CW, CZ, CM 2 or 3 come back 1, with their values in CW/CZ/CM 1 units (the transformers atom's A, B, E; R4).
- NOMV 0 comes back BASKV, the end's ratedU (R4): IEEE14's three units and most atom windings, computed in the test
  (`_nominal_zero`).
- A 3-winding unit's SBASE1-2, 2-3, 3-1 come back SBASE: the transformers atom's E (R4).
- Blank RMA/RMI and VMA/VMI take RAW's defaults that hang on CW and COD (1.1/0.9, R4), which the schema's static
  defaults do not hold: the test fills them (`IMPORT_DEFAULTS`), and they come back written (E).
- A shifter's RMA/RMI with 0° off its grid come back moved by the offset (the R4b atom's K; R4b-3).
- COD 0 RMA/RMI/NTP that no tap holds come back blank (defaults; O; P's were blank; R4b-4).
- A voltage control's extended range comes back as its extended steps' RMA/RMI/NTP (Q; R4b-5).
- A negative CONT comes back positive (S; R4b-8); a COD ±3 CONT comes back blank.
- NMETR off a tie comes back blank (2; RAW-22): none in the committed fixtures; about 2165 a local case.
- WINDV, RMA, RMI, VMA, VMI, R, X, MAG, CR, CX and the table T, F: rel 1e-9.
- ZCOD, VMSTAR, ANSTAR, O1..F4, NODk: unset, not compared.

### Import fix found by the export (R4b-5)

`ratio_tap` extended a range when WINDV sat exactly at RMA or RMI: rounding put the step a hair past NTP or 1, and
`ceil`/`floor` added a step, so the tap came back one step wider (RMA/RMI) with NTP + 1. About 50 local windings a
case. The extension now applies only to a WINDV outside RMI..RMA (R4b-5's rule), and a WINDV at an end is that end's
step. No golden changed; `test_ratio_tap_at_an_end_of_its_range_is_not_extended`.

### Results

All 18 atoms, IEEE14, WECC240 and IEEE118: every compared Transformer and Impedance correction slot equals the RAW
as read, except the list above; the E0 to E3 tables are as before. The transformers and R4b atoms write and read
back unchanged. `to_model` exports IEEE14 whole. Put in CW = CZ = CM = 1 by the importer's own conversions
(`transformer_ohms`, `magnetizing_siemens`, `winding_unit_kv`; a scratch check, not a test), the atoms' CW/CZ/CM 2
and 3 units (A, B, E, N) come back at rel 1e-9.

**Local case set** (29 v34 cases of one network, never committed; 3 run, counts only): every transformer (7391 to
7402 a case, about 680 of them 3-winding, 66 phase shifters, 49 tabulars) and all 32 impedance correction tables
come back keyed as on import, each case in about 80 s. About 40 % of the units have CW, CZ or CM 2 or 3 and so come
back in other units; put in CW = CZ = CM = 1 as above, every R, X, SBASE, MAG, NOMV, WINDV, ANG, COD, VMA, VMI, CR,
CX, TAB, STAT and RATE matches at rel 1e-9. Per case the differences left are only the listed ones: NMETR off a tie
2163 to 2168; COD 0 RMA/RMI/NTP that no tap holds, which come back as defaults (R4b-4: about 650 to 700 windings);
a shifter's RMA/RMI with 0° off its grid 10 (R4b-3); a COD ±3 CONT 18 and a negative CONT 11 (R4b-8); the one
extended voltage-control range (R4b-5). Two defects surfaced and are fixed: WINDV of a winding without a tap (above)
and the import's spurious range extension. The E0 to E3 differences are unchanged.

### Slots (generated from `SLOTS`)

#### TransformerRecord

| RAW slot | kind | from / why |
|---|---|---|
| i | written | I: end 1's busNumber |
| j | written | J: end 2's busNumber |
| k | written | K: end 3's busNumber; 0 for a 2-winding unit |
| circuit | written | CKT: the xf_<I>_<J>_<K>_<CKT> key, else the next free (X2) |
| cw | rule | CW 1: WINDV, RMA, RMI in pu of the bus's BASKV |
| cz | rule | CZ 1: R, X in pu on SBASE and the bus's BASKV |
| cm | rule | CM 1: MAG1, MAG2 in pu on SBASE and bus 1's BASKV |
| mag1 | written | MAG1: get_transformer_model core g, moved to bus 1's BASKV (admittance_on_bus_base) |
| mag2 | written | MAG2: the core b, as MAG1 |
| nmetr | written | NMETR: on a tie, the winding whose terminal holds no TieFlow (the lower of two); off a tie blank (RAW-22) |
| name | written | NAME: X2; blank when it is the key I_J_K_CKT |
| status | rule | STAT: 0 when inService is false; 2, 3, 4 when winding 2, 3, 1 alone is disconnected (R4b-6); else 1 |
| o1 | unset | ownership is an asset concept (CIM 18 gap) |
| f1 | unset | ownership is an asset concept (CIM 18 gap) |
| o2 | unset | ownership is an asset concept (CIM 18 gap) |
| f2 | unset | ownership is an asset concept (CIM 18 gap) |
| o3 | unset | ownership is an asset concept (CIM 18 gap) |
| f3 | unset | ownership is an asset concept (CIM 18 gap) |
| o4 | unset | ownership is an asset concept (CIM 18 gap) |
| f4 | unset | ownership is an asset concept (CIM 18 gap) |
| vecgrp | written | VECGRP: vectorGroup |
| zcod | unset | ZCOD: zero-sequence data is in the sequence file |
| r1_2 | written | R1-2: r1 + r2 + the mesh r, pu on SBASE moved to bus 1's BASKV (impedance_on_bus_base; CZ 1); 2-winding |
| x1_2 | written | X1-2: the mesh (1, 2) x, as R1-2 |
| sbase1_2 | written | SBASE1-2: a 2-winding unit's ratedS (MVA); a 3-winding unit's SBASE, since no end holds a pair base (R4) |
| r2_3 | written | R2-3: r2 + r3 + the mesh r, pu on SBASE moved to bus 2's BASKV (impedance_on_bus_base; CZ 1); 3-winding |
| x2_3 | written | X2-3: the mesh (2, 3) x, as R2-3 |
| sbase2_3 | written | SBASE2-3: a 2-winding unit's ratedS (MVA); a 3-winding unit's SBASE, since no end holds a pair base (R4) |
| r3_1 | written | R1-3: r1 + r3 + the mesh r, pu on SBASE moved to bus 1's BASKV (impedance_on_bus_base; CZ 1); 3-winding |
| x3_1 | written | X1-3: the mesh (1, 3) x, as R1-3 |
| sbase3_1 | written | SBASE1-3: a 2-winding unit's ratedS (MVA); a 3-winding unit's SBASE, since no end holds a pair base (R4) |
| vmstar | unset | VMSTAR: the star point's solved voltage, which the Delta model omits |
| anstar | unset | ANSTAR: as VMSTAR |
| windv1 | written | WINDV1: get_tap_voltage(actual) of the end's RatioTapChanger / bus 1's BASKV (CW 1); without one, ratedU / BASKV (the import writes no tap at ratio NOMV) |
| nomv1 | written | NOMV1: winding 1's ratedU (kV) |
| ang1 | written | ANG1: -(phaseShift + the PhaseTapChangerLinear's (step - neutral) x increment) (raw_angle); a 2-winding unit's ANG1 is winding 1's less winding 2's |
| rate1_1 | written | RATE1-1: the olt_rate1 limit on winding 1's terminal (device_ratings) |
| rate1_2 | written | RATE1-2: the olt_rate2 limit on winding 1's terminal (device_ratings) |
| rate1_3 | written | RATE1-3: the olt_rate3 limit on winding 1's terminal (device_ratings) |
| rate1_4 | written | RATE1-4: the olt_rate4 limit on winding 1's terminal (device_ratings) |
| rate1_5 | written | RATE1-5: the olt_rate5 limit on winding 1's terminal (device_ratings) |
| rate1_6 | written | RATE1-6: the olt_rate6 limit on winding 1's terminal (device_ratings) |
| rate1_7 | written | RATE1-7: the olt_rate7 limit on winding 1's terminal (device_ratings) |
| rate1_8 | written | RATE1-8: the olt_rate8 limit on winding 1's terminal (device_ratings) |
| rate1_9 | written | RATE1-9: the olt_rate9 limit on winding 1's terminal (device_ratings) |
| rate1_10 | written | RATE1-10: the olt_rate10 limit on winding 1's terminal (device_ratings) |
| rate1_11 | written | RATE1-11: the olt_rate11 limit on winding 1's terminal (device_ratings) |
| rate1_12 | written | RATE1-12: the olt_rate12 limit on winding 1's terminal (device_ratings) |
| cod1 | written | COD1: the controlled tap changer: a RatioTapChanger with ltcFlag false 0, else +-1 voltage, +-2 reactivePower; a PhaseTapChangerLinear under activePower +-3; + when the control is enabled |
| cont1 | written | CONT1: the busNumber of the control's terminal; the winding's own 0; blank for COD +-3 |
| rma1 | written | RMA1: the stepped tap's highStep voltage / BASKV, or a shifter's larger end angle (deg); blank for a fixed tap |
| rmi1 | written | RMI1: as RMA1, at lowStep or the smaller end angle |
| vma1 | written | VMA1: the control's target + deadband / 2: pu of the regulated bus's BASKV, Mvar or MW by mode |
| vmi1 | written | VMI1: as VMA1, target - deadband / 2 |
| ntp1 | written | NTP1: highStep - lowStep + 1 of the stepped tap |
| tab1 | written | TAB1: the number of the end's ImpedanceTapChangerTabular's table |
| cr1 | written | CR1: lineDropR as pu on SBASE and the regulated bus's BASKV (per_unit_from_ohms) |
| cx1 | written | CX1: lineDropX, as CR1 |
| cnxa1 | unset | CNXA1: only COD +-5 uses it, which is not mapped |
| nod1 | unset | NOD1: a node of a node-breaker bus, written by E5 |
| windv2 | written | WINDV2: a 2-winding unit's fixed RatioTapChanger neutralU / bus 2's BASKV, ratedU / BASKV without one; a 3-winding unit's as WINDV1 |
| nomv2 | written | NOMV2: winding 2's ratedU (kV) |
| ang2 | written | ANG2: -(phaseShift + the PhaseTapChangerLinear's (step - neutral) x increment) (raw_angle); a 2-winding unit's ANG1 is winding 1's less winding 2's (3-winding only) |
| rate2_1 | written | RATE2-1: the olt_rate1 limit on winding 2's terminal (device_ratings) |
| rate2_2 | written | RATE2-2: the olt_rate2 limit on winding 2's terminal (device_ratings) |
| rate2_3 | written | RATE2-3: the olt_rate3 limit on winding 2's terminal (device_ratings) |
| rate2_4 | written | RATE2-4: the olt_rate4 limit on winding 2's terminal (device_ratings) |
| rate2_5 | written | RATE2-5: the olt_rate5 limit on winding 2's terminal (device_ratings) |
| rate2_6 | written | RATE2-6: the olt_rate6 limit on winding 2's terminal (device_ratings) |
| rate2_7 | written | RATE2-7: the olt_rate7 limit on winding 2's terminal (device_ratings) |
| rate2_8 | written | RATE2-8: the olt_rate8 limit on winding 2's terminal (device_ratings) |
| rate2_9 | written | RATE2-9: the olt_rate9 limit on winding 2's terminal (device_ratings) |
| rate2_10 | written | RATE2-10: the olt_rate10 limit on winding 2's terminal (device_ratings) |
| rate2_11 | written | RATE2-11: the olt_rate11 limit on winding 2's terminal (device_ratings) |
| rate2_12 | written | RATE2-12: the olt_rate12 limit on winding 2's terminal (device_ratings) |
| cod2 | written | COD2: the controlled tap changer: a RatioTapChanger with ltcFlag false 0, else +-1 voltage, +-2 reactivePower; a PhaseTapChangerLinear under activePower +-3; + when the control is enabled (3-winding only) |
| cont2 | written | CONT2: the busNumber of the control's terminal; the winding's own 0; blank for COD +-3 (3-winding only) |
| rma2 | written | RMA2: the stepped tap's highStep voltage / BASKV, or a shifter's larger end angle (deg); blank for a fixed tap (3-winding only) |
| rmi2 | written | RMI2: as RMA2, at lowStep or the smaller end angle (3-winding only) |
| vma2 | written | VMA2: the control's target + deadband / 2: pu of the regulated bus's BASKV, Mvar or MW by mode (3-winding only) |
| vmi2 | written | VMI2: as VMA2, target - deadband / 2 (3-winding only) |
| ntp2 | written | NTP2: highStep - lowStep + 1 of the stepped tap (3-winding only) |
| tab2 | written | TAB2: the number of the end's ImpedanceTapChangerTabular's table (3-winding only) |
| cr2 | written | CR2: lineDropR as pu on SBASE and the regulated bus's BASKV (per_unit_from_ohms) (3-winding only) |
| cx2 | written | CX2: lineDropX, as CR2 (3-winding only) |
| cnxa2 | unset | CNXA2: only COD +-5 uses it, which is not mapped |
| nod2 | unset | NOD2: a node of a node-breaker bus, written by E5 |
| windv3 | written | WINDV3: get_tap_voltage(actual) of the end's RatioTapChanger / bus 3's BASKV (CW 1); without one, ratedU / BASKV (the import writes no tap at ratio NOMV) |
| nomv3 | written | NOMV3: winding 3's ratedU (kV) |
| ang3 | written | ANG3: -(phaseShift + the PhaseTapChangerLinear's (step - neutral) x increment) (raw_angle); a 2-winding unit's ANG1 is winding 1's less winding 2's (3-winding only) |
| rate3_1 | written | RATE3-1: the olt_rate1 limit on winding 3's terminal (device_ratings) |
| rate3_2 | written | RATE3-2: the olt_rate2 limit on winding 3's terminal (device_ratings) |
| rate3_3 | written | RATE3-3: the olt_rate3 limit on winding 3's terminal (device_ratings) |
| rate3_4 | written | RATE3-4: the olt_rate4 limit on winding 3's terminal (device_ratings) |
| rate3_5 | written | RATE3-5: the olt_rate5 limit on winding 3's terminal (device_ratings) |
| rate3_6 | written | RATE3-6: the olt_rate6 limit on winding 3's terminal (device_ratings) |
| rate3_7 | written | RATE3-7: the olt_rate7 limit on winding 3's terminal (device_ratings) |
| rate3_8 | written | RATE3-8: the olt_rate8 limit on winding 3's terminal (device_ratings) |
| rate3_9 | written | RATE3-9: the olt_rate9 limit on winding 3's terminal (device_ratings) |
| rate3_10 | written | RATE3-10: the olt_rate10 limit on winding 3's terminal (device_ratings) |
| rate3_11 | written | RATE3-11: the olt_rate11 limit on winding 3's terminal (device_ratings) |
| rate3_12 | written | RATE3-12: the olt_rate12 limit on winding 3's terminal (device_ratings) |
| cod3 | written | COD3: the controlled tap changer: a RatioTapChanger with ltcFlag false 0, else +-1 voltage, +-2 reactivePower; a PhaseTapChangerLinear under activePower +-3; + when the control is enabled (3-winding only) |
| cont3 | written | CONT3: the busNumber of the control's terminal; the winding's own 0; blank for COD +-3 (3-winding only) |
| rma3 | written | RMA3: the stepped tap's highStep voltage / BASKV, or a shifter's larger end angle (deg); blank for a fixed tap (3-winding only) |
| rmi3 | written | RMI3: as RMA3, at lowStep or the smaller end angle (3-winding only) |
| vma3 | written | VMA3: the control's target + deadband / 2: pu of the regulated bus's BASKV, Mvar or MW by mode (3-winding only) |
| vmi3 | written | VMI3: as VMA3, target - deadband / 2 (3-winding only) |
| ntp3 | written | NTP3: highStep - lowStep + 1 of the stepped tap (3-winding only) |
| tab3 | written | TAB3: the number of the end's ImpedanceTapChangerTabular's table (3-winding only) |
| cr3 | written | CR3: lineDropR as pu on SBASE and the regulated bus's BASKV (per_unit_from_ohms) (3-winding only) |
| cx3 | written | CX3: lineDropX, as CR3 (3-winding only) |
| cnxa3 | unset | CNXA3: only COD +-5 uses it, which is not mapped |
| nod3 | unset | NOD3: a node of a node-breaker bus, written by E5 |

#### ImpedanceCorrectionRecord

| RAW slot | kind | from / why |
|---|---|---|
| table_number | written | I: the ict_<I> key, else the next number (X2) |
| points | written | the table's points (get_impedance_table), by T ascending |

#### ImpedanceCorrectionPoint

| RAW slot | kind | from / why |
|---|---|---|
| t | written | Ti: an angle point's raw_angle(angle) (deg), or a ratio point's ratio x ratedU / BASKV of its users' winding (users that disagree, or none, raise) |
| f_real | written | Re(Fi): 1 + rEnd1 / 100 (impedance_factor); rEnd1 != xEnd1, or rEnd2/3, xEnd2/3 set, raise |
| f_imag | rule | Im(Fi): 0 (CIM's deviations are real) |
