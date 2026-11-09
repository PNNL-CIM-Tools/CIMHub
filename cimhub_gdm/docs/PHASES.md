# Phases

Index and decisions: [`GDM_REWRITE_PLAN.md`](GDM_REWRITE_PLAN.md). Each family follows
[`FAMILY_RECIPE.md`](FAMILY_RECIPE.md) and [`TEST_DESIGN.md`](TEST_DESIGN.md). Paths are under `cimhub_gdm/`. Each
family's `GDM_MAPPING.md` section is approved before its code (as DSS-12).

The 2026-11-06 plan put the network shell, buses and source in Phase 3 because their builders didn't exist. B1-B3 have
landed, so they move to Phase 1, and `to_cim` works end to end from the first slice. The phases are renumbered:
old 4 (transformers) is now 3, old 5 (DER) is now 4, old 6 (close-out) is now 5.

## Phase 0: mapping rules (docs only)

**Status:** drafted 2026-11-08, waiting for approval and open points G1-G6.

**Deliverable:** [`GDM_MAPPING.md`](GDM_MAPPING.md): build order and class roles, identity, code tables, units,
derived values, per-phase rules, BaseVoltage/containers/frequency, time series, shared CIM models with DSS, CIM 18
gaps, cross-cutting fail-fast rules, the atom list, and findings for other owners. Field tables were generated with
`fields_table` from `Cls.example()` and GDM's p5r test dataset. Each family adds its own section later.

**Exit:** the user approves `GDM_MAPPING.md` and answers G1-G6.

## Phase 1: scaffold, shell, buses, source, switches

