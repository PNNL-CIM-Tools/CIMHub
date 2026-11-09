# PSS/E RAW v34 rewrite on `.cimtbl`: wave plan

**Status:** RAW-1/2/3/15, the zone split and the node-breaker slice decided by the user 2026-11-08.
**R0 reader + writer done 2026-11-08:**
- `raw34_reader.py` / `raw34_writer.py` are rewritten on one schema-driven layout (`record_layout.py`) and cover
  every §4.1 row; the phase-2 layouts raise.
- All `ifabsent`s are removed (RAW-3).
- IEEE14, WECC240 and the node-breaker atom round-trip losslessly; 43 tests.
- Against the seed reader, every value agrees, except that blanks are now `None` and names are trimmed. The seed
  never read transformer lines 3-5 past RATE1-12 (COD..NOD, all 122 WECC240 transformers).

**R0 mappers done 2026-11-08** (spec approved the same day): master, zone, area interchange, and bus with
substations, BusbarSections, voltage limits (kV) and SvVoltage, through `RawImporter` / `raw_to_cim`
(`BusBranchModel`).
- IEEE14 goldens are committed under `tests/goldens/IEEE14/`.
- IEEE14 (11 substations), WECC240 (134) and the node-breaker atom bind.
- Every WECC240 limit and solved voltage in SI equals pu × BASKV; 64 tests.
- **R1 done 2026-11-08** (81 tests; atoms `cimhub_raw/tests/atoms/branch/`). **R2 done 2026-11-08** (112 tests; atoms
`tests/atoms/load/`, `tests/atoms/shunt/`). **R3 done 2026-11-08** (130 tests; atom `tests/atoms/generator/`; RAW-7, RAW-23..25). **R4 done 2026-11-08** (166
tests; atom `tests/atoms/transformer/`; RAW-5, RAW-6; R5 next) (`cimhub_raw/docs/CIMTBL_MAPPING.md`, RAW-9/12/13/20/21/22). Runs in parallel
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

- **Every public transformer has the same form:** 2-winding, CW = CZ = CM = 1, ANG = 0, MAG = 0. COD1 = 0
  except two WECC240 voltage controls (6103-6104, 6302-6304: COD1 = 1, CONT on the 230 kV side; corrected
  2026-11-08, the seed reader never read COD). Every unit carries NTP/RMA/RMI, and IEEE14's WINDV1 is off-nominal
  with CONT 0. Three-winding units, CW 2/3, CZ 2/3 and CM 2 appear only in hand-written atoms.
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
not to equipment. Every bus gets a `BusbarSection` (RAW-19), whose Terminal is the regulated point (RAW-11), so
buses come before every controlled device.

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
  *Decided 2026-11-08:* merge only within a zone, so a transformer or zero-impedance device that joins two zones
  stays a boundary. The fix belongs in CIM (a bus → zone association, §6a); the split is the interim form.
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
- A duplicate key raises in the reader, with both line numbers. Core's `GraphModel.add_to_graph` raises too on
  `rc_1` (C1, 2026-11-08), so no reader can drop one.

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
| R4 | Transformer: 2- and 3-winding, CW 1/2/3, CZ 1/2/3, CM 1/2, taps and controls COD 0/±1/±2 (RAW-5, RAW-6; ±3/±5 phase shifters raise until a case has one, user 2026-11-08) | one atom per code combination; z in ohms equals the PSS/E conversion; IEEE14 + WECC240 bind whole |
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

