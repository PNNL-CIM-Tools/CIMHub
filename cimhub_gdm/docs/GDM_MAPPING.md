# GDM → cim18v17 mapping rules

**Status:** Phase 0 draft, 2026-11-08, for user approval. Cross-cutting rules only. Each family adds its own section
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
| 3 | catalogs | `MatrixImpedanceBranchEquipment`, `SequenceImpedanceBranchEquipment`, `GeometryBranchEquipment`, `BareConductorEquipment`, `ConcentricCableEquipment`, `DistributionTransformerEquipment`, `PowerTransformerEquipment`, the regulator template (B17), `InverterEquipment` (AssetInfo, B20) | catalog |
| 4 | sources | `DistributionVoltageSource` (+ `VoltageSourceEquipment`, `PhaseVoltageSourceEquipment`) | instance + inline |
| 5 | branches | the 3 switch components, `MatrixImpedanceFuse`, `MatrixImpedanceRecloser`, the 3 line components, `DistributionTransformer`, `DistributionRegulator`, `DistributionReactor` (+ their switch equipment, controllers, `ReactorEquipment`) | instance + inline |
| 6 | shunts | `DistributionLoad`, `DistributionCapacitor` (+ load/capacitor equipment and capacitor controllers) | instance + inline |
| 7 | DER | `DistributionSolar`, `DistributionBattery` (+ `SolarEquipment`, `BatteryEquipment`, `InverterController` and settings) | instance + inline |

Inline classes are in `INLINE` and read through their parent. Classes with no CIM home are in `UNTRANSCRIBED` with a
reason: `RecloserControllerEquipment`, `TimeCurrentCurve`, `Curve` (until B12), `ThermalLimitSet` (no GDM field
references it). A coverage test fails when a GDM release adds a class that is in no list.

## 2. Identity

- **mRID** = `mrid(PREFIX, gdm.name)`, with the name as written. Prefixes come from the `cimtbl-translate` table: `sw_` `ln_`
  `lc_` `ld_` `cap_` `src_` `xf_` `xc_` `wire_` `cable_` `spc_` `wc_` `pv_` `storage_` `bv_` `fdr_` `sub_`; buses
  are bare. Child mRIDs follow its child table (`<xf>_<n>`, `<xc>_wdg_<n>`, `<lc>_<row><column>`, `<spc>_<n>`,
  `<wc>_<n>`, `<ln>_limits`). Missing prefixes reuse the DSS wave's (`zip_constant_pq`/`_z`/`_i`, `exp_<p>_<q>`).
- **GUID names.** ditto names many GDM objects with a GUID string (p5r: every `LoadEquipment`, `InverterEquipment`,
  `SolarEquipment`, `VoltageSourceEquipment`, `MatrixImpedanceSwitchEquipment` and `DistributionTransformerEquipment`,
  e.g. `372a4dea-63f2-4737-bc0f-5549c04b3d54`). `cimprofiles.identity` would take a GUID-shaped mRID verbatim as the
  object's identifier. So when the name is a GUID, the mRID is `rehash_mrid(cim_class, name)` with no prefix (B18;
  OPEN_DECISIONS 9). Only catalogs are affected, because inline objects take child mRIDs from their parent. `<guid>_1`
  (p5r phase loads) is free text, not a GUID.
