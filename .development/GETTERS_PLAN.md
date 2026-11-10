# Export getters

**Status:** started 2026-11-08 in a worktree, moved onto `rc_1` the same day once the DSS importer was done.
Design: skill `export-getters` (SKILL.md + reference.md). G1-G5 committed (230fd8a); G6a-G6d uncommitted.

**Decision change (user, 2026-11-08):** `REWRITE_PLAN.md` F1 said getters are built on demand, each landing with its
first consumer in the DSS wave. The getters started ahead of DSS S6. Each getter is still tested against
hand-computed numbers on the core shapes (and inline atoms), and the first real consumer (DSS S6, then the RAW
exporter) may ask for signature changes before anything is frozen.

## Scope

- Getters live in `cimhub_core/src/cimhub_core/getters/`, tests in `cimhub_core/tests/test_getters_*.py`; the
  design rules in the `export-getters` skill.
- A missing upstream feature goes to `.development/UPSTREAM_REQUESTS.md` (I9), not a local stand-in.

## Order

| # | getters | status |
|---|---|---|
| G1 | `get_line_sequence_impedance` steps 1-3 (lumped, sequence code × length, phase matrix reduced), `ImpedanceSource`, `SequenceImpedance` | **done 2026-11-08**, 17 tests |
| G2 | Kron reduction of neutral conductors in step 3: series Z by `derived/kron.py`, shunt b/g by the phase block (V_n = 0); s1/s2 still raise | **done 2026-11-08**, 24 getter + Kron tests (Kersting Example 4.1) |
| G3 | `get_line_sequence_impedance_per_length` (steps 2-3 per length), `get_line_phase_impedance_matrix` (`PhaseMatrix`, stored code; sequence code expanded only with `expand_sequence=True`) | **done 2026-11-08**, 31 getter tests |
| G4 | wide fan-out: `get_terminal_nodes`, `get_conductor_phases` (+ `get_terminal_phases`), `get_base_voltage`, `get_switch_state(which=)`, `get_current_limits` | **done 2026-11-08**, 37 tests |
| G5 | `get_spacing_xy` / `get_spacing_distances` (XYSpacing and ConductorDistanceSpacing), `get_line_conductor_xy` (`spacingYOffset`), `derived/spacing.py` | **done 2026-11-08**, 24 tests |
| G6a | `get_transformer_units`, `get_transformer_model` (`TransformerModel`: windings, mesh, core on one declared power base; five CIM forms) | **done 2026-11-08**, 23 tests |
| G6b | `get_tap_steps`/`get_tap_ratio`, `get_shunt_reactive_power`, `get_phase_loads`/`get_load_response`, `get_source`, `get_der_output` (+ `phase_power.device_power`) | **done 2026-11-08**, 46 tests |
| G6c | `get_regulating_control`, `get_tap_changer_control`, `get_equipment_control` (`getters/control.py`) | **done 2026-11-08**, 16 tests |
| G6d | `get_inverter_rating`, `get_inverter_unit`, `get_photovoltaic_unit`, `get_battery_unit`, `get_machine_rating`, `get_machine_impedance` (`getters/der.py`); `getters.required_qty` shared | **done 2026-11-08**, 15 tests |
| S6b | `get_wire_info`, `get_configuration_wires` (`getters/wire.py`), `get_asset_info_current_limits`, `get_phase_impedance_code`/`get_sequence_impedance_code`, `derived/capacitance.py` (`b_from_c`, `c_from_b`) | **done 2026-11-09** with the DSS S6b exporter (`cimhub_opendss/docs/EXPORT_MAPPING.md`) |
| S6c | `get_transformer_model`: a template Y and an instance Yn agree, and the instance's kind wins (T2); a BY_TANK_ENDS coil's phases follow its instance phase ends (T3); `derived/regulator.py` (`secondary_to_primary`, `primary_to_secondary`, `line_drop_ohms`, `line_drop_volts`) | **done 2026-11-09** with the DSS S6c exporter |
| S6e | `get_inverter_units` (`InverterUnitShare`: a shared PowerElectronicsConnection chopped by maxP share, each unit's own p or its share of the connection's; `getters/der.py`), `get_series_compensator` (`getters/series_compensator.py`, ohm) | **done 2026-11-09** with the DSS S6e exporter |
| S6f | `get_location_coordinates` (`LocationCoordinates`: a Location's points in order and each Terminal's point; `getters/location.py`) | **done 2026-11-09** with the DSS S6f exporter |
| S6g | `get_earth_resistivity` (`getters/earth.py`: `EarthData`, rho in ohm-m from the profile's Resistance), `get_reclose_delays` (`getters/switch_state.py`) | **done 2026-11-09** with the DSS S6g slice |
| RAW E0 | `get_node_voltage`, `get_voltage_limits` (`getters/voltage.py`, `NodeVoltage`, `VoltageLimits`; the limit-set and agreement helpers of `current_limits.py` shared); `export_slots.py` moved from the DSS exporter to core | **done 2026-11-09** with the RAW E0 exporter (`cimhub_raw/docs/EXPORT_MAPPING.md`), 6 tests |
| RAW E1 | `get_limits_by_type` (`getters/limits_by_type.py`: limits of one class keyed by `OperationalLimitType`); `get_shunt_admittance` (`getters/shunt.py`, `ShuntAdmittance`: g, b of the sections in service, S or pu); `get_series_compensator(unit, base_power=)` (pu); `required_qty(..., **bases)` | **done 2026-11-09** with the RAW E1 exporter, 6 tests (`test_getters_bus_branch_units.py`) |
| RAW E2 | none new. Found: `get_machine_rating` / `get_inverter_rating` require `ratedU`, which a RAW machine had none of | closed by RAW E3-1: the importer writes ratedU = BASKV; the getters keep the requirement |
| RAW E3 | **`get_unit_limits`** (`der.py`: a GeneratingUnit's `minOperatingP`/`maxOperatingP` or any PowerElectronicsUnit's `minP`/`maxP`, `(min, max)` in the caller's sign, as stored: a minimum above its maximum is returned, not raised, E3-5, user 2026-11-09; the Q limits keep the check); `get_transformer_model` reads a star `PowerTransformerEnd.x` (E3-2, user 2026-11-09: with no mesh, (i, j) x = xᵢ + xⱼ, the mesh r None; star + mesh raises; was G6b's raise); `get_tap_steps` / `get_tap_ratio`: a fixed tap (lowStep = highStep) has increment None and ratio 1 (E3-3) | done 2026-11-09, on `raw-exporter` |
| G7 | geometry → impedance engine (step 4), validated against `opendssdirect` | raises `NotImplementedError` today |

## G1 decisions (confirmed by the user 2026-11-08)

- **`unit`** is `'ohm'` (admittance in S) or `'pu'` (admittance in pu, one base as in `set_attr`). Anything else
  raises. Per-length units belong to G3's per-length getter.
- **`b`, `g` and the zero sequence are `None` when unset**, as `get_qty` returns them. `r` and `x` are required.
  Each spoke states its own rule for `None` (skill semantic rule 8: RAW/MATPOWER write `B` = 0.0, a set `g` raises
  in both; DSS writes `C1=0`/`C0=0` so the engine's 3.4/1.6 nF defaults never apply).
- **Matrix reduction** is the exact inverse of `derived/sequence.phase_matrix`: self/mutual are the means of the
  diagonal/off-diagonal, positive = Zs − Zm, zero = Zs + 2 Zm. Two conductors use the same formula; one conductor
  gives positive = Z11 and no zero sequence. A missing entry, or b/g set on some entries only, raises.
- **Agreement check** runs only when both sources are within `derive` (the default `LUMPED` never reads the code).
  `DISAGREEMENT_REL_TOL = 1e-6`, relative only, so a lumped 0 against a tiny derived b raises. The tolerance is
  reference.md §3's open question.
- `base_power` is ignored for `'ohm'`.

## G3 open point

- **Capacitance.** GLM (`c11` …, nF/mile) and DSS (`C1`/`C0`, `cmatrix`, nF per length) want capacitance; CIM
  and the getters give susceptance. C = b / (2πf) needs a frequency, either the code's `calculatedFrequency` or
  `network.base_frequency` (semantic rule 7). **Closed 2026-11-09 (DSS S6b, plan E5):** f =
  `network.base_frequency`; the DSS spoke raises on a code whose `calculatedFrequency` differs.
  `derived/capacitance.c_from_b` (b in nS, f in Hz -> C in nF).

## G4 decisions and open points

- **Nodes:** `get_terminal_nodes(equipment, *, topological=False)`. A FeederModel's terminals have only
  ConnectivityNodes, a BusBranchModel's only TopologicalNodes; the caller names which, no fallback.
- **Phases** are `Terminal.phases` (the canonical PhaseCode cimtables writes; blank is balanced ABC, U10). A line
  orders them by `ACLineSegmentPhase.sequenceNumber`, and its children must be its terminals' set. Every terminal of
  the equipment must agree, so a transformer raises: read each end's terminal with `get_terminal_phases`. The line
  impedance getters now take their conductor order from `get_conductor_phases`.
- **Base voltage:** CIM's rule, `form` required ('LL' as stored, 'LN' = LL/√3). A ConnectivityNode or
  ConductingEquipment inside a VoltageLevel takes `VoltageLevel.BaseVoltage` (its own disregarded); elsewhere its own
  (`ConnectivityNode.BaseVoltage` is new in cim18v17 for nodes outside a VoltageLevel; the DSS importer writes it,
  the core shapes don't). TopologicalNode and TransformerEnd: their own.
- **Switch state:** `True` = open; `which` required.
- **Current limits:** every set on the equipment and its terminals; kind by `OperationalLimitType.durationKind`,
  value by `CurrentLimit.normalValue`; limits of one kind and season must agree (`math.isclose`).
- **Seasons** (user, 2026-11-08: wanted for CYME and others): `OperationalLimitType.season` (GridAPPS-D extension).
  `season=None` reads the all-year limits; a season reads its own, per kind falling back to the all-year one. DSS
  `Seasons`/`Ratings` index a SeasonDayTypeSchedule and are not imported.
- **Open:** a split-phase leg's 'LN' raises (120 V is not 240/√3).

## G5 decisions and open points

- Rewritten from CIMHub_2_0 `transformations/lines` (cimhub_2026, `WireSpacingInfo`): its 0.0 default coordinate,
  10 m default height, logged fallbacks and `PhaseToPhaseSpacing` builder are gone. Getters read, `derived/` computes.
- Both getters take the spacing (the exporter's template), key conductors by sequence number (matching
  `ACLineSegmentPhase.sequenceNumber`), and read either form. `height=` from the first sketch is dropped: CIM requires
  a height per position, and a missing one raises.
- `ConductorDistance` is read by the CIM attributes `sequenceNumber1/2` + `conductorKind1/2` (kind `earth` = a
  height). Rows with only the GridAPPS-D `fromPhase`/`toPhase` raise.
- XY from distances: first conductor at x = 0 (CIM's frame origin is the structure centre line; DSS and GLM use only
  relative x), mirror images to the right, every stored distance checked against the result.
- `get_spacing_distances` returns pairwise distances only (they do not depend on the origin). For a
  ConductorDistanceSpacing they are the stored values and every pair is needed; XY positions need only enough pairs
  to place each conductor.
- **Heights are per line** (user, 2026-11-08): `ACLineSegment.spacingYOffset` (cim101 draft) is the height of the
  spacing's origin, which may be the pole top or crossarm centre, so one spacing serves any pole height.
  `get_line_conductor_xy(line)` = spacing y + offset; unset offset = origin at ground (the CIM XYSpacing default). A
  ConductorDistanceSpacing's earth distances are heights above ground; an offset on its line raises. The line's
  spacing is `ACLineSegment.WireSpacing` or `WireConfiguration.WireSpacing`, and both set must be the same one.
  DSS `h=` and GLM `distance_AE` are therefore per line: one native spacing per (spacing, offset).
- **Open:** `DISTANCE_REL_TOL = 1e-4` (GLM writes 6 digits).

## G6a decisions and open points

- **User, 2026-11-08:** one normalized model for every CIM form; one result per transformer unit (a
  `TransformerTank`, a `PowerTransformer` without tanks, an `AutoTransformer`); the caller declares the power base.
- Forms (`TransformerForm`): BY_ENDS, AUTO, BY_PHASE_ENDS (tank windings between instance `TransformerPhaseEnd`s,
  matched to the `PowerTransformerEnd` by `endNumber`), BY_TANK_ENDS (template end n = instance end n), BY_LUGS
  (a lug's `sequenceNumber` names the instance phase end on the ends' Terminals).
- Winding order: end number, then a coil's lowest phase-end `sequenceNumber` (H, X1-X2, X2-X3).
- **Base:** every percent/pu is on `base_power` (e.g. `network.base_power`), else winding 1's `ratedS`, the base DSS
  (`%R`, `XHL`, `%noloadloss`, `%imag`) and GLM put everything on. The stored percent is read on its From winding with
  `get_qty`, then moved by the power ratio only (UPSTREAM_REQUESTS U12). A winding's `baseS` is per phase, so its
  whole-unit power is winding 1's `ratedS` × baseS / baseS₁. `'ohm'` is not offered: ohms differ by form (a coil's on a
  TransformerWinding, the wye equivalent on a PowerTransformerEnd) and no consumer wants them.
- **Core:** BY_ENDS reads `g`/`b` of the one end that holds them; tank forms read `noLoadLoss` (g = P/S) and
  `percentMagnetizingCurrent` (b, on winding 1's rating) from the tank or its configuration, and both setting one
  raises. `TransformerCore.g/b` set raises (not read). AUTO has no core.
- Connection and grounding: the instance end's; on BY_TANK_ENDS also the TankEnd's, and two that are set must agree.
  `TransformerWinding.connection` (GridAPPS-D) is not read; a coil's phases show phase-to-phase vs phase-to-neutral.
- Raise: a PowerTransformer with tanks passed whole, a tank with both its own windings and a configuration, a bank
  of template tanks (which phases each serves is open until the multi-can form is settled), a coil across two ends,
  an unset mesh `x`, an unrated winding 1, and (since RAW E3-2) a star `PowerTransformerEnd.x` beside a mesh impedance; a star x alone is read (CGMES's form).
- **Open:** mesh `r0`/`x0` and zero-sequence data are not read; `percentImpedance`/`loadLoss` (test summaries) are
  not checked against the mesh; template banks.

## G6b decisions and open points

- **Tap changer:** positions as stored; ratio = 1 + (position − neutralStep) × stepVoltageIncrement / 100 at
  `which` = `'actual'` (step) | `'normal'` | `'low'` | `'high'`, no default (as switch state). No default
  increment (the old 0.625 % fallback is gone). RatioTapChanger only; PhaseTapChanger not read.
- **Shunt:** Q = bPerSection × V² × sections; `sections` (`'actual'`/`'normal'`/`'maximum'`) and `voltage`
  (`'nominal'` = nomU, or `'base'` = the BaseVoltage, LN for one phase conductor else LL) are both required. `nomQ`
  is not read; a set `gPerSection` or per-phase `bPerSection` raises (no producer writes one; the CIM per-phase
  voltage is wye LN / delta LL, decide with the first one). The old nomU → BaseVoltage fallback is gone.
- **Per phase** (loads and DER, `phase_power.device_power`): the `<Class>Phase` children's p/q when every child has
  them (they must be the conductors and sum to the total, rel 1e-6), else the total split evenly over the phase
  conductors; the neutral carries none. `split` says which. Children without values (cimtables' U10 per-phase rows)
  count as none.
- **Load response:** ZIP fractions as stored, each three summing to 1 (rel 1e-6); or exponents. No response raises.
- **Source:** voltageMagnitude and nominalVoltage required, `magnitude_pu` on nominalVoltage; `angle_unit` required;
  r/x/r0/x0/r2/x2 in ohm or pu on BaseVoltage + `base_power`; unset is None.
- **DER sign:** `sign='load'` (CIM) or `'generation'` (negated, a zero stays 0.0); RotatingMachine phases hold no p/q,
  so a machine's total is split; a machine has no connection (U8).

## G6c decisions and open points

- **Targets:** `targetValue`, `targetDeadband`, the allowed min/max and the reverse target/band are plain floats in
  primary units of the mode (V, A, W, VAr) × `targetValueUnitMultiplier`; returned in the caller's `unit` (default
  the mode's SI unit) through the CIMUnit classes, never a local factor. powerFactor, timeScheduled, admittance and
  temperature are returned as stored (`unit` None); a unit or multiplier for them raises.
- **Both sides:** `ptRatio`/`ctRatio` on a TapChanger and its TapChangerControl must agree when both are set; the
  result carries the agreed value in `control.pt_ratio`/`ct_ratio`. The tap side adds `controlEnabled`, `ltcFlag`,
  `ctRating` (A, a plain float), the delays; the control side the line drop (primary ohm), reverse settings and
  voltage limits. A regulated device adds `controlEnabled` and, on a ShuntCompensator, `aVRDelay`.
- A control must monitor a Terminal and have a mode and a target; no control is `None` (tap: `control=None`).
- `monitoredPhase` is parsed to SinglePhaseKind tokens (`terminals.phase_code_tokens`). `ptPhase`/`ctPhase` and
  `TapChanger.ptPhase` are not read (the DSS importer writes none).

## G6d decisions and open points

- **Limit sign** (confirmed by the user 2026-11-09)**:** `maxQ`/`minQ` (inverter, SynchronousMachine) and `maxP`/`minP` (PowerElectronicsUnit) are written
  in the generation sign by every producer (DSS `kvarMax`/`-kvarMaxAbs`, `Pmpp`/0, `kWrated`/`-kWrated`; RAW
  QT/QB). Each pair comes back as `(min, max)` in the caller's `sign=`: as stored for `'generation'`, negated and
  swapped for `'load'`. A minimum above its maximum raises (a producer that wrote the load sign).
- **`idlingP`** is "real power consumed while idling", a loss: returned as stored in either sign.
- **Required:** `ratedS` and `ratedU` on an inverter and a machine; everything else unset is None. `ratedU` is line
  to line as stored; the DSS exporter undoes its importer's 1-phase wye x sqrt 3 (`injection.line_kv`).
- **One unit per connection** (`get_inverter_unit`); several units, a PowerElectronicsWindUnit and an
  AsynchronousMachine are not read until a producer writes one.
- **Machine impedance:** r, r0, x0, r2, x2 in ohm or pu on the machine's own ratedU/ratedS (`z_base`). cim18v17 has
  no positive-sequence machine reactance (RAW ZX, DSS Xd/Xdp/Xdpp): U13. The IEC 60909 short-circuit data (`ikk`,
  `mu`, star point earthing), voltage limits, AVR delays and capability curves are not read.
- `BatteryUnit.minimumE` is documented in CIM as a percent but typed RealEnergy; it is read as an energy (the type,
  as the DSS importer writes `%reserve x kWhrated`).
- Open: GeneratingUnit (`maxOperatingP`/`minOperatingP`, RAW PT/PB for a machine) comes with the bus-branch shapes.
