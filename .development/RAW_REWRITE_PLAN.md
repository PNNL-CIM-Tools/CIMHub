# PSS/E RAW v34 rewrite on `.cimtbl`: wave plan

**Status:** draft 2026-11-08; RAW-1/2/3/15 and the node-breaker slice decided by the user the same day. Seed copied
and baseline-tested; nothing is mapped yet. Runs in parallel
with the DSS wave on branch `raw-v34`, in a worktree that sits beside the repo checkout (and so beside the `CIM-*`
checkouts, which the root `../CIM-*` path sources need).
**Master plan:** [`REWRITE_PLAN.md`](REWRITE_PLAN.md) (its F3 wave for `cimhub_raw`). **Pattern:**
[`DSS_REWRITE_PLAN.md`](DSS_REWRITE_PLAN.md). **Contract, shapes, spec format:** the `cimtbl-import-contract`,
`cimtbl-shapes` and `cimtbl-mapping-spec` skills.
**Mapping spec:** `cimhub_raw/docs/CIMTBL_MAPPING.md`, grown one section per slice, each section approved before
its code (as DSS-12).

User decisions, 2026-11-08:
- **RAW v34 only.** The reader raises on any other `REV`.
- **Every v34 record class is mapped, in two phases.** Phase 1 is the power-flow core, with hand-written atoms for
  the forms no public case has. Phase 2 covers DC, FACTS, GNE, induction machines and impedance correction. Phase 1
  leaves a stub module for each phase-2 table, which raises when its table is populated.
- **Fixtures:** IEEE 14 and WECC240 may be committed. No other RAW case may be committed or named in docs. Other
  local cases may only be used in an uncommitted sweep (§5).
- **Workspace:** this branch adds `cimhub_raw` to the root `pyproject.toml` members and re-locks. It touches nothing
  else at the root.
- **Containers (RAW-2):** every bus lands in a `Substation`. Substations are merged across zero-impedance
  devices, series capacitors and transformers, as the old converter did (§3.2). Area → `ControlArea`, Zone →
  `SubGeographicalRegion`, and Owner is a CIM 18 gap (ownership is an asset-management concept in CIM).
- **Defaults (RAW-3)** are mapped from the RAW v34 specification (the user can supply the PDF).
- **Series capacitors (RAW-15):** a branch with X < 0 becomes a `SeriesCompensator` with `compensatorType =
  capacitor` (the cim18v17 `CompensatorKind` extension), with `x` copied verbatim (negative).
- **Node-breaker:** the v34 SUBSTATION section is phase 1, as slice R6. Its first atom is the hand-built
  two-bus case created in PSS/E 34.9, committed as `tests/atoms/substation/two_bus_node_breaker.raw`.

The wave ends when `raw_to_cim` builds cim18v17 only from the `.cimtbl` artifacts and `cim_to_raw` reads cim18v17.
The old converter tree (`importer/<class>/` and `exporter/<class>/`, about 10,900 lines), `cimgraph_raw_extension`,
`schema/data_profile/raw_extension.py` and `schema/models/rawModel.py` (all cim17v40) are not carried over.

## 1. What the public cases contain

Read 2026-11-08 with the old reader, which is the seed:

| record | IEEE14 | WECC240 | phase |
|---|---:|---:|---|
| Case identification + system-wide data | 1 | 1 | 1 (master) |
| Bus | 14 | 243 | 1 |
| Load | 11 | 139 | 1 |
| Fixed shunt | 1 | 0 | 1 |
| Generator | 5 | 146 | 1 |
| Branch | 17 | 329 | 1 |
| System switching device | 0 | 0 | 1 (atom only) |
| Transformer | 3 | 122 | 1 |
| Area | 1 | 4 | 1 |
| Zone | 1 | 14 | 1 |
| Owner | 1 | 1 | 1 |
| Switched shunt | 0 | 7 | 1 |
| Inter-area transfer | 0 | 0 | 1 (atom only) |
| Multi-section line | 0 | 0 | 1 (atom only; groups branches) |
| Two-terminal DC, VSC DC, multi-terminal DC | 0 | 0 | 2 |
| FACTS device, GNE device, induction machine | 0 | 0 | 2 |
| Impedance correction | 0 | 0 | 2 |
| Substation (node-breaker, v34) | 0 | 0 | 1, slice R6 (hand-built atom: 2 substations, 4 + 4 nodes, 4 + 3 breakers, 4 terminals) |