**Schema audit against the v34.9 Data Formats Reference (2026-11-08)** found these, all now in the uncommitted
diff on top of `7bff112`. Four agents compared every power-flow record in chapter 1 with the YAML; every file was
reviewed after, and a sample of defaults was checked against the spec text.
- **Defaults:** 378 `raw_default` annotations plus 17 distinct `raw_default_rule`s for defaults that depend on
  another field (WINDV on CW; RMA/RMI on CW and COD; SBASE1-2 = SBASE; O1, AREA, ZONE, OWNER = the bus's).
  String defaults are normalized: an ID is `"1"`, a blank name is `""`.
- **`ifabsent` that disagree with the spec,** left for R0 to delete:
  - branch, generator and transformer F2/F3/F4: 0.0, but the spec says 1.0;
  - induction machine DCODE 1 vs 2; A/B/D/E 0.0 vs 1.0; XM 0.0 vs 2.5; R1/X1/R2/X2 0.0 vs 999.0; E2 1.0 vs 1.2;
  - FACTS IMX: 9999.0, but the spec says 0.0;
  - several "no default allowed" fields that carry a default (X1-2, the two-terminal DC RDC/SETVL/VSCHD, ...).
- **New schema:**
  - `substation.yaml`: `SubstationRecord`, `SubstationNodeRecord`, `StationSwitchingDeviceRecord`, and one union
    `EquipmentTerminalRecord` (I, NI, TYP, J, K, ID; the node-breaker atom writes exactly this layout);
  - the multi-terminal DC sub-records: `MultiTerminalConverterRecord`, `MultiTerminalDCBusRecord`,
    `MultiTerminalDCLinkRecord`;
  - `RatingRecord` for the system-wide RATING lines;
  - switched shunt NREG; generator NREG is now serialized (the IEEE14 header lists it).
- **Facts fixed:** 3-winding-only transformer fields got `serialize_if: k != 0`, so a 2-winding line 4 is
  `WINDV2, NOMV2`, as both public cases write it. The branch and switch `order` values no longer collide after the
  12-wide RATE block. VSC units (ALOSS in kW, IMAX in A) and DC descriptions were corrected. Optional IDs now have
  `required: false`, except the identifier slots, which `gen-python` requires.
- **Bus references stay `integer`.** The reader resolves extended names (§3.3), so no slot holds one.

R0 reader and writer work that the audit added:

| is | proposed |
|---|---|
| the reader stores each RATING line as a string; the schema now types it `RatingRecord` | parse into `RatingRecord`s (set number, name, description) |
| the reader builds no multi-terminal DC sub-records and no substation records | build them, driven by the header counts (NCONV, NDCBS, NDCLN) and the nested `0` terminators |
| the writer drops a blank second title line (IEEE14 has one) and strips the leading blank of title line 1 | the two title lines are written verbatim, always two |
| `VscDcRecord` repeats the header per converter; impedance correction is flat T1..F11, while v34 allows up to 99 points | P2 (their stubs raise until then): split into a VSC line + converter pair, and an `ImpedanceCorrectionPoint` per point |

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
  - Every bus lands in a `Substation`, merged per §3.2, never across a zone boundary.
  - Area → `ControlArea` (netInterchange = PDES, pTolerance = PTOL; the swing bus `ISW` untranscribed unless a
    home is found). `ControlArea` holds no nodes, so how a bus's AREA round-trips (through its zone's region, or
    `ControlArea` ↔ equipment) is settled in R5.
  - Zone → `SubGeographicalRegion` under the case's `GeographicalRegion`; a substation's `Region` is its zone.
  - Owner → untranscribed, and logged as a CIM 18 gap (§6a).
  - No `VoltageLevel`s: the old converter's Bus → `VoltageLevel` caused 34 mRID collisions in WECC240.
- **RAW-3. Defaults** mapped from the v34 specification, in a `raw_default` annotation; the mapper fills them and lists them (§3.4). *Decided 2026-11-08.*
- **RAW-4. Identity** per §3.3. *Recommended.* The bus number I also goes to `TopologicalNode.busNumber`, which
  cim18v17 has.
