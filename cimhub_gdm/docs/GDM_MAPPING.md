# GDM → cim18v17 mapping rules

**Status:** Phase 0 approved 2026-11-08; Phases 1-4 (shell, buses, sources, switches; lines, loads, capacitors,
§15-§17; transformers, regulators, §18-§19; DER, reactors, §20-§21) built and committed; Phase 5 (the reference
system, the XML round trip) built 2026-11-09, for review. Cross-cutting rules only. Each family adds its own section
(field table generated from `FIELDS`, derived values, fail-fast list, atoms) when it lands, approved before its code.
**Plan:** [`GDM_REWRITE_PLAN.md`](GDM_REWRITE_PLAN.md); decisions: [`OPEN_DECISIONS.md`](OPEN_DECISIONS.md); targets:
[`CLASS_TARGETS.md`](CLASS_TARGETS.md). Contract: `cimtbl-import-contract` skill, reference §9 (builder-native).

**Samples** (skill `cimtbl-mapping-spec`: "classify real fields, never invented ones"):
- `Cls.example()` for each of the 68 concrete GDM 2.4.1 classes (every class but `Location` has one);
- `p5r.json` from the GDM repo's own test dataset (`tests/dataset/p5r/`, data format 2.0.1), loaded through GDM's
  upgrade chain: 65 components, 19 classes, 6 time series on 4 components, made by ditto from an OpenDSS feeder.

- ditto (`NREL-ditto` 0.1.8, a dev dependency; it pins `grid-data-models==2.4.1`) run over the vendored public DSS
  decks: IEEE13_original, IEEE123, IEEE37 and 4bus-OYOD convert (1,117 components in total). IEEE13_CDPSM and
  IEEE13_Assets fail inside ditto (§14).

- gdmloader (`uv run --with gdmloader`, not a dependency): all 8 `gdm_data` DistributionSystems at data version
  2_4_1 load on GDM 2.4.1 unchanged: 15,613 components. That includes `p1rhs7_1247`, a SMART-DS feeder with 13,380
  components: 2,510 buses with coordinates, 503 transformers (481 center-tap), 1,870 split-phase loads and 81 fuses.

None is committed here. Atoms build their systems in Python ([`TEST_DESIGN.md`](TEST_DESIGN.md)); ditto runs at test
time (§12, sweep and parity).

## 1. Build order and class roles

`ORDER` in `gdm_to_cim.py` is the build order, and it is the dispatch. A reference must exist before the object that
names it is built:

| # | step | GDM classes | role |
|---|---|---|---|
| 1 | network shell | `DistributionSubstation`, `DistributionFeeder` | shell |
| 2 | buses | `DistributionBus` (+ `VoltageLimitSet`, `Location` inline) | instance |
| 3 | catalogs | `MatrixImpedanceBranchEquipment`, `SequenceImpedanceBranchEquipment`, `GeometryBranchEquipment`, `BareConductorEquipment`, `ConcentricCableEquipment`, `DistributionTransformerEquipment`, `PowerTransformerEquipment` (+ `WindingEquipment` inline; a regulator's catalog also becomes a TapChangerInfo when a regulator first names it, B17) | catalog |
| 4 | sources | `DistributionVoltageSource` (+ `VoltageSourceEquipment`, `PhaseVoltageSourceEquipment`) | instance + inline |
| 5 | branches | the 3 switch components, `MatrixImpedanceFuse`, `MatrixImpedanceRecloser`, the 3 line components, `DistributionTransformer`, `DistributionRegulator`, `DistributionReactor` (+ their switch equipment, controllers, `RegulatorController`, `ReactorEquipment`) | instance + inline |
| 6 | shunts | `DistributionLoad`, `DistributionCapacitor` (+ load/capacitor equipment and capacitor controllers) | instance + inline |
| 7 | DER | `DistributionSolar`, `DistributionBattery` (+ `SolarEquipment`, `BatteryEquipment`, `InverterEquipment` inline; the inverter and battery equipment become an InverterInfo / BatteryInfo when a DER first names them, B20; `InverterController` and its settings are `PENDING`) | instance + inline |

Inline classes are in `INLINE` and read through their parent. Classes with no CIM home are in `UNTRANSCRIBED` with a
reason: `RecloserControllerEquipment`, `TimeCurrentCurve`, `Curve` (until B12), `ThermalLimitSet` (no GDM field
references it). A coverage test fails when a GDM release adds a class that is in no list.

## 2. Identity

- **mRID** = `object_mrid(PREFIX, component, cim_class, naming)`: `PREFIX` + the name as written. Prefixes come from
  the `cimtbl-translate` table: `sw_` `ln_` `lc_` `ld_` `cap_` `cc_` `src_` `xf_` `xc_` `vr_` `tci_` `cool_` `wire_` `cn_` `spc_` `wc_`
  `pv_` `storage_` `inv_` `batt_` `rx_` `bv_` `fdr_` `sub_`; buses are bare. A concentric cable is `cn_`, as the DSS wave writes CNData. Child mRIDs follow its child table (`<xf>_<n>`, `<xc>_end_<n>`, `<xc>_wdg_<n>`, `<xc>_mesh_<i><j>`,
  `<xc>_lug_<designation>`, `<end>_tap`, `<vr>_end<n>`, `<vr>_tap`, `<vr>_ctrl`, `<pec>_unit`, `<lc>_<row><column>`, `<spc>_<n>`,
  `<wc>_<n>`, `<ln>_limits`). Missing prefixes reuse the DSS wave's (`zip_constant_pq`/`_z`/`_i`, `exp_<p>_<q>`).
- **GUID names.** ditto names many GDM objects with a GUID string (p5r: every `LoadEquipment`, `InverterEquipment`,
  `SolarEquipment`, `VoltageSourceEquipment`, `MatrixImpedanceSwitchEquipment` and `DistributionTransformerEquipment`,
  e.g. `372a4dea-63f2-4737-bc0f-5549c04b3d54`). `cimprofiles.identity` would take a GUID-shaped mRID verbatim as the
  object's identifier. So when the name is a GUID, the mRID is `rehash_mrid(cim_class, name)` with no prefix (B18;
  OPEN_DECISIONS 9). Only catalogs are affected, because inline objects take child mRIDs from their parent. `<guid>_1`
  (p5r phase loads) is free text, not a GUID.
- **Empty or clashing names** → `rehash_mrid(cim_class, str(gdm.uuid))` (OPEN_DECISIONS 10).
  `shared.name_clashes` finds them once per import (`Naming.clashing`). In p5r and every gdmloader system, only inline
  objects have empty or repeated names. **B18 landed** (`cimbuilder.network.rehash_mrid`, CIM-Builder working tree,
  2026-11-08): GUID-named catalogs import (SMART-DS p1rhs7: all 38 line codes are rehashed).
- **Feeders and substations** can't be rehashed: their mRIDs are fixed before `new_feeder_model` sets the model scope
  that `rehash_mrid` seeds from. An empty, GUID or clashing feeder or substation name raises (`check_shell_name`); no
  sample has one.
- **`uuid`** is structural: it is used only for the rehash and for the time-series warning, never copied.
- **Names** go to `IdentifiedObject.name` unchanged, GUID names included. ditto's output (IEEE13) has GUID names on every
  transformer, load and capacitor equipment and on 6 of 36 line-code equipments.
- **Model name.** The CIM `Model` is `system.name`. ditto leaves it `None`, so `to_cim` raises on an empty name, and the
  sweep sets `system.name` to the deck stem first.

## 3. Code tables

Plain dicts in the family modules, read through `lookup(table, value, slot=, record_id=gdm.name)`. An unmapped value
raises. Values are CIM enum strings, and builders build the enum (C1).

| table | GDM → CIM | used by |
|---|---|---|
| `PHASE` | `A`→`A`, `B`→`B`, `C`→`C`, `N`→`N`, `S1`→`s1`, `S2`→`s2` | every `phases` string; `phases_text` joins in written order (`[S1, S2, N]` → `s1s2N`) |
| `SHUNT_CONNECTION` | `STAR` → `Y`, grounded; `DELTA` → `D`, not grounded (as the DSS wave writes loads and capacitors; GDM has no grounding flag); `OPEN_DELTA`, `OPEN_STAR`, `ZIG_ZAG` raise (`PhaseShuntConnectionKind` has no home for them) | loads, capacitors |
| `TANK_END_CONNECTION` | `STAR` → `Y`, `DELTA` → `D` on the template's TankEnd; open and zig-zag raise | transformer catalogs |
| `end_connection` | instance end, as GDM writes it (G8): a 3-phase STAR end is `Yn` when its phases list N (the neutral brought out), else `Y`; a 1-phase STAR end `Y`; DELTA `D`; a center tap's low side `I`. `grounded` = the winding's `is_grounded`; a grounded delta raises | transformer instances |
| `VOLTAGE_TYPE` | `line-to-line` or `line-to-ground`; selects the `system_voltage` factor (§5) | buses, sources, windings, capacitors, DER |
| `BATTERY_STATE` | `charging`, `discharging`; `idling` → `waiting` | batteries |
| `CAPACITOR_CONTROL_MODE` | by controller class: Voltage → `voltage`, Current → `currentFlow`, ActivePower → `activePower`, ReactivePower → `reactivePower`; DailyTimed raises (OPEN_DECISIONS 12) | capacitor controls |
| ~~`WIRE_INSULATION`~~ | not built: no wire or cable builder has an insulation-material keyword, so `insulation` is untranscribed (§15; G5 is moot until one does) | |

GDM's `WireInsulationType` values are relative permittivities (`XLPE = 2.3`); the DSS wave leaves its `EpsR`
untranscribed for the same reason.

## 4. Units

- **Verbatim.** `qty(q)` = `Qty(q.magnitude, str(q.units))`: GDM's own unit, no `.to()`, no `* 1e3`. GDM units vary
  per object (p5r lengths in `kilometer`, the examples in `meter`; impedances in `ohm / kilometer`, `ohm / meter` and
  `ohm / mile`), which is why this spoke is builder-native.
- **Spelling map.** `UNIT_SPELLINGS = {'kilova': 'kVA', 'va': 'VA'}`. Every other unit seen in the samples parses in
  the CIM registry, and an unknown spelling raises.
- **Quantity-kind guard.** W, VA and VAr all convert into each other in the CIM registry (checked:
  `1 kilowatt` → `1000 VAr`), so a power in the wrong quantity is never caught by units. `qty(q, kind)` therefore
  checks the unit name against the target's kind (`active`: watt family; `reactive`: var family; `apparent`: va
  family) and raises on a mismatch. The samples already have such mismatches:
  - GDM's `example()`s set `reactive_power` to `1000 watt` (`DistributionSolar`, `DistributionBattery`);
  - p5r sets `SolarEquipment.rated_power`, a GDM `ActivePower`, to `3.0 kilova` (**G1**).
