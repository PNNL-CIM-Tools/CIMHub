# GDM → cim18v17 importer on CIM-Builder: wave plan

**Status:** moved here 2026-11-08 from the predecessor repo, where it was planned 2026-11-06 for an in-place
replacement. Rewritten for the fresh start: the importer is written new, so nothing is ported or deleted family by
family. Branch `gdm-builder`, in a worktree beside the repo checkout (like `raw-v34`). **Phases 0-4 done and committed; Phase 5 (close-out) built 2026-11-09, for review** ([`PHASES.md`](PHASES.md)).
DSS/GDM parity is written on rc_1 after the merge.
**Master plan:** [`REWRITE_PLAN.md`](../../.development/REWRITE_PLAN.md), wave F2' (builder-native, D11).
**Contract:** the `cimtbl-import-contract` skill, reference §9 (builder-native spokes).
**Mapping rules:** [`GDM_MAPPING.md`](GDM_MAPPING.md), the Phase 0 deliverable.

## Outcome

`GdmImporter().to_cim(system)` returns a cim18v17 `FeederModel` built only through CIM-Builder keyword methods.

- GDM quantities go to builders verbatim as `Qty(magnitude, unit)`: no `.to()`, no `* 1e3`.
- Every GDM field is classified: `FIELDS` plus `check_fields` (I3).
- mRIDs are `mrid(prefix, gdm.name)`, with the name as written. GDM's `uuid` is never an mRID.
- GDM `*Equipment` catalogs become CIM 18 templates (I6).
- Each atom is a small GDM system built in the test, imported with `to_cim`, and compared with a reviewed `.cimtbl`
  golden through `cimtables.diff_models`.
- **The CIM model matches the other spokes.** Where the DSS wave has already decided a CIM model (D10 tank
  configurations, DSS-2 center-tap lugs, DSS-7 ZIP fractions, DSS-13 regulators), GDM follows it, and the goldens use
  the core shapes (`cimhub_core/shapes/`, the `cimtbl-shapes` skill). The same CIM should come out of a DSS deck and of
  the GDM system ditto makes from it.

## Why builder-native, not `.cimtbl` (D11, reconfirmed 2026-11-08)

- GDM has no file format. A `.cimtbl` for it would be a made-up dump of pydantic objects, not a verbatim native table,
  so I1/I4 buy nothing.
- GDM quantities carry their unit per value (one conductor in ft, the next in m). A `.cimtbl` column carries one unit
  in its header, so the spoke would have to convert, which breaks I2.
- The test goldens are `.cimtbl` in the core shapes. So the builders are checked against the same shapes the DSS and
  RAW spokes write: GDM is the first real parity check between CIM-Builder and cimtables.

## Ground rules

- **Invariants.** I2, I3, I5 (builders construct; the spoke never calls `cim.X(...)`), I6, I8 and I9 apply. I1, I4 and
  I7 don't: GDM writes no artifact. The reader (`gdm_reader.py`) is still the only module that touches the filesystem.
- **Scope.** This branch edits `cimhub_gdm/` plus the root `pyproject.toml` and `uv.lock`, which it changed to add the
  member and the `NREL-ditto` dev dependency. Nothing else at the root, not core, not the `../CIM-*` repos. Requests go to their owners:

  | need | owner |
  |---|---|
  | builders | the user (this session lists gaps, it never writes builders) |
  | cimtables, cimprofiles, cim-graph | their sessions, through `UPSTREAM_REQUESTS.md` at merge time |
  | core (`codes.py`, `derived/`, shapes) | the core owner |

- **Exporter: not in this wave.** The predecessor's CIM→GDM exporter is on the cimhub_2026 profile, which D13 removes.
  It is rewritten on the core getters in a later wave. Until then, there is no GDM round trip.
- **Dependency:** `grid-data-models~=2.4` from PyPI (2.4.1 at setup). `NREL-ditto~=0.1.8` is in the root `dev` group
  (added 2026-11-08, user decision) for the DSS → GDM sweep and parity tests; it pins `grid-data-models==2.4.1`. The predecessor ran an editable 2.3.3 checkout;
  2.4 adds the classes marked *new in 2.4* in [`CLASS_TARGETS.md`](CLASS_TARGETS.md).