- **RAW-5. Transformer impedance codes.** *Decided 2026-11-08 (user, with the R4 spec; `CIMTBL_MAPPING.md#transformer-r4`):*
  every code is derived to ohm/S (`transformer_ohms`, `magnetizing_siemens`); the pu bullets below were the first proposal.
  - CZ 1 → `r/x (pu system)` on the end's BaseVoltage and SBASE.
  - CZ 2 → `(pu)` on the winding's SBASE and NOMV, or the bus BASKV when NOMV = 0.
  - CZ 3 → derived (load loss in W plus \|Z\| in pu), by a named function.
  - CM 1 → MAG1/MAG2 `g/b (pu system)`; CM 2 → derived (no-load loss in W plus exciting current in pu).
  - Three-winding Z12/Z23/Z31 go directly onto three `TransformerMeshImpedance` rows, with no star conversion.
  - *Checked 2026-11-08:* cimtables cannot base a mesh row in `(pu system)` (no `BaseVoltage` on the row). The user
    chose ohm/S for every code (2026-11-08), so the R4 draft derives `transformer_ohms` / `magnetizing_siemens`.
  - *cim18v17 (user 2026-11-08):* no `TransformerStarImpedance`/`TransformerStarAdmittance`; a 2-winding r/x/g/b on
    end 1; a mesh-given 3-winding as `TransformerMeshImpedance` rows with g/b on the end (Delta model).
- **RAW-6. Turns ratio and taps.** *Decided 2026-11-08 (user, with the R4 spec).*
  - `ratedU` = NOMV, or BASKV when NOMV = 0.
  - WINDV (per CW) is an off-nominal ratio. It becomes a `RatioTapChanger`, never a raw ratio in `step`
    (`TapChanger.step` is a tap position).
  - `step` is derived from WINDV, RMA, RMI and NTP by a named function, with `stepVoltageIncrement` =
    (RMA − RMI)/(NTP − 1) in percent.
  - COD 0 with WINDV ≠ 1 still needs a tap changer (fixed, no control). COD ±1/±2/±3 add a `TapChangerControl`
    (voltage, reactive power, active power), and a negative COD sets the control out of service.
  - This is the riskiest mapping in the wave; R4's spec section works it out on atoms first.
  - *R4 draft 2026-11-08* (`CIMTBL_MAPPING.md#transformer-r4`): steps 1..NTP, neutralStep nearest ratio 1 with
    neutralU exact; COD 0/±1/±2 mapped, ±3/±4/±5 raise; CONT 0 names the winding's own terminal (user).
- **RAW-7. Generators.** *Decided 2026-11-08 (user, with the R3 spec; `CIMTBL_MAPPING.md#generator-r3`).*
  - Per record, by WMOD (RAW-24): `SynchronousMachine` `sm_` + `GeneratingUnit` `gu_` + `ControlAreaGeneratingUnit`
    `cagu_`, or `PowerElectronicsConnection` `pec_` + `PowerElectronicsUnit` `pecu_` +
    `ControlAreaPowerElectronicsUnit` `capu_`, all keyed `<I>_<ID>`, in the `ControlArea` of the bus's AREA.
  - `p` = −PG, `q` = −QG (load sign convention). QT/QB → maxQ/minQ, MBASE → ratedS, PT/PB → the unit's P limits,
    all copied.
  - Per plant (bus I): one `RegulatingControl` `gc_<I>`, since VS/IREG/RMPCT are plant quantities in PSS/E (the
    records must agree, else raise). Enabled iff bus IDE is 2 or 3; target VS × BASKV(IREG) in V.
  - The `synchronous_machine` shape and the prefixes are core and translate-skill requests (C2, C3).
- **RAW-23. Machine attributes.** *User 2026-11-08:* `SynchronousMachine.referencePriority` (IDE 3) and `qPercent`
  (RMPCT) added to cim18v17. ZR → the existing `r (ohm)`. **TODO:** cim18v17 has no positive-sequence machine
  reactance for ZX ("bizarre", user), so a new profile extension is to be made; ZX is untranscribed until then.
- **RAW-24. WMOD.** *User 2026-11-08:* a CSP plant is a steam-turbine synchronous machine (WMOD 0 in PSS/E, so
  `SynchronousMachine` + `GeneratingUnit`); a PV farm is converter-interfaced, so `PowerElectronicsConnection` +
  a `PowerElectronicsUnit` (concrete in cim18v17, no kind) carries it. WMOD 1 → the latter; 2, 3, 4 raise until a
  case has one. Gap: RAW cannot say PV vs wind, or an induction-machine wind plant.