- **Percent and per-unit floats.** GDM documents these bare floats as percent; they go to builders as
  `Qty(v, 'percent')` (R14):

  | field | CIM | note |
  |---|---|---|
  | `WindingEquipment.resistance` | `TransformerWinding.r` (percent on the winding's baseU/baseS) | ohm-typed: `z_base` conversion, so baseU/baseS first |
  | `DistributionTransformerEquipment.winding_reactances` | `TransformerMeshImpedance.x` (percent on the From winding) | one per coupling pair |
  | `magnetizing_current_pct` | `TransformerTankConfiguration.percentMagnetizingCurrent` | PerCent |
  | `pct_no_load_loss`, `pct_full_load_loss` | `noLoadLoss`, `loadLoss` (W), derived (§5) | |
  | `SolarEquipment.resistance` / `reactance`, battery and inverter efficiencies, `cutin`/`cutout_percent` | untranscribed | no home (B20 may add some) |

  Per-unit floats: `tap_positions`, `min_tap_pu`/`max_tap_pu` (tap derivations, §5); `cutoff_voltage_pu`,
  `min`/`max_voltage_pu` untranscribed.
- **Value + unit pairs.** `CircuitBreakerEquipment.interrupting_current` (`25.0`) and `interrupting_current_unit`
  (`kiloampere`) → `Qty(25.0, 'kiloampere')`. The unit field is structural.

## 5. Derived values

Each is a pure, named function in `shared.py` (or its family module), with a unit test against an independent formula.

| function | formula | notes |
|---|---|---|
| `system_voltage(v, voltage_type, phases)` | `line-to-line`: v; `line-to-ground` on a split-phase (`S1`/`S2`) bus: 2v; other `line-to-ground`: √3·v | buses and 3-phase ratings. Every sample bus is `line-to-ground`. 7.19977 kV → 12.47 kV, 39.84 kV → 69 kV, and p1rhs7's 1,667 `S1S2` buses at 0.1201 kV → 240 V. Single-phase A/B/C buses at 7.2 kV → 12.47 kV (the system's BaseVoltage). Coil voltages (`baseU`, 1-phase and center-tap windings) are never multiplied; the transformer section says which value is the coil |
| `base_voltage_mrid(v_system)` | 4 significant figures; `bv_<kV with p>kv` at ≥ 1 kV, else `bv_<V>v` | 12.4700 kV → `bv_12p47kv`; 4.1600 kV → `bv_4p16kv`; 0.48003 kV → `bv_480v` |
| `susceptance(c, f)` | b = 2πf·C, in pint (`Qty(2π·60·C.magnitude, f'hertz * {C.units}')`) | per matrix element, negative off-diagonals included; 10 nF/km → 3.7699e-9 S/m |
| `injection(power)` | −power (`0.0 − v`, so zero stays 0.0) | PV output and battery discharge in the CIM load sign; also `q` (§20) |
| `battery_state(p)` | discharging if p > 0, charging if p < 0, else waiting | GDM `active_power` is the output |
| `panel_power(rated_power)` | the panel's active power; an apparent unit is taken as the same active one, with a WARNING | ditto writes the panel Pmpp in kVA (§14, §20) |
| `coupling_pairs(equipment)` | GDM `SequencePair` indices → 0-based winding pairs | the examples and every gdmloader system are 0-based (center taps `0→1, 0→2, 1→2`); the GDM repo's p5r is 1-based (`1→2`). 0-based if any index is 0, else 1-based. GDM requires every pair exactly once, so a complete set is never ambiguous; an index out of range raises |
| `loss(pct, rated_s)` | noLoadLoss = pct_no_load × S / 100; loadLoss = pct_full_load × S / 100, active power in S's prefix | p5r: 0.6 % and 1.74408 % of 75 kVA. 1.74408 = 2 × 0.87204 (the winding r), a consistency check the test asserts |
| `tap_step(tap_pu, total_taps, min_pu, max_pu)` | neutralStep = 0; highStep = +total_taps / 2; lowStep = −total_taps / 2; stepVoltageIncrement = (max − min) / total_taps × 100 %; step = (tap − 1) / ((max − min) / total_taps) | a tap position, never a ratio; 32 taps, 0.9-1.1 → ±16, 0.625 %. Raises on an odd count, an asymmetric range, or a tap between steps. Computed here, not by `cimbuilder.core.tap_steps`, whose exact float comparison rejects 0.9-1.1 (§14) |
| `regulator_targets(controller)` | targetValue = v_setpoint × pt_ratio; targetDeadband = bandwidth × pt_ratio; min/maxLimitVoltage = the limits × pt_ratio | PT-secondary settings → primary V |
| `system_voltage` / `coil_voltage` / `winding_powers` (§18) | ratedU line-to-line; baseU the coil; ratedS, baseS per coil | |
| `ldc_ohm(v_setting, pt_ratio, ct_primary)` | R or X in ohm = v_setting × pt_ratio / ct_primary | GDM gives `ldc_R`/`ldc_X` in volts (the relay setting); CIM `lineDropR`/`lineDropX` are ohm |
| `capacitor_targets(controller)` | targetValue = (on + off) / 2; targetDeadband = off − on; × pt_ratio or ct_ratio | |

## 6. Per-phase values

GDM carries several values per phase where CIM has one per object:

| GDM | equal on every phase | differs by phase |
|---|---|---|
| load `phase_loads` p/q (OPEN_DECISIONS 13) | one EnergyConsumer, totals, **no** EnergyConsumerPhase (G3: `phases=None`) | totals plus EnergyConsumerPhase p/q. A standalone single-phase load and an s1/s2 triplex load always get phase children. SMART-DS writes each triplex customer as two loads, one on `S1` and one on `S2` (935 each in p1rhs7), so each is a single-phase load with one child |
| load ZIP coefficients | one LoadResponseCharacteristic | raise: CIM has one LRC per EnergyConsumer |
| switch `is_closed` | `Switch.open = not is_closed[0]` | SwitchPhase `open` per phase (`SwitchPhaseBuilder`) |
| capacitor `phase_capacitors` | LinearShuntCompensator totals | raise (the Phase 2 exit check; per-phase children carry no values yet) |
| capacitor `state` | `sections` = `num_banks_on` when on, else 0 | raise (G6, as recommended) |
| capacitor `controllers` | one RegulatingControl | raise |
| source `voltage`, `voltage_type`, r/x | EnergySource values | raise (EnergySourcePhase has only `phase`) |
| source `angle` | `voltageAngle` = phase A's angle; the others must be 120° apart | raise otherwise; p5r is A 0°, B 120°, C 240° (**G2**) |
| transformer `tap_positions` | nominal: nothing to write; off nominal: a RatioTapChanger per end (G4) | raise: one RatioTapChanger per end |
| regulator `tap_positions`, `controllers` | | one VoltageRegulator, tap changer and control per phase (§19) |

## 7. BaseVoltage, containers, frequency

- **BaseVoltage:** one per distinct `base_voltage_mrid(system_voltage(bus.rated_voltage, bus.voltage_type,
  bus.phases))`. Every ConnectivityNode names its BaseVoltage (cim18v17 `ConnectivityNode.BaseVoltage`). Equipment
  takes the BaseVoltage of its (first) bus.
- **Containers** (OPEN_DECISIONS 1): `EquipmentContainer` = the component's `feeder`, else its `substation`, else the
  system Feeder `fdr_<system.name>`. Buses use the same rule for `ConnectivityNodeContainer`.
- **Frequency:** `FREQUENCY_HZ = 60`, written as the BaseFrequency (through `new_feeder_model`) and as
  `calculatedFrequency` on every PerLengthImpedance.

## 8. Time series

Mapped since 2026-11-11 (`importer/time_series.py`, [`TIMESERIES_NEEDS.md`](TIMESERIES_NEEDS.md) §5) when the caller
passes `time_points`: a load's `active_power` / `reactive_power` go to one `EnergyConnectionSchedule` `<ld>_pq`
(`_p` / `_q` when their times differ), named by the series' `profile_name`, else the load's. The points go to the
`EnergyConnectionTimePoint` table. Any other series is dropped with one `WARNING` listing class, name, and each
series' variable name, type and features; without `time_points`, all of them are. In p5r this is two loads × (`active_power` PMult,
`reactive_power` QMult) and two PV systems × `irradiance` PMult, all `use_actual=False` multipliers.

## 9. Shared CIM models with the DSS wave

GDM writes the CIM the DSS spoke writes for the same equipment, so a DSS deck and its ditto-made GDM system can be
compared (a cross-format test). Where the DSS wave decided a model, GDM follows it:

| topic | DSS decision | GDM |
|---|---|---|
| tank configuration | D10, the XfmrCode goldens | catalogs → `TransformerTankConfiguration`: a TankEnd and winding per winding, no template phases; a center tap by lug. The DSS wave's 3-phase *Transformer* (no XfmrCode) is still balanced ends with no tank (§18) |
| center tap | DSS-2 (lugs H1 H2 X1 X3 X2, additive polarity) | `is_center_tapped = True` |
| ZIP | DSS-7 (`zip_constant_pq`/`_z`/`_i`, `exp_<p>_<q>`) | pure Z, I or P loads reference the shared rows; exponents → `exp_` rows; any other tuple gets its own row |
| switch class | DSS-9 | by equipment class (OPEN_DECISIONS 14) |
| regulators | DSS-13 (VoltageRegulator + AutoTransformerEnds) | one single-phase VoltageRegulator per phase with lugs and a series winding (CIMTBL-Models `regulator_example`), TapChangerInfo from B17; the DSS wave writes ends and a mesh, no winding (§19) |
| line limits | S2 / S3a (`<ln>_limits`, `<ln>_norm` + `<ln>_emerg` CurrentLimits; wire ratings on the WireInfo's set) | the catalog's `ampacity`, or a geometry's first conductor's `ampacity` and `emergency_ampacity`, on the line's set. The wire info's own set has no builder (§14) |
| balanced phases | S4b-9: blank for balanced ABC on every device but lines and transformer ends | the same (`builder_phases`); lines keep their phases |
| loads, capacitors | S4a: wye grounded, delta not; nomU as the DSS kV (line-to-line for 3-phase, across the unit otherwise); one section; `cc_` controls on the own terminal by Update | the same; `cc_<capacitor>` (GDM controllers have no names) |

## 10. CIM 18 gaps

Untranscribed unless noted. Each is logged in `CIMTBL-Models/distribution/CIM18_GAPS.md` by its owner.

| GDM | why |
|---|---|
| bus `coordinate` (`Location` x, y, crs) | ConnectivityNode is not a PowerSystemResource (B14). In SMART-DS data, x/y are longitude/latitude with `crs = None`; the synthetic cases use (0, 0) |
| bus `voltagelimits` | OperationalLimitSet hangs on equipment or terminals, not on a ConnectivityNode |
| `in_service = False` (any class) | no CIM home for "modelled but out of service" on these classes; **raises** |
| fuse `delay`, `tcc_curve`; recloser controller | no `FuseCharacteristicCurve` / `RecloseSequence` in cim18v17 |
| switch-equipment r/x/c matrices, `construction`, `trip_circuit_count` | a switch has no impedance in CIM |
| `TransformerMounting`, PV irradiance, PV R/X, battery idling efficiency, inverter ramp limits, cut-in/cut-out and efficiency, reactor length | no home; the B20 AssetInfo classes have no slot for them (§20, §21) |
| DailyTimed capacitor control, inverter controllers | `PENDING`, so they **raise** (OPEN_DECISIONS 12, still open) |
| curves | until B12 |

## 11. Fail fast (cross-cutting)

The importer raises on each of these, naming the class, the object and the field:
- a class that is `PENDING` or in no list, orphan inline equipment, supplemental attributes;
- an unmapped enum (the `lookup` message), an unknown unit spelling, or a power unit of the wrong kind (§4);
- a GUID or clashing name until B18 lands;
- per-phase values CIM can't hold (§6);
- coupling indices out of range (§5); the transformer, regulator and DER cases in §18-§20;
- `in_service = False`;
- a `RegulatorController` whose `controlled_bus` is not one of the regulator's buses, or whose `min_v_limit` >
  `max_v_limit`. GDM's own `RegulatorController.example()` has 132 V / 102 V, swapped.

## 12. Atom list

One golden per row in `tests/atoms/<family>/`, each on the shared shell ([`TEST_DESIGN.md`](TEST_DESIGN.md)).

| family | atom | covers | needs |
|---|---|---|---|
| shell | `shell_only` | 2 feeders + substation, buses at 4.16 kV LL, 2.4018 kV LG (→ `bv_4p16kv`), 480 V, 240 V split-phase | B1, B2 |
| source | `balanced_3ph` | EnergySource, LG voltage → LL, angle, r/x/r0/x0 | B3 |
| switch | `load_break`, `breaker`, `disconnector`, `fuse`, `recloser`, `one_phase_open`, `second_feeder` | class by equipment, SwitchPhase, container from `feeder` | switch builders |
| line | `matrix_3ph`, `matrix_1ph`, `sequence_3ph`, `geometry_overhead`, `geometry_cable`, `limits`, GeometrySwitch (built: `lines.cimtbl`) | catalogs once, ωC, lower triangle, geometry not matrices | B4-B6, B13 |
| load | `balanced_3ph`, `unbalanced_3ph`, `single_phase_b`, `triplex_s1s2`, `one_leg`, `delta_bc`, `zip_general`, `exponential` (built: `loads.cimtbl`) | decision 13, ZIP rows | B11 |
| capacitor | `fixed_3ph`, `single_phase`, `delta`, `off`, one per controller kind (built: `capacitors.cimtbl`; U3 closed, no `xfail`) | sections, nomU, control targets | B10 |
| transformer | `dyn_3ph` (p5r's 75 kVA unit, Dyn1, ONAN), `three_winding` (catalog tap), `single_phase` (1-based couplings, instance tap), `phase_to_phase`, `center_tap` (built: `transformers.cimtbl`) | D10, DSS-2, percent r/x, losses, coupling indices, G4, G8 | the TankEnd method (§14) |
| regulator | `single_phase_ldc`, `bank` (built: `regulators.cimtbl`) | per-phase VoltageRegulator, TapChangerInfo (B17), tap step, LDC ohms | |
| der | `pv_3ph` (two sharing an inverter), `pv_split_phase` (an unnamed inverter), `pv_one_phase` (absorbing vars), `battery_discharging`, `battery_charging` (built: `der.cimtbl`) | sign, PEC + unit, InverterInfo / BatteryInfo (B20), ratedU line-to-line | B20 |
| reactor | `three_phase`, `one_phase` (built: `reactors.cimtbl`) | SeriesCompensator, Terminal phases, r0 = r | `SeriesCompensatorBuilder` (§14) |
| e2e | `reference` (built: `e2e/reference.cimtbl`, self-contained, `Model = ieee13`) | an IEEE13-like system end to end: every family on one feeder, catalogs shared across instances | all |

**Sweep** (not atoms, nothing committed): ditto converts each vendored public deck that it can read, and `to_cim`
must either import it or stop with a listed reason (a `PENDING` class or a §11 fail-fast). This is the GDM equivalent
of the DSS deck sweep. An opt-in second sweep runs the same check over the gdmloader systems (network, never in CI).
The **XML round trip** (`test_xml_round_trip.py`) writes every atom family in one system to cim18v17 XML,
reloads it, and expects `diff_models` to find nothing. The **DSS/GDM parity** test imports the same deck through the
DSS spoke and through ditto + `to_cim`, and compares the two models with `diff_models`. It is matched by topology,
not mRID (a cross-format test, root `tests/cross_format/`), with ditto's known losses (regulators, angle sign, grounding) as listed
expected differences. It is written on rc_1 after this branch merges (user, 2026-11-09; `PHASES.md` Phase 5).

## 13. Open points for approval

- **G1. Power in the wrong quantity in real data.** p5r's `SolarEquipment.rated_power` (GDM `ActivePower`) is spelled
  in `kva` (3.0 and 5.0), so the §4 guard raises and p5r can't import. The gdmloader copy shows what the value is: the
  inverters are 2.5 kVA and the output is 2.5 kW, so `rated_power` is the PV array's real-power rating (OpenDSS
  `Pmpp`), and only the unit word is wrong. *Recommendation:* keep the guard, and for exactly this field read a
  va-family spelling as the same-magnitude watt spelling (`kva` → `kW`) into `PhotoVoltaicUnit.maxP`, with a note.
  This is a spelling fix like `UNIT_SPELLINGS`, not unit math. Any other mismatch raises.
- **G2. Source angle convention.** p5r gives A 0°, B 120°, C 240°, and so does every gdmloader system. ditto shows
  where this comes from: IEEE13's
  `Vsource angle=30` (standard ABC rotation) becomes A 30°, B 150°, C 270°. So the +120° is ditto's convention, not
  an ACB system. *Recommendation:* accept a 120° spacing in either direction and write phase A's angle as
  `voltageAngle`. Report the convention to ditto/GDM (§14).
- **G3. Balanced loads without phase children.** **Decided (user, 2026-11-08):** balanced three-phase equipment of every
  class passes `phases=None` to its builder (`shared.builder_phases`), so it gets no per-phase children and no
  Terminal phases. The DSS wave has to adopt the same rule. The original question: decision 13 wants no
  EnergyConsumerPhase for a balanced 3-phase load. Both CIM-Builder (`add_connectivity(phases=...)`) and cimtables (the `phases` column) write the
  Terminal's phases only through `add_phase_children`, which always creates the children. The core `load` shape's
  `ld_y1 … ABC` row therefore makes three children too. Options:
  - (a) a builder/cimtables option to set Terminal phases only, plus a core shape change (DSS S4 adopts it too);
  - (b) leave phases unset on balanced loads, so absent means ABC.

  *Recommendation:* (a). It needs the CIM-Builder and CIM-Tables owners, and the DSS wave to agree before S4.
- **G4. Off-nominal taps on a plain transformer.** **Decided (user, 2026-11-08):** a RatioTapChanger on that
  PowerTransformerEnd with `step` from `tap_step` and no control. The tap is the instance's `tap_positions` when set
  and off nominal, else the catalog winding's (ditto writes DSS `taps=` on the catalog: IEEE123 1.0375, p1rhs7
  1.03125); both off nominal and different raises (§18).
- **G5. `WIRE_INSULATION` mappings.** Moot for now: no builder keyword takes an insulation material (§3, §15).
- **G6. Capacitor `state`** (`list[bool]`) vs `num_banks_on`. ditto writes a single entry (`[True]`) even for a
  3-phase bank, and GDM's own `example()` one per phase, so `state` is either one entry for the whole bank or one per
  phase. **Built as recommended (Phase 2), for confirmation:** sections = `num_banks_on` when `state` is on, 0 when off;
  any other length, or a state that differs by phase, raises.
- **G7. Lines keep their phases** (Phase 2, following the DSS wave's S4b-9). G3's "every class" would give a balanced
  ABC line no ACLineSegmentPhases, but those carry the conductor order that a PerLengthPhaseImpedance's rows and a
  WireConfiguration's positions are numbered by, and the DSS goldens keep them. *Built:* lines always write
  `phases`. OPEN_DECISIONS 13 is amended to say so.
- **G8. Wye neutrals.** **Decided (user, 2026-11-08, revised the same day):** map GDM as written. Y and Yn are
  different transformers, so the grounding flag is never overridden. A 3-phase wye end is `Yn` when the winding's
  phases list N (the neutral brought out), else `Y`; `grounded` = `is_grounded`. A single-phase wye coil written
  with one phase (`A`) returns to the neutral, so its end is `AN` (GDM treats N as optional there; that is GDM's
  meaning, not a grounding claim). The first draft grounded every wye; it was withdrawn.
  - Consequence for DSS-derived data: ditto's OpenDSS reader hard-codes `is_grounded=False` (a TODO,
    `readers/opendss/components/transformers.py:113`) and lists N only for an explicit `.0` node, so every
    ditto-made wye imports ungrounded, and `Y` unless the deck spelled out the neutral (p1rhs7: 481 center taps
    `I` ungrounded, 481 primaries `Y` ungrounded on `xN`, 43 3-phase `Y` ungrounded). The DSS goldens write `Yn`
    grounded for the same decks, so DSS/GDM parity shows these until ditto reads the grounding (§14).

## 14. Findings for other owners

