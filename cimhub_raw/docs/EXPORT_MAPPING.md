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
| transformer_ratings_units | rule | XFRRAT 0 (MVA); E4 settles CurrentLimit ratings |
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
service; `"pu"` on the shunt's BaseVoltage and `base_power`; E2 reads fixed and switched shunts with it too). One
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