- **RAW-25. Implicit step-up transformer.** RT + jXT ≠ 0 raises `NotImplementedError` until a case has one (both
  cases: 0); GTAP untranscribed. The physical form, a generator-with-GSU builder shape, is a TODO for an owner
  (C8): the user had seen it as a CIM-Builder GUI feature, but converters need it as much.
- **RAW-8. Loads.** *Decided 2026-11-08 (user, with the R2 spec; `CIMTBL_MAPPING.md#load-r2`).*
  - p = PL + IP + YP, q = QL + IQ − YQ (`load_p_q`; YQ < 0 is inductive, checked against the v34 data format).
  - ZIP fractions by `zip_mix`: one shared `zip_<six fractions>` row per distinct mix. Core's
    `zip_constant_pq`/`_i`/`_z` take over the pure mixes once `raw-v34` takes `rc_1` (its core has no
    `load_response` yet).
  - SCALE 1 → `ConformLoad`, 0 → `NonConformLoad`: CIM's own load-pattern split, so SCALE is mapped.
  - `LoadArea` `la_<area>` (→ `ca_<area>`) ⊃ `SubLoadArea` `sla_<area>_<zone>` ⊃ `clg_`/`nclg_<area>_<zone>`,
    through `SubLoadArea.LoadArea` (added to the profile by the user 2026-11-08). The zone of a load is still
    read from its bus's substation; a load ZONE ≠ its bus's is also listed as untranscribed (gap).
  - INTRPT, DGENP/Q/M, OWNER untranscribed.
