# GridLAB-D rewrite on `.cimtbl`: importer wave plan

**Status:** approved by the user 2026-11-09. **The exporter wave (§8) was approved by the user 2026-11-21 ("implement the plan") and built the same day, X0-X5, committed (`4ee084a`, `docs/EXPORT_MAPPING.md`); its §8.3 tests that were left out (tier 2, the forms atom) built 2026-11-21 by the user's "go on to next phase", committed with the WireConfiguration rule (`f74f3f5`, §8.7). IEEE 8500 (X5's last deck, the series reactor both ways, S7) built 2026-11-21 by the user's "go for the next phase", uncommitted (§8.8).** **S0 built 2026-11-09** (§4, findings in §3.5). GLM-1 re-decided and GLM-17 deferred by the user the same day. **S1 approved (S1-2, S1-3 amended) and built 2026-11-09.** **S2 approved (S2-3 amended) and built 2026-11-09** (`CIMTBL_MAPPING.md` S2; it amends GLM-11, GLM-12 and section 2 row 3). S0-S2 committed (`3aa8e6d`). **S3a (lines, switches) approved and built 2026-11-09** (`CIMTBL_MAPPING.md` S3a; it amends GLM-10 and drops the section 7 `switch` row). **S3a committed (`928f77d`). S3b (transformers) approved with the user's S3b-1/-4/-5/-9, built and committed (`3cd6983`)** (`CIMTBL_MAPPING.md` S3b; it amends GLM-6 and adds two section 7 core rows). **S3c (regulators) built 2026-11-09 by the user's direction (VoltageRegulator + two ideal AutoTransformerEnds), committed (`02d8fce`)** (`CIMTBL_MAPPING.md` S3c; it amends GLM-7). **The transformer getter reads an ideal AutoTransformer (2026-11-10, by the user's direction), which closes S3c's section 7 core row.** **S4a (loads, capacitors) approved 2026-11-10 with the user's S4a-2 TODO, S4a-5 and S4a-8 (a), built the same day; it and the getter change committed (`7bfe45b`)** (`CIMTBL_MAPPING.md` S4a; it amends GLM-8 and drops the section 7 `load` shape row). **S4b (DER) approved 2026-11-10 with the user's calls (GridLAB-D's PV logic, CONSTANT_PF batteries a Java defect, ratedU line to line) and built the same day, uncommitted** (`CIMTBL_MAPPING.md` S4b; it amends GLM-13). **S5 (the deck sweep, the D6 golden directory, tier 4, G7) proposed 2026-11-10, approved as recommended and built 2026-11-16, uncommitted** (`CIMTBL_MAPPING.md` S5). **S6 (a utility's Milsoft WindMil decks, by the user's direction 2026-11-16) built and approved 2026-11-16, uncommitted** (`CIMTBL_MAPPING.md` S6; it amends S3a-3, S3b-3 and S3c-6). The importer is complete for every mapped class. Branch `glm-importer` (worktree
`CIMHub-glm`, off `rc_1` at `d0901e7`). This wave is the **importer** (`glm_to_cim`). The exporter (`cim_to_glm` on
the core getters) gets its own plan once the importer is done, as DSS S6 did.
**Master plan:** [`REWRITE_PLAN.md`](REWRITE_PLAN.md) (F3+, GridLAB-D). **Contract, shapes, spec format:** the
`cimtbl-import-contract`, `cimtbl-shapes` and `cimtbl-mapping-spec` skills. **Template:** this plan follows
[`DSS_REWRITE_PLAN.md`](DSS_REWRITE_PLAN.md); where GLM behaves the same, it reuses the DSS decision.
**Mapping spec:** `cimhub_gridlabd/docs/CIMTBL_MAPPING.md`, one section per slice, each approved before that slice's
code (as DSS-12).

The wave ends with `glm_to_cim(path, artifact_dir=None)` building cim18v17 only from the `.cimtbl` artifacts, for
every class the public decks hold, with each unmapped class counted in the master.

## 0. What carries over from CIMHub_2_0

Spoke seed rule (master plan): `schema/`, the reader and the writer are copied and reviewed; every converter is
written fresh. CIMHub_2_0's `cimhub_gridlabd/` stays the read-only oracle (copy outputs, never import code).

| old module | lines | verdict | why |
|---|---:|---|---|
| `schema/linkml/**` (90 yaml), `schema/gridlabd.py` (generated) | 27k + yaml | COPY | no CIM profile import; each slot has `unit.ucum_code` and `native_name`. Defaults are missing (§3.3) |
| `schema/cpp_parser.py`, `property_parser.py`, `linkml_generator.py` | 1,225 | COPY | the schema's provenance: they regenerate it from the GridLAB-D C++ source. Review that they hold no absolute paths |
| `importer/glm_text_reader.py`, `glm_reader.py` (GLM-JSON), `glm_serialization.py`, `glm_registry.py` | 1,067 | ~~COPY, then fix~~ **rewritten in S0** (`glm_reader.py`, `glm_schema.py`) | a line-regex state machine feeding a JSON-shaped dict, with `name`/`parent` attached by `setattr`; making it fail fast and unit-preserving touched every line, so it was rewritten on the same schema. GLM-JSON is deferred to after the migration (GLM-17) |
| `exporter/glm_writer.py`, `glm_text_writer.py` | 490 | deferred to the exporter wave | nothing in the importer uses them; they are copied when their first test is written |
| `importer/<class>/` (17 modules), `common.py`, `glm_to_cim.py` | 1,625 | DROP | cimhub_2026, `cim.X(...)`, `link_terminal`, `propagate_base_voltages` after bind (I1, I5) |
| `exporter/<class>/`, `cim_to_glm.py` | 3,800 | not in this wave | the exporter wave, written fresh on the getters |
| `tests/` | 4,000 | DROP | cimhub_2026 atoms; reader tests are rewritten in S0 against the fixed reader |
| `docs/audit/`, `docs/refactor/CIM_PROFILE_GAPS.md` | | READ, don't copy | the attribute-level findings (Java reference map, CIM gaps) feed the per-slice specs |

## 1. What the decks contain