- **Every public transformer has the same form:** 2-winding, CW = CZ = CM = 1, COD1 = 0 (no control).
  Three-winding units, CW 2/3, CZ 2/3, CM 2 and tap controls appear only in hand-written atoms.
- **Extended bus names.** The node-breaker atom refers to buses as `'TOPO_BUS_1  115.00'` (12-character name plus
  base kV) rather than by number, in every record that names a bus. The seed reader fails on it (R0).
- **Substations under the §3.2 rule:** IEEE14 has 11 (largest 3 buses); WECC240 has 131 (largest 7), with 9 series
  capacitors. Every branch in both cases has LEN = 0.
- **IEEE 118 is out of scope:** its file declares REV 33, has 7 duplicate `I-J-CKT` branch keys, and its README
  records hand edits made so it would parse.

## 2. Artifacts and their order

One file per native table (D4); the stem is the LinkML schema module. Proposed `MAPPING_ORDER`:

| # | artifact | native class | shape | references |
|---|---|---|---|---|
| 0 | `<Model>.cimtbl` (master) | case identification + system-wide data | `common` plus `BasePower` (SBASE), `BaseFrequency` (BASFRQ), one `BaseVoltage` per distinct BASKV, one `GeographicalRegion` for the case, the rating-set `OperationalLimitType`s (RAW-9) | |
| 1 | `area_interchange.cimtbl`, `zone.cimtbl` | Area, Zone | new: `ControlArea` (`ca_`, C3); `SubGeographicalRegion` (`srgn_<zone>`) | 0 |
| 1b | `owner.cimtbl` | Owner | none: no file. Owner and every O1/F1..O4/F4 are untranscribed (CIM 18 gap, §6a) | |
| 2 | `bus.cimtbl` | Bus | `line_bus_branch` (`TopologicalNode` `bus_<I>` + `BaseVoltage`), plus `Substation`s (`sub_<lowest bus>`, synthesized from §3.2) | 0, 1 |
| 2b | `substation.cimtbl` | Substation section (R6) | new: `Substation` (`sub_s<IS>`), `ConnectivityNode` (`<sub>_n<NI>`, in its bus's `TopologicalNode`), `Breaker`/`Disconnector` (`sw_`), terminal placement | 2 |
| 3 | `branch.cimtbl` | Branch | `line_bus_branch` (`ACLineSegment` in `(pu system)`) + ratings; X < 0: `SeriesCompensator` (`compensatorType = capacitor`) | 2 |
| 4 | `switch.cimtbl` | System switching device | `switch` with `bus1`/`bus2` | 2 |
| 5 | `multi_section_line.cimtbl` | Multi-section line | new: a grouping of the branches in 3 (RAW-12) | 3 |
| 6 | `transformer.cimtbl` | Transformer (2- and 3-winding) | `transformer_by_ends` with `bus` + `RatioTapChanger`/`TapChangerControl` (RAW-6) | 2 (controlled bus) |
| 7 | `load.cimtbl` | Load | `load` with `bus`; ZIP response (RAW-8) | 2 |
| 8 | `fixed_shunt.cimtbl` | Fixed shunt | `shunt` with `bus` (`LinearShuntCompensator`) | 2 |
| 9 | `switched_shunt.cimtbl` | Switched shunt | `shunt` (+ `RegulatingControl`); blocks of steps (RAW-10) | 2, 6 |
| 10 | `generator.cimtbl` | Generator | new: `synchronous_machine` (bus-branch) (RAW-7) | 2 |
| 11 | `interarea_transfer.cimtbl` | Inter-area transfer | RAW-2 | 1 |
| P2 | `two_terminal_dc`, `vsc_dc`, `multi_terminal_dc`, `facts_device`, `gne_device`, `induction_machine`, `impedance_correction` | | phase 2 stubs, §4 | |

A remote regulated bus (generator `IREG`, switched shunt `SWREG`, transformer `CONT1`) is a reference to a node,
not to equipment. That is why buses come before every controlled device, and why RAW-11 is open.

## 3. Native passes the mappers share

### 3.1 Bus voltages: no walk

Every RAW bus carries its own `BASKV`, so RAW needs no `cimtopology.core.walk`. `bus.cimtbl` writes one
`TopologicalNode` per bus, with the `BaseVoltage` of its BASKV. Each equipment row also carries its own
`BaseVoltage`, which must equal its buses', as in DSS.

### 3.2 Substations (RAW-2)

Every bus lands in a `Substation`, and buses joined by equipment that sits inside a substation share one. The
merge equipment, as the old converter's `createSubstationMap` had it, corrected below:
- every system switching device;
- a zero-impedance branch: R = 0 and \|X\| ≤ THRSHZ (system-wide `GENERAL`, default 0.0001), PSS/E's own test;
- a branch whose CKT starts with `@` (breaker) or `*` (switch), as the old rule had it (to check against the
  spec);
- a series capacitor (a branch with X < 0, RAW-15);
- every transformer (all of its windings' buses).

The old rule also merged on `LEN = 0`. That is dropped: LEN = 0 only means "length not given", and it holds for
every branch in both public cases, so the old rule merged across ordinary lines. The old rule also merged VSC DC
and series FACTS; those wait for their phase-2 slices.

**Grouping** is `cimtopology.core.Topology(network).islands()` over a `Network` holding only the merge equipment,
with every bus in `nodes`, so a bus on no merge equipment is its own substation. The spoke writes no union-find
(contract, topology).
- **mRID:** `sub_<lowest bus number>`, name = that bus's NAME. The result is deterministic, whatever the
  islands' roots.
- **Rows:** the `Substation` rows go in `bus.cimtbl`, under `# synthesized: substations merged across ...`, so the
  grouping is reviewable. Each lists its buses and the merge equipment on its row comment.
- **Zones.** Two WECC240 substations straddle zones (buses 1001 and 4006, each within one area). A substation can
  sit in only one `SubGeographicalRegion`, so taking one zone would lose the other buses' zones on the round trip.
  *Recommended:* merge only within a zone, so a transformer or zero-impedance device that joins two zones stays a
  boundary. *To confirm in R0.*
- **Node-breaker (R6):** a bus listed in a SUBSTATION block belongs to that `sub_s<IS>`, which takes precedence
  over the merge. A merged group holding buses of two SUBSTATION blocks raises until a case shows the intent.

### 3.3 Identity (RAW-4)

- mRID = prefix + the record's natural key, in source case. Blank padding is trimmed, because PSS/E compares IDs
  trimmed (`'1 '` is circuit `1`). The key is the reader's `composite_id`, joined with `_`:
  - Bus `bus_<I>`;
  - Branch `ln_<I>_<J>_<CKT>`;
  - Transformer `xf_<I>_<J>_<K>_<CKT>`;
  - Load `ld_<I>_<ID>`;
  - Fixed shunt `cap_<I>_<ID>`;
  - Switch `sw_<I>_<J>_<CKT>`.
- Extended bus names (`'TOPO_BUS_1  115.00'`) resolve to the bus number through the bus table (name + BASKV),
  in the reader. Every bus reference is a number after reading. An extended name that matches no bus, or matches
  two, raises.
- Prefixes the `cimtbl-translate` table lacks, for generators, areas and switched shunts, are requested from its
  owners (RAW-7, RAW-2). None is invented here.
- `name` = the record's `NAME` when it is not blank, else the key.
- A duplicate key raises in the reader, with both line numbers. Core's `GraphModel.add_to_graph` still warns and
  drops on a collision; that fix is a core request (§7, C1).

### 3.4 Defaults (RAW-3, decided 2026-11-08)

RAW writers routinely omit trailing fields and leave fields blank, and the format gives each one a default. The
seed reader fills these defaults while parsing, and the schema carries about 400 `ifabsent`s, so a filled default
cannot be told apart from a written value. Each default is checked against the RAW v34 specification (the user
supplies the PDF; no manual text is copied into the repo, only the values). Following DSS-6:
- A `raw_default` annotation replaces each `ifabsent`.
- The reader leaves an unwritten field as `None`.
- The mapper fills it and lists it on the row comment (`# defaulted: F1=1.0`).
- The writer writes back only what was read.

## 4. Slices

Each slice delivers its mappers, atoms with goldens (`tests/atoms/<table>/`), its `CIMTBL_MAPPING.md` section
(generated with `fields_table`) and the extended sweep. Each section is approved before its code.

| slice | content | exit |
|---|---|---|
| R0 | **Seed** (done 2026-11-08: copied, with only docstring paths changed; reader + writer moved to the package root as `raw34_reader.py` / `raw34_writer.py`; the dead `annotation_writer.py` left behind; `tests/test_raw34_reader.py` holds the baseline): LinkML schema, `raw34_schema.py`, `composite_id.py`, reader, writer. **Reader fixes** (§4.1). Package skeleton, `pyproject.toml`, workspace member. The SUBSTATION section parsed into new schema classes. Orchestrator `raw_to_cimtbl.py` (`MAPPING_ORDER`, `RawImporter(CimtblImporter)` with `model_cls = BusBranchModel`); master, area, zone, and `bus.cimtbl` with the merged substations (§3.2). Phase-2 stub modules (done 2026-11-08). | IEEE14, WECC240 and the node-breaker atom read; master + area + zone + bus bind; IEEE14 has 11 substations; read → write → read is lossless on all three |
| R1 | Branch (+ ratings, line shunts RAW-13, series capacitors RAW-15), system switching device, multi-section line | IEEE14 + WECC240 branches bind; every z in ohms equals R·BASKV²/SBASE |
| R2 | Load, fixed shunt, switched shunt | values in SI equal hand formulas; WECC240's 7 switched shunts bind |
| R3 | Generator (new `synchronous_machine` shape, core request C2) | 151 machines bind; p sign = load convention |
| R4 | Transformer: 2- and 3-winding, CW 1/2/3, CZ 1/2/3, CM 1/2, taps and controls COD ±1/±2/±3 (RAW-5, RAW-6) | one atom per code combination; z in ohms equals the PSS/E conversion; IEEE14 + WECC240 bind whole |
| R5 | Area interchange values (ControlArea), inter-area transfer, how a bus's AREA is recorded (RAW-2) | the whole public cases bind with nothing listed as not mapped |
| R6 | Node-breaker: SUBSTATION blocks → `Substation`, `ConnectivityNode`s in their bus's `TopologicalNode`, substation switching devices (TYPE → `Breaker`/`Disconnector`, STATUS/NSTAT → `open`/`normalOpen`), equipment terminals placed on nodes. Needs a mixed bus-branch/node-breaker load path in cimtables (request) | the two-bus atom binds; each branch terminal sits on the node the terminal record names |
| E | Exporter `cim_to_raw` on the core getters; tiers 2 and 3 | IEEE14 + WECC240 round-trip RAW → cimtbl → CIM → RAW, equal field by field minus untranscribed fields |
| P2 | Phase 2, one slice per table: impedance correction (→ `TapChangerTablePoint`), two-terminal DC, VSC DC, multi-terminal DC, FACTS, GNE, induction machine | each one atom-proven; new shapes requested from core first |

R1–R3 are independent of one another after R0. R4 is the largest slice; it carries most of the spec's derived
formulas.

### 4.1 Reader fixes (R0)

The seed reader works on the public cases but breaks I8 in these places:

| is | proposed |
|---|---|
| sections are found by searching for the `BEGIN ... DATA` comment text, with a PowerWorld workaround; a section that is not found is `[]` | sections are positional, in v34 order. Each is ended by a `0` record (the comment after it is ignored). A missing terminator or a `Q` before the end raises |
| any `REV` is read; v33 has its own branch layout | REV ≠ 34 raises (user, 2026-11-08); the v33 branch path is deleted |
| a duplicate key keeps the first record and logs a warning | raises with both line numbers |
| defaults are filled while parsing (`if len(fields) > 26 else 1`), and the schema has `ifabsent` | RAW-3 |
| `' / '` splits a line wherever it appears, including inside quoted names | the comment starts at the first `/` outside quotes |
| `logging.basicConfig(level=INFO)` at import | removed (a library must not configure logging) |
| a FACTS record that fails to parse is logged and skipped | raises |
| the v34 SUBSTATION section is not read | parsed into new schema classes (substation, node, switching device, terminal; nested blocks with their own `0` terminators) |
| an extended bus name (`'NAME  BASKV'`) where a number is expected raises a conversion error | resolved to the bus number (§3.3) |
| a `.raw` extension mismatch is a warning | kept (harmless) |
| **writer:** fixed-point `precision: 5` writes `1.00000E-7` as `0.00000`. WECC240 read → write → read loses 17 branch `R`, 1 branch `X` and 79 transformer `R1-2` (checked 2026-11-08). IEEE14 round-trips exactly | floats are written so they read back to the same value (`repr`, or E-format when fixed point would lose digits); a round-trip test on both cases |

### 4.2 Phase-2 stubs (R0)

`importer/cimtbl/<table>.py` for each phase-2 table holds `NATIVE_CLASS`, a docstring that names the target CIM
classes and open questions, and `map_<table>(native)`. That function returns an empty document when the table has
no records, and raises `NotImplementedError("RAW <class>: phase 2, RAW_REWRITE_PLAN.md §4")` otherwise. They are
in `MAPPING_ORDER`, so a case that uses one fails at once and names it. They hold no `FIELDS` yet:
`scaffold_mapper` writes those when the slice starts, from real atom records.

## 5. Sweep

- **Committed cases:** IEEE14 and WECC240 under `cimhub_raw/tests/cases/`, and the hand-built node-breaker atom
  under `tests/atoms/substation/`. A README gives each one's source, URL,
  license and any edits (split-readiness rule 4). IEEE14's origin (the UW archive case, converted to v34 by
  rawd34) must be recorded before commit; WECC240 is the NREL "contains no CEII" release.
- **Local sweep:** `CIMHUB_RAW_SWEEP_DIR` names a directory of other v34 cases. The sweep test skips when it is
  unset. Its results go to the console only. Spec sections report them as counts ("N local cases"), never by name
  or content.

## 6. Decisions

Each decision has a recommendation; the slice's spec section settles it.

- **RAW-1. v34 only.** *Decided 2026-11-08.*
- **RAW-2. Containers.** *Decided 2026-11-08.*
  - Every bus lands in a `Substation`, merged per §3.2 (the zone boundary is to confirm).
  - Area → `ControlArea` (netInterchange = PDES, pTolerance = PTOL; the swing bus `ISW` untranscribed unless a
    home is found). `ControlArea` holds no nodes, so how a bus's AREA round-trips (through its zone's region, or
    `ControlArea` ↔ equipment) is settled in R5.
  - Zone → `SubGeographicalRegion` under the case's `GeographicalRegion`; a substation's `Region` is its zone.
  - Owner → untranscribed, and logged as a CIM 18 gap (§6a).
  - No `VoltageLevel`s: the old converter's Bus → `VoltageLevel` caused 34 mRID collisions in WECC240.