- **Empty or clashing names** → `rehash_mrid(cim_class, str(gdm.uuid))` (OPEN_DECISIONS 10). Until B18 lands, a GUID
  name or a clash raises, naming the class and both uuids. In p5r, only inline objects have empty or repeated names.
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
| `SHUNT_CONNECTION` | `STAR` → `Yn` when grounded else `Y`; `DELTA` → `D`; `OPEN_DELTA`, `OPEN_STAR`, `ZIG_ZAG` raise (`PhaseShuntConnectionKind` has no home for them) | loads, capacitors |
| `WINDING_CONNECTION` | `STAR` → `Yn` / `Y` by `is_grounded`; `DELTA` → `D`; `OPEN_DELTA` → `oD`; `OPEN_STAR` → `oY`; `ZIG_ZAG` → `Zn` / `Z` by `is_grounded` | transformer windings |
| `VOLTAGE_TYPE` | `line-to-line` or `line-to-ground`; selects the `system_voltage` factor (§5) | buses, sources, windings, capacitors, DER |
| `BATTERY_STATE` | `charging`, `discharging`; `idling` → `waiting` | batteries |
| `CAPACITOR_CONTROL_MODE` | by controller class: Voltage → `voltage`, Current → `currentFlow`, ActivePower → `activePower`, ReactivePower → `reactivePower`; DailyTimed raises (OPEN_DECISIONS 12) | capacitor controls |
| `WIRE_INSULATION` | `XLPE` → `crosslinkedPolyethylene`, `EPR` → `ethylenePropyleneRubber`, `SILICONE_RUBBER` → `siliconRubber`, `PAPER` → `oilPaper`, `PE` → `highMolecularWeightPolyethylene`, `AIR` → `insulated = false` (no material), `PVC`, `TEFLON`, `MICA` → `other` | cables, geometry (**G5**: confirm) |

GDM's `WireInsulationType` values are relative permittivities (`XLPE = 2.3`). The code table keys on the member
name, not the value.

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
| `generation_p(p)` | −p | PV output and battery discharge (CIM load sign) |
| `coupling_pairs(equipment)` | GDM `SequencePair` indices → 1-based winding numbers | the examples and every gdmloader system are 0-based (center taps `0→1, 0→2, 1→2`); the GDM repo's p5r is 1-based (`1→2`). 0-based if any index is 0, 1-based if any index equals the winding count; otherwise (a single `1→2` on a 3-winding unit) raise |
| `losses(pct, rated_s)` | noLoadLoss = pct_no_load × S / 100; loadLoss = pct_full_load × S / 100 | p5r: 0.6 % and 1.74408 % of 75 kVA. 1.74408 = 2 × 0.87204 (the winding r), a consistency check the test asserts |
| `tap_step(tap_pu, total_taps, min_pu, max_pu)` | neutralStep = 0; highStep = +total_taps / 2; lowStep = −total_taps / 2; stepVoltageIncrement = (max − min) / total_taps × 100 %; step = (tap − 1) / ((max − min) / total_taps) | a tap position, never a ratio; 32 taps, 0.9-1.1 → ±16, 0.625 % |
| `regulator_targets(controller)` | targetValue = v_setpoint × pt_ratio; targetDeadband = bandwidth × pt_ratio | on the PT secondary basis |
| `ldc_ohm(v_setting, pt_ratio, ct_primary)` | R or X in ohm = v_setting × pt_ratio / ct_primary | GDM gives `ldc_R`/`ldc_X` in volts (the relay setting); CIM `lineDropR`/`lineDropX` are ohm |
| `capacitor_targets(controller)` | targetValue = (on + off) / 2; targetDeadband = off − on; × pt_ratio or ct_ratio | |

## 6. Per-phase values

GDM carries several values per phase where CIM has one per object:

| GDM | equal on every phase | differs by phase |
|---|---|---|
| load `phase_loads` p/q (OPEN_DECISIONS 13) | one EnergyConsumer, totals, **no** EnergyConsumerPhase (G3: `phases=None`) | totals plus EnergyConsumerPhase p/q. A standalone single-phase load and an s1/s2 triplex load always get phase children. SMART-DS writes each triplex customer as two loads, one on `S1` and one on `S2` (935 each in p1rhs7), so each is a single-phase load with one child |
| load ZIP coefficients | one LoadResponseCharacteristic | raise: CIM has one LRC per EnergyConsumer |
| switch `is_closed` | `Switch.open = not is_closed[0]` | SwitchPhase `open` per phase (`SwitchPhaseBuilder`) |
| capacitor `phase_capacitors` | LinearShuntCompensator totals | plus LinearShuntCompensatorPhase |
| capacitor `state` | `sections` from `num_banks_on` | **G6** |
| source `voltage`, `voltage_type`, r/x | EnergySource values | raise (EnergySourcePhase has only `phase`) |
| source `angle` | `voltageAngle` = phase A's angle; the others must be 120° apart | raise otherwise; p5r is A 0°, B 120°, C 240° (**G2**) |
| transformer `tap_positions` | 1.0 everywhere on a `DistributionTransformer`: nothing to write | **G4** |