- **RAW-9. Ratings.** *Decided 2026-11-08 (with the R1 spec).*
  - RATE1..12 are MVA, so each becomes an `ApparentPowerLimit` (`normalValue (MVA)`, copied) on the
    `OperationalLimitSet` on the equipment's first terminal (RAW-20).
  - The master writes twelve `OperationalLimitType`s `olt_rate<n>`, named from the `RATING` records (else
    `RATEn` / `RATING SET n`), `direction = absoluteValue`, `durationKind` unset.
  - A zero rating is no limit (PSS/E's meaning), so it writes no row.
  - NXFRAT > 0 (XFRRAT for transformers, R4): a current expressed as MVA, so a `CurrentLimit` with
    `normalValue (kA)` = RATEn / (√3 × BASKV), derived by `current_from_rating`. Blank: MVA, defaulted.
- **RAW-10. Switched shunts.** *Decided 2026-11-08; one shunt per block per the user ("match physical reality
  of how they are wired and switched").*
  - Each block becomes a `LinearShuntCompensator` `swsh_<I>_b<k>` (Ni sections of Bi / SBASE pu), and all of
    them name one `RegulatingControl` `cc_<I>`, which is always written (disabled when MODSW = 0).
  - BINIT is split across the blocks in RAW's switching order (`block_sections`).
  - MODSW 1/2 → voltage, discrete/continuous. Target and deadband are in V from VSWHI/VSWLO on the regulated
    bus's BASKV.
  - MODSW 3/5 raise (no case); MODSW 4/6 are phase 2.
  - ADJM and RMPCT are untranscribed.
  - `NonlinearShuntCompensator` is not used: one sequence of totals cannot say which bank is in.
- **RAW-11. Remote regulation.** *Decided 2026-11-08 (user).* `RegulatingControl.Terminal` names a terminal by
  design, never a node: "the terminal could connect into either a topological node or a connectivity node.
  Sometimes it is useful to model regulation at a terminal of a bus bar object" (CIM UML). So a control
  regulating bus I names the Terminal of that bus's `BusbarSection`, `bb_<I>_T1` (RAW-19). In a node-breaker
  substation (NREG ≠ 0) it names the Terminal of a `BusbarSection` on that node (R6). This is not a CIM gap.
  WECC240: 137 of 146 generators regulate another bus.
- **RAW-12. Multi-section line.** *Decided 2026-11-08 (with the R1 spec).*
  - The sections are ordinary branch records joined through dummy buses, and map as usual.
  - The record becomes a `Line` `msl_<I>_<J>_<ID>` (prefix requested, C3) in `multi_section_line.cimtbl`, after
    `branch.cimtbl`; an `Update Table` row moves each section into it. The path I, DUM1, .., J must name exactly
    one unused branch per step, and each dummy bus exactly two branches, or the mapper raises.
  - The dummy buses stay as `TopologicalNode`s.
- **RAW-13. Branch line shunts GI/BI/GJ/BJ** have no home on `ACLineSegment`, which has only a total `bch`/`gch`.
  *Decided 2026-11-08 (user): an ordinary shunt; the missing link to the line is partly an argument for a
  node-breaker model.* Neither public case sets one (counted 2026-11-08).
  - A `LinearShuntCompensator` `cap_<I>_<J>_<CKT>_i` / `_j` at each end where G + jB ≠ 0, `(pu system)` on
    `nomU` = BASKV, `inService` = the branch's ST. "Switched with the line" is carried by the mRID only (CIM 18
    gap). An atom covers it.
- **RAW-14. Solved state.** *Decided 2026-11-08 (user).* Bus VM/VA → one `SvVoltage` per `TopologicalNode` in
  `bus.cimtbl` (identity-only, `identifier` = `<I>_sv`): `v (kV)` = VM × BASKV (derived, `kv_from_per_unit`) and
  `angle (deg)` = VA (copied). `cim_to_raw` writes them back. Generator PG/QG → `RotatingMachine.p`/`q` (RAW-7).
- **RAW-17. A blank BASFRQ.** The spec's default is "the present option setting", which is not a value. A blank
  becomes 60 Hz, PSS/E's shipped setting, marked `# defaulted: BASFRQ=60` on the master's BaseFrequency (WECC240
  leaves it blank). *Recommended; listed for the user.*
- **RAW-18. Node mRIDs.** A `TopologicalNode`'s mRID is the bare bus number. The `cimtbl-translate` prefix table,
  which its owners maintain, gives nodes no prefix. The core shape example `line_bus_branch.cimtbl` writes
  `bus_1`, so the example should follow the table (C2). Equipment on the bus references the node by that number
  (`bus=1001`). *Recommended; listed for the user.*
- **RAW-19. A `BusbarSection` per bus.** *Decided 2026-11-08 (user).* An `OperationalLimitSet` belongs to a
  terminal, never a node (the old OpenDSS cim100 export put limits on nodes, which CIM does not allow). So
  `bus.cimtbl` gives every bus a `BusbarSection` `bb_<I>` (prefix requested, C3) on its `TopologicalNode`. Its
  terminal `bb_<I>_T1` carries:
  - the bus's voltage limits: an `OperationalLimitSet` `bb_<I>_limits` with four `VoltageLimit`s
    (NVHI/NVLO/EVHI/EVLO). High vs low is `OperationalLimitType.direction` (`OperationalLimitDirectionKind`
    high/low) and normal vs emergency is `durationKind`, so the limits need four types beside the shared
    `absoluteValue` ones: `olt_normal_high`/`olt_normal_low` (`durationKind=normal`) and
    `olt_emergency_high`/`olt_emergency_low` (`durationKind=emergency`), in `common.cimtbl` (C2). The values are
    written in kV: `normalValue (kV)` = pu × BASKV (derived, `kv_from_per_unit`; user 2026-11-08). A pu cell would
    need cimtables to reach the base through `Terminal.ConductingEquipment.BaseVoltage`, one hop too many;
  - any regulating control of that bus (RAW-11).
- **RAW-20. Rating limits on terminals.** *Decided 2026-11-08 (user).* One `OperationalLimitSet`
  `<eq>_ratings` on the equipment's first terminal (`sequenceNumber` 1, bus I) holds the nonzero ratings, for
  branches, series capacitors and switches (transformers in R4).
- **RAW-21. Branch LEN.** *Decided 2026-11-08 (user).* `Conductor.length (km)`: RAW's "user-selected units" are
  taken as km ("if it is wrong then too bad"). LEN = 0 writes no length.
- **RAW-22. Metered end MET.** *Decided 2026-11-08 (user).* Untranscribed and logged as a CIM 18 gap: the use
  cases are power flow only, no interchange balancing. No `TieFlow` from MET. WECC240's 81 MET = 2 branches are
  written back as 1 (expected difference).
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
| Zone membership of a bus: a node reaches a region only through its container, so all the buses of a substation share one zone | Zone table, bus ZONE | substations split at zone boundaries (§3.2) | here and in the shared register |
| A bus's own control area, and the area slack bus. Equipment is covered since the 2026-11-08 profile: `ControlAreaGeneratingUnit`, `LoadGroup` → `SubLoadArea` (an `EnergyArea`) → `ControlArea`, `TieFlow` on terminals. A node or `BusbarSection` still has no area | bus AREA, area ISW | equipment memberships written (R2, R3, R5); bus AREA and ISW untranscribed | here and in the shared register |
| ~~The load-area hierarchy (`SubLoadArea` → `LoadArea`)~~ added to the profile 2026-11-08 (user). Still open: the area/zone of machines and DC equipment, and a zone association for equipment | induction machine and multi-terminal DC bus AREA/ZONE; load ZONE ≠ bus ZONE | loads in `LoadArea` ⊃ `SubLoadArea` per (area, zone); machine and DC AREA/ZONE untranscribed | here and in the shared register |
| The metered (loss-allocation) end of a branch | branch, switch, multi-section line MET | untranscribed (RAW-22) | here and in the shared register |
| A shunt switched with its line, in a bus-branch model (a node-breaker model says it by placement) | branch GI/BI/GJ/BJ | an ordinary `LinearShuntCompensator` per end, linked by mRID only (RAW-13) | here and in the shared register |
| A shunt's or converter's share of a coordinated voltage control (`SynchronousMachine.qPercent` exists only for machines; in cim18v17 since 2026-11-08, RAW-23) | switched shunt RMPCT; generator RMPCT on WMOD 1 | untranscribed (R2) | here and in the shared register |
| The kind of a renewable bus-branch generator: PV, wind, or an induction machine (RAW-24) | generator WMOD 1 | a kindless `PowerElectronicsConnection` + `PowerElectronicsUnit` (R3) | here and in the shared register |
| A machine's positive-sequence reactance: TODO, a profile extension (RAW-23) | generator ZX | untranscribed (R3) | here and in the shared register |

Not gaps (by design, user 2026-11-08): limits and regulation always sit on a terminal. A bus's voltage limits and
its regulation use the Terminal of its `BusbarSection` (RAW-11, RAW-19).

## 7. Ownership and requests

The RAW session owns `cimhub_raw/**` and this file. On this branch only, it also owns the `cimhub_raw` member line
in the root `pyproject.toml` / `uv.lock`. Requests to the core owner:

| # | ask | blocks |
|---|---|---|
| C1 | ~~`GraphModel.add_to_graph` raises on a duplicate key instead of warning and dropping (I8)~~ done on `rc_1` 2026-11-08 (uncommitted): `GraphModel.add_to_graph` raises `ValueError` on an identifier already in its class (user: the new API shape; identifiers seed mRIDs, unique at least within the local model). The RAW reader keeps its own earlier raise, which names both line numbers | nothing (the RAW reader checks first) |
| C2 | `line_bus_branch` with a `BusbarSection` per bus, and its node mRID made bare (RAW-18); the voltage `OperationalLimitType`s with `direction` high and low (normal and emergency) in `common.cimtbl`; shapes `control_area` (ControlArea, ControlAreaGeneratingUnit, ConformLoadGroup, SubLoadArea, TieFlow), `synchronous_machine` (bus-branch), `series_compensator`, a node-breaker `substation` (ConnectivityNodes in TopologicalNodes), and bus-branch variants of `load`, `shunt`, `switch` and `transformer_by_ends` (`bus` in place of `node`), each with a loading example; `transformer_by_ends` itself to cim18v17's model (user 2026-11-08: a 2-winding r/x/g/b on end 1, end 2 zero, no mesh row; a mesh only where the source gives one, R4) | R0–R6 |
| C3 | prefixes for BusbarSection, SynchronousMachine, GeneratingUnit, ControlArea, ControlAreaGeneratingUnit, SubLoadArea, ConformLoadGroup, TieFlow, SeriesCompensator, the switched-shunt block (`swsh_`), LoadArea (`la_`), SubLoadArea (`sla_`), ConformLoadGroup (`clg_`), NonConformLoadGroup (`nclg_`), the multi-section `Line` (`msl_`), SynchronousMachine (`sm_`), GeneratingUnit (`gu_`), ControlAreaGeneratingUnit (`cagu_`), the plant control (`gc_`), a kindless PowerElectronicsConnection (`pec_`), PowerElectronicsUnit (`pecu_`), ControlAreaPowerElectronicsUnit (`capu_`), the transformer (`xf_`, ends `xf_<key>_<k>`, `_mesh_<ij>`, `_tap<k>`, `_ctrl<k>`, the regulator shape's suffixes) in the `cimtbl-translate` table (its owners) | R0–R4 |
| C4 | the ZIP fraction function and the CZ/CM derivations as U4 candidates | nothing |
| C5 | `scripts/leak-gate.sh`: `--exclude-dir=.git` does not skip a worktree's `.git` *file*, so the gate always fails in a worktree; add `--exclude=.git` | a clean gate on this branch |
| C6 | ~~`cimhub_core.cimtbl.fill_defaults` keeps attributes `dataclasses.replace` drops (the reader's composite `record.ID`)~~ done on `rc_1` 2026-11-08 (uncommitted), with a test. `importer/cimtbl/records.py`'s `fill_keyed_defaults` goes once `raw-v34` takes `rc_1`; so do the pure `zip_` rows in `load.py` (core's `zip_fractions.cimtbl` replaces them) | R1, R2 |
| C7 | ~~the golden diff (`cimtbl_testing._keyed_records`) crashes on a master's `Import` records~~ already fixed on `rc_1` (it keys them as `("Import", path)`); `raw-v34` predates the fix | R1 |
| C8 | **TODO, owner wanted:** a generator-with-step-up-transformer builder shape (the machine, a `PowerTransformer` and the internal node between them). RAW's implicit GSU (RT/XT/GTAP) needs it, and it is a common need beyond RAW (user, 2026-11-08); the user had thought of it as a CIM-Builder GUI feature | RAW-25 (a nonzero RT/XT raises meanwhile) |
| U-RAW-2 | cimtables: a second `SubLoadArea` naming one `ControlArea` binds without error and overwrites the 0..1 inverse `ControlArea.EnergyArea`; it should raise (I8) | nothing (R2 hangs sub-areas on a `LoadArea`) |
| U-RAW-3 | cimtables: a unit on a unitless float column (`RegulatingControl.targetValue (kV)`) is silently dropped; it should raise | nothing (R2 writes V) |
| ~~U-RAW-1~~ | withdrawn 2026-11-08: bus voltage limits and solved voltages are written in kV, derived as pu × BASKV (RAW-14, RAW-19) | |

## 8. Oracle

There is no open PSS/E engine. The checks are:
- **Unit math.** Every value in SI (`cimtables.get_qty`) equals the PSS/E conversion, computed independently in the
  test. For example, z = R·BASKV²/SBASE for a branch.
- **Round trip (tier 3).** RAW → `.cimtbl` → CIM → RAW, field by field, minus the untranscribed fields.
- **Regression.** The frozen CIMHub_2_0 converter's outputs on IEEE14 and WECC240. These are copied outputs, never
  imported code, and every difference is listed.