| owner | finding |
|---|---|
| core | `cimtbl._samples` tests `value == []`, which is ambiguous for numpy arrays. So `fields_table`/`fields_stub` crash on GDM's matrix and coordinate quantities. Use an explicit emptiness check |
| GDM maintainers | the gdm-cases data at format 2.0.0 can't load on 2.4.1: the upgrade chain starts at 2.0.1, and relabelled files then fail `PhaseVoltageSourceEquipment` validation. `RegulatorController.example()` has min/max voltage limits swapped. `example()`s use `watt` for reactive power |
| CIM-Profiles | W, VA and VAr interconvert in the CIM unit registry (X2) |
| gdmloader (0.0.5) | Downloads are cached outside the working directory (nothing lands in the cwd). It pins `fsspec`/`gcsfs ~=2025.3.2`, so it runs as `uv run --with gdmloader`, not as a workspace dependency |
| infrasys | `System.list_parent_components` misses components held in a list (`VoltageSourceEquipment.sources`) and components nested in another component (a switch equipment's controller). So the orphan check walks the model fields itself (`gdm_to_cim._referenced_uuids`) |
| GDM (validation) | GDM already rejects a switch between buses of different line-to-ground voltage, and `conductor_phases` that don't cover exactly the switch phases, so the importer doesn't repeat those checks |
| GDM (validation, Phase 2) | GDM checks a matrix catalog's size against the line's phases, and that both voltage exponents are set together; it does not check a geometry's conductor count, so the importer does |
| CIM-Builder (Phase 2; filed as B21-B25 on 2026-11-08) | (a) no builder links an `AssetInfo` to its `OperationalLimitSet`, so a wire's `emergency_ampacity` has no home on the wire info (the DSS wave writes `wire_<x>_limits`); (b) `OperationalLimitSetBuilder.add_limit_type` has no `durationKind` (the core `common` shape writes it); (c) no builder sets `Equipment.normallyInService` (the DSS wave writes it on loads and capacitors); (d) `ConcentricNeutralCableInfoBuilder` has no `diameterOverNeutral`, and no wire builder an insulation material; (e) `LinearShuntCompensatorBuilder.add_connectivity` requires `compensatorType`, which the DSS goldens don't write. (b), (c) and (e) are differences the DSS/GDM parity test will show |
| CIM-Builder (Phase 3, edited in this session with the user's go-ahead, 2026-11-08, uncommitted) | `TransformerTankConfigurationBuilder` had no TankEnd method, required lugs on every winding (and named it by lug), and required template phase ends on a mesh (B26). Added `add_transformer_tank_end(endNumber, connectionKind, grounded, rground, xground)`; `add_transformer_winding` takes `FromTransformerEnd`/`ToTransformerEnd`, optional lugs, an optional `TransformerWinding` mRID and an optional `connection`; `add_mesh_impedance` takes the ends optionally. Builder suite 172 → 176 passed. B27 (filed): `VoltageRegulatorBuilder.add_auto_transformer_end` has no `grounded` (the DSS goldens write it), so a regulator winding's `is_grounded` is untranscribed. Still open there: `cimbuilder.core.tap_steps.tap_steps_from_boost_buck` compares the boost and buck step with `!=`, so 0.9-1.1 pu (10.000000000000009 vs 9.999999999999998 %) raises; use `math.isclose` |
| CIM-Profiles | `TransformerTankEnd` is sliced only into `construction` (connectionKind, TankConfiguration); its `endNumber`, `grounded`, `rground`, `xground` are in no part, so the new builder method sets them through the merged profile |
| ditto (Phase 3, grounding) | the OpenDSS reader writes `is_grounded=False` on every winding (`readers/opendss/components/transformers.py:113`, "TODO: Should be moved to the transformer model"), and `winding_phases` gets N only from an explicit `.0` node, though OpenDSS grounds an unspecified wye neutral. Its CIM and CYME readers do read grounding. Ask: set `is_grounded` from the bus nodes (and the default `.0`) |
| ditto (Phase 3) | regulators become plain transformers with the solved tap on the catalog (a `taps=[1 1.0625]` regulator comes back 1.025); delta windings are written line-to-ground (kV / √3), and a delta tertiary whose bus is not that voltage fails GDM's 15 % check. gdmloader p1rhs7's center taps have reactances (0-1, 0-2, 1-2) = (2.4, 1.6, 2.4): H-X1 ≠ H-X2, which no symmetric center tap has; today's ditto writes XHL, XHT, XLT in that order correctly, so the data predates it. Imported as written |
| GDM (validation, Phase 3) | GDM checks a transformer's coupling count and distinct pairs, a center tap's 3 buses with bus 2 = bus 3, winding voltage within 15 % of the bus, and one regulator controller per phase, so the importer doesn't repeat those checks |
| ditto (Phase 4) | the OpenDSS PVSystem reader writes the panel's Pmpp as `ActivePower(kw_dc, "kilova")` (`readers/opendss/components/pv_systems.py`, `_build_pv_equipment`), so `SolarEquipment.rated_power` is in kVA; gdmloader p5r has it too. The importer takes it as kW with a WARNING (§20). Its `readers/opendss/components/storage.py` is empty, so no DSS Storage reaches GDM; and it sets `InverterEquipment.dc_to_ac_efficiency` from `%Pmpp`. Ask: write kW, and read Storage |
| CIM-Builder (Phase 4, edited in this session with the user's go-ahead, 2026-11-08, uncommitted) | there was no SeriesCompensator builder (OPEN_DECISIONS 17b). Added `cimbuilder/object_builder/line/series_compensator.py`: `SeriesCompensatorBuilder` with `add_connectivity(node1, node2, phases, EquipmentContainer, BaseVoltage)` (phases on both Terminals: the class has no per-phase child), `add_electrical(r, x)` and `add_short_circuit(r0, x0)`; 3 tests, builder suite 176 → 179 passed. `PowerElectronicsConnectionBuilder` has no `grounded` (commented out) and its `ratedS` docstring says VAr |
| ditto (0.1.8) | IEEE13_CDPSM fails (`TypeError: 'NoneType' object is not iterable`, `branches.py:187`); IEEE13_Assets fails (`'str' object cannot be interpreted as an integer`, in geometry); regulators (Transformer + RegControl) become plain `DistributionTransformer`s with no controller and `tap_positions=None`; phase angles step +120° (B leads A); `system.name` is `None`; `voltage_type` set as a `str`, not the enum (pydantic serialization warnings). The importer reads enums through `VoltageTypes(value)`, so both forms work |

## 15. Lines (Phase 2)

`importer/line.py`. Catalogs are built eagerly, once each, before any instance (§1); an instance names its catalog
by the catalog's mRID.

A matrix or sequence catalog is a named catalog shared by lines, so it is a template (DSS-14, as a DSS LineCode): the
PerLengthImpedance has `isTemplate=true` and is held by a WireConfiguration `<lc>_wc` (the catalog's name, its
`PerLengthImpedance`, no WireSpacing). Its lines name that WireConfiguration and set no `ACLineSegment.PerLengthImpedance`
of their own. A geometry catalog is a WireConfiguration that names a WireSpacing.

| GDM | CIM | rule |
|---|---|---|
| `MatrixImpedanceBranchEquipment` | PerLengthPhaseImpedance `lc_<name>` + PhaseImpedanceData `<lc>_<row><column>`; WireConfiguration `<lc>_wc` | lower triangle (row ≥ column, 1-based, conductor order); r, x as written; b = `susceptance(c)` = 2π·60·C; `conductorCount` = n; `calculatedFrequency` = 60 Hz; `isTemplate` = true. Non-square, mismatched or asymmetric matrices raise |
| `SequenceImpedanceBranchEquipment` | PerLengthSequenceImpedance `lc_<name>`; WireConfiguration `<lc>_wc` | r, x, r0, x0 as written; bch, b0ch = 2π·60·C1, C0; `isTemplate` = true |
| `BareConductorEquipment` | OverheadWireInfo `wire_<name>` | gmr; radius = diameter / 2; `ac_resistance` → rAC25, `dc_resistance` → rDC20 (as DSS); ampacity → ratedCurrent |
| `ConcentricCableEquipment` | ConcentricNeutralCableInfo `cn_<name>` | as DSS CNData: `phase_ac_resistance` → rAC25, `strand_ac_resistance` → neutralStrandRDC20, `cable_diameter` → diameterOverJacket; radii from diameters |
| `GeometryBranchEquipment` | XYSpacing `spc_<name>` (isTemplate) + XYConductorPosition `<spc>_<n>`; WireConfiguration `wc_<name>` + WireSequenceConfiguration `<wc>_<n>` → the wire or cable info | positions as written; `numberOfPhases` and the positions' `kind` are not written (GDM's catalog doesn't say which conductor is the neutral) |
| `MatrixImpedanceBranch`, `SequenceImpedanceBranch`, `GeometryBranch` | ACLineSegment `ln_<name>` | node1/node2, `phases` always (G7), length as written, BaseVoltage of bus 1; `WireConfiguration` (the catalog's `<lc>_wc` or the geometry's `wc_<name>`); `<ln>_limits` with `<ln>_norm` (the catalog's ampacity, or a geometry's first conductor's) and `<ln>_emerg` (that conductor's `emergency_ampacity`; a cable has none) |
| `GeometrySwitch` | LoadBreakSwitch `sw_<name>` (switch.py) | as every switch; ratedCurrent from the geometry's first conductor |

OperationalLimitTypes `olt_normal` / `olt_emergency` (as the core `common` shape, without `durationKind`, §14) are
created the first time a line names them.

**Fail fast:** asymmetric or mismatched matrices; a geometry line whose phase count isn't its conductor count (GDM
checks the matrix case itself); a line without exactly 2 buses; `in_service=False`.

**Atoms** (`tests/atoms/line/lines.cimtbl`, `gdm_atoms.add_lines`): a 3×3 matrix code shared by two lines (one
written CAB), a 1×1 code in ohm/km, a sequence code, an overhead geometry with a neutral (ABCN on two ABCN buses), a
cable geometry, a GeometrySwitch; ratings. A GUID-named catalog is rehashed (`test_line_import.py`).

**Real data:** every gdmloader and ditto line is a `MatrixImpedanceBranch`; no sample has a sequence or geometry
line, a cable or a GeometrySwitch. SMART-DS p1rhs7: 1,841 lines (1,186 on S1 S2), 38 codes, all imported.

**`MatrixImpedanceBranch`**

| MatrixImpedanceBranch field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | structural | never copied; the rehashed mRID when the name is empty or clashes (B18) |
| `name` | `str` |  | copied | `create.mRID`, `create.name`; mRID = ln_ + name; a GUID name is rehashed (B18) |
| `substation` | `Optional[DistributionSubstation]` |  | structural | EquipmentContainer when there is no feeder |
| `feeder` | `Optional[DistributionFeeder]` |  | structural | EquipmentContainer |
| `in_service` | `bool` |  | structural | False raises: no CIM home |
| `buses` | `list[DistributionBus]` |  | structural | node1, node2; BaseVoltage from bus 1 (GDM requires equal bus voltages) |
| `length` | `Distance` |  | copied | `add_connectivity.length` |
| `phases` | `list[Phase]` |  | structural | ACLineSegmentPhase per conductor, in conductor order, balanced ABC included |
| `equipment` | `MatrixImpedanceBranchEquipment` |  | structural | WireConfiguration <lc>_wc (the template); its ampacity → the line's normal CurrentLimit |


**`SequenceImpedanceBranch`**

| SequenceImpedanceBranch field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | structural | never copied; the rehashed mRID when the name is empty or clashes (B18) |
| `name` | `str` |  | copied | `create.mRID`, `create.name`; mRID = ln_ + name; a GUID name is rehashed (B18) |
| `substation` | `Optional[DistributionSubstation]` |  | structural | EquipmentContainer when there is no feeder |
| `feeder` | `Optional[DistributionFeeder]` |  | structural | EquipmentContainer |
| `in_service` | `bool` |  | structural | False raises: no CIM home |
| `buses` | `list[DistributionBus]` |  | structural | node1, node2; BaseVoltage from bus 1 (GDM requires equal bus voltages) |
| `length` | `Distance` |  | copied | `add_connectivity.length` |
| `phases` | `list[Phase]` |  | structural | ACLineSegmentPhase per conductor, in conductor order, balanced ABC included |
| `equipment` | `SequenceImpedanceBranchEquipment` |  | structural | WireConfiguration <lc>_wc (the template); its ampacity → the line's normal CurrentLimit |


**`GeometryBranch`**

| GeometryBranch field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | structural | never copied; the rehashed mRID when the name is empty or clashes (B18) |
| `name` | `str` |  | copied | `create.mRID`, `create.name`; mRID = ln_ + name; a GUID name is rehashed (B18) |
| `substation` | `Optional[DistributionSubstation]` |  | structural | EquipmentContainer when there is no feeder |
| `feeder` | `Optional[DistributionFeeder]` |  | structural | EquipmentContainer |
| `in_service` | `bool` |  | structural | False raises: no CIM home |
| `buses` | `list[DistributionBus]` |  | structural | node1, node2; BaseVoltage from bus 1 (GDM requires equal bus voltages) |
| `length` | `Distance` |  | copied | `add_connectivity.length` |
| `phases` | `list[Phase]` |  | structural | ACLineSegmentPhase per conductor, in conductor order, balanced ABC included |
| `equipment` | `GeometryBranchEquipment` |  | structural | WireConfiguration; the first conductor's ampacity and emergency_ampacity → the line's CurrentLimits (the DSS engine's rule) |


**`GeometrySwitch`**

| GeometrySwitch field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | structural | never copied; the rehashed mRID when the name is empty or clashes (B18) |
| `name` | `str` |  | copied | `create.mRID`, `create.name`; mRID = sw_ + name; a GUID name is rehashed (B18) |
| `substation` | `Optional[DistributionSubstation]` |  | structural | EquipmentContainer when there is no feeder |
| `feeder` | `Optional[DistributionFeeder]` |  | structural | EquipmentContainer |
| `in_service` | `bool` |  | structural | False raises: no CIM home |
| `buses` | `list[DistributionBus]` |  | structural | node1, node2; BaseVoltage from bus 1 (GDM requires equal bus voltages) |
| `length` | `Distance` |  | untranscribed | a switch has no length in CIM |
| `phases` | `list[Phase]` |  | structural | builder_phases: None for balanced ABC with one state for every phase |
| `is_closed` | `list[bool]` |  | structural | open = not closed; differing per phase → SwitchPhase open |
| `equipment` | `GeometryBranchEquipment` |  | structural | a GeometryBranchEquipment catalog: LoadBreakSwitch; ratedCurrent from its first conductor, as a geometry line's normal limit |


**`MatrixImpedanceBranchEquipment`**

| MatrixImpedanceBranchEquipment field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | structural | never copied; the rehashed mRID when the name is empty or clashes (B18) |
| `name` | `str` |  | copied | `create.mRID`, `create.name`; mRID = lc_ + name; a GUID name is rehashed (B18) |
| `construction` | `LineType` |  | untranscribed | no home on PerLengthImpedance |
| `r_matrix` | `ResistancePULength` |  | structural | PhaseImpedanceData r, lower triangle (row ≥ column); asymmetric raises |
| `x_matrix` | `ReactancePULength` |  | structural | PhaseImpedanceData x, lower triangle; asymmetric raises |
| `c_matrix` | `CapacitancePULength` |  | derived | PhaseImpedanceData b = 2πf·C (susceptance), lower triangle; asymmetric raises |
| `ampacity` | `Current` |  | structural | the normal CurrentLimit of every line using it |


**`SequenceImpedanceBranchEquipment`**

| SequenceImpedanceBranchEquipment field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | structural | never copied; the rehashed mRID when the name is empty or clashes (B18) |
| `name` | `str` |  | copied | `create.mRID`, `create.name`; mRID = lc_ + name; a GUID name is rehashed (B18) |
| `pos_seq_resistance` | `ResistancePULength` |  | copied | `add_electrical.r` |
| `zero_seq_resistance` | `ResistancePULength` |  | copied | `add_short_circuit.r0` |
| `pos_seq_reactance` | `ReactancePULength` |  | copied | `add_electrical.x` |
| `zero_seq_reactance` | `ReactancePULength` |  | copied | `add_short_circuit.x0` |
| `pos_seq_capacitance` | `CapacitancePULength` |  | derived | bch = 2πf·C1 (susceptance) |
| `zero_seq_capacitance` | `CapacitancePULength` |  | derived | b0ch = 2πf·C0 (susceptance) |
| `ampacity` | `Current` |  | structural | the normal CurrentLimit of every line using it |


**`GeometryBranchEquipment`**

| GeometryBranchEquipment field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | structural | never copied; the rehashed mRID when the name is empty or clashes (B18) |
| `name` | `str` |  | copied | `create.mRID`, `create.name`; mRID = spc_ / wc_ + name; a GUID name is rehashed (B18) |
| `conductors` | `list[BareConductorEquipment] | list[ConcentricCableEquipment]` |  | structural | WireSequenceConfiguration <wc>_<n> → the wire or cable info, in order |
| `horizontal_positions` | `Distance` |  | copied | `add_wire_position_row.xCoord`; XYConductorPosition <spc>_<n> |
| `vertical_positions` | `Distance` |  | copied | `add_wire_position_row.yCoord` |
| `insulation` | `WireInsulationType` |  | untranscribed | a permittivity; CIM has no permittivity, and no builder keyword sets an insulation material |


**`BareConductorEquipment`**

| BareConductorEquipment field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | structural | never copied; the rehashed mRID when the name is empty or clashes (B18) |
| `name` | `str` |  | copied | `create.mRID`, `create.name`; mRID = wire_ + name; a GUID name is rehashed (B18) |
| `conductor_diameter` | `Distance` |  | derived | radius = diameter / 2 |
| `conductor_gmr` | `Distance` |  | copied | `add_asset_info.gmr` |
| `ampacity` | `Current` |  | copied | `add_asset_info.ratedCurrent`; also a geometry line's normal CurrentLimit |
| `ac_resistance` | `ResistancePULength` |  | copied | `add_asset_info.rAC25`; no temperature given; rAC25 as DSS |
| `emergency_ampacity` | `Current` |  | structural | a geometry line's emergency CurrentLimit; the wire info's own limit set has no builder (finding) |
| `dc_resistance` | `ResistancePULength` |  | copied | `add_asset_info.rDC20` |


**`ConcentricCableEquipment`**

| ConcentricCableEquipment field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | structural | never copied; the rehashed mRID when the name is empty or clashes (B18) |
| `name` | `str` |  | copied | `create.mRID`, `create.name`; mRID = cn_ + name; a GUID name is rehashed (B18) |
| `strand_diameter` | `Distance` |  | derived | neutralStrandRadius = diameter / 2 |
| `conductor_diameter` | `Distance` |  | derived | radius = diameter / 2 |
| `cable_diameter` | `Distance` |  | copied | `add_asset_info.diameterOverJacket` |
| `insulation_thickness` | `Distance` |  | copied | `add_asset_info.insulationThickness` |
| `insulation_diameter` | `Distance` |  | copied | `add_asset_info.diameterOverInsulation` |
| `ampacity` | `Current` |  | copied | `add_asset_info.ratedCurrent`; also a geometry line's normal CurrentLimit |
| `conductor_gmr` | `Distance` |  | copied | `add_asset_info.gmr` |
| `strand_gmr` | `Distance` |  | copied | `add_asset_info.neutralStrandGmr` |
| `phase_ac_resistance` | `ResistancePULength` |  | copied | `add_asset_info.rAC25`; rAC25 as DSS |
| `strand_ac_resistance` | `ResistancePULength` |  | copied | `add_asset_info.neutralStrandRDC20`; CIM's only strand resistance, as DSS |
| `num_neutral_strands` | `int` |  | copied | `add_asset_info.neutralStrandCount` |
| `rated_voltage` | `Voltage` |  | copied | `add_asset_info.ratedVoltage` |
| `insulation` | `WireInsulationType` |  | untranscribed | a permittivity; no builder keyword sets an insulation material |


## 16. Loads (Phase 2)

`importer/load.py`; OPEN_DECISIONS 13.

- **Totals** on the EnergyConsumer `ld_<name>`: p, q summed over the phase loads (CIM load sign: consumption
  positive), each checked to be an active or reactive power unit (§4).
- **Phases:** balanced ABC with equal phases → `phases=None` (no children). Any other load gets a child per phase,
  and per-phase p, q (`Update` on the child) only when the phases differ. cimtables writes a delta load's children
  per branch (`ld_x_BC`, phase B), as CIM defines them; a 2-phase delta load is one branch, so its phase loads only
  sum, and a 3-phase delta load whose phases differ raises (GDM gives per-phase values, CIM per-branch ones).
- **Connection:** `SHUNT_CONNECTION` (§3). **Customers:** `num_customers`, the same on every phase, else raises.
- **Load model:** one LoadResponseCharacteristic, the same on every phase, else raises. Voltage exponents set (GDM sets
  both or neither) → `exp_<p>_<q>` (exponentModel); else the ZIP fractions: the shared `zip_constant_pq`/`_z`/`_i`
  rows, or `zip_<pZ>_<pI>_<pP>_<qZ>_<qI>_<qP>` for any other tuple. Each row is created the first time it is named.
  The shared rows are written by this spoke too, until the branch has `cimhub_core.load_response` (on `rc_1`).
- `min_voltage_pu`, `max_voltage_pu`, `cutoff_voltage_pu` are untranscribed (DSS's Vminpu likewise).

**Fail fast:** an unmapped connection; a load on N; the model or customer count differing by phase; an unequal
3-phase delta; a power in the wrong unit kind.

**Atoms** (`tests/atoms/load/loads.cimtbl`): balanced, unbalanced, single-phase B, triplex S1 S2, one leg S2,
delta BC, a general ZIP tuple, an exponential model.

**Real data:** every per-phase p, q is equal; every ZIP tuple is pure P, Z or I, except IEEE37's (I/Z fractions
with exponents 1 and 2 → `exp_1_2`, the DSS wave's row). SMART-DS writes each triplex customer as an S1 load and an
S2 load (935 each).

**`DistributionLoad`**

| DistributionLoad field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | structural | never copied; the rehashed mRID when the name is empty or clashes (B18) |
| `name` | `str` |  | copied | `create.mRID`, `create.name`; mRID = ld_ + name; a GUID name is rehashed (B18) |
| `substation` | `Optional[DistributionSubstation]` |  | structural | EquipmentContainer when there is no feeder |
| `feeder` | `Optional[DistributionFeeder]` |  | structural | EquipmentContainer |
| `in_service` | `bool` |  | structural | False raises: no CIM home |
| `bus` | `DistributionBus` |  | structural | node; BaseVoltage |
| `phases` | `list[Phase]` |  | structural | None for balanced ABC with equal phases, else an EnergyConsumerPhase each; N raises |
| `equipment` | `LoadEquipment` |  | structural | inline |


**`LoadEquipment`**

| LoadEquipment field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | untranscribed | inline: no CIM object of its own |
| `name` | `str` |  | untranscribed | inline: no CIM object of its own |
| `phase_loads` | `list[PhaseLoadEquipment]` |  | structural | one per phase: summed into the totals; per phase when they differ |
| `connection_type` | `ConnectionType` |  | mapped | SHUNT_CONNECTION → phaseConnection, grounded |


**`PhaseLoadEquipment`**

| PhaseLoadEquipment field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | untranscribed | inline: no CIM object of its own |
| `name` | `str` |  | untranscribed | inline: no CIM object of its own |
| `real_power` | `ActivePower` |  | copied | `add_ssh.p`; summed over phases; per phase when they differ |
| `reactive_power` | `ReactivePower` |  | copied | `add_ssh.q`; summed over phases; per phase when they differ |
| `z_real` | `float` |  | mapped | pConstantImpedance of the LoadResponseCharacteristic |
| `z_imag` | `float` |  | mapped | qConstantImpedance |
| `i_real` | `float` |  | mapped | pConstantCurrent |
| `i_imag` | `float` |  | mapped | qConstantCurrent |
| `p_real` | `float` |  | mapped | pConstantPower |
| `p_imag` | `float` |  | mapped | qConstantPower |
| `num_customers` | `Optional[Annotated[int, Gt(gt=0)]]` |  | copied | `add_connectivity.customerCount`; the same on every phase, else raises |
| `min_voltage_pu` | `float | None` |  | untranscribed | no home on LoadResponseCharacteristic (DSS Vminpu likewise) |
| `max_voltage_pu` | `float | None` |  | untranscribed | no home on LoadResponseCharacteristic |
| `cutoff_voltage_pu` | `float` |  | untranscribed | no home on LoadResponseCharacteristic |
| `active_power_voltage_exponent` | `float | None` |  | mapped | with the reactive exponent: an exp_<p>_<q> row (exponentModel), overriding the ZIP fractions |
| `reactive_power_voltage_exponent` | `float | None` |  | mapped | see active_power_voltage_exponent (GDM sets both or neither) |


## 17. Capacitors (Phase 2)

`importer/capacitor.py`.

- **LinearShuntCompensator** `cap_<name>`, `compensatorType=capacitor` (the builder requires it): nomQ = the phase
  capacitors' sum; nomU across one unit: line-to-line (`system_voltage`) for balanced ABC, the rating as written
  otherwise, which must be line-to-ground for a wye and line-to-line for a delta (the DSS wave's nomU); bPerSection =
  nomQ / (nomU² · maximumSections), computed by the builder; maximumSections = `num_banks`; normalSections =
  sections = `num_banks_on` when `state` is on, else 0 (G6).
- **Per-phase values** (kvar, banks, banks on) that differ raise; children carry no values.
- **Control:** RegulatingControl `cc_<capacitor>` on the capacitor's own Terminal `<cap>_T1` (GDM names no monitored
  element), `monitoredPhase` = the first phase, `discrete`, `enabled`; the compensator gets it with
  `controlEnabled=true` and `aVRDelay` = `delay_on`. One controller, or one per phase, all equal, else raises.

  | controller | mode | targetValue, targetDeadband (primary side, unitless in CIM) |
  |---|---|---|
  | Voltage | voltage | (on + off) / 2 × pt_ratio, \|off − on\| × pt_ratio, in V; ptRatio |
  | Current | currentFlow | × ct_ratio, in A; ctRatio |
  | ActivePower | activePower | in W |
  | ReactivePower | reactivePower | in var |
  | DailyTimed | | `PENDING`: needs a schedule (OPEN_DECISIONS 12) |

  Converting the setpoints to V, A, W or var is the spoke's one `.to()`: CIM's targets have no unit
  (`capacitor_targets`). `delay_off` and `dead_time` are untranscribed.
- `resistance`, `reactance` untranscribed.

**Fail fast:** per-phase values that differ; an ambiguous `state`; a single-phase rating that doesn't match the
connection; an unmapped connection; controllers that differ; a capacitor on N.

**Atoms** (`tests/atoms/capacitor/capacitors.cimtbl`): fixed 3-phase, single-phase, delta rated line-to-ground with 2
banks, switched off, and one of each controller. The own-terminal control writes by `Update` (U3 closed), so the
plan's `xfail` was not needed.

**Real data:** only the ditto decks have capacitors (6), all fixed, `state=[True]`.

**`DistributionCapacitor`**

| DistributionCapacitor field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | structural | never copied; the rehashed mRID when the name is empty or clashes (B18) |
| `name` | `str` |  | copied | `create.mRID`, `create.name`; mRID = cap_ + name; a GUID name is rehashed (B18) |
| `substation` | `Optional[DistributionSubstation]` |  | structural | EquipmentContainer when there is no feeder |
| `feeder` | `Optional[DistributionFeeder]` |  | structural | EquipmentContainer |
| `in_service` | `bool` |  | structural | False raises: no CIM home |
| `bus` | `DistributionBus` |  | structural | node; BaseVoltage |
| `phases` | `list[Phase]` |  | structural | None for balanced ABC, else a LinearShuntCompensatorPhase each; N raises |
| `controllers` | `list[CapacitorControllerBase]` |  | structural | one RegulatingControl cc_<name>; one controller, or one per phase, all equal |
| `equipment` | `CapacitorEquipment` |  | structural | inline |
| `state` | `list[bool]` |  | structural | one entry or one per phase, all equal (G6): sections = num_banks_on when on, else 0 |


**`CapacitorEquipment`**

| CapacitorEquipment field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | untranscribed | inline: no CIM object of its own |
| `name` | `str` |  | untranscribed | inline: no CIM object of its own |
| `phase_capacitors` | `list[PhaseCapacitorEquipment]` |  | structural | one per phase, equal; nomQ is their sum |
| `connection_type` | `ConnectionType` |  | mapped | SHUNT_CONNECTION → phaseConnection, grounded |
| `rated_voltage` | `Voltage` |  | derived | nomU: line-to-line for balanced ABC (system_voltage), else as written |
| `voltage_type` | `VoltageTypes` |  | structural | selects the system_voltage factor; must match the connection off ABC |


**`PhaseCapacitorEquipment`**

| PhaseCapacitorEquipment field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | untranscribed | inline: no CIM object of its own |
| `name` | `str` |  | untranscribed | inline: no CIM object of its own |
| `resistance` | `Resistance` |  | untranscribed | no home on LinearShuntCompensator |
| `reactance` | `Reactance` |  | untranscribed | no home on LinearShuntCompensator |
| `rated_reactive_power` | `ReactivePower` |  | copied | `add_electrical.nomQ`; summed over phases |
| `num_banks_on` | `int` |  | copied | `add_electrical.normalSections`, `add_ssh.sections`; 0 when state is off |
| `num_banks` | `int` |  | copied | `add_electrical.maximumSections` |


**`VoltageCapacitorController`**

| VoltageCapacitorController field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | untranscribed | inline: no CIM object of its own |
| `name` | `str` |  | untranscribed | inline; the control is named after its capacitor |
| `delay_on` | `Optional[Time]` |  | copied | `add_regulating_control.aVRDelay` |
| `delay_off` | `Optional[Time]` |  | untranscribed | CIM has one delay, aVRDelay |
| `dead_time` | `Optional[Time]` |  | untranscribed | no CIM home |
| `on_voltage` | `Voltage` |  | derived | targetValue = (on + off) / 2 × pt_ratio, in V |
| `off_voltage` | `Voltage` |  | derived | targetDeadband = |off − on| × pt_ratio, in V |
| `pt_ratio` | `float` |  | copied | `add_regulating_control.ptRatio`; also scales the targets |


**`CurrentCapacitorController`**

| CurrentCapacitorController field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | untranscribed | inline: no CIM object of its own |
| `name` | `str` |  | untranscribed | inline; the control is named after its capacitor |
| `delay_on` | `Optional[Time]` |  | copied | `add_regulating_control.aVRDelay` |
| `delay_off` | `Optional[Time]` |  | untranscribed | CIM has one delay, aVRDelay |
| `dead_time` | `Optional[Time]` |  | untranscribed | no CIM home |
| `on_current` | `Current` |  | derived | targetValue = (on + off) / 2 × ct_ratio, in A |
| `off_current` | `Current` |  | derived | targetDeadband = |off − on| × ct_ratio, in A |
| `ct_ratio` | `float` |  | copied | `add_regulating_control.ctRatio`; also scales the targets |


**`ActivePowerCapacitorController`**

| ActivePowerCapacitorController field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | untranscribed | inline: no CIM object of its own |
| `name` | `str` |  | untranscribed | inline; the control is named after its capacitor |
| `delay_on` | `Optional[Time]` |  | copied | `add_regulating_control.aVRDelay` |
| `delay_off` | `Optional[Time]` |  | untranscribed | CIM has one delay, aVRDelay |
| `dead_time` | `Optional[Time]` |  | untranscribed | no CIM home |
| `on_power` | `ActivePower` |  | derived | targetValue = (on + off) / 2, in W |
| `off_power` | `ActivePower` |  | derived | targetDeadband = |off − on|, in W |


**`ReactivePowerCapacitorController`**

| ReactivePowerCapacitorController field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | untranscribed | inline: no CIM object of its own |
| `name` | `str` |  | untranscribed | inline; the control is named after its capacitor |
| `delay_on` | `Optional[Time]` |  | copied | `add_regulating_control.aVRDelay` |
| `delay_off` | `Optional[Time]` |  | untranscribed | CIM has one delay, aVRDelay |
| `dead_time` | `Optional[Time]` |  | untranscribed | no CIM home |
| `on_power` | `ReactivePower` |  | derived | targetValue = (on + off) / 2, in VAr |
| `off_power` | `ReactivePower` |  | derived | targetDeadband = |off − on|, in VAr |


## 18. Transformers (Phase 3)

`importer/transformer.py`. The shape is the DSS wave's XfmrCode/Transformer goldens (D10, DSS-2), built through
CIM-Builder; the `TransformerTankEnd` method (`add_transformer_tank_end`) was added to
`TransformerTankConfigurationBuilder` for it (§14).

**Catalog** (`DistributionTransformerEquipment`, `PowerTransformerEquipment`) → TransformerTankConfiguration
`xc_<name>`, built once, unreferenced ones included:

- noLoadLoss, loadLoss = pct × winding 1's `rated_power` / 100, as active power in the rating's prefix (`loss`);
  `magnetizing_current_pct` → percentMagnetizingCurrent.
- **By tank end** (every catalog but a center tap): a TransformerTankEnd `<xc>_end_<n>` per winding with
  `connectionKind` STAR → `Y`, DELTA → `D` and no phases (instance end n is template end n), and a TransformerWinding
  `<xc>_wdg_<n>` on it (`FromTransformerEnd`).
- **By lug** (center tap, DSS-2): TransformerLugs H1 H2 X1 X3 X2 with `sequenceNumber` 1-5, the instance conductor
  each lands on (end 1: phase, N; end 2: s1, s2, N); windings `<xc>_wdg_1` H1→H2, `_2` X1→X2 (s1→N), `_3` X2→X3
  (N→s2), so the polarity of `bus.1.0` / `bus.0.2` is in the coils. A center tap must be three single-phase wye
  windings.
- **Winding values:** ratedU = line-to-line nameplate (`system_voltage`: a line-to-ground rating × √3, a center-tap
  half's × 2); baseU = the coil (`coil_voltage`: line-to-ground on a wye, line-to-line on a delta; ditto writes delta
  windings line-to-ground, so they are × √3); ratedS = `rated_power`, baseS = `rated_power` / `num_phases` (a center
  tap half: ratedS = half, baseS = the full kVA, as DSS); r = `resistance` in percent on the coil base.
- **Mesh** `<xc>_mesh_<i><j>` per coupling pair (`coupling_pairs`: 0-based if any index is 0, else 1-based), x =
  the reactance in percent on the From winding's base. GDM's reactances are on winding 1's kVA (DSS semantics), so a
  From winding rated otherwise raises.
- **`PowerTransformerEquipment`:** `vector_group` must equal what the windings make (`vector_group`: ANSI phasing,
  every wye grounded: `Dyn1`, `YNyn0`, `YNd1`, `Dd0`); `cooling_class` → CoolingInfo `cool_<name>` (B20), each
  instance tank's AssetDatasheet; `fluid_type` untranscribed.

**Instance** (`DistributionTransformer`) → PowerTransformer `xf_<name>`:

- a PowerTransformerEnd `<xf>_<n>` per bus with its Terminal `<xf>_T<n>`; a center tap's halves (`S1 N`, `N S2`, the
  same bus by GDM's own validation) are one end and one Terminal, `s1s2N`, connection `I`, grounded.
- **Wye neutrals (G8, user 2026-11-08):** as GDM writes them. A 3-phase STAR end is `Yn` when its phases list N,
  else `Y`; a single-phase STAR end is `Y`, with N added when the coil is written with one phase (`B` → `BN`);
  `grounded` = the winding's `is_grounded`. DELTA: `D`, not grounded (a grounded delta raises). A center tap's low
  side is grounded as its halves are (they must agree). ditto-made data imports ungrounded (§13 G8, §14).
- TransformerTank `<xf>_tank` on `xc_<equipment>`; for a center tap, a TransformerPhaseEnd `<xf>_<n>_<phase>` per
  conductor, `sequenceNumber` 1-5 matching the lugs. Ends by tank end need no phase ends.
- **Taps (G4, user 2026-11-08):** a winding off nominal gets a RatioTapChanger `<end>_tap` on its PowerTransformerEnd,
  with no control: ±`total_taps` / 2, stepVoltageIncrement = (max − min) / total_taps × 100 %, normalStep = step =
  (tap − 1) / increment, which must be a whole step; neutralU = the coil. The tap is the instance's
  `tap_positions` when set and off nominal, else the catalog winding's (ditto writes a DSS `taps=` there; GDM's
  validator fills the instance's with 1.0). Raises when both are off nominal and differ, when one winding's phases
  differ, or when a center tap half is off nominal.

**Fail fast:** open-delta, open-wye and zig-zag windings (no mapping yet); a grounded delta; center tap halves
grounded differently; a malformed center tap; coupling indices out of range; a From winding not rated winding 1's
kVA; a `vector_group` mismatch (connections and phasing; its neutral marks are the instance's N, not checked); the tap
cases above; `in_service=False`. Taps are read for the phase conductors only: GDM keeps one per listed phase, N
included.

**Atoms** (`tests/atoms/transformer/transformers.cimtbl`): `t_dy` (a `PowerTransformerEquipment`, Dyn1, ONAN, p5r's
75 kVA values; LV `Yn` grounded), `t3w` (Y-Y-D three-winding: HV `Y` ungrounded as ditto writes it, LV `Yn`
ungrounded, a catalog tap → step 2), `t_ln` (single-phase wye, grounded, `B` → `BN`, 1-based couplings, an instance
tap → step 4), `t_ll` (single-phase phase-to-phase delta), `t_ct` (center tap, grounded).

**Real data:** all 4 ditto decks and all 8 gdmloader systems import through Phase 3 (Phase 4 classes stripped).
SMART-DS p1rhs7: 503 transformers, 481 center taps (16 lug catalogs, 2,405 phase ends), and the substation's
catalog tap 1.03125 → step 5. ditto's regulators arrive as plain transformers with a catalog tap (IEEE13: 3,
IEEE123: 7, IEEE37: 2 RatioTapChangers, no control).

**Not the DSS goldens yet** (parity, §9): the DSS wave writes a 3-phase Transformer as balanced PowerTransformerEnds
with no tank and no template (`regulators_transformer.cimtbl`), and leaves plain-transformer taps untranscribed.

**`DistributionTransformer`**

| DistributionTransformer field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | structural | never copied; the rehashed mRID when the name is empty or clashes (B18) |
| `name` | `str` |  | copied | `create.mRID`, `create.name`; mRID = xf_ + name; a GUID name is rehashed (B18) |
| `substation` | `Optional[DistributionSubstation]` |  | structural | EquipmentContainer when there is no feeder |
| `feeder` | `Optional[DistributionFeeder]` |  | structural | EquipmentContainer |
| `in_service` | `bool` |  | structural | False raises: no CIM home |
| `buses` | `list[DistributionBus]` |  | structural | a PowerTransformerEnd per bus, node and BaseVoltage; a center tap's halves share end 2 |
| `winding_phases` | `list[list[Phase]]` |  | structural | the end's Terminal phases as written (a 3-phase wye listing N is Yn); a 1-phase wye coil gets its N; a center tap's halves must be S1 N and N S2 → s1s2N |
| `tap_positions` | `list[list[float]] | None` |  | structural | a RatioTapChanger <end>_tap when off nominal (G4); else the catalog winding's |
| `equipment` | `DistributionTransformerEquipment` |  | structural | TransformerTank <xf>_tank on TankConfiguration xc_<equipment> |


**`DistributionTransformerEquipment`**

| DistributionTransformerEquipment field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | structural | never copied; the rehashed mRID when the name is empty or clashes (B18) |
| `name` | `str` |  | copied | `create.mRID`, `create.name`; mRID = xc_ + name; a GUID name is rehashed (B18) |
| `mounting` | `TransformerMounting` |  | untranscribed | no CIM home |
| `pct_no_load_loss` | `float` |  | derived | noLoadLoss = pct × winding 1 rated_power / 100, in W |
| `pct_full_load_loss` | `float` |  | derived | loadLoss = pct × winding 1 rated_power / 100, in W |
| `windings` | `list[WindingEquipment]` |  | structural | a TankEnd and a TransformerWinding each; by lug for a center tap |
| `coupling_sequences` | `list[SequencePair]` |  | structural | the mesh pairs, 0- or 1-based (coupling_pairs) |
| `winding_reactances` | `list[Annotated[float, FieldInfo(annotation=NoneType, required=True, metadata=[Strict(strict=True), Ge(ge=0), Le(le=100)])]]` |  | copied | `add_mesh_impedance.x` (percent); on the From winding's base, which must be winding 1's kVA |
| `is_center_tapped` | `bool` |  | structural | selects the lug template (DSS-2) |
| `magnetizing_current_pct` | `float | None` |  | copied | `add_electrical.percentMagnetizingCurrent` (percent) |


**`PowerTransformerEquipment`**

| PowerTransformerEquipment field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | structural | never copied; the rehashed mRID when the name is empty or clashes (B18) |
| `name` | `str` |  | copied | `create.mRID`, `create.name`; mRID = xc_ + name; a GUID name is rehashed (B18) |
| `mounting` | `TransformerMounting` |  | untranscribed | no CIM home |
| `pct_no_load_loss` | `float` |  | derived | noLoadLoss = pct × winding 1 rated_power / 100, in W |
| `pct_full_load_loss` | `float` |  | derived | loadLoss = pct × winding 1 rated_power / 100, in W |
| `windings` | `list[WindingEquipment]` |  | structural | a TankEnd and a TransformerWinding each; by lug for a center tap |
| `coupling_sequences` | `list[SequencePair]` |  | structural | the mesh pairs, 0- or 1-based (coupling_pairs) |
| `winding_reactances` | `list[Annotated[float, FieldInfo(annotation=NoneType, required=True, metadata=[Strict(strict=True), Ge(ge=0), Le(le=100)])]]` |  | copied | `add_mesh_impedance.x` (percent); on the From winding's base, which must be winding 1's kVA |
| `is_center_tapped` | `bool` |  | structural | selects the lug template (DSS-2) |
| `magnetizing_current_pct` | `float | None` |  | copied | `add_electrical.percentMagnetizingCurrent` (percent) |
| `vector_group` | `str | None` |  | structural | connections and phasing checked against the windings (vector_group), neutral marks not; a mismatch raises |
| `cooling_class` | `str | None` |  | copied | `add_asset_info.typeOfCooling`; CoolingInfo cool_<equipment>, each tank's AssetDatasheet |
| `fluid_type` | `str | None` |  | untranscribed | no Specification/Medium builder |


**`WindingEquipment`**

| WindingEquipment field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | untranscribed | inline: no CIM object of its own |
| `name` | `str` |  | untranscribed | inline; the winding is <xc>_wdg_<n> |
| `resistance` | `float` |  | copied | `add_transformer_winding.r` (percent); on the winding's own base |
| `is_grounded` | `bool` |  | copied | `add_power_transformer_end.grounded`; each instance end of this winding; a grounded delta raises. Regulators: no AutoTransformerEnd keyword (B27), untranscribed |
| `rated_voltage` | `Voltage` |  | derived | ratedU line-to-line (system_voltage); baseU the coil (coil_voltage) |
| `voltage_type` | `VoltageTypes` |  | structural | selects the system_voltage and coil_voltage factors |
| `rated_power` | `ApparentPower` |  | copied | `add_transformer_winding.ratedS`; baseS = rated_power / num_phases; a center tap half: ratedS = rated_power / 2, baseS = rated_power |
| `num_phases` | `int` |  | structural | 1 or 3; selects the end connection and baseS |
| `connection_type` | `ConnectionType` |  | mapped | TANK_END_CONNECTION, end_connection; open and zig-zag raise |
| `tap_positions` | `list[float]` |  | structural | the instance's tap when the instance's are nominal (G4) |
| `total_taps` | `int` |  | structural | tap_step: highStep, lowStep, stepVoltageIncrement |
| `min_tap_pu` | `float` |  | structural | tap_step |
| `max_tap_pu` | `float` |  | structural | tap_step |

## 19. Regulators (Phase 3)

`importer/regulator.py`, after CIMTBL-Models `regulator_example.cimtbl` (OPEN_DECISIONS 7, DSS-13).

- **One single-phase regulator per regulated phase:** VoltageRegulator `vr_<name>` named `<name>` (one phase), or
  `vr_<name>_<phase>` named `<name>_<phase>` (a unit of a bank; its tap changer and control take the unit's name too,
  so each unit, which exports as its own GDM regulator, has a name of its own: EXPORT_MAPPING.md#regulators), with AutoTransformerEnds `<vr>_end1` (S, bus 1) and `<vr>_end2` (L, bus 2), Terminals
  `<vr>_T1`/`_T2`, phase `<phase>N` (a single-phase coil returns to N); `is_grounded` untranscribed until the end
  builder takes `grounded` (B27); baseU = the coil, ratedS = the through rating per phase. Lugs S (1, end 1),
  L (2, end 2), SL (3); the series winding `<vr>_wdg` S→SL tapped at L, ratedS = the buck/boost rating (through ×
  (max_tap − 1)). The catalog must be two wye windings with the same phases on both sides (a phase-to-phase regulator
  is not mapped yet).
- **TapChangerInfo** `tci_<equipment>` (B17): the catalog's tap range (±16, 0.625 %), through rating per phase,
  neutralU the coil; each tap changer's AssetDatasheet. The catalog is also built as a tank configuration (§18), as
  every catalog is. cim18v17 has no AutoTransformer configuration, so the two-winding stand-in impedance (winding r,
  coupling x) is untranscribed.
- **RatioTapChanger** `<vr>_tap` on the AutoTransformerEnd of `tapped_winding` (1-based; default 2, the L side):
  range and increment from `tap_step`, step from the instance's tap on that phase (else the catalog's), normalStep 0,
  neutralU the coil, `ltcFlag`, `controlEnabled`, ptRatio, ctRating = `ct_primary` (a plain float in A),
  initialDelay = `delay`.
- **TapChangerControl** `<vr>_ctrl` per phase (GDM requires one controller per phase, matched by
  `controlled_phase`): mode `voltage`, the Terminal of the end on `controlled_bus`, monitoredPhase; targetValue,
  targetDeadband, minLimitVoltage, maxLimitVoltage = the PT-secondary settings × pt_ratio, in V
  (`regulator_targets`, the same unit exception as `capacitor_targets`); lineDropR/X = setting × pt_ratio /
  ct_primary in ohm when `use_ldc`; reversible; `max_step` untranscribed.

**Fail fast:** `min_v_limit` above `max_v_limit` (GDM's own `example()` has 132 / 102 V); a `controlled_bus` that is
not a regulator bus (also in GDM's `example()`); a controller on an unregulated phase; a non-wye or mismatched
catalog; `tapped_winding` other than 1 or 2.

**Atoms** (`tests/atoms/regulator/regulators.cimtbl`): `r1` (one phase, line drop compensation, step 2), `rb` (a bank
of three, steps 1, 2, 0).

**Real data:** none. ditto converts regulators to plain transformers (§14), and no gdmloader system has one.

**Not the DSS goldens yet:** the DSS wave writes a regulator as one VoltageRegulator per Transformer (ABCN ends for a
gang), with the stand-in impedance as an end-to-end mesh and no lugs or winding.

**`DistributionRegulator`**

| DistributionRegulator field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | structural | never copied; the rehashed mRID when the name is empty or clashes (B18) |
| `name` | `str` |  | copied | `create.mRID`, `create.name`; mRID = vr_ + name; a GUID name is rehashed (B18) |
| `substation` | `Optional[DistributionSubstation]` |  | structural | EquipmentContainer when there is no feeder |
| `feeder` | `Optional[DistributionFeeder]` |  | structural | EquipmentContainer |
| `in_service` | `bool` |  | structural | False raises: no CIM home |
| `buses` | `list[DistributionBus]` |  | structural | end 1 (S) on bus 1, end 2 (L) on bus 2 |
| `winding_phases` | `list[list[Phase]]` |  | structural | one VoltageRegulator per phase, ends <phase>N; the same on both windings |
| `tap_positions` | `list[list[float]] | None` |  | structural | RatioTapChanger step on the tapped winding (tap_step); the catalog winding's when nominal |
| `equipment` | `DistributionTransformerEquipment` |  | structural | TapChangerInfo tci_<equipment>; two wye windings |
| `controllers` | `list[RegulatorController]` |  | structural | a TapChangerControl each, matched to its phase by controlled_phase |


**`RegulatorController`**

| RegulatorController field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | untranscribed | inline: no CIM object of its own |
| `name` | `str` |  | untranscribed | inline; the control is named after its regulator |
| `tapped_winding` | `Optional[int]` |  | structural | 1-based; the end the RatioTapChanger sits on (default 2, the L side) |
| `delay` | `Optional[Time]` |  | copied | `add_regulating_control.initialDelay` |
| `v_setpoint` | `Voltage` |  | derived | targetValue = v_setpoint × pt_ratio, in V |
| `min_v_limit` | `Voltage` |  | derived | minLimitVoltage = min_v_limit × pt_ratio; above max raises |
| `max_v_limit` | `Voltage` |  | derived | maxLimitVoltage = max_v_limit × pt_ratio |
| `pt_ratio` | `float` |  | copied | `add_regulating_control.ptRatio`; also scales the voltages |
| `use_ldc` | `bool` |  | copied | `add_regulating_control.lineDropCompensation` |
| `is_reversible` | `bool` |  | copied | `add_regulating_control.reversible` |
| `ldc_R` | `Optional[Voltage]` |  | derived | lineDropR = ldc_R × pt_ratio / ct_primary, in ohm |
| `ldc_X` | `Optional[Voltage]` |  | derived | lineDropX = ldc_X × pt_ratio / ct_primary, in ohm |
| `ct_primary` | `Optional[Current]` |  | copied | `add_regulating_control.ctRating` (A); a plain float in A (I2 exception); also the LDC ohm base |
| `max_step` | `int` |  | untranscribed | no CIM home |
| `bandwidth` | `Voltage` |  | derived | targetDeadband = bandwidth × pt_ratio, in V |
| `controlled_bus` | `DistributionBus` |  | structural | the Terminal of the end on it; not a regulator bus raises |
| `controlled_phase` | `Phase` |  | copied | `add_regulating_control.monitoredPhase`; also picks the regulator a per-phase controller controls |

## 20. DER (Phase 4)

`importer/der.py`, after the DSS wave's PVSystem and Storage goldens (`cimhub_opendss/tests/atoms/der/`).

- **PowerElectronicsConnection** `pv_<name>` / `storage_<name>` on the DER's bus: `ratedS` = the inverter's
  `rated_apparent_power`; `ratedU` = the equipment's `rated_voltage`, line-to-line (`system_voltage`: a split-phase
  0.12 kV rating → 0.24 kV, a 2.4018 kV phase rating → 4.16004 kV); the snapshot `p`, `q` in the load sign
  (`injection`: −active_power, −reactive_power, so generation and discharge are negative; a zero stays 0.0). Phases
  as `builder_phases` (none for ABC, G3). GDM names no connection kind for a DER, so `phaseConnection` is not written
  (the DSS goldens write Y or D from `conn`); `maxQ`, `minQ`, `maxIFault` have no GDM source.
- **PhotoVoltaicUnit** `<pec>_unit`: `maxP` = the panel's `rated_power` (`panel_power`). ditto writes that as an
  ActivePower in kVA (§14); an apparent unit is taken as the same active one (3.0 kVA → 3.0 kW) with a WARNING (user,
  2026-11-08). Irradiance, the panel R/X and `power_temp_curve` are untranscribed; no SolarPanelInfo slot fits a GDM
  field, so none is built.
- **BatteryUnit** `<pec>_unit`: `ratedE` = `rated_energy`; `maxP` = `rated_power`, `minP` = −`rated_power` (one rating
  both ways, as the DSS goldens write `kWrated`); charging and discharging efficiency in percent;
  `batteryState` from the sign of `active_power` (`battery_state`: discharging above zero, charging below, waiting at
  zero). `idling_efficiency` is untranscribed (`idlingP` is a power). GDM has no stored energy, so `storedE` is not
  written.
- **AssetInfo** (OPEN_DECISIONS 15-18, B20): the inverter is an InverterInfo `inv_<inverter>` on the connection's
  AssetDatasheet, a GenerationInverterInfo under a PV and a StorageInverterInfo under a battery, with
  `apparentPowerMaximum`; it is built the first time a DER names it, so DERs sharing an inverter share one. The battery
  equipment is a BatteryInfo `batt_<equipment>` (`ratedCapacity` = `rated_energy`) on the BatteryUnit's
  AssetDatasheet. GDM's default inverter name is empty: the mRID is then the rehashed uuid (B18) and no name is
  written. The inverter's ramp limits, cut-in/cut-out, efficiency and curve have no InverterInfo slot in the profile;
  whether the InverterInfo or PowerElectronicsUnit child classes hold them is a TODO (OPEN_DECISIONS, "the missing
  inverter and DER attributes").
- **Inverter controllers** stay `PENDING` (OPEN_DECISIONS 12): `function_block_control` has classes but no builder,
  so a system with one stops at the coverage check.

**Fail fast:** a DER on the neutral (`N` in its phases); an inverter shared by a PV and a battery (it would be two
InverterInfo classes at once); a power in the wrong quantity (§4), except the panel's kVA above.

**p5r** (the only sample with DER): 2 PVs at 2.5 kW on 2.5 kVA inverters, 480 V; both panels rated in kVA, so 2
warnings; their irradiance time series are dropped (§8, T2).

**`DistributionSolar`**

| DistributionSolar field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | structural | never copied; the rehashed mRID when the name is empty or clashes (B18) |
| `name` | `str` |  | copied | `create.mRID`, `create.name`; mRID = pv_ + name; a GUID name is rehashed (B18) |
| `substation` | `Optional[DistributionSubstation]` |  | structural | EquipmentContainer when there is no feeder |
| `feeder` | `Optional[DistributionFeeder]` |  | structural | EquipmentContainer |
| `in_service` | `bool` |  | structural | False raises: no CIM home |
| `bus` | `DistributionBus` |  | structural | the Terminal's ConnectivityNode; BaseVoltage |
| `phases` | `list[Phase]` |  | structural | PowerElectronicsConnectionPhase children; none for ABC (G3); N raises |
| `irradiance` | `Irradiance` |  | copied | `add_ssh.irradiance`: PhotoVoltaicUnit.irradiance (B16b); an irradiance series stays dropped (T2) |
| `active_power` | `ActivePower` |  | derived | PowerElectronicsConnection p = -active_power (injection) |
| `reactive_power` | `ReactivePower` |  | derived | PowerElectronicsConnection q = -reactive_power (injection) |
| `controller` | `InverterController | None` |  | structural | an InverterController is PENDING (OPEN_DECISIONS 12) |
| `inverter` | `InverterEquipment` |  | structural | ratedS; InverterInfo inv_<inverter> on the AssetDatasheet |
| `equipment` | `SolarEquipment` |  | structural | ratedU; PhotoVoltaicUnit <pec>_unit |


**`DistributionBattery`**

| DistributionBattery field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | structural | never copied; the rehashed mRID when the name is empty or clashes (B18) |
| `name` | `str` |  | copied | `create.mRID`, `create.name`; mRID = storage_ + name; a GUID name is rehashed (B18) |
| `substation` | `Optional[DistributionSubstation]` |  | structural | EquipmentContainer when there is no feeder |
| `feeder` | `Optional[DistributionFeeder]` |  | structural | EquipmentContainer |
| `in_service` | `bool` |  | structural | False raises: no CIM home |
| `bus` | `DistributionBus` |  | structural | the Terminal's ConnectivityNode; BaseVoltage |
| `phases` | `list[Phase]` |  | structural | PowerElectronicsConnectionPhase children; none for ABC (G3); N raises |
| `active_power` | `ActivePower` |  | derived | PowerElectronicsConnection p = -active_power (injection); BatteryUnit batteryState from its sign (battery_state) |
| `reactive_power` | `ReactivePower` |  | derived | PowerElectronicsConnection q = -reactive_power (injection) |
| `controller` | `InverterController | None` |  | structural | an InverterController is PENDING (OPEN_DECISIONS 12) |
| `inverter` | `InverterEquipment` |  | structural | ratedS; InverterInfo inv_<inverter> on the AssetDatasheet |
| `equipment` | `BatteryEquipment` |  | structural | ratedU; BatteryUnit <pec>_unit |


**`SolarEquipment`**

| SolarEquipment field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | untranscribed | inline: no CIM object of its own |
| `name` | `str` |  | untranscribed | inline; the unit is named after its DER |
| `rated_power` | `ActivePower` |  | copied | `add_electrical.maxP`; PhotoVoltaicUnit; a kVA unit (ditto) is taken as kW with a WARNING (panel_power) |
| `power_temp_curve` | `Curve | None` |  | untranscribed | until the Curve builder (B12, OPEN_DECISIONS 16) |
| `resistance` | `float` |  | untranscribed | no CIM home (no PowerElectronicsConnection impedance) |
| `reactance` | `float` |  | untranscribed | no CIM home (no PowerElectronicsConnection impedance) |
| `rated_voltage` | `Voltage` |  | derived | PowerElectronicsConnection ratedU, line-to-line (system_voltage) |
| `voltage_type` | `VoltageTypes` |  | structural | how rated_voltage becomes line-to-line |


**`BatteryEquipment`**

| BatteryEquipment field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | structural | never copied; the rehashed mRID when the name is empty or clashes (B18) |
| `name` | `str` |  | copied | `create.mRID`, `create.name`; mRID = batt_ + name; a GUID name is rehashed (B18) |
| `rated_energy` | `EnergyDC` |  | copied | `add_electrical.ratedE`, `add_asset_info.ratedCapacity`; BatteryUnit ratedE; BatteryInfo batt_<equipment> ratedCapacity |
| `rated_power` | `ActivePower` |  | derived | BatteryUnit maxP = rated_power, minP = -rated_power (one rating both ways) |
| `charging_efficiency` | `float` |  | copied | `add_electrical.chargingEfficiency` (percent) |
| `discharging_efficiency` | `float` |  | copied | `add_electrical.dischargingEfficiency` (percent) |
| `idling_efficiency` | `float` |  | untranscribed | no CIM home: BatteryUnit idlingP is a power |
| `rated_voltage` | `Voltage` |  | derived | PowerElectronicsConnection ratedU, line-to-line (system_voltage) |
| `voltage_type` | `VoltageTypes` |  | structural | how rated_voltage becomes line-to-line |


**`InverterEquipment`**

| InverterEquipment field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | structural | never copied; the rehashed mRID when the name is empty or clashes (B18) |
| `name` | `str` |  | copied | `create.mRID`, `create.name`; mRID = inv_ + name; a GUID name is rehashed (B18) |
| `rated_apparent_power` | `ApparentPower` |  | copied | `add_electrical.ratedS`, `add_asset_info.apparentPowerMaximum`; PowerElectronicsConnection ratedS; InverterInfo apparentPowerMaximum |
| `rise_limit` | `Optional[ActivePowerOverTime]` |  | untranscribed | no InverterInfo slot |
| `fall_limit` | `Optional[ActivePowerOverTime]` |  | untranscribed | no InverterInfo slot |
| `cutout_percent` | `float` |  | untranscribed | no InverterInfo slot |
| `cutin_percent` | `float` |  | untranscribed | no InverterInfo slot |
| `dc_to_ac_efficiency` | `float` |  | untranscribed | no InverterInfo slot |
| `eff_curve` | `Optional[Curve]` |  | untranscribed | until the Curve builder (B12, OPEN_DECISIONS 16) |


## 21. Reactors (Phase 4)

`importer/reactor.py`, after the DSS wave's series Reactor golden (`cimhub_opendss/tests/atoms/reactor/`;
OPEN_DECISIONS 17b).

- **SeriesCompensator** `rx_<name>` between `buses[0]` (Terminal 1) and `buses[1]` (Terminal 2), on bus 1's
  BaseVoltage (GDM requires both buses at one voltage): `r`, `x` = the ReactorEquipment's lumped values; `r0` = r,
  `x0` = x (no mutual coupling, as the DSS goldens write it). SeriesCompensator has no per-phase class, so a reactor of
  fewer than three phases writes its phases on both Terminals; balanced ABC writes none (G3).
- `length` is untranscribed (the impedance is lumped). SeriesReactorInfo has no r/x slot, so no AssetInfo is built.
- **Builder:** CIM-Builder had no SeriesCompensator builder. With the user's go-ahead (2026-11-08) this session added
  `SeriesCompensatorBuilder` (`add_connectivity` with Terminal phases, `add_electrical` r/x, `add_short_circuit`
  r0/x0); uncommitted there (§14).
- **No current limits:** GDM's reactor has no ampacity (the DSS goldens write `rx_<name>_limits`).

**`DistributionReactor`**

| DistributionReactor field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | structural | never copied; the rehashed mRID when the name is empty or clashes (B18) |
| `name` | `str` |  | copied | `create.mRID`, `create.name`; mRID = rx_ + name; a GUID name is rehashed (B18) |
| `substation` | `Optional[DistributionSubstation]` |  | structural | EquipmentContainer when there is no feeder |
| `feeder` | `Optional[DistributionFeeder]` |  | structural | EquipmentContainer |
| `in_service` | `bool` |  | structural | False raises: no CIM home |
| `buses` | `list[DistributionBus]` |  | structural | Terminal 1 on bus 1, Terminal 2 on bus 2; bus 1's BaseVoltage (GDM requires both at one voltage) |
| `length` | `Distance` |  | untranscribed | no CIM home: a reactor's r, x are lumped |
| `phases` | `list[Phase]` |  | structural | Terminal phases as written; none for ABC (G3) |
| `equipment` | `ReactorEquipment` |  | structural | r, x |


**`ReactorEquipment`**

| ReactorEquipment field | type | samples | kind | target |
|---|---|---|---|---|
| `uuid` | `UUID` |  | untranscribed | inline: no CIM object of its own |
| `name` | `str` |  | untranscribed | inline; no SeriesReactorInfo slot for r, x, so no AssetInfo |
| `resistance` | `Resistance` |  | copied | `add_electrical.r`, `add_short_circuit.r0`; r0 = r: no mutual coupling |
| `reactance` | `Reactance` |  | copied | `add_electrical.x`, `add_short_circuit.x0`; x0 = x: no mutual coupling |