- **RAW-3. Defaults** mapped from the v34 specification, in a `raw_default` annotation; the mapper fills them and lists them (§3.4). *Decided 2026-11-08.*
- **RAW-4. Identity** per §3.3. *Recommended.*
- **RAW-5. Transformer impedance codes.**
  - CZ 1 → `r/x (pu system)` on the end's BaseVoltage and SBASE.
  - CZ 2 → `(pu)` on the winding's SBASE and NOMV, or the bus BASKV when NOMV = 0.
  - CZ 3 → derived (load loss in W plus \|Z\| in pu), by a named function.
  - CM 1 → MAG1/MAG2 `g/b (pu system)`; CM 2 → derived (no-load loss in W plus exciting current in pu).
  - Three-winding Z12/Z23/Z31 go directly onto three `TransformerMeshImpedance` rows, with no star conversion.
  - The base cimtables uses for a mesh row in `(pu system)` is checked in R4, before the spec is approved.
- **RAW-6. Turns ratio and taps.**
  - `ratedU` = NOMV, or BASKV when NOMV = 0.
  - WINDV (per CW) is an off-nominal ratio. It becomes a `RatioTapChanger`, never a raw ratio in `step`
    (`TapChanger.step` is a tap position).
  - `step` is derived from WINDV, RMA, RMI and NTP by a named function, with `stepVoltageIncrement` =
    (RMA − RMI)/(NTP − 1) in percent.
  - COD 0 with WINDV ≠ 1 still needs a tap changer (fixed, no control). COD ±1/±2/±3 add a `TapChangerControl`
    (voltage, reactive power, active power), and a negative COD sets the control out of service.
  - This is the riskiest mapping in the wave; R4's spec section works it out on atoms first.
