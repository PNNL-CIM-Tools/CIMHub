# DistOPF → `.cimtbl` mapping

**Status: DRAFT, awaiting approval (2026-11-13).** No mapper is written until the decisions in
[Decisions to approve](#decisions-to-approve) are settled. Contract: skill `cimtbl-import-contract`; shapes: skill
`cimtbl-shapes`; plan: `.development/REWRITE_PLAN.md` (F3+).

Samples come from the public DistOPF 1.1.0 cases (`distopf` wheel on PyPI, MIT): `ieee13`, `ieee34`,
`ieee123_30der`, `triplex_pv` and `epri_j1`. Three of them are committed under `tests/cases/` (see its README).

## The format in one paragraph

A DistOPF case is a directory of CSV files. Every electrical value is **per unit**: powers on `s_base` (VA per
phase; 1 MVA in every public case), impedances on the row's own `z_base` (ohm), which is `v_ln_base² / s_base` of
the branch's to-bus. Voltages are line-to-neutral (`v_ln_base`, V). Branches carry a 3×3 (or s1/s2 2×2) series
impedance matrix and no ratings, lengths, connections or winding voltages. Records reference buses by integer `id`
(`fb`, `tb`; generator, capacitor and battery `id` = their bus's id). Names are unique within each case.

## Artifact files and order

| native table (CSV) | artifact stem | shape(s) | depends on |
|---|---|---|---|
| master | `<case>` | `common.cimtbl`: Feeder `fdr_<case>`, BaseVoltages `bv_<kV>` (one per distinct `v_ln_base`) | — |
| `BranchRecord` (`branch_data.csv`) | `branch` | line by PerLengthImpedance, switch, series compensator; transformer and regulator per D3/D4 | master |
| `RegulatorRecord` (`reg_data.csv`) | `regulator` | voltage_regulator (D4) | branch |
| `BusRecord` (`bus_data.csv`) | `bus` | load (per-phase, D5), source | master |
| `CapacitorRecord` (`cap_data.csv`) | `capacitor` | shunt (per-phase, D8) | master |
| `GeneratorRecord` (`gen_data.csv`) | `generator` | inverter-based DER (D9) | master |
| `BatteryRecord` (`bat_data.csv`) | `battery` | inverter-based DER, `BatteryUnit` (D10) | generator (hybrid units) |
| `ScheduleRecord` (`schedules.csv`) | `schedule` | deferred (D11) | all |

ConnectivityNodes are generated from the `node`/`node1`/`node2` cells: the mapper resolves `fb`/`tb`/`id` to the
bus `name`, and the node's mRID is that name verbatim.

## Decisions to approve

Each has a recommendation. These are the modeling calls that decide every mapper below.

| # | question | recommendation | alternative |
|---|---|---|---|
| D1 | **Per unit → absolute.** cimtables has no `pu` path for powers, and branch `z_base` is the row's own (on a center-tap row 160 V while the to-bus is 120 V), so `(pu system)` cannot reproduce it. | **derived**, two named functions: `ohms(z_pu, z_base)` = z_pu × z_base (ohm, from the row's `z_base`); `watts(p_pu, s_base)` = p_pu × s_base (W, VAr, VA from the row's or bus's `s_base`). Formula in each table comment. | `(pu system)` with `BasePower = 3 × s_base` and `BaseVoltage = √3 × v_ln_base`: correct for lines and loads, wrong for center-tap rows; still no path for powers (an upstream ask to CIM-Tables). |
| D2 | **Line impedance home.** DistOPF gives a total-impedance matrix and no length (`length` is 0.0 where present). | One `PerLengthPhaseImpedance` per line, `lc_<line>`, data in `ohm/m`, and the segment's `length (m) = 1`; the table comment says "total impedance; DistOPF has no length". `length` untranscribed. No de-duplication of equal matrices. | `ACLineSegment.r/x` (scalars: loses the mutuals). |
| D3 | **Transformers** (`transformer`, `center_tap_xfmr`). The format has only a series impedance between two voltage levels: no kVA, no connection, no winding kV. | `transformer by balanced ends` with `ratedU` = √3 × the from- and to-bus `v_ln_base` (derived), `ratedS` = 3 × `s_base` (the per-unit base, written `# defaulted: DistOPF has no rating`), `connectionKind` Y/Y grounded (DistOPF's line-to-neutral model, `# defaulted`), mesh `r`/`x` from `r_aa`/`x_aa` via D1. Fail fast on unequal diagonals or nonzero off-diagonals. `center_tap_xfmr`: fail fast until the 1-phase template form is agreed. | Fail fast on every transformer until a template is designed. |
| D4 | **Regulators.** A regulator is a `transformer` branch plus a `reg_data` row with the same `fb`/`tb`, and taps differ by phase (IEEE 13: 9, 6, 9). | `voltage_regulator` shape, one `VoltageRegulator` per phase in `reg_data.phases` (`rc_<branch>_<phase>`), the branch's impedance as its mesh, `step` = `tap_<ph>` (copied), `stepVoltageIncrement (percent)` = 100 × (`ratio_max` − `ratio_min`) / `num_taps` (derived), `lowStep`/`highStep` = ∓`num_taps`/2, `neutralStep` 0; absent `ratio_min`/`ratio_max`/`num_taps` take DistOPF's defaults 0.9 / 1.1 / 32 (`# defaulted`). `ratio_<ph>` untranscribed (DistOPF derives it from the tap; the mapper raises if it disagrees). **No `TapChangerControl`** (DistOPF optimizes taps itself and has no settings), so the shape needs a no-control form. | Balanced `regulator` shape: only when all taps are equal. |
| D5 | **Loads.** Per-phase `pl_*`/`ql_*` on the bus record. | One `EnergyConsumer` per loaded bus (`ld_<bus>`), always with per-phase `EnergyConsumerPhase` rows (DistOPF has no balanced load), p/q via D1. `cvr_p`/`cvr_q` copied to an exponential `LoadResponseCharacteristic` `exp_<cvr_p>_<cvr_q>` (`exp_0.8_3` already in the core shape). Needs the per-phase load shape added to core (listed as not yet catalogued). | Balanced rows when all three phases are equal. |
| D6 | **Source.** `bus_type` SWING. | `EnergySource` `src_<bus>`, `voltageMagnitude (kV)` = `v_a` × √3 × `v_ln_base` (derived); raise if `v_a`, `v_b`, `v_c` differ. `v_*` on PQ buses: untranscribed (solver start values). | — |
| D7 | **Bus voltage limits** `v_min`/`v_max`. | Untranscribed: CIM hangs `VoltageLimit` on Equipment or Terminal, not ConnectivityNode. | `OperationalLimitSet` on the bus's load Terminal (only buses with equipment). |
| D8 | **Capacitors.** | `LinearShuntCompensator` `cap_<name>` with per-phase `LinearShuntCompensatorPhase` rows; `nomQ (kVAr)` derived via D1; `nomU (kV)` = √3 × `v_ln_base`; `bPerSection` = q × s_base / v_ln_base² (derived); `sections` 1. No control (none in the format). | — |
| D9 | **DER** (`gen_data`). No unit kind except `gen_shape` (`PV`, a schedule column) or the rare `type`. | `PowerElectronicsConnection` `pv_<name>` + `PhotoVoltaicUnit` `<pec>_unit` for every record; per-phase `PowerElectronicsConnectionPhase` p/q, negated (load sign, derived). `ratedS` = Σ `s_<ph>_max` × s_base (derived); `maxQ`/`minQ` = Σ per-phase limits; `±100` pu means unlimited and is untranscribed. `control_variable`: untranscribed (no network-profile home). `type=diesel` raises. | `SynchronousMachine` for `diesel`. |
| D10 | **Batteries** (`bat_data`, keyed by bus). Is `s_max`/`energy_capacity` per phase or three-phase? The format doesn't say. | Ask DistOPF's authors; until then fail fast on batteries. Proposed targets: `storage_<name>` with `BatteryUnit` `ratedE`, `minimumE` = `min_soc` × capacity, `storedE` = `start_soc` × capacity, efficiencies × 100 to percent (all derived); `annual_cycle_limit`, `max_soc`, `control_variable` untranscribed. A `pv+bess` bus shares one connection (the `hybrid_h1` form). | — |
| D11 | **Schedules** (`schedules.csv`, `*_loadshape.csv`; `load_shape`/`gen_shape` name a column). | Defer to a second pass that follows CIM-Builder's schedule builder (`cimbuilder.object_builder.schedule`, not yet pushed). Until then the schedule part is untranscribed and `load_shape`/`gen_shape` are untranscribed. | — |
| D12 | **Coordinates** `latitude`/`longitude`. IEEE cases hold local x/y (400, 200), not degrees. | `location` shape with `crs_local`, `POINT` per equipment at its bus; leave out where every value is 0.0. | Untranscribed. |
| D13 | **Switch class.** DistOPF has one `switch` type. | `LoadBreakSwitch` `sw_<name>`; `status` OPEN/open → `open`/`normalOpen` true, CLOSED/blank → false (blank `# defaulted`); the tiny closed-switch impedance is untranscribed. | `Breaker` (the old 2_0 converter). |
| D14 | **`reactor` branches** (9500 cases). | `series_compensator` shape, r/x via D1 (diagonal only, else raise). | — |
| D15 | **Format drift** (see Sweep). | Update the schema to DistOPF 1.1.0 (line shunts `b_<ph>`, `g_sh_*`, `b_sh_*`; `ratio_*`, `ratio_min/max`, `num_taps`; `gen_shape`; battery `p`/`q`; `s_<ph>` branch ratings) and make the reader **raise** on an unknown column or CSV file (I8); the deprecated `battery_data.csv` raises with DistOPF's own deprecation reason. | Keep warning and ignoring (silent data loss). |
| D16 | `has_gen`/`has_load`/`has_cap`, `bus_type` PQ, `primary_phase`. | Untranscribed; the mapper raises when a flag contradicts the tables (a `has_cap=True` bus with no capacitor). `primary_phase` selects the transformer's primary phase on a center-tap row (structural, with D3). | — |

## Identity

| record | mRID | name | notes |
|---|---|---|---|
| bus | ConnectivityNode = bus `name` verbatim (generated from node cells) | — | `id` is structural: it resolves `fb`/`tb` and device `id`s |
| line | `ln_<name>`; impedance `lc_<name>`, data identifiers `lc_<name>_<row><column>` | `name` | |
| switch | `sw_<name>` | `name` | |
| transformer | `xf_<name>`, ends `<xf>_<n>`, mesh `<xf>_mesh_12` | `name` | |
| regulator | `rc_<branch>_<phase>` | branch `name` | the branch row becomes the regulator, not a transformer |
| load / source | `ld_<bus>`, `src_<bus>` | bus `name` | one per bus |
| capacitor / DER / battery | `cap_<name>`, `pv_<name>`, `storage_<name>`, units `<pec>_unit` | record `name` | `name` is the device's own name (`pv_1051` in the 9500 cases, so `pv_pv_1051`: prefixes are never stripped); it equals the bus name in only 121 of 1,274 public records. `id` is the bus (structural) |

## Per-table classification (proposed)

Kinds follow D1–D16; "via D1" means the derived `ohms`/`watts` function. Once mappers exist these tables are
regenerated from `FIELDS` with `fields_table(..., fields=FIELDS)`, and `check_fields` keeps them complete.

### BusRecord

| field | samples | kind | target |
|---|---|---|---|
| `id` | `1`, `10` | structural | resolves branch `fb`/`tb` and device `id` to this bus's name |
| `name` | `sourcebus`, `675` | copied | the ConnectivityNode mRID (node cells), `ld_`/`src_` suffix |
| `pl_a`..`ql_c`, `pl_s1`..`ql_s1s2` | `0.485`, `0.0018` | derived | `EnergyConsumerPhase.p/q (W, VAr)` = value × `s_base` via D1, one row per nonzero phase |
| `bus_type` | `SWING`, `PQ` | structural | SWING makes the `EnergySource` (D6) |
| `v_a`, `v_b`, `v_c` | `1.0001`, `1.0` | derived | SWING: `EnergySource.voltageMagnitude`; else untranscribed (D6) |
| `v_ln_base` | `2401.78`, `66395.28` | derived | `BaseVoltage.nominalVoltage (kV)` = √3 × value / 1000 (`bv_<kV>`) |
| `s_base` | `1000000.0` | structural | the power base of D1 |
| `v_min`, `v_max` | `0.95`, `1.05` | untranscribed | D7 |
| `cvr_p`, `cvr_q` | `0.8`, `3.0` | copied | `LoadResponseCharacteristic.pVoltageExponent`/`qVoltageExponent` (D5) |
| `phases` | `abc`, `c` | mapped | which `EnergyConsumerPhase` rows exist |
| `primary_phase` | `a` | untranscribed | D16 (structural for center-tap secondaries) |
| `has_gen`, `has_load`, `has_cap` | `False`, `True` | untranscribed | D16, checked against the tables |
| `latitude`, `longitude` | `400.0`, `200.0` | structural | D12 |
| `load_shape` | `default` | untranscribed | D11 |

### BranchRecord

| field | samples | kind | target |
|---|---|---|---|
| `name` | `632633`, `xfm1` | copied | `IdentifiedObject.name`; mRID per Identity |
| `fb`, `tb` | `14`, `4` | structural | `node1`/`node2` = the buses' names |
| `from_name`, `to_name` | `secbus` | untranscribed | redundant with `fb`/`tb`; the mapper raises on a mismatch |
| `r_aa`..`x_cc` | `0.01235`, `0.0` | derived | line: `PhaseImpedanceData.r/x (ohm/m)` via D1, lower triangle over the line's phases; transformer/reactor: D3/D14 |
| `r_s1s1`..`x_s2s2` | `2.67`, `0.52` | derived | triplex line: `PhaseImpedanceData` (s1, s2) via D1 |
| `primary_phase` | `a`, `b` | structural | center-tap primary (D3, D16) |
| `branch_type` | `line`, `switch`, `transformer` | mapped | `BRANCH_TYPE`: line/overhead_line/triplex_line → line, switch, transformer, center_tap_xfmr, reactor; blank raises |
| `status` | `CLOSED`, `OPEN` | mapped | `Switch.open`/`normalOpen` (D13) |
| `s_base` | `1000000.0` | structural | D1 |
| `v_ln_base` | `2401.78` | derived | `BaseVoltage` of the segment (to-bus base) |
| `z_base` | `5.7685` | structural | the impedance base of D1, copied into the table comment |
| `phases` | `abc`, `cb`, `s1s2` | copied | `ACLineSegment` / switch `phases` (conductor order kept: `cb` stays CB) |
| `s_a_max`..`s_c_max` | `0.0` | untranscribed | per-phase thermal ratings; home `OperationalLimitSet` + `ApparentPowerLimit`, not mapped until a case sets one |
| `length` | `0.0` | untranscribed | D2 |

### RegulatorRecord, CapacitorRecord, GeneratorRecord, BatteryRecord

Per D4, D8, D9, D10. Their tables are filled once those decisions are settled, from the same `fields_table`
output (`tests/cases/` plus the sweep cases).

### ScheduleRecord

Deferred (D11).

## Sweep (reader only, 2026-11-13)

The seeded reader reads 24 of the 25 public cases. It warns and **drops** these columns and files (D15):

| dropped | cases |
|---|---|
| `gen_shape` | 22 |
| `ratio_a/b/c` (regulators) | 11 |
| line charging `b_a/b/c`, shunts `g_sh_*`, `b_sh_*` | epri_j1, ieee9500, ieee9500_wye, smartds_small_v2 |
| `ratio_min`, `ratio_max`, `num_taps` | epri_j1, ieee9500, ieee9500_wye, smartds_small_v2 |
| battery `p`, `q` | epri_j1, smartds_small_v2 |
| named schedule columns (`commercial`, `com_kw_19955_pu.p`, ...) | epri_j1, ieee33, smartds_small_v2 |
| branch `s_a/b/c` | ieee123_alternate |
| `battery_data.csv` (DistOPF's deprecated battery table) | 5 cases |
| `default_loadshape.csv`, `pv_loadshape.csv`, `case_metadata.json` | 8 cases |

Stops: `9500` (`gen_data.csv` line 101 holds `(None,)` cells, a source error; it stays a stop). Mapper-level
stops already visible: `4Bus-YY-Bal_dss` and `4Bus-YY-Bal_dss_batt` place a capacitor on bus `id` 0, which no bus
has (unresolved reference, raises).

## Reader/schema findings

- Fixed: the schema's fixed-decimal `precision` annotations (16 places; 6 for schedules) truncated values on
  write (`0.687429118` → `0.687429`). Removed, so floats are written in Python's shortest round-trip form, as
  DistOPF's pandas writer does. Read → write → read is now exact on the committed cases.
- The writer emits every schema column (empty triplex columns included) and `0` as `0.0`; DistOPF reads both.
  Not byte-identical; not a goal for this format.
- Integer slots read through `int(float(text))`, so `0.5` silently becomes `0`; boolean slots map any unknown
  text to False. Both should raise (I8); fixed with D15.
- Schema comments still describe the old CIM-constructing import (`EnergyConsumerPhase(...).p = pl_a × s_base`);
  rewritten to the `.cimtbl` column per field when the mappers land (`linkml-native-schema` rule 7).

## CIM 18 gaps

- Per-phase DER ratings and reactive limits (`s_<ph>_max`, `q_<ph>_max/min`): `PowerElectronicsConnectionPhase`
  has only p and q (summed onto the connection, D9).
- DER control mode (`control_variable`): no home in the network profile parts.
- Bus voltage limits on a ConnectivityNode (D7).

## Reference model and expected differences

`tests/cases/ieee13` is the reference model (tier 3). Known differences from a hand translation of IEEE 13: no
transformer ratings or connections (D3); regulators without controls (D4); line impedances as total, not
per-length, values (D2).