Census of the 29 public GLM decks in GridAPPS-D Powergrid-Models `models/feeders/GridLABD/` (IEEE13 cdpsm/assets/
houses, IEEE123, IEEE123_transactive, and the 24 PNNL taxonomy feeders `orig_*`), by raw text, 2026-11-09
(throwaway scripts; S5's deck sweep replaces them).

| class | objects | decks | slice | notes |
|---|---:|---:|---|---|
| triplex_node | 16,375 | 25 | S1 (node), S4a (its load) | 7,492 are children (`parent` a triplex_meter); 8,772 carry `power_12`, i.e. they are loads |
| node | 13,992 | 29 | S1 | 26 `bustype SWING`/`SWING_PQ`; 25 have a `parent` |
| transformer | 9,040 | 29 | S3b | |
| triplex_line | 8,787 | 24 | S3a | |
| triplex_meter | 7,509 | 24 | S1 | a node with metering; 2 have a `parent` |
| overhead_line | 7,424 | 26 | S3a | |
| underground_line | 4,278 | 26 | S3a | |
| fuse | 1,599 | 25 | S3a | |
| load | 1,532 | 27 | S4a | 1,429 by `constant_power_X`; 103 by `base_power_X` + fractions |
| transformer_configuration | 1,474 | 29 | S3b | 856 `SINGLE_PHASE_CENTER_TAPPED`, 614 `WYE_WYE` (3-phase and 1-phase), 2 `DELTA_DELTA`, 2 `DELTA_GWYE`; no open delta |
| meter | 1,455 | 25 | S1 | |
| line_configuration | 754 | 29 | S2 | 722 by spacing + conductors (geometry), 32 by z-matrix (the Java CIMHub exports) |
| switch | 588 | 29 | S3a | |
| line_spacing | 238 | 26 | S2 | distances written in `in` on many (§3.4, GLM-2) |
| overhead_line_conductor | 163 | 23 | S2 | |
| underground_line_conductor | 91 | 26 | S2 | concentric neutral |
| capacitor | 82 | 25 | S4a | control VOLT 48, MANUAL 22, unset 12; `capacitor_X` in `MVAr` on 70 |
| regulator, regulator_configuration | 39, 39 | 29 | S3c | all `WYE_WYE` |
| recloser | 35 | 8 | S3a | |
| triplex_line_configuration, triplex_line_conductor | 26, 25 | 26, 25 | S2 | 25 by conductors, 1 by z-matrix |
| inverter, solar, battery | 10, 2, 3 | 2, 1, 1 | S4b | `solar`/`battery` nested in their inverter |
| substation | 4 | 4 | S1 | the swing source of the Java exports |
| house, ZIPload, waterheater | 15 each | 1 | not mapped (GLM-14) | IEEE13_houses only |
| recorder, multi_recorder, fncs_msg | 15, 1, 1 | 7, 1, 1 | not mapped (GLM-14) | no schema class or no CIM home |
| triplex_load | 1 | 1 | S4a | |

Directives: `#set` 33, `module` 58, `schedule` 9 blocks, `#define` 1, `#include` 0. The Java exports reference
`${VSOURCE}` without defining it (GLM-15). Nested `object` blocks occur (inverter → solar/battery).

## 2. Artifacts and their order

One file per native table (D4); the stem is the LinkML schema module. The master imports them in this order (G6):

| # | artifact | native class | shape | references |
|---|---|---|---|---|
| 0 | `<model>.cimtbl` (master) | the model name, `clock`/`module powerflow` settings, the not-mapped counts | `common` (Feeder, BaseFrequency, BaseVoltage) | |
| 0b | `zip_fractions.cimtbl` | none (core, always written) | `common` (DSS-7) | |
| 1 | `bus.cimtbl` (amended in S0) | every root bus object (GLM-4): any `node` or `triplex_node` subclass, so meters, loads, capacitors and substations too | `ConnectivityNode` + `BaseVoltage` | 0 |
| 2 | `overhead_line_conductor.cimtbl`, `underground_line_conductor.cimtbl`, `triplex_line_conductor.cimtbl` | conductors | `wire_info` | |
| 3 | `line_spacing.cimtbl` | line_spacing | **`ConductorDistanceSpacing` (S2-2, amended from XYSpacing):** GLM gives distances, not coordinates | |
| 4 | `line_configuration.cimtbl`, `triplex_line_configuration.cimtbl` | configurations | `line_by_wire_configuration` (WireConfiguration) or `line_by_impedance` (catalog), per record (GLM-11) | 2, 3 |
| 5 | `transformer_configuration.cimtbl` | transformer_configuration | `transformer_template`, `transformer_template_1ph` | |
| 6 | `regulator_configuration.cimtbl` | regulator_configuration | none on its own: read by the regulator mapper (structural) | |
| 7 | `substation.cimtbl` + the swing rows of the node files | substation, `bustype SWING` | `source` | 1 |
| 8 | `overhead_line.cimtbl`, `underground_line.cimtbl`, `triplex_line.cimtbl` | lines | `line_by_wire_configuration`, `line_by_impedance` | 1, 4 |
| 9 | `switch.cimtbl`, `fuse.cimtbl`, `recloser.cimtbl` | switches | `switch` | 1 |
| 10 | `transformer.cimtbl` | transformer | `transformer_by_template` | 1, 5 |
| 11 | `regulator.cimtbl` | regulator (+ its configuration) | `voltage_regulator`, `regulator` | 1, 6 |
| 12 | `load.cimtbl`, `triplex_load.cimtbl`, and the load rows of `triplex_node.cimtbl` | loads | `load` | 0b, 1 |
| 13 | `capacitor.cimtbl` | capacitor | `shunt` | 1, 8 (a control monitoring a line terminal) |
| 14 | `inverter.cimtbl` (+ nested `solar`/`battery` rows, D4 "induced") | inverter, solar, battery | `der` | 1 |

**Amended in S0:** in GridLAB-D a `load`, `capacitor` or `meter` is itself a node (a bus), and lines may end on
one, so ConnectivityNodes cannot wait for the equipment files. As in DSS, `bus.cimtbl` holds every root bus,
written from the topology walk; a child bus object resolves to its root (GLM-4). A meter then has nothing else to
write (GLM-5), so there is no `node.cimtbl` or `meter.cimtbl`.

## 3. Native passes the mappers share

These run on the reader's objects before any mapper and construct no CIM (I5).

### 3.1 Bus voltages and systems (GLM-1)

> **Superseded (GLM-1, decided 2026-11-09):** BaseVoltage is the walk's kV; a node's `nominal_voltage` is checked
> against it and disagreements are listed in `bus.cimtbl`, not raised. The rule below stopped 24 of 29 decks on the
> taxonomy meters' constant `nominal_voltage 480`.

Unlike DSS, every GLM node states its own `nominal_voltage`, line to neutral, in V (7200 on a 12.47 kV feeder,
120 on a triplex secondary). GridLAB-D uses it as the per-unit base and the initial guess. So the source of the
BaseVoltage is the node, not an inference. What the node does not say is its **system**: 7200 V phase to neutral
is a 12.47 kV BaseVoltage on a 3-phase feeder (even on a 1-phase lateral, `phases AN`), and 120 V is a 240 V
split-phase secondary.

The spoke builds a `cimtopology.core.Network` (sources: substation and SWING nodes; branches: lines, switches,
fuses, reclosers; transformers: one `Coil` per winding from the configuration, a regulator as equal-kV coils).
`walk(network)` gives each bus its `BusSystem`. Then, per root node:
- BaseVoltage kV = `nominal_voltage` × √3 on a 3-phase system, × 2 on a split-phase one, × 1 on a single-phase
  one, through one named, tested derived function, rounded by `cimtopology.core.nominal_kv` (so 7200 → 12.47).
- The walk's own kV for the bus must agree within 10 % (the DSS tolerance); otherwise the import raises with the
  node, both values and the coil that set the walk's value.

### 3.2 Phases and identity

- GLM phases (`ABCN`, `CAB`, `AS`, `BS`, `ABCD`, `S` on triplex) → CIM `PhaseCode` through a spoke code table,
  sorted (CAB → ABC). `D` selects a delta connection (mapped) and is not a conductor. `S` on a split-phase bus →
  `s1s2`, with `N` kept.
- mRID = prefix + the GLM `name` in source case (D3). An unnamed object is named by GridLAB-D `<class>:<id>`, and
  references (`from node:632`) use that form; the reader resolves both forms to one name, and a reference to an
  unknown object raises.

### 3.3 GLM defaults (GLM-3, as DSS-6)

A slot the deck does not set takes GridLAB-D's default, from the class's C++ `create()`/`init()`. The reader
leaves it `None`. Same rule as DSS-6: the default lives in the LinkML schema as a `glm_default` annotation (never
`ifabsent`); a mapper fills an unset slot through the core `schema_defaults(cls, "glm_default")` +
`fill_defaults`, and lists it in the row comment (`# defaulted: impedance=0.0001+0.00033j`). Each slice fills the
annotations for its own classes from the GridLAB-D C++ source, values only, citing the file. Derived defaults
(`power_rating` = the sum of the phase ratings when unset) are structural rules in the spec, not annotations.

### 3.4 Reader rules (S0, built 2026-11-09)

| is | becomes |
|---|---|
| a value with an inline unit (`2.5 MVAr`, `12MVA`, `distance_AN 30 in`) is converted to the slot's declared unit on read (`to_unit`) | kept as written: the reader records the written unit per (record, slot); the mapper puts it in the column header (GLM-2). No unit math in the spoke (I2) |
| an unresolved `${MACRO}` drops the field with a warning | raises, unless the caller passes it (`defines=`, like `gridlabd -D`; GLM-15) |
| a numeric slot whose text does not parse is stored in `_glm_expressions` and left `None`, silently | **amended in S0:** kept verbatim in `GlmModel.expressions`, slot unset; the orchestrator raises when one sits on a record a mapper reads (`check_expressions`). Raising in the reader would make every house deck unreadable (`random.normal(...)`), and the Java exports drive every load by `ieeezipload.value*44721.36` (GLM-8) |
| an object type with no schema class is logged at INFO and dropped | kept as a count on the model; the master lists it (`# not mapped: recorder 3`) |
| `#include` is ignored | followed relative to the including file; a missing file raises |
| `schedule`, `class`, `#ifdef` blocks are skipped | `schedule` blocks are kept by name (S4a needs them, GLM-8); `class` and `#if*` raise until a deck needs them |
| a duplicate object name overwrites silently | raises |
| a property set twice on one object | the last value is kept, as GridLAB-D does, with one warning per (class, property) and a count (182 fuses in R5-12.47-3) |
| `Object` (capital O) | raises: GridLAB-D's parser is case-sensitive (`load.cpp` `literal` uses `strncmp`) |
| `object house:..20 { ... }`, `object triplex_line_conductor: { ... }` | a range makes N copies with their nested objects; an empty header id is no id; an unnamed object is `<class>:<id>`, else `<class>:<position>` |
| complex text in polar form (`7200+120d`, `r` radians) | parsed (tests pin each form against the C++ parser's rules) |
| nested `object` blocks set `parent` | kept, and covered by a test (inverter → solar) |

Every rule has a reader test (`tests/test_glm_reader.py`).

### 3.5 S0 findings (2026-11-09)

- **Reader:** 28 of 29 decks read. IEEE123_transactive stops at line 26728 on `Object battery`, a typo GridLAB-D
  rejects too. All 29 read in about 10 s.
- **Schema fixes:** `glm_object` (the object header every GridLAB-D object has: `name` as identifier, `parent`,
  `groupid`, `latitude`, ...; no class publishes it, so the scrape never saw it) is the base of every object class,
  in `types/common.yaml` and in `linkml_generator.py`. `residential_enduse` is hand-written: it publishes the enduse
  struct with an empty prefix (`PT_enduse, ""`), so `power_fraction` & co. are direct properties of ZIPload,
  waterheater, house and 15 more, which the scrape does not expand (IEEE13_houses needs them). Doxygen `\p`-style
  commands in descriptions take their `@p` form (gen-python copied them into docstrings as invalid escapes).
  The unused `_directives` placeholders are removed. `triplex_node` inherits `powerflow_object`, not `node`, on
  purpose (`PT_INHERIT, "powerflow_object"` in `triplex_node.cpp`): the schema is right, so topology treats both
  `node` and `triplex_node` subclasses as buses.
- **Topology:** `WYE_WYE` ratings are line to line for any phase count (the taxonomy writes 12500/480 V on a 1-phase
  `CN` unit; GridLAB-D applies only the ratio to phase voltages and takes `Np = V_primary / sqrt(3)`), so every
  `WYE_WYE` coil is polyphase. A regulator is a branch (it keeps the voltage), not equal-kV coils. 27 of 29 decks
  walk with every bus reached; IEEE13_houses stops because its bus-634 center taps are rated 2401 V on a 480 V bus.
- **Node voltages (reopens GLM-1):** on every taxonomy feeder, every `meter` has `nominal_voltage 480`, whatever bus
  it is on: 1,449 meters on 480 V secondaries (where GridLAB-D reads 480 as phase to neutral, so 831 V line to
  line) and 20 on 12.47-34.5 kV primaries. IEEE13 cdpsm/assets and IEEE123 agree with the walk on every bus.
- **Core, on this branch:** `serialization.get_schema_annotations` re-parsed every YAML of a schema for each class
  it was asked about; GLM's 79 files cost about 4 s per class (80 s for IEEE13_cdpsm). It now parses each file once
  per process (`_load_yaml`). `scripts/leak-gate.sh` excludes a worktree's `.git` file. Candidate for core: the
  `AUTHORITY` constant, now defined in three spokes.
- **Deferred to their first consumer:** the `glm_default` helper (S1 or later, when a slice adds the first
  annotation) and the phase code table (S3a; not needed: the line and switch phases are letter sets, S3a-3, S3a-7).

## 4. Slices

Each slice delivers its mapper(s), atoms with goldens (`tests/atoms/<class>/`), its `CIMTBL_MAPPING.md` section
(the table generated with `fields_table(..., fields=FIELDS)`), and an extended deck sweep. `scaffold_mapper`
writes the stubs.

| slice | content | exit |
|---|---|---|
| S0 | workspace member + seed (§0); reader (§3.4); `importer/topology.py` (`glm_network` on `cimtopology.core`); orchestrator `glm_to_cimtbl.py` with `MAPPING_ORDER`, master document, `GlmImporter(CimtblImporter)`, the expression guard; small decks vendored (§5) | **built 2026-11-09:** 28 of 29 decks read and 27 walk with every bus reached, the stops listed as deck defects (§3.5); the IEEE13_cdpsm master binds |
| S1 | buses (`bus.cimtbl`: every root bus, BaseVoltage from the walk, GLM-1/4/5) and the swing source (`source.cimtbl`: substation / SWING buses, stiff default impedance, `BasePower`) | **built 2026-11-09 (CIMTBL_MAPPING.md S1):** every deck binds master + bus + source except the two listed deck defects; IEEE13_cdpsm bus and source goldens committed with the master's |
| S2 | catalogs: overhead/underground/triplex conductors (`wire_info`), line_spacing (XYSpacing), line_configuration and triplex_line_configuration (geometry → WireConfiguration, z-matrix → PerLengthPhaseImpedance; GLM-11, GLM-12) | **built 2026-11-09 (CIMTBL_MAPPING.md S2):** every catalog binds on the 27 decks that bind S1; geometry stays geometry (distances as written) |
| S3a | overhead/underground/triplex lines (ratings → OperationalLimitSet); switch, fuse, recloser (GLM-10) | **built 2026-11-09 (CIMTBL_MAPPING.md S3a):** every line and switching device binds on the 27 decks that bind S2; each geometry line's phases are its spacing's positions |
| S3b | transformer_configuration templates (3-phase by TankEnd, 1-phase, center-tap by lugs) and transformer instances (GLM-6) | **built 2026-11-09 (CIMTBL_MAPPING.md S3b):** every transformer binds on the 27 decks that bind S3a, each tank's %Z fields equal GridLAB-D's own `zt`/`zc` (or center-tap star) in ohms; IEEE13_cdpsm's agree with the DSS import in SI (expected differences listed) |
| S3c | regulator + regulator_configuration → `VoltageRegulator` + `RatioTapChanger` + `TapChangerControl` (GLM-7) | **built 2026-11-09 (CIMTBL_MAPPING.md S3c):** every regulator binds on the 27 decks that bind S3b (35 as 102 units), each unit's tap, step and band equal GridLAB-D's; IEEE13_cdpsm's agree with the DSS golden in taps, steps and ratios (expected differences listed: GLM holds no kVA or impedance, and the Java export wrote `MANUAL`) |
| S4a | load, triplex_load, triplex_node power; capacitor + its control (GLM-8) | every load and capacitor binds; IEEE13_cdpsm loads/caps equal the DSS golden's  **built 2026-11-10** |
| S4b | inverter + solar/battery (`der`, GLM-13) | the IEEE13_cdpsm DER bind (IEEE123_transactive's stop at the reader on `Object battery`) |
| S5 | deck sweep test (`tests/test_cimtbl_sweep.py`); tier-4 IEEE 13 GLM vs DSS check; G7 throughput on `orig_R3-12.47-3` (12,608 objects) | **built 2026-11-16 (CIMTBL_MAPPING.md S5):** 27 of 29 decks bind with every slice's GridLAB-D check and 2 stop as listed; the IEEE13_cdpsm directory (16 files) is the reference golden and binds on its own (D6); tier 4 at the root `tests/cross_format/` (13 tests); G7 about 5,500 rows/s |
| S6 | a utility's GridLAB-D decks (Milsoft WindMil exports, kept out of git) bind as GridLAB-D runs them | **built 2026-11-16 (CIMTBL_MAPPING.md S6):** the exports repaired so GridLAB-D loads them (the user's calls: widen 1-phase paths feeding wider sections; parallel cans for customers behind one 1-phase can; one nameplate to the bus; open ties across phases kept, so 10 decks need them removed to run in GridLAB-D); the converter maps coil-rated wyes, `SINGLE_PHASE`, matrix N, 0 diagonals, own-output `REMOTE_NODE`, open ties across phases (`phaseSide1`/`phaseSide2`), and checks link phases; all 22 bind with every slice check (`CIMHUB_GLM_UTILITY_DECKS`) |

## 5. Tests

- **Tier 1/1b per class:** a native GLM atom gives the golden; the golden plus prereqs binds.
- **Completeness:** `check_fields(FIELDS, NATIVE_CLASS)` per mapper.
- **Decks:** the small public decks are vendored in `cimhub_gridlabd/tests/decks/` with their origin (Powergrid-
  Models URL, license, edits) in its README: IEEE13_cdpsm (18 KB), IEEE13_assets (15 KB), IEEE13_houses (29 KB),
  IEEE123 (67 KB), `orig_GC-12.47-1` (17 KB), `orig_R1-12.47-3` (45 KB). The rest run when `CIMHUB_GLM_DECKS`
  points at a directory with the same layout (as `CIMHUB_DSS_DECKS`).
- **Deck sweep** (marked `roundtrip`): each deck binds or stops with a listed error; a new stop fails the test.
- **Bus voltages:** every node's BaseVoltage agrees with the walk (§3.1) on every sweep deck.
- **Cross-format (GLM-16):** IEEE13_cdpsm.glm is the Java CIMHub export of the same IEEE 13 model as the DSS
  importer's committed IEEE13_CDPSM golden. Per class, the GLM import must equal the DSS import in SI within
  tolerance, matched by connected nodes, with the expected differences listed (GLM has no source impedance, its
  regulators are banked, etc.). This is the end-to-end check while no engine is available.

## 6. Decisions

Each item has a recommendation and the slice that needs it.

| # | question | recommendation | slice |
|---|---|---|---|
| GLM-1 | Where BaseVoltage comes from | **Decided by the user 2026-11-09 (amended from the approved plan by the S0 data, §3.5):** the walk's kV from the source and transformer ratings (as DSS-1), which GridLAB-D's own solution follows. Each root bus whose `nominal_voltage`, on the walk's system, disagrees by more than 10 % is listed in `bus.cimtbl`'s comment, not raised. The taxonomy meters' constant `nominal_voltage 480` made the first rule stop 24 of 29 decks | S1 |
| GLM-2 | Inline units on values | Value-verbatim: the reader keeps the written unit; the column header carries it (`distance_AN (in)`, `nomQ (MVAr)`), and rows whose units differ go in separate `Table` blocks of the same class. The alternative, converting on read to the declared unit as GridLAB-D does, breaks I2 | S0 |
| GLM-3 | Defaults | `glm_default` annotation from the C++ source, filled per slice, applied by core `fill_defaults`, listed as `# defaulted` (as DSS-6) | S0 + per slice |
| GLM-4 | Parent-child nodes (7,492 triplex nodes, 25 nodes, 2 meters) | GridLAB-D solves a child as its parent's bus, so a child is not its own ConnectivityNode: its equipment lands on the root's node. The child's name is listed in the root row's comment (`# children: tn_2`); a child whose `nominal_voltage` or phases disagree with its root raises | S1 |
| GLM-5 | Meters | A meter or triplex_meter is a node: a ConnectivityNode, nothing more. Billing and measurement slots are untranscribed (no network-profile home) | S1 |
| GLM-6 | Transformers | **Amended in S3b (S3b-3, S3b-4, S3b-5, S3b-9):** GLM stores %Z, so the impedance and shunt go on the `TransformerTankConfiguration`'s `percentImpedance`, `loadLoss`, `noLoadLoss`, `percentMagnetizingCurrent`, moved to each tank's nameplate so GridLAB-D's ohms are kept (no mesh, no winding `r`); `WYE_WYE` voltages are line to line on every phase count (not phase to neutral); unequal cans are a tank each under a `TransformerBankConfiguration`; every configuration is written. Originally: a `transformer_configuration` is a template (`TransformerTankConfiguration`), every `transformer` a `PowerTransformer` + tank by template (D10 conventions; center tap by the DSS lug template, H1 H2 X1 X3 X2). Per-unit `impedance`/`impedance1`/`impedance2` and `shunt_impedance` go on the template in `(pu)` on its own base; the star→mesh split for the center tap is a named derived function (detail in the S3b spec). 1-phase `WYE_WYE` voltages are phase to neutral (`ratedU` LL is derived ×√3, `baseU` the coil) | S3b |
| GLM-7 | Regulators | **Amended by S3c-1/-2 (the user's): two ideal `AutoTransformerEnd`s, no tank end, no mesh, no `ratedS` (GLM has neither); GLM has no LTC, so no `PowerTransformerEnd`.** Follow DSS-13: equal-kV → `VoltageRegulator` (AutoTransformer). `control_level INDIVIDUAL` (or per-phase `tap_pos_X` that differ) → one 1-phase regulator per phase, each with its own `RatioTapChanger` + `TapChangerControl` (matches the three DSS units of IEEE 13); `BANK` → one gang unit, `ABCN` | S3c |
| GLM-8 | Loads | **Amended by S4a-2/-5 (the user's, 2026-11-10): a `<schedule>.value*K` base is K (TODO: CGMES schedule classes once profile export works); explicit constant current and impedance raise.** Per-phase p/q: a `load` is one EnergyConsumer with an `EnergyConsumerPhase` per phase (GLM loads are unbalanced by construction). Constant-power components are copied (complex → p, q); constant-current and constant-impedance components and the `base_power` + fraction form give derived ZIP fractions per load, with one LoadResponseCharacteristic per distinct fraction set (as DSS-7's `exp_` rows). A `base_power_X` that names a schedule raises until its rule is set (taxonomy/transactive decks) | S4a |
| GLM-9 | Swing source | **Decided 2026-11-09 (S1-2, S1-3):** `substation` and `bustype SWING` buses → `EnergySource`; voltage from `positive_sequence_voltage` / `voltage_A`; a stiff default impedance (|Z| = kV² / 10,000 MVA, X/R 10) so round trips work, since GridLAB-D's swing has none. `SWING_PQ` is ignored: a plain bus with a row comment, revisited if something breaks | S1 |
| GLM-10 | Switches | **Amended in S3a (S3a-6, S3a-7, S3a-10):** `status` gives `open` and `normalOpen`; a per-phase state that differs from it raises (no deck has one, so no `SwitchPhase` rows); N is dropped from a switch's phases; `sectionalizer` is not mapped (cim18v17 has no class, no deck has one). Originally: switch → LoadBreakSwitch, fuse → Fuse (`current_limit` → `ratedCurrent`), recloser → Recloser, sectionalizer → Sectionalizer; `status` → `open`/`normalOpen`; per-phase `phase_X_state` that differ → per-phase rows. Reliability slots (`mean_replacement_time`, `retry_time`) untranscribed | S3a |
| GLM-11 | Line configurations | **Amended in S2 (S2-9):** b derived from c (CIM has no capacitance on PhaseImpedanceData), rows compacted, and both forms on one record raise (GridLAB-D would use the matrix). Originally: a configuration with spacing + conductors is geometry (WireConfiguration); with `z11..z33` only, a `PerLengthPhaseImpedance` (`ohm/mi`, `c` in nF/mi verbatim). Both on one record: geometry, with the matrix untranscribed and noted (never substitute) | S2 |
| GLM-12 | Triplex geometry | **Amended in S2 (S2-8):** a derived `ConductorDistanceSpacing` (D12 = d + 2t, D1N = d + t, `triplex_line.cpp`), not an XYSpacing; the z-matrix cross-check is dropped (no readable deck has one). Originally: GLM gives a triplex configuration as conductors + `insulation_thickness` + `diameter`, with no spacing object. Recommendation: an `XYSpacing` derived from those (named function, the GridLAB-D triplex formula cited), so it stays geometry; check it against the triplex z-matrix the Java exports carry for the same conductors | S2 |
| GLM-13 | DER | `inverter` → `PowerElectronicsConnection` (`rated_power` is per phase in GLM: ratedS derived × phase count), nested `solar` → `PhotoVoltaicUnit`, `battery` → `BatteryUnit`. diesel_dg / windturb_dg: not mapped until a deck has one. **Amended by S4b (the user's calls, 2026-11-10):** the output is GridLAB-D's own (PV: its static-weather closed form, with the irradiance on `PhotoVoltaicUnit.irradiance`; a battery: its CONSTANT_PQ set point, CONSTANT_PF read as the Java export's defect); `ratedU` is the bus's line-to-line voltage; split phase is `s1s2` D across the legs; the datasheets are `GenerationInverterInfo`/`StorageInverterInfo`, `SolarArrayInfo`/`SolarPanelInfo` and `BatteryInfo` | S4b |
| GLM-14 | Not mapped | recorder, multi_recorder, player, fncs_msg, house, ZIPload, waterheater and every class with no deck: listed with counts in the master comment, so nothing disappears silently (as DSS-11). Houses have no network-profile home | S0 |
| GLM-15 | `${VSOURCE}` in the Java exports | `glm_to_cim(path, defines={"VSOURCE": ...})`; without it the reader raises naming the macro. Vendored IEEE13 atoms pass it explicitly | S0 |
| GLM-16 | Test oracle | No GridLAB-D engine is installed. For the importer: the tier-4 IEEE 13 GLM vs DSS comparison (§5) plus spot checks against the C++ formulas. Building GridLAB-D for power-flow parity is deferred to the exporter wave | S3b on |
| GLM-17 | GLM-JSON input | **Decided by the user 2026-11-09: deferred to a phase after the migration.** GLM-JSON is GridLAB-D's new official format (reference schema in GridLAB-D's `utilities/json_schema`), but `.glm` is the commonly used one, so the `.glm` reader comes first. The S0 reader keeps parsing (pass 1, raw objects) apart from typing (pass 2), so a JSON front end can feed the same pass 2 | after the migration |

Master-plan decisions this wave inherits: D6 (the reference golden is vendored), D7 (`Model` = the name the caller
passes), D9 (conductor ratings → `WireInfo.ratedCurrent` + AssetInfo `OperationalLimitSet`; line ratings on the
line's own set), D10 and D14 (no open delta in the decks, so it stays fail fast).

## 7. Dependencies

| owed by | item | blocks |
|---|---|---|
| user | TODO (S4a-2): a GLM load schedule (`<schedule>.value*K`) to the CGMES schedule classes (`ConformLoadSchedule`, `SeasonDayTypeSchedule`) once profile export works; today only K is mapped and the reference is a row comment. **2026-11-16, the user:** nc_schedule schedule classes now have a Parquet sidecar for their points (`cimhub_gdm/time_points.py`, rc_1 `1c800cc`), meant for GLM `player` files too. Moved to `cimhub_core.time_points` the same day by the user's direction (the `time-points` extra: pyarrow, cim-builder), so a GLM schedule/player slice can use it | a GLM schedule/player slice |
| user (cim-tables) | reference an `Identity`-only row by its `identifier`: `InverterInfo.InverterCapabilities` → `InverterCapabilities` (S4b-11). cim-tables does not index `Identity` rows today (`CIMTBL_DESIGN.md:141`), so S4b names the capability flag in the row comment instead of writing the row | S4b-11's `InverterCapabilities` |
| core | `der` shape: `p2` (and `storage_b2`) say `s1s2` Y at 208 V, two 120 V legs to neutral, from the DSS IEEE 13. GridLAB-D's split-phase inverter sits across the legs at 240 V (S4b-4, S4b-5), so the shape should show `s1s2` D at 240 V. The DSS exporter must then write such a DER across the legs | the exporter wave's GLM round trip |
| core | `shunt` shape and getter: per-phase `LinearShuntCompensatorPhase` b, for a gang capacitor whose `capacitor_A/B/C` differ. No deck has one: S4a-10 raises on it, and the getter keeps its raise | when a deck needs it |
| ~~core~~ | ~~`switch` shape: per-phase `SwitchPhase` states (GLM-10)~~ dropped in S3a (S3a-6): no deck has per-phase states, so they raise | — |
| core | transformer getter: read `percentImpedance`/`loadLoss` (with the center tap's Hopkinson split) where there is no mesh, and a bank of lugged template tanks by its phase ends; today it reads impedance only from winding `r` and the mesh and raises on a bank (S3b-5, S3b-9; the same %Z gap the DSS exporter hit). **Narrowed on rc_1 `d832796`:** `BY_TANK_IMPEDANCE` reads %Z, loadLoss and a bank from a tank with no template (the GIS form), with the Hopkinson center tap; what remains is reading the same values from the tank's `TankConfiguration` (GLM's form). **Done 2026-11-16:** a template with no winding `r` and no mesh reads its `percentImpedance`/`loadLoss` by the same split, and a bank of lugged template tanks is read can by can (`getters/transformer.py`) | done |
| core | candidates now used by two spokes: the center-tap lug layout (DSS `xfmrcode.py`, GLM `transformer_configuration.py`) and `limit_types` (S3b-11) | — |
| ~~core~~ | ~~control getter (S5-4)~~ **done 2026-11-21 (exporter wave):** `get_tap_changer_control` (via `get_regulating_control`) raised `targetValue is unset` on a disabled control. GLM's `MANUAL` regulators without a band (the 3 IEEE 13 units) have none, as GridLAB-D reads none; the getter should return `target` None when `enabled` is false. Tier 4 compares their taps and asserts the raise until then (`test_4_regulator_controls`) | the exporter wave |
| core | `source` shape: an ideal swing with zero impedance binds (GLM-9) | S1 |
| ~~core~~ | **done 2026-11-21 (exporter wave, `get_stored_distances`):** `getters.spacing.get_spacing_distances` needed every conductor's height, which 224 GLM spacings and every triplex spacing lack; distances do not need heights, so the check belongs in `get_spacing_xy` (S2-2, S2-8) | the exporter wave's GLM round trip |
| core | derived functions: LN→system kV (GLM-1), triplex spacing (GLM-12), ZIP fractions (GLM-8); each goes to `derived/` when a second spoke needs it, else stays in the spoke | S1, S2, S4a |
| ~~root workspace~~ | ~~`cimhub_gridlabd` added to the root `pyproject.toml` members and sources, then one `uv lock`~~ done in S0, with the same `cimtables` → `cim-tables` rename that is uncommitted on `rc_1` | — |
| user | `cim-topology` release (0.1.0, from 0.1.0a2 on PyPI) carrying `cimtopology.core`; then the root `../CIM-Graph-Topology-Processor` path source can become a version pin. Until then the sibling checkout must be on a branch with `cimtopology.core` (its `develop` lacks it) | the walk |
| user | TODO (X4, 2026-11-21, the user's): a GLM battery's `nominal_voltage` (its DC terminal voltage, 48 V in the IEEE 13 decks) must round-trip through `DCConductingAssetInfo`; until then the importer keeps only `BatteryInfo.numberOfCells` (floor(V / 4.1)) and the exporter leaves it unset, so GridLAB-D's internal battery model takes its `battery_type` default (`battery.cpp:665`). Not from `PowerElectronicsConnection.ratedU`, which is the AC side | a battery DC slice |
| user | review of this plan and of each slice's spec section | every slice |

## 8. The exporter wave (plan 2026-11-21, approved by the user the same day; X0-X5 built 2026-11-21, uncommitted)

`GlmExporter(FormatExporter).to_model(network) -> GlmModel`, written fresh in `cimhub_gridlabd/exporter/`, one module
per GLM class, on the core getters (`export-getters` skill), as DSS §8. The `GlmModel` it returns has the shape
`GlmReader.read_all()` returns (schema dataclasses), so a new `GlmWriter` writes a deck the reader and the importer
read back. CIMHub_2_0's `exporter/` (4,300 lines, cimhub_2026, `WireSpacingInfo`, a silent `WYE_WYE` default for
unknown winding pairs, a 1.0 V `nominal_voltage` fallback in the writer) is the oracle only. Each sub-slice has its
own section in `cimhub_gridlabd/docs/EXPORT_MAPPING.md`, approved before its code.

### 8.1 Sub-slices

| # | content | getters (new or changed in **bold**) |
|---|---|---|
| X0 | framework: `GlmExporter`, `EXPORT_ORDER`, `SLOTS` per class (`cimhub_core.export_slots`), naming (X1), `GlmWriter` (§8.2), the per-atom harness (§8.3); `node`/`triplex_node` from ConnectivityNodes (phases from the terminals, `nominal_voltage` LN from the BaseVoltage), the swing (X6) | `get_terminal_phases`, `get_base_voltage`, `get_source` |
| X1 | lines: `overhead_line_conductor`, `underground_line_conductor`, `triplex_line_conductor`; `line_spacing` from the spacing's distances; `line_configuration` / `triplex_line_configuration` by conductors + spacing (geometry) or by z-matrix (a PerLengthImpedance only); `overhead_line`, `underground_line`, `triplex_line`; `switch`, `fuse`, `recloser`, `sectionalizer` with `status` from the switch state | `get_wire_info`, **`get_spacing_distances` without heights** (§7 core row), `get_line_phase_impedance_matrix(expand_sequence=True)`, `get_switch_state`, `get_current_limits` |
| X2 | transformers: `transformer_configuration` + `transformer` for GridLAB-D's connections (X2), the wye-wye replacement for every other model (X3), the three-winding star split (X4); `regulator_configuration` + `regulator` from a VoltageRegulator | `get_transformer_units`, `get_transformer_model`, `get_tap_steps`, **`get_tap_changer_control` with `target` None when disabled** (§7 core row) |
| X3 | `load`, `triplex_load` (constant power/current/impedance per phase from the ZIP fractions), `capacitor` (+ its control) | `get_phase_loads`, `get_load_response`, `get_shunt_reactive_power`, `get_regulating_control` |
| X4 | `inverter` + nested `solar` / `battery` (GridLAB-D's per-phase `rated_power`, S4b's PV and battery rules inverted) | `get_der_output`, `get_inverter_units`, the DER rating getters |
| X5 | whole decks: the idempotence sweep over every binding GLM deck; cross-format, DSS-imported CIM (IEEE 13/123/8500) to GLM; power-flow parity in GridLAB-D (X9) | — |

### 8.2 Writer (X0)

A new `glm_writer.py` (reader-writer skill), not the CIMHub_2_0 one: class order as a `WRITE_ORDER` list (every
object after what it names: conductors, spacings, configurations, nodes, links, then loads and DER, which are
`parent`ed); a `clock` block and `module powerflow { solver_method NR; }`; one `object <class> { ... }` per record,
the slot's `native_name` and value only (a quantity in the slot's schema unit, a complex `a+bj` through one
`format_complex`); `None` never written. No fallback values: a class GridLAB-D cannot initialise without a slot
(`nominal_voltage`) raises in the exporter, naming the CIM object.

### 8.3 Tests

- **Per atom (tier 2, every sub-slice):** atom `.glm` → `glm_to_cim` → `to_model` → writer → reader → importer; the
  two `.cimtbl` texts equal, except each listed difference. An exported golden `.glm` is committed beside each atom
  (D6) so a diff shows what changed.
- **Transformer forms (X2):** atoms built as `.cimtbl` text for the forms no GLM deck holds (YNd, Dyn11, Yz, a
  three-winding YNyn0d1, an unregulated AutoTransformer), exported and checked against hand-computed GLM values (the
  star impedances, the leg ratings).
- **Idempotence (X5):** export(import(export(import(deck)))) is the same text as export(import(deck)) on every deck
  that binds.
- **Parity (X5):** bus voltages of the exported deck against the original in GridLAB-D 6.0 (X9).

### 8.4 Decisions

| # | question | recommendation |
|---|---|---|
| X1 | Names | DSS E1 unchanged: `cimhub_core.names.export_name` (`name`, `mrid`, `uri`; default `mrid`), sanitized by a GLM rule (`glm_safe_name`: no whitespace, `;`, `{`, `}`, quotes; `:` is GridLAB-D's class:id form, so replaced), one namespace per deck (GLM names are global), a collision raises naming both |
| X2 | Native transformer connections | **Decided by the user 2026-11-21: native where GridLAB-D's C++ has the model.** Two windings: Y/Yn–Y/Yn → `WYE_WYE` (one or two phases: lugged cans, `SINGLE_PHASE` is the same case, `transformer.cpp:263`); D–D on three phases → `DELTA_DELTA`; D–Yn on three phases at GridLAB-D's fixed shift (`DELTA_GWYE`: the high side leads the low side by 30°, `transformer.cpp:663`) → `DELTA_GWYE`; a centre tap (s1, s2, N) → `SINGLE_PHASE_CENTER_TAPPED`, its halves folded back into the full winding's R + jX by S3b's star (the importer's split inverted). %Z on winding 1's `ratedS` (the getter's default base), `primary_voltage`/`secondary_voltage` as S3b-3 |
| X3 | Every other two-winding model | **Decided by the user 2026-11-21:** a two-winding `WYE_WYE` from the PowerTransformerEnds' `ratedU`/`ratedS` and the (1, 2) mesh: Y–D, Yn–D, D–Y, D–Yn at another shift (Dyn11), Z/Zn, an open delta, an AutoTransformer that is not a VoltageRegulator. Each is logged once per unit and listed in `EXPORT_MAPPING.md` as an expected difference (the phase shift, the zero-sequence path, the grounding are lost). Four or more windings raise |
| X4 | Three windings (not a centre tap) | **Decided by the user 2026-11-21:** a star split into three two-winding transformers, winding i → a fake 1 kV star node (`<unit>_star`, three-phase, `nominal_voltage` 577.35 V LN). The star impedances on winding 1's ratedS: Zᵢ = (Zᵢⱼ + Zᵢₖ − Zⱼₖ) / 2, each leg on its own winding's `ratedS` (z × Sᵢ / S₁). The core on leg 1. Each leg's connection and a non-positive branch: §8.5 Q1, Q2 |
| X5 | Regulators | A VoltageRegulator → `regulator` + `regulator_configuration` (S3c inverted: band, steps, increment, taps per phase, `Control` from the TapChangerControl's mode and `enabled`). A RatioTapChanger on a plain PowerTransformer (an LTC) → the transformer at its actual tap folded into `primary_voltage`, the control dropped and listed |
| X6 | The swing | Each EnergySource → a `substation` (`bustype SWING`, `positive_sequence_voltage` from `nominalVoltage`, the angle). GLM's swing is ideal: a source impedance is not written and is listed (power flow differs from DSS by the source drop) |
| X7 | Values CIM leaves unset | DSS E4: the getters' `None` follows a written spoke rule with a comment; LinkML `glm_default`s are never read. GridLAB-D requires R > 0 and X > 0 on every `transformer_configuration` (`transformer_configuration.cpp:337`), so a winding with no `r` takes §8.5 Q2's floor |
| X8 | Units | Each GLM slot's unit is the schema's (`unit.ucum_code`; GLM has fixed units: ft, mile, ohm/mile, V, VA, nF/mile). The exporter asks each getter for that unit (`glm_schema.registry_unit`); no factor in spoke code |
| X9 | Oracle | GridLAB-D 6.0 from the PyPI `gridlabd` wheel (§8.5 Q3) |

### 8.5 The user's answers (2026-11-21)

- **Q1 the star legs' connection (X4): each leg keeps its winding's connection where X2 has one.** A D winding is
  `DELTA_GWYE` into the star (the delta on the winding's side), a Y/Yn winding `WYE_WYE`; any other winding is
  `WYE_WYE` (X3). So a YNyn0d1 keeps its d1 shift.
- **Q2 a non-positive R or X (X4, X7): a floor of 1e-6 pu.** A star branch, or a winding with no `r`, whose R or X
  is ≤ 0 is written at 1e-6 pu on its leg's base, logged once per unit and listed in `EXPORT_MAPPING.md`.
- **Q3 the parity oracle (X9): GridLAB-D 6.0**, a test oracle only, as `opendssdirect` is for DSS. X5 compares bus
  voltages with the original deck's. **2026-11-21:** v6.0 is released (tag `v6.0`, branch `release/v6.0`) with a
  `gridlabd` 6.0.0 abi3 wheel on PyPI (manylinux x86_64, macOS, Windows; Python >= 3.10) whose API loads a deck and
  reads node voltages (`GridLabD().load_glm`, `run`, `get_objects_by_class`, `get_object_property_value` → complex).
  So the oracle is a dev-group pin `gridlabd~=6.0.0` (the root `pyproject.toml`, bootstrap session), not a CMake
  build. The C++ citations in this plan are to v6.0 (`CIMHub_2_0/cimhub_gridlabd/gridlab-d`, fast-forwarded to
  `feature/1478` `3d2c998c`, whose source equals `release/v6.0`); v6.0 changes no transformer, regulator or line
  model since the importer wave's tree (checkpointing, macOS `isa_*` exports, formatting), only line numbers.
  **Confirmed 2026-11-21:** the 6.0.0 wheel (with its declared `nanobind-backend` 1.0.0, nanobind's split-mode
  runtime) loads and solves the vendored `IEEE13_cdpsm.glm` unedited under NR. Notes for the X5 harness: the wheel has
  no `gridlabd` CLI, only the library; `GridLabD` runs a worker process and returns only "failed to load model file",
  so load errors need `DirectGridLabD` (in-process, prints the parser's message), which lacks
  `get_object_property_value`; the Java exports' `ieeezipload.value*K` needs the GridAPPS-D run-file pattern
  (`module tape; class player { double value; }` and a `player` named `ieeezipload`), as a `schedule` source is a bare
  name (`ieeezipload*K`); the deck's bus `634` is `SWING_PQ`, a plain second swing without a `fault_check`, so it
  backfeeds `xf_xfm1` and blows `swt_fuse1`. As a PQ bus the feeder solves with no overload (650 at 1.0, `rg60`
  1.067/1.054/1.074, 671 1.003/1.027/0.999).

### 8.6 Built (2026-11-21)

All of X0-X5, spec `cimhub_gridlabd/docs/EXPORT_MAPPING.md` (its slot tables generated from `SLOTS` and checked).
`gridlabd~=6.0.0` is in the root dev group (by the user's direction). Results:

- GLM-origin (the Java exports, run as the importer reads them): IEEE 13 cdpsm (DER included), IEEE 13 assets,
  IEEE 123 within 2.5e-5 of the original in GridLAB-D; the PNNL exports solve; a second export(import()) pass is
  the same text on all five vendored decks that bind.
- DSS-origin (`tests/cross_format/test_dss_to_glm.py`, against OpenDSS's own frozen solution, line to line): native
  forms within 5e-4 (IEEE 13, IEEE 123, 4-bus YY and DY); the listed differences within their bounds (YD/GrdYD
  1.4e-3, CDPSM 3e-3, Assets 2 %, IEEE 37 1.75 %); OYOD and YYD solve.

Decisions taken in the build (on top of X1-X9, §8.5):

| # | decision | by |
|---|---|---|
| X10 | Single-phase units with a phase-to-phase coil on the same buses are one bank, then X2-X4 (YYD: a Y-Y-D star split; OYOD: an open-delta bank written WYE_WYE on its three phases) | the user, 2026-11-21 |
| X11 | A delta regulator bank is one `WYE_WYE` regulator, each coil's tap on its own phase: GridLAB-D 6.0 solves no delta regulator under NR (`OPEN_DELTA_ABBC` FBS only, the rest throw) | X3's rule, carried to regulators; listed |
| X12 | Battery `nominal_voltage` (DC) is unset until it round-trips through `DCConductingAssetInfo` (§7 TODO); not from ratedU, the AC side | the user, 2026-11-21 |
| X13 | A PV inverter is `CONSTANT_PF` at CIM's power factor (GridLAB-D's PV logic, S4b-1, so it reads back); a battery `CONSTANT_PQ` at its set point; PV loss factors 1 (CIM's p holds them) | S4b's rule |
| X14 | `line_capacitance TRUE` in the deck: CIM's b is model data, and GridLAB-D ignores every `c` without it | — |
| X15 | The importer's splits are inverted by name, so a GLM model round-trips: regulator units `<base>_<phase>` (S3c), capacitor units `<base>_<phase>` (S4a-8), a triplex 240 V part `<base>_12` (S4a-6) | — |
| X16 | Bare wires in an underground configuration: `outer_diameter` 1.2 x diameter (the Java exporter's); tape shields: `shield_gmr`, `shield_resistance` by Kersting eq. 4.89 (the Java exporter's): GridLAB-D needs both | — |
| X17 | Non-voltage capacitor controls (time, VAR, current) are MANUAL at the actual state, logged, as an LTC's control (X5); voltage-exponent loads with exponents 0, 1, 2 are ZIP | — |

Core getter changes (2026-11-21, tested): `get_wire_info` reads `rAC50`; `get_stored_distances` returns a
spacing's distances and heights as stored (partial, or empty), and `get_spacing_distances` no longer needs heights;
`get_regulating_control` returns `target` None on a disabled control.

### 8.7 The §8.3 tests that X0-X5 left out (2026-11-21, by the user's "go on to next phase"; uncommitted)

X0-X5 shipped without two of §8.3's tests, and they found exporter defects:

- **Tier 2** (`tests/test_export_atoms.py`): each importer atom deck (but the bare catalog, which `line.glm` includes)
  through the exporter and the importer again; the two CIM models are equal (`cimtables.diff_models`, SI) under the
  X1 names, except three listed differences: a template no equipment uses is not written (configurations are per
  use); a bus's `nominal_voltage` is its BaseVoltage's, so a deck's rounded 2401.78 V comes back 2401.7771 (a
  regulator end's baseU and neutralU, 1.2e-6); a battery's numberOfCells (X12's TODO). Each exported deck is the
  golden `<atom>.exported.glm` beside its atom.
- **The forms atom** (`atoms/transformer/forms.cimtbl`, CIM by balanced ends): YNd1, Dyn11, YNzn and an unregulated
  AutoTransformer written WYE_WYE (X3), a YNyn0d1 star split (X4), each checked against values computed in the test
  (the star branches, each leg on its own ratedS, the d leg DELTA_GWYE), committed as `forms.exported.glm` and
  solved in GridLAB-D 6.0.
- **IEEE 8500 (X5) was blocked in the DSS importer** (done in §8.8: the stop was another copy of the deck): switch `A333_48332_sw` (`bus1=D5746546-1_INT.3`,
  `phases` unset, so OpenDSS's 3) fills its conductors as OpenDSS does, nodes 3 2 3, and cimtables refuses phases
  `CBC` (`line.cimtbl`, `LoadBreakSwitch`). The deck is not vendored (`CIMHUB_DSS_DECKS`, `IEEE/IEEE8500/Master.dss`;
  its file names' case also differs from its `Redirect`s on Linux). Owed by the DSS spoke.

Defects the tests found, fixed (each in `EXPORT_MAPPING.md`):

| # | defect | fix |
|---|---|---|
| X18 | a BANK capacitor monitoring one phase (`pt_phase A` on ABC) raised | `pt_phase` the control's monitored phases, else the unit's own |
| X19 | the swing's `nominal_voltage` was the BaseVoltage's (7199.56 V for the deck's 7200), its `base_power` dropped | `nominal_voltage` the EnergySource's nominalVoltage / sqrt 3; `base_power` the graph's BasePower when it holds one |
| X20 | a triplex line's ratings were dropped | written on its service letter |
| X21 | a gang regulator (one VoltageRegulator on ABC) came back as three; a MANUAL regulator's compensator settings were dropped | one VoltageRegulator alone is `control_level` BANK, `PT_phase`/`CT_phase` its monitored phase; the compensator wherever CIM holds a line drop |
| X22 | an unequal-can bank (`powerX_rating`) came back as one transformer per can | a PowerTransformer's cans under one TransformerBankConfiguration are one WYE_WYE, named by it, each can's own pu x S_total / (3 S_can) (the importer's k inverted), which must agree |
| X23 | X13's PV rule wrote derating, soiling and the inverter's efficiency 1, so a deck with losses produced 1 / (0.95 x 0.95 x 0.9) of CIM's p; the array's tilt, azimuth, shading and the panel's efficiency were dropped | the datasheets written; `derating` = p / GridLAB-D's lossless static output at its defaults for what CIM lacks (the importer's `static_dc_output`; a 0 `Pmax_temp_coeff` is GridLAB-D's panel default, `solar.cpp:571`), so GridLAB-D's output is CIM's p from any origin; a p above it raises |
| X24 | a battery's `soc_reserve` and `max_charge_rate` were dropped; `max_charge_rate` was -minP and `max_discharge_rate` maxP, neither CIM's; no batteryType was written LI_ION | `soc_reserve` minimumE / ratedE, `max_charge_rate` chargeRateActiveMax, `max_discharge_rate` unset (both LOAD_FOLLOWING only); no batteryType is unset, GridLAB-D's UNKNOWN |
| X25 | a polyphase unregulated AutoTransformer raised (no ratedU; the X3 log line read an unset connection) | its ends' baseU, line to line on a polyphase end (the voltage_regulator shape) |
| X26 | (the user's review, 2026-11-21) X1 called any line with a WireConfiguration geometry; the test is WireConfiguration.WireSpacing. A WireConfiguration with only a PerLengthImpedance (a template DSS LineCode) is a matrix, and the WireConfiguration is the equivalence route an XYSpacing and a ConductorDistanceSpacing may both point to | core `get_line_geometry` (a configuration with a WireSpacing) and `get_line_code` (the line's PerLengthImpedance, else its WireConfiguration's; both set and different raise), used by the impedance getters and `line_key`. Then (the user's rule, 2026-11-21, DSS-14, skill `wire-configuration`) every importer writes a named catalog lines share (DSS LineCode, GLM z-matrix line_configuration, GDM catalog) as an `isTemplate=true` impedance behind a WireConfiguration `<lc>_wc` with no WireSpacing, and a line's own values as `ACLineSegment.PerLengthImpedance` with `isTemplate=false`. The DSS, GDM and GLM exporters read both through the two getters; the DSS exporter writes a line's own impedance inline |

GLM-origin parity after the fixes: IEEE 13 cdpsm 1.7e-5, IEEE 13 assets 9.6e-6, IEEE 123 4.0e-6 (was within 2.5e-5).

Core changes (tested): `getters.der` gains `get_photovoltaic_datasheet` (SolarArrayInfo + SolarPanelInfo) and
`get_inverter_datasheet` (GenerationInverterInfo / StorageInverterInfo, `chargeRateActiveMax`);
`getters.line_impedance` gains `get_line_code` and `get_line_geometry` (X26), and its getters read the code and
the geometry through them; `cimtbl_testing.assert_text_matches_golden` record-diffs only a `.cimtbl` golden and shows a unified diff for
another (an exported `.glm`).

### 8.8 IEEE 8500 (2026-11-21, by the user's "go for the next phase"; uncommitted)

X5's last deck. `CIMHUB_DSS_DECKS`' copy (`CIMHub_2_0/test_data/.../IEEE/IEEE8500/Master.dss`) binds in the DSS
sweep: its switch `A333_48332_sw` writes `phases=1`, so §8.7's stop (phases unset, OpenDSS's 3 filled as `CBC`) came
from another copy of the deck, not the importer. Three things stood between it and GridLAB-D:

| # | finding | done |
|---|---|---|
| X27 | its triplex codes carry a cmatrix (3.0 / -2.4 nF per kft), and a triplex matrix with b raised | the b is not written, logged per configuration: GridLAB-D 6.0's `triplex_line` has no shunt admittance (`triplex_line.cpp:315` fills only the series matrix), so no form holds it; about 0.1 VAr per kft at 240 V. Listed |
| X28 | its source impedance is a series Reactor (a SeriesCompensator, the feeder head), which no GLM module exported | `exporter/series_reactor.py`: a `series_reactor`, `phase_X_impedance` = r + jx on each phase, a link's ratings; r0/x0 other than r/x and a varistor raise (GridLAB-D's reactor has no coupling, `series_reactor.cpp:105`). The importer reads it back (`CIMTBL_MAPPING.md` S7, `importer/cimtbl/series_reactor.py`): equal phases → one SeriesCompensator, r0 = r, x0 = x; an unset phase (GridLAB-D's 0 is a switch stand-in) or the resistance/reactance aliases raise. Atom `atoms/series_reactor/` (tiers 1, 1b, 2) |
| — | the deck sets no regulator tap, so CIM's taps are neutral: frozen there with controls off the feeder collapses (0.70 pu in OpenDSS, 31 iterations; GridLAB-D's NR never converges and, at one instant, retries forever) | the harness's `SOLVED_TAPS`: both engines at the taps OpenDSS's own controlled solve reaches (`FEEDER_REGA` 1.0125 … `VREG3_A` 1.10), written into CIM's `step` before the export; OpenDSS's iteration cap raised to 100 |
| — | at full load GridLAB-D's NR stalls (a fixed mismatch of 1568; also with constant-impedance loads, a 100 MVA base, the reactor as a switch, or 2000 iterations) and solves at 0.9 (lowest bus 0.96 pu). **The user, 2026-11-21: keep 0.9 load**; their OPF team sees the same with this feeder's undersized secondaries | `LOAD_MULTIPLIER`: OpenDSS `loadmult` 0.9, the GLM deck's `base_power_X` × 0.9 |

Result: within 5.3e-3 line to line of OpenDSS (`m1069311`), bound 1e-2; the cause is not isolated (candidates:
1,177 centre-tap services, ideal regulators, X27). The test (import, export, both solves) takes 22 s.