- **RAW-7. Generators.**
  - `SynchronousMachine` + `GeneratingUnit`; `p` = −PG under the CIM load sign convention.
  - QT/QB → maxQ/minQ, MBASE → ratedS, ZR/ZX → r/x in `(pu)` on MBASE, PT/PB → the unit's maxOperatingP/
    minOperatingP.
  - The `synchronous_machine` shape and its prefixes are core and translate-skill requests (C2, C3).
- **RAW-8. Loads.**
  - One `EnergyConsumer` per load, with p = PL + IP + YP and q = QL + IQ − YQ (YQ is positive for a capacitive
    admittance load, so it enters q with a minus sign).
  - A derived `LoadResponseCharacteristic` per distinct fraction mix gives the constant-power, current and
    impedance fractions. Its function is a U4 candidate.
  - SCALE, INTRPT, DGENP/Q/M and LOADTYPE: untranscribed unless a home is found.
- **RAW-9. Ratings.**
  - RATE1..12 are MVA, so each becomes an `ApparentPowerLimit` on the branch's or transformer's
    `OperationalLimitSet`.
  - One `OperationalLimitType` per rating set, named from the system-wide `RATING` records, goes in the master.
  - A zero rating is no limit (PSS/E's meaning), so it writes no row.
- **RAW-10. Switched shunts.** Blocks Ni × Bi become a `NonlinearShuntCompensator` with one point per cumulative
  step, or a `LinearShuntCompensator` when there is one block. MODSW → `RegulatingControl` mode;
  VSWHI/VSWLO → the target value and deadband.
- **RAW-11. Remote regulation.** CIM puts a `RegulatingControl` on a `Terminal`, but a RAW controlled bus may have no
  equipment of its own. Options: the terminal of any equipment on that bus, picked deterministically; or a
  cimtables request to name a `TopologicalNode`. *Open*, decided in R2.
- **RAW-12. Multi-section line.**
  - The sections are ordinary branch records joined through dummy buses.
  - Proposed: the branches map as usual, and the multi-section record becomes a `Line` container holding them.
  - The dummy buses stay as `TopologicalNode`s.
- **RAW-13. Branch line shunts GI/BI/GJ/BJ** have no home on `ACLineSegment`, which has only a total `bch`/`gch`.
  - Proposed: a `LinearShuntCompensator` at each end where the value is nonzero.
  - Alternatively they could raise until a public case sets them. R1 counts the public cases first.
- **RAW-14. Solved state.** Bus VM/VA and generator PG/QG are a solved case. Proposed: VM/VA → `SvVoltage` per
  `TopologicalNode` in `bus.cimtbl`, so `cim_to_raw` can write them back. PG/QG are the machine's `p`/`q`
  (RAW-7). *To decide in R0.*
- **RAW-15. Negative branch reactance.** *Decided 2026-11-08.* WECC240 has 9 branches with X < 0 (for example
  `2404-3893`: R = 1e-7, X = −0.00935), which are series capacitors. Each becomes a `SeriesCompensator` (`sc_`,
  C3) with `compensatorType = capacitor`. That attribute uses `CompensatorKind {capacitor, reactor}`, a WiresEXT
  enum in cim18v17. `r`/`x` are copied verbatim, in `(pu system)`, so `x` stays negative. A series capacitor is a
  merge edge for substations (§3.2). A branch with X > 0 stays an `ACLineSegment`: RAW gives no way to tell a
  series reactor from a short line.
- **RAW-16. Mixed bus-branch / node-breaker models (R6).** A case with SUBSTATION blocks has `ConnectivityNode`s
  in some substations and bare `TopologicalNode`s elsewhere. The load path (`BusBranchModel` vs a node-breaker
  model) is checked against cimtables before R6's spec; a gap there is filed upstream (I9).

### 6a. CIM 18 gaps

| gap | RAW fields | today | logged |
|---|---|---|---|
| Ownership of network equipment: CIM puts ownership in asset management (`AssetOwner` / `Ownership` on an `Asset`), not on a `PowerSystemResource` | Owner table (I, OWNAME); O1/F1..O4/F4 on loads, generators, branches, transformers, switched shunts, FACTS, VSC; bus OWNER | untranscribed | here and in the mapping spec; also to the shared CIM 18 gap register (`CIMTBL-Models/distribution/CIM18_GAPS.md`) |

## 7. Ownership and requests

The RAW session owns `cimhub_raw/**` and this file. On this branch only, it also owns the `cimhub_raw` member line
in the root `pyproject.toml` / `uv.lock`. Requests to the core owner:

| # | ask | blocks |
|---|---|---|
| C1 | `GraphModel.add_to_graph` raises on a duplicate key instead of warning and dropping (I8) | nothing (the RAW reader checks first) |
| C2 | shapes `synchronous_machine` (bus-branch), `series_compensator`, a node-breaker `substation` (ConnectivityNodes in TopologicalNodes), and bus-branch variants of `load`, `shunt`, `switch` and `transformer_by_ends` (`bus` in place of `node`), each with a loading example | R0–R6 |
| C3 | prefixes for SynchronousMachine, GeneratingUnit, ControlArea, SeriesCompensator, NonlinearShuntCompensator in the `cimtbl-translate` table (its owners) | R0–R3 |
| C4 | the ZIP fraction function and the CZ/CM derivations as U4 candidates | nothing |

## 8. Oracle

There is no open PSS/E engine. The checks are:
- **Unit math.** Every value in SI (`cimtables.get_qty`) equals the PSS/E conversion, computed independently in the
  test. For example, z = R·BASKV²/SBASE for a branch.
- **Round trip (tier 3).** RAW → `.cimtbl` → CIM → RAW, field by field, minus the untranscribed fields.
- **Regression.** The frozen CIMHub_2_0 converter's outputs on IEEE14 and WECC240. These are copied outputs, never
  imported code, and every difference is listed.