## 7. BaseVoltage, containers, frequency

- **BaseVoltage:** one per distinct `base_voltage_mrid(system_voltage(bus.rated_voltage, bus.voltage_type,
  bus.phases))`. Every ConnectivityNode names its BaseVoltage (cim18v17 `ConnectivityNode.BaseVoltage`). Equipment
  takes the BaseVoltage of its (first) bus.
- **Containers** (OPEN_DECISIONS 1): `EquipmentContainer` = the component's `feeder`, else its `substation`, else the
  system Feeder `fdr_<system.name>`. Buses use the same rule for `ConnectivityNodeContainer`.
- **Frequency:** `FREQUENCY_HZ = 60`, written as the BaseFrequency (through `new_feeder_model`) and as
  `calculatedFrequency` on every PerLengthImpedance.

## 8. Time series

Dropped in the first pass (OPEN_DECISIONS 2). One `WARNING` lists every component with `system.has_time_series(c)`:
class, name, and each series' variable name, type and features. In p5r this is two loads × (`active_power` PMult,
`reactive_power` QMult) and two PV systems × `irradiance` PMult, all `use_actual=False` multipliers.

## 9. Shared CIM models with the DSS wave

GDM writes the CIM the DSS spoke writes for the same equipment, so a DSS deck and its ditto-made GDM system can be
compared (tier 4). Where the DSS wave decided a model, GDM follows it:

| topic | DSS decision | GDM |
|---|---|---|
| tank configuration | D10 | catalogs → `TransformerTankConfiguration`, a TankEnd per winding, no template phases |
| center tap | DSS-2 (lugs H1 H2 X1 X3 X2, additive polarity) | `is_center_tapped = True` |
| ZIP | DSS-7 (`zip_constant_pq`/`_z`/`_i`, `exp_<p>_<q>`) | pure Z, I or P loads reference the shared rows; exponents → `exp_` rows; any other tuple gets its own row |
| switch class | DSS-9 | by equipment class (OPEN_DECISIONS 14) |
| regulators | DSS-13 (VoltageRegulator + AutoTransformerEnds) | from the B17 template |
| line limits | S2 / S3a (`<ln>_limits`, normal + emergency CurrentLimit; wire ratings on the WireInfo's set) | `ampacity` on the line's set; conductor `ampacity`/`emergency_ampacity` on the wire info's set |

## 10. CIM 18 gaps

Untranscribed unless noted. Each is logged in `CIMTBL-Models/distribution/CIM18_GAPS.md` by its owner.

| GDM | why |
|---|---|
| bus `coordinate` (`Location` x, y, crs) | ConnectivityNode is not a PowerSystemResource (B14). In SMART-DS data, x/y are longitude/latitude with `crs = None`; the synthetic cases use (0, 0) |
| bus `voltagelimits` | OperationalLimitSet hangs on equipment or terminals, not on a ConnectivityNode |
| `in_service = False` (any class) | no CIM home for "modelled but out of service" on these classes; **raises** |
| fuse `delay`, `tcc_curve`; recloser controller | no `FuseCharacteristicCurve` / `RecloseSequence` in cim18v17 |
| switch-equipment r/x/c matrices, `construction`, `trip_circuit_count` | a switch has no impedance in CIM |
| `TransformerMounting`, PV irradiance, PV R/X, efficiencies | no home (some may land with B20) |
| DailyTimed capacitor control, inverter controllers | **raise** (OPEN_DECISIONS 12, still open) |
| curves | until B12 |

## 11. Fail fast (cross-cutting)

The importer raises on each of these, naming the class, the object and the field:
- a class that is `PENDING` or in no list, orphan inline equipment, supplemental attributes;
- an unmapped enum (the `lookup` message), an unknown unit spelling, or a power unit of the wrong kind (§4);
- a GUID or clashing name until B18 lands;
- per-phase values CIM can't hold (§6);
- ambiguous coupling indices (§5);
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
| line | `matrix_3ph`, `matrix_1ph`, `sequence_3ph`, `geometry_overhead`, `geometry_cable`, `limits` | catalogs once, ωC, lower triangle, geometry not matrices | B4-B6, B13 |
| load | `balanced_3ph`, `unbalanced_3ph`, `single_phase_b`, `triplex_s1s2`, `zip_z`, `zip_general`, `exponential` | decision 13, ZIP rows | B11 |
| capacitor | `fixed_3ph`, `per_phase`, `voltage_control` (golden `xfail` on U3) | sections, nomU LL, control targets | B10 |
| transformer | `single_phase`, `center_tap`, `dyn_3ph` (p5r's 75 kVA unit), `three_winding` | D10, DSS-2, percent r/x, losses, coupling indices | mesh mRID fix |
| regulator | `single_phase_ldc`, `bank` | B17 template, tap step, LDC ohms | B17 |
| der | `pv`, `battery` | sign, PEC + unit | |
| e2e | `reference` (Phase 5) | an IEEE13-like system end to end | all |

**Sweep** (not atoms, nothing committed): ditto converts each vendored public deck that it can read, and `to_cim`
must either import it or stop with a listed reason (a `PENDING` class or a §11 fail-fast). This is the GDM equivalent
of the DSS deck sweep. An opt-in second sweep runs the same check over the gdmloader systems (network, never in CI).
From Phase 5, the **DSS/GDM parity** test imports the same deck through the DSS spoke and
through ditto + `to_cim`, and compares the two models with `diff_models`. It is matched by topology, not mRID (tier 4,
root `tests/cross_format/`), with ditto's known losses (regulators, angle sign) as listed expected differences.

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
- **G4. Off-nominal taps on a plain transformer.** `DistributionTransformer.tap_positions` ≠ 1.0. *Recommendation:* a
  RatioTapChanger on that end with `step` from `tap_step` and no control. It raises until an atom covers it.
- **G5. `WIRE_INSULATION` mappings** (§3), especially PE, PAPER and the `other` group.
- **G6. Capacitor `state`** (`list[bool]`) vs `num_banks_on`. ditto writes a single entry (`[True]`) even for a
  3-phase bank, so `state` is either one entry for the whole bank or one per phase. Any other length raises.
  *Recommendation:* sections = `num_banks_on` where `state` is True and 0 where False, per phase when they differ.

## 14. Findings for other owners

| owner | finding |
|---|---|
| core | `cimtbl._samples` tests `value == []`, which is ambiguous for numpy arrays. So `fields_table`/`fields_stub` crash on GDM's matrix and coordinate quantities. Use an explicit emptiness check |
| GDM maintainers | the gdm-cases data at format 2.0.0 can't load on 2.4.1: the upgrade chain starts at 2.0.1, and relabelled files then fail `PhaseVoltageSourceEquipment` validation. `RegulatorController.example()` has min/max voltage limits swapped. `example()`s use `watt` for reactive power |
| CIM-Profiles | W, VA and VAr interconvert in the CIM unit registry (X2) |
| gdmloader (0.0.5) | Downloads are cached outside the working directory (nothing lands in the cwd). It pins `fsspec`/`gcsfs ~=2025.3.2`, so it runs as `uv run --with gdmloader`, not as a workspace dependency |
| infrasys | `System.list_parent_components` misses components held in a list (`VoltageSourceEquipment.sources`) and components nested in another component (a switch equipment's controller). So the orphan check walks the model fields itself (`gdm_to_cim._referenced_uuids`) |
| GDM (validation) | GDM already rejects a switch between buses of different line-to-ground voltage, and `conductor_phases` that don't cover exactly the switch phases, so the importer doesn't repeat those checks |
| ditto (0.1.8) | IEEE13_CDPSM fails (`TypeError: 'NoneType' object is not iterable`, `branches.py:187`); IEEE13_Assets fails (`'str' object cannot be interpreted as an integer`, in geometry); regulators (Transformer + RegControl) become plain `DistributionTransformer`s with no controller and `tap_positions=None`; phase angles step +120° (B leads A); `system.name` is `None`; `voltage_type` set as a `str`, not the enum (pydantic serialization warnings). The importer reads enums through `VoltageTypes(value)`, so both forms work |