**Status:** built 2026-11-08, waiting for review.
- `scripts/test-all.sh gdm`: 63 passed; the 8 opt-in gdmloader cases skip; 2 ditto decks xfail (ditto can't read them).
- The opt-in gdmloader sweep (`CIMHUB_GDMLOADER=1`): all 8 systems stop only at `PENDING` classes.
- The ditto sweep: the 4 readable decks do the same.
- Changes from the plan below:
  - `GeometrySwitch` moved to Phase 2, because its equipment is a geometry catalog.
  - The bus-voltage check across a switch is GDM's own validator, not ours.
  - Untranscribed values go to `DEBUG` through a local formatter, because core's `untranscribed_values` formats
    through `cell()`, which raises on GDM objects.

**Goal:** `to_cim(system)` works end to end on a system with a source, buses and switches, and the harness proves
itself on one complete family.

**Create:**
- `src/cimhub_gdm/importer/gdm_to_cim.py`: `GdmImporter(FormatImporter)` with `model_cls = FeederModel` and
  `to_cim(self, model, *, network=None)` matching the base signature; `gdm_to_cim(system)`; the lists `ORDER`,
  `INLINE`, `UNTRANSCRIBED`, `PENDING`; `check_coverage`, `check_unique_names`, `components`,
  `drop_time_series_warning`. Every class not ported yet starts in `PENDING`, tagged with its phase.
- `src/cimhub_gdm/importer/shared.py`: `qty`, `UNIT_SPELLINGS`, `system_voltage`, `base_voltage_mrid`, `phases_text`,
  `container_mrid`, `susceptance`, `FREQUENCY_HZ = 60`, `AUTHORITY`.
- `src/cimhub_gdm/importer/network.py`: `new_feeder_model(AUTHORITY, system.name, Feeder, ...)`, the other Feeders
  (`FeederBuilder`) and Substations (`SubstationBuilder`).
- `src/cimhub_gdm/importer/bus.py`: `DistributionBus` → ConnectivityNode + BaseVoltage, built before any equipment
  so `connectivity.add_connectivity` reuses the node. `coordinate` and `voltagelimits` per OPEN_DECISIONS 12;
  `in_service=False` raises.
- `src/cimhub_gdm/importer/source.py`: `DistributionVoltageSource` → EnergySource `src_` (`EnergySourceBuilder`:
  `add_connectivity`, `add_electrical`, `add_short_circuit`, `add_ssh`). Unequal per-phase values raise.
- `src/cimhub_gdm/importer/switch.py`: the switch classes and their equipment and controllers, the CIM class picked by
  equipment class (OPEN_DECISIONS 14; `EarthingSwitchEquipment` pending until B19). `is_closed` → `open` = not
  closed; `normalOpen` from the controller's `normal_state`, else from `is_closed`; `ampacity` → `ratedCurrent`;
  impedance matrices, `length`, fuse `delay` and `tcc_curve`, and the recloser controller untranscribed (no fuse
  curves or reclose sequences in cim18v17, OPEN_DECISIONS 12).
- Tests: `conftest.py`, `gdm_atoms.py`, `atoms/prereqs/shell.cimtbl`, `atoms/{shell,source,switch}/*.cimtbl`,
  `test_{shared,coverage,network,source,switch}_import.py`, `test_api_conformance.py`, `test_ditto_sweep.py`
  (every deck stops at a listed `PENDING` class for now).
- `README.md`: usage and what is still pending.

**Exit checks:**
- The shell, source and switch atoms pass `diff_models`; `check_fields` passes for every class touched.
- `test_coverage_import.py` passes, including the time-series drop warning.
- The no-legacy-profile test passes.
- `scripts/test-all.sh gdm` is green.

## Phase 2: lines, loads, capacitors

**Status: built 2026-11-08, awaiting review.** 116 passed, 8 skipped (gdmloader, opt-in), 2 xfailed (ditto can't read
two decks); the opt-in gdmloader sweep passes 8 of 8. With the Phase 3/4 classes stripped, all 4 ditto decks and all
8 gdmloader systems import through Phase 2 (SMART-DS p1rhs7: 1,841 lines, 1,896 loads). The spec is
`GDM_MAPPING.md` §15-§17. Changes from the plan below:
  - Lines keep their phases, balanced ABC included (G7, the DSS wave's S4b-9).
  - Limit mRIDs are `<ln>_norm` / `<ln>_emerg` and the cable prefix `cn_`, as the DSS goldens write them.
  - Wye loads and capacitors are `Y`, grounded; delta `D`, not grounded (the DSS wave's S4a), instead of `Yn`.
  - A capacitor's nomU is line-to-line for balanced ABC and the rating across the unit otherwise (the DSS rule), not
    always line-to-line. Unequal per-phase capacitors raise (the exit check), so no LinearShuntCompensatorPhase values.
  - A capacitor control is `cc_<capacitor>` (the DSS prefix); U3 had closed, so the control golden is not `xfail`.
  - `DailyTimedCapacitorController` is `PENDING`, not a raise inside the build.
  - Wire insulation is untranscribed (no builder keyword), so G5 is moot; the wire info's own limit set has no
    builder, so `emergency_ampacity` rates geometry lines only (`GDM_MAPPING.md` §14).
  - B18 landed: GUID and clashing names are rehashed (`shared.object_mrid`, `Naming`); every add function takes
    `naming` instead of `system_name`.
  - GDM validates a matrix's size against the line's phases and the voltage exponents' pairing, so those checks are
    GDM's.

**Create:** `importer/line.py`, `importer/load.py`, `importer/capacitor.py`; goldens `atoms/{line,load,capacitor}/`;
`test_{line,load,capacitor}_import.py`.

**Lines**
- MatrixImpedanceBranch → ACLineSegment `ln_` with PerLengthPhaseImpedance `lc_` (a catalog built once): lower
  triangle only (row ≥ column), identifier `<lc>_<row><column>`; raise on an asymmetric matrix; `conductorCount` = n;
  b = `susceptance(c, FREQUENCY_HZ)`; `calculatedFrequency` = 60 Hz.
- SequenceImpedanceBranch → ACLineSegment with PerLengthSequenceImpedance (prefix per OPEN_DECISIONS 9).
- GeometryBranch → ACLineSegment with WireConfiguration `wc_` → XYSpacing `spc_` (isTemplate) + XYConductorPosition
  `<spc>_<n>` + WireSequenceConfiguration `<wc>_<n>` → OverheadWireInfo `wire_` / ConcentricNeutralCableInfo
  `cable_`. Never substitute an impedance matrix for the geometry (`conductor-geometry` skill).
- Limits: the line's own OperationalLimitSet `<ln>_limits` with CurrentLimit `<ln>_normal` from `ampacity` and
  `<ln>_emergency` from the wire's `emergency_ampacity` where present; wire ratings on the wire info's set, as the DSS
  S2 slice does.

**Loads**
- OPEN_DECISIONS 13: a three-phase load with equal phases is one EnergyConsumer with the totals; EnergyConsumerPhase
  children only when the per-phase values differ, for a single-phase load (A, B or C), and for s1/s2 triplex.
- `num_customers` → `customerCount`.
- ZIP: pure constant-power, -impedance or -current loads reference the shared `zip_constant_pq` / `_z` / `_i`
  LoadResponseCharacteristics (DSS-7); any other tuple gets one LRC per distinct tuple.
- The phase count must equal the number of phase loads (the predecessor copied phase 0 onto extra phases).

**Capacitors**
- Totals on the LinearShuntCompensator: `nomU` (line-to-line, from `system_voltage`), `nomQ`, `bPerSection`; sections
  from `num_banks_on` / `num_banks` as `int`. Per-phase equipment that differs by phase → LinearShuntCompensatorPhase.
- Controllers → RegulatingControl `<cap>_ctrl` (`RegulatingControlBuilder`), mode from the controller class, target
  and deadband derived, Terminal = the capacitor's own terminal (GDM names no monitored element), `delay_on` →
  `aVRDelay` via `LinearShuntCompensatorBuilder.add_regulating_control`. `DailyTimedCapacitorController` raises.
- The control atom's golden needs U3 (a control row monitoring its own equipment's Terminal). Until U3 lands, the
  control atom is `xfail(strict=True)` on the golden, and its control values are asserted on the built objects.

**Exit:** atoms and `check_fields` pass for every class touched; fail-fast tests for an asymmetric matrix, unequal
per-phase capacitors and an unmapped `ConnectionType`.

## Phase 3: transformers and regulators

**Status: built 2026-11-08, awaiting review.** 160 passed, 8 skipped (gdmloader, opt-in), 2 xfailed; the opt-in
gdmloader sweep passes 8 of 8. With the Phase 4 classes stripped, all 4 ditto decks and all 8 gdmloader systems
import completely (SMART-DS p1rhs7: 503 transformers, 481 center taps). The spec is `GDM_MAPPING.md` §18-§19.
Changes from the plan below:
  - Catalogs follow the DSS wave's XfmrCode goldens: a TankEnd and winding per winding (`<xc>_end_<n>`,
    `<xc>_wdg_<n>`), or lugs for a center tap; no template phase ends. CIM-Builder had no TankEnd method; with the
    user's go-ahead this session added `add_transformer_tank_end` and loosened `add_transformer_winding` and
    `add_mesh_impedance` (B26, `GDM_MAPPING.md` §14; uncommitted in CIM-Builder).
  - Instance phase ends only for a center tap (its lugs need them); a by-end template's end n is the instance's end n.
  - Wye ends as GDM writes them (G8, user, revised): `Yn` when N is listed, `grounded` = `is_grounded`; a 1-phase
    wye coil gets its N. ditto-made data therefore imports ungrounded (its OpenDSS reader hard-codes
    `is_grounded=False`); the ask is in `GDM_MAPPING.md` §14. Taps are read for the phase conductors only.
  - B27 filed: no `grounded` on `add_auto_transformer_end`, so regulators leave `is_grounded` untranscribed.
  - G4 decided (user): taps from the instance, else the catalog; a RatioTapChanger with no control.
  - Regulators: one single-phase VoltageRegulator per phase, after CIMTBL-Models `regulator_example.cimtbl`;
    TapChangerInfo `tci_` is B17's catalog home; the stand-in impedance is untranscribed. GDM requires one controller
    per phase, so there is no gang regulator.
  - Prefix `vr_` (the CIMTBL-Models example) for regulators, not `xf_`.
  - Coupling indices: GDM requires every pair once, so they are never ambiguous; out of range raises.
  - Plain-transformer taps and the regulator shape are not in the DSS goldens yet (parity, §18-§19).

**Entry:** the mesh mRID fix (plan's upstream table) for transformers; B17 (regulator template) for regulators. The
two land separately: transformers don't wait for B17.

**Create:** `importer/transformer.py`, `importer/regulator.py`; goldens in `atoms/transformer/`, `atoms/regulator/`: single-phase, center-tap, 3-phase Dyn,
3-winding, regulator bank, regulator with LDC. Start each from the DSS S3b golden for the same pattern.

- **Catalog:** `DistributionTransformerEquipment` (and `PowerTransformerEquipment`) → TransformerTankConfiguration `xc_`
  per D10: TankEnd per winding (3-phase and non-center-tap), lugs + windings for a center tap (DSS-2), TransformerCore
  `<xc>_core`, TransformerMeshImpedance `<xc>_mesh_<i><j>`.
- **Instance:** `DistributionTransformer` → PowerTransformer `xf_` with TransformerTank `<xf>_tank` (`TankConfiguration` =
  `xc_`) and one PowerTransformerEnd `<xf>_<n>` per bus on that bus's node and phases, plus TransformerPhaseEnds
  (`TransformerBankFromConfigurationBuilder`).
- **Regulator** (OPEN_DECISIONS 7): the regulator catalog becomes the B17 template, and each `DistributionRegulator`
  becomes a VoltageRegulator (DSS-13: two AutoTransformerEnds) built from it, with RatioTapChanger `<xf>_tap` +
  TapChangerControl `<xf>_ctrl` from its `RegulatorController`.
- **Percent impedances:** winding `r` and mesh `r`/`x` are ohm-typed: `Qty(v, 'percent')` on the winding base, so the
  base is set first. Mesh x is on the From winding's base. One pairwise mesh per `coupling_sequences` entry; no
  hand-split of X for 3+ windings. Coupling indices are normalised 0- or 1-based by one tested function.
- **Regulators:** `step` = `tap_step(...)`; `highStep`/`lowStep` from `total_taps` and the pu limits; `controlled_bus`
  must be one of the regulator's buses, else raise; `TapChangerControl.Terminal` is the regulator's terminal on that
  bus; `monitoredPhase` = `controlled_phase`.
- **Connections:** OPEN_DELTA and ZIG_ZAG raise until mapped.

**Exit:** atoms and `check_fields` pass; percent values read back with `get_qty(..., 'percent')` equal GDM's numbers.

## Phase 4: DER and reactors

**Entry:** none beyond Phase 1. The AssetInfo parts (B20) and curves (B12) are untranscribed until their builders land
(OPEN_DECISIONS 15-18), and then added without changing the rest. The reactor waits on 17b.

**Create:** `importer/der.py` (and `importer/reactor.py` if 17 lands as a separate family); goldens; tests.
- **PV:** PowerElectronicsConnection `pv_<name>` with `ratedS` (from the inverter), `ratedU` (line-to-line), `p`, `q`;
  PhotoVoltaicUnit `<pec>_unit` with `maxP`. Irradiance untranscribed.
- **Storage:** PowerElectronicsConnection `storage_<name>` with BatteryUnit `<pec>_unit`: `ratedE`, `storedE` where GDM
  has it, `batteryState`.
- **Sign:** generation and discharge are negative `p`, through one named function.
- **AssetInfo** (OPEN_DECISIONS 15-18): `GenerationInverterInfo` / `StorageInverterInfo`, `BatteryInfo`,
  `SolarPanelInfo` on the PowerElectronicsConnection's `AssetDatasheet`, where slots fit; the rest untranscribed.
  Inverter controllers per OPEN_DECISIONS 12.
- **Curves:** untranscribed until B12 (OPEN_DECISIONS 16); then Curve + CurveData `<curve>_<n>`, deterministic.
- **Reactor:** per OPEN_DECISIONS 17b.

**Exit:** atoms and `check_fields` pass; `PENDING` holds only classes the user has signed off as waiting on upstream.

## Phase 5: close-out

- **Reference system:** an IEEE13-like system built in Python in `tests/gdm_atoms.py`, run through `to_cim()`, compared
  with `tests/atoms/e2e/reference.cimtbl` by `diff_models`.
- **ditto sweep and DSS/GDM parity** ([`TEST_DESIGN.md`](TEST_DESIGN.md)). The sweep test exists from Phase 1, and
  its list of expected stops shrinks phase by phase.
- **XML round trip:** build → `write_xml` (cim18v17) → reload → `diff_models(built, reloaded) == []`, and a PerCent
  value serializes as `5.0`.
- **Docs:** README (usage, cim18v17, gaps), `GDM_MAPPING.md` final field tables and atom list, these plan docs marked
  done, gaps logged upstream, open asks moved to `.development/UPSTREAM_REQUESTS.md`.
- **Exporter hand-off note:** the importer output is cim18v17; the CIM→GDM exporter wave restores the round trip.

**Exit:** `scripts/test-all.sh` green; the only `xfail`s are documented upstream ones.

## Later: time series

When the user's Curve + RegularIntervalSchedule profile and its builders (B16) land, per
[`TIMESERIES_NEEDS.md`](TIMESERIES_NEEDS.md) §4:
- one RegularIntervalSchedule per infrasys `time_series_uuid`, values verbatim in their units (unit `none` for
  multipliers), RegularTimePoints with deterministic identifiers;
- the link to each component's CIM equipment and scheduled attribute (N4);
- `NonSequentialTimeSeries` and `Deterministic` per N2 and N8;
- `drop_time_series_warning` is deleted, and the drop test becomes the family's atom.