- **Style** (`cimhub-style` skill): enum maps are plain dicts read through `lookup`; derived values come only from
  named, unit-tested functions; there is no try/except around builder calls; each catalog is built once.

## Decided

| decision | answer | where |
|---|---|---|
| builder-native | yes (D11, reconfirmed 2026-11-08) | above |
| feeders | several per system; each piece of equipment's container comes from its own feeder/substation | OPEN_DECISIONS 1 |
| time series | **first pass: dropped, with one warning** naming the components and series; the static snapshot is imported. Load series mapped onto nc_schedule EnergyConnectionSchedules since 2026-11-11 (actual values, points in Parquet) | OPEN_DECISIONS 2, [`TIMESERIES_NEEDS.md`](TIMESERIES_NEEDS.md) |
| network shell | CIM-Builder `cimbuilder.network.new_feeder_model` (B1) | OPEN_DECISIONS 3 |
| frequency | 60 Hz, `FREQUENCY_HZ = 60` | OPEN_DECISIONS 4 |
| BaseVoltage | line-to-line, rounded to 4 significant figures for dedupe and mRID | OPEN_DECISIONS 5 |
| 3-phase tank configuration (D10) | a TankEnd per winding, no phases on the template; instance end n = template end n; center taps by lugs (DSS-2) | OPEN_DECISIONS 6 |
| enums | builders take strings and build the enum (C1) | OPEN_DECISIONS 8 |
| Authority / Model (D7) | a fixed CIMHub `Authority`; `Model` = `DistributionSystem.name` | |
| regulators | a regulator template from CIM-Builder (B17, from the CYME regulator database + the GDM catalog); DSS-13 instances | OPEN_DECISIONS 7 |
| mRIDs, name clashes | `mrid(prefix, name)`; an empty or clashing name, or a GUID token, is rehashed into a new UUID (B18) | OPEN_DECISIONS 9, 10 |
| untranscribed values | in `FIELDS`; logged at `DEBUG` for a caller's log file when needed | OPEN_DECISIONS 11 |
| protection | fuse/recloser/breaker classes mapped; fuse curves and reclose sequences untranscribed | OPEN_DECISIONS 12 |
| loads | EnergyConsumer for balanced three-phase; EnergyConsumerPhase for unequal phases, single-phase and s1/s2 triplex | OPEN_DECISIONS 13 |
| switch class | by GDM equipment class | OPEN_DECISIONS 14 |
| catalog detail | map onto cim18v17 AssetInfo classes where they exist (B20), skip the rest | OPEN_DECISIONS 15-18 |

## Upstream status (checked 2026-11-08)

Builder requests went to the user on 2026-11-06, and the handoff landed on CIM-Builder `gdm_support` (`b57faa1`,
`6d05e54`). Round 2 (B17-B20) was filed 2026-11-08. The request text stays in the predecessor repo's private requests
doc, because B17 names vendor fields. What remains:

| id | item | owner | blocks |
|---|---|---|---|
| mesh | `TransformerMeshImpedance` mRID: the core shapes use `<xc>_mesh_<from><to>` (`xc_ct5_mesh_12`). `TransformerTankConfigurationBuilder` (uncommitted) writes `mesh_<FromWinding>_<ToWinding>`; `TransformerBankBuilder.add_mesh_impedance` still writes `<FromWinding>_mesh_<ToWinding>`. `PowerTransformerBuilder` already matches (`<xf>_mesh_<i><j>`) | user | Phase 3 goldens |
| U5 | builder modules that still import cimhub_2023 / cim18gad | user's cleanup agent (in progress) | none, if GDM uses only cim18v17 builders; a test checks no legacy profile is imported |
| B12 | Curve + CurveData builder | user | inverter efficiency and PV power-temperature curves (untranscribed until then, OPEN_DECISIONS 16) |
| B14 | bus coordinates | decision (OPEN_DECISIONS 12) | bus `coordinate` |
| B17 | regulator template (CYME regulator database + GDM catalog); cim18v17 has no AutoTransformer configuration, so the shape is the owner's call | user | `DistributionRegulator` (Phase 3) |
| B18 | `rehash_mrid(class_name, token)`: a GUID token → a new seeded UUID string; free text unchanged | user | empty or clashing names (until then a clash raises) |
| B19 | `GroundDisconnector` builder | user | `EarthingSwitchEquipment` (pending until then) |
| B20 | AssetInfo builders: `GenerationInverterInfo`/`StorageInverterInfo`, `BatteryInfo`, `SolarPanelInfo`, `SeriesReactorInfo`, `CoolingInfo`, `SwitchInfo`, + `AssetDatasheet` on the instance | user | nothing: those fields are untranscribed until it lands |
| B16, B16b | EnergyConnectionSchedule builder (nc_schedule, in the profile since 512fafd); `irradiance` on the PV builder | built 2026-11-11 at the user's go-ahead (uncommitted in CIM-Builder) | the time-series family; static PV irradiance |
| U3 (old R11) | a `.cimtbl` control row that monitors its own equipment's generated Terminal | CIM-Tables | capacitor-control **goldens** only; the builder path has no ordering problem |
| X2 | `va` and `kilova` (GDM's ApparentPower spellings) are undefined in the CIM unit registry. `kilovar`/`var` parse. W, VA and VAr share dimensions, so a wrong-quantity mapping never raises | CIM-Profiles | nothing: `UNIT_SPELLINGS = {'va': 'VA', 'kilova': 'kVA'}` covers it; risk 17 stays |
| X3b | the cim18v17 `protection` part fails to import (`TypeError: 'C' already defined`) | CIM-Profiles | nothing for GDM: the switch classes are in `electrical_unbalanced`, and fuse curves / reclose sequences are untranscribed |
| X7 | missing `cimtbl-translate` prefixes: PerLengthSequenceImpedance, Curve, general LoadResponseCharacteristic, InverterInfo, schedules (`ts_`) | CIMTBL-Models maintainers | those mRIDs; the DSS wave's choices (`ln_<line>_lc`, `zip_constant_*`, `exp_*`) are reused where they fit |

Closed since the 2026-11-06 plan: B1-B11, B13, C1-C6, D1-D9, X1/R14 (`Qty(v, 'percent')` on PerCent stores `v`), X4
(handled inside `new_feeder_model`), R7 `get_qty`, R8 `diff_models`, R10 (`#` in mRIDs), D10.

## Phases

[`PHASES.md`](PHASES.md) has the deliverables and exit checks.

| phase | goal | waits on |
|---|---|---|
| 0 | `GDM_MAPPING.md` (cross-cutting rules) | nothing |
| 1 | orchestrator, `shared.py`, coverage and time-series drop, network shell + buses + source, switches; `to_cim` end to end | Phase 0 approved |
| 2 | lines (matrix, sequence, geometry + wire/cable catalogs + limits), loads (incl. ZIP), capacitors (incl. control) | Phase 1 |
| 3 | transformers (catalog, instance, center tap) and regulators | mesh mRID fix; B17 for regulators |
| 4 | DER (PV, battery, inverter), reactors | B20 adds the AssetInfo parts later; reactors wait on OPEN_DECISIONS 17b |
| 5 | reference system end to end, XML round trip, docs | Phases 1-4 |
| built | time series onto nc_schedule (TIMESERIES_NEEDS.md T1-T6), 2026-11-11 | B16 |

**Companion docs:**
- [`FAMILY_RECIPE.md`](FAMILY_RECIPE.md): module layout, catalogs built once, the steps per family.
- [`CLASS_TARGETS.md`](CLASS_TARGETS.md): GDM class → CIM target, builder and phase.
- [`TEST_DESIGN.md`](TEST_DESIGN.md): the atom harness, goldens and assertions.
- [`OPEN_DECISIONS.md`](OPEN_DECISIONS.md): decisions (all but 12-rest and 17b answered 2026-11-08), and risks.
- [`TIMESERIES_NEEDS.md`](TIMESERIES_NEEDS.md): the nc_schedule mapping, decisions T1-T6 and the B16 builder request.
